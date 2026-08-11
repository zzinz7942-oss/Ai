"""
hardware_bot.py
스마트폰 텔레그램 앱 - 집 본체 PC 실시간 연동 철물 자재 검색, 네이버 쇼핑 최저가 & 카카오내비 주소 연동 봇
- 밖에서 스마트폰 텔레그램으로 "자재명, 주소" 전송 시 실시간 수신 및 카카오내비 연동
- "OOO 최저가" 전송 시 네이버 쇼핑 API 가격낮은순(sort=asc) 상위 3개 최저가/몰이름/구매링크 답장
"""

import os
import re
import sys
import time
import urllib.parse
import threading
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# 절전 시간 설정 (총 2시간 = 7200초, 5분 전 사전 알림 = 300초 전)
SLEEP_TIMEOUT_SECONDS = 7200
WARN_BEFORE_SECONDS = 300
WARN_TIMEOUT_SECONDS = SLEEP_TIMEOUT_SECONDS - WARN_BEFORE_SECONDS  # 6900초 (1시간 55분)

# UTF-8 인코딩 강제 설정 (CMD 한글 깨짐 방지)
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUTF8"] = "1"

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

import requests

ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(ENV_PATH)

# ==============================================================================
# 🔑 [네이버 쇼핑 API 인증키 설정] (나중에 직접 입력 가능)
# ==============================================================================
NAVER_CLIENT_ID = ""
NAVER_CLIENT_SECRET = ""

# ==============================================================================
# 🛠️ [HARDWARE_DB] 철물 자재 품목 마스터 딕셔너리 (새 자재 추가 시 이곳에 입력)
# ==============================================================================
HARDWARE_DB = {
    "앙코르앵글": {
        "name": "앙코르 앵글 (Encore Angle)",
        "spec": "50x50x4T, 40x40x3T / 아연도금 고강도 철재",
        "usage": "선반 제작, 경량 스틸 구조물 조립, 건축 조인트 보강용",
        "search_kw": "앙코르앵글 조립식앵글"
    },
    "세파볼트": {
        "name": "세파 볼트 (Separator Bolt)",
        "spec": "F형, D형 / 100mm, 150mm, 200mm 콘크리트 거푸집용",
        "usage": "콘크리트 유로폼 간격 유지 및 벽체 두께 고정용",
        "search_kw": "세파볼트 유로폼자재"
    },
    "앙카볼트": {
        "name": "세트 앵커 볼트 (Set Anchor Bolt)",
        "spec": "M10 x 80mm, M12 x 100mm, M16 x 150mm",
        "usage": "콘크리트 바닥/벽면 구조물 고정 및 기계 세팅용",
        "search_kw": "세트앙카 앙카볼트"
    },
    "전선관": {
        "name": "주름관 전선관 (난연 CD관)",
        "spec": "16mm, 22mm, 28mm / 100m 롤 단위",
        "usage": "옥내 전선 배관 및 매립 전선 보호용",
        "search_kw": "난연CD관 전선관"
    },
    "PVC파이프": {
        "name": "PVC 배수관 파이프 (VG1 / VG2)",
        "spec": "50mm, 75mm, 100mm / 본당 길이 4m",
        "usage": "건축 배수관, 하수관 및 빗물관 설치용",
        "search_kw": "PVC배수관 파이프"
    },
    "C형강": {
        "name": "아연도 C형강 (C-Channel)",
        "spec": "100x50x20x2.3T, 125x50x20x3.2T / 본당 6m",
        "usage": "공장/창고 지붕 퍼린(Purlin), 하지 구조재",
        "search_kw": "C형강 구조용강관"
    },
    "아시바파이프": {
        "name": "단관비계 파이프 (아시바 파이프)",
        "spec": "외경 48.6mm x 2.3T / 길이 1m~6m",
        "usage": "건설 현장 가설 비계, 과수원 지주대, 펜스 설치",
        "search_kw": "단관비계 아시바파이프"
    },
    "석고보드": {
        "name": "일반 석고보드 (Gypsum Board)",
        "spec": "9.5T x 900 x 1800mm, 12.5T 방화/방수",
        "usage": "실내 내벽 칸막이, 천장 마감재",
        "search_kw": "석고보드 천장재"
    },
    "우레탄폼": {
        "name": "일회용 / 폼건용 충진 우레탄폼",
        "spec": "750ml 캔 / 단열 방수 일체형",
        "usage": "창틀, 문틀 틈새 단열 시공, 기밀 충진",
        "search_kw": "우레탄폼 충진재"
    },
    "콘크리트못": {
        "name": "고강도 콘크리트 전용 타격못",
        "spec": "25mm, 35mm, 50mm / 100개입 소박스",
        "usage": "콘크리트 벽면 가구, 전기 박스, 앵글 고정",
        "search_kw": "콘크리트못 타격못"
    }
}


def fetch_naver_lowest_prices(keyword: str) -> str:
    """네이버 쇼핑 API 호출 후 최저가(sort=asc) 상위 3개 품목 파싱"""
    client_id = NAVER_CLIENT_ID or os.getenv("NAVER_CLIENT_ID", "")
    client_secret = NAVER_CLIENT_SECRET or os.getenv("NAVER_CLIENT_SECRET", "")

    encoded_kw = urllib.parse.quote(keyword)
    web_fallback_url = f"https://search.shopping.naver.com/search/all?query={encoded_kw}&sort=price_asc"

    if not client_id or not client_secret:
        return f"""🏷️ <b>[{keyword} 네이버 쇼핑 최저가 검색]</b>

⚠️ <i>NAVER_CLIENT_ID / SECRET 이 설정되지 않았습니다.
아래 직접 링크를 누르시면 네이버 쇼핑 가격 낮은 순(최저가) 결과로 연결됩니다.</i>

🛒 <b>네이버 쇼핑 최저가 직통 보기</b>: <a href="{web_fallback_url}">쇼핑몰 가격비교 바로가기</a>"""

    url = f"https://openapi.naver.com/v1/search/shop.json?query={encoded_kw}&display=3&sort=asc"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("items", [])

            if not items:
                return f"🔍 '{keyword}' 키워드에 대한 네이버 쇼핑 상품을 찾지 못했습니다.\n🛒 <a href='{web_fallback_url}'>네이버 웹 검색 바로가기</a>"

            reply = f"🏷️ <b>[{keyword} 네이버 쇼핑 최저가 TOP 3]</b>\n\n"
            for idx, item in enumerate(items, 1):
                clean_title = re.sub(r'<[^>]+>', '', item.get("title", ""))
                price = int(item.get("lprice", 0))
                price_str = f"{price:,}원" if price > 0 else "가격 정보 없음"
                mall = item.get("mallName") or "네이버 쇼핑"
                link = item.get("link", web_fallback_url)

                reply += f"{idx}. <b>{clean_title}</b>\n"
                reply += f"   🏪 <b>쇼핑몰</b>: {mall}\n"
                reply += f"   💰 <b>최저가</b>: {price_str}\n"
                reply += f"   🛒 <b>구매링크</b>: <a href='{link}'>상품 보러가기</a>\n\n"

            reply += f"🔗 <a href='{web_fallback_url}'>네이버 쇼핑 전체 최저가 더보기</a>"
            return reply
        else:
            return f"⚠️ 네이버 API 오류 (HTTP {resp.status_code})\n🛒 <a href='{web_fallback_url}'>네이버 웹 최저가 보기</a>"
    except Exception as e:
        return f"⚠️ 최저가 조회 실패: {e}\n🛒 <a href='{web_fallback_url}'>네이버 웹 최저가 보기</a>"


def search_hardware_item(user_text: str) -> dict:
    """사용자가 입력한 텍스트에서 철물 품목 검색"""
    for key, data in HARDWARE_DB.items():
        if key in user_text or data["name"] in user_text:
            return data

    tokens = [t.strip() for t in user_text.replace(",", " ").split() if len(t.strip()) > 1]
    item_name = tokens[0] if tokens else user_text
    return {
        "name": f"{item_name} (커스텀 요청 품목)",
        "spec": "현장 수동 규격 확인 필요",
        "usage": "건축/설비 자재",
        "search_kw": item_name
    }


def extract_address(user_text: str) -> str:
    """메시지에서 주소 부분 추출"""
    parts = [p.strip() for p in user_text.split(",") if len(p.strip()) > 1]
    if len(parts) >= 2:
        return parts[1]

    words = user_text.split()
    for idx, w in enumerate(words):
        if any(k in w for k in ["시", "구", "군", "대로", "로", "길", "동", "리"]):
            return " ".join(words[idx:])

    return user_text


def format_telegram_reply(user_text: str) -> str:
    """수신된 메시지 분석 후 텔레그램 답장 HTML 텍스트 생성"""
    # 1. '최저가' 키워드 포함 메시지 처리
    if "최저가" in user_text:
        keyword = user_text.replace("최저가", "").replace("검색", "").strip()
        if not keyword:
            keyword = user_text
        return fetch_naver_lowest_prices(keyword)

    # 2. 기존 철물 자재 & 카카오내비 현장 배달 연동 처리
    item_info = search_hardware_item(user_text)
    address = extract_address(user_text)

    encoded_kw = urllib.parse.quote(item_info["search_kw"])
    encoded_addr = urllib.parse.quote(address)

    google_img_url = f"https://www.google.com/search?tbm=isch&q={encoded_kw}"

    kakaonavi_deeplink = f"kakaonavi://search?q={encoded_addr}"
    kakaomap_url = f"https://map.kakao.com/?q={encoded_addr}"
    navermap_url = f"https://map.naver.com/v5/search/{encoded_addr}"

    reply_html = f"""🛠️ <b>[철물 자재 & 현장 내비 연동 결과]</b>

📦 <b>품목명</b>: {item_info['name']}
📏 <b>규격/사양</b>: {item_info['spec']}
💡 <b>주요용도</b>: {item_info['usage']}
🖼️ <b>구글 이미지</b>: <a href="{google_img_url}">자재 실물 사진 보기</a>

----------------------------------------
📍 <b>배달 현장 주소</b>: {address}
🚗 <b>카카오내비 앱 실행</b>: <a href="{kakaonavi_deeplink}">kakaonavi:// 실행</a>
🗺️ <b>카카오맵 지도</b>: <a href="{kakaomap_url}">웹 지도 열기</a>
🧭 <b>네이버지도</b>: <a href="{navermap_url}">네이버지도 열기</a>
----------------------------------------
⏰ <i>실시간 연동 시각: {time.strftime('%Y-%m-%d %H:%M:%S')}</i>"""

    return reply_html


class TelegramHardwareBot:
    def __init__(self, bot_token: str):
        self.token = bot_token
        self.api_url = f"https://api.telegram.org/bot{self.token}"
        self.offset = 0
        self.warn_timer = None
        self.sleep_timer = None
        self.last_chat_id = None

    def reset_sleep_timer(self):
        """마지막 메시지 처리 시점 기준으로 2시간(7200초) 절전 타이머를 초기화/연장 (1시간 55분 후 사전 경고 알림)"""
        if self.warn_timer is not None:
            self.warn_timer.cancel()
        if self.sleep_timer is not None:
            self.sleep_timer.cancel()

        self.warn_timer = threading.Timer(WARN_TIMEOUT_SECONDS, self.send_warning_notification)
        self.warn_timer.daemon = True
        self.warn_timer.start()
        print(f"⏱️ 스마트 절전 타이머 초기화: {SLEEP_TIMEOUT_SECONDS}초(2시간) 동안 무응답 시 절전 예약 (1시간 55분 후 사전 경고 알림)")

    def send_warning_notification(self):
        """절전 진입 5분 전 사전 경고 텔레그램 메시지 전송 및 5분 뒤 최종 절전 모드 진입 예약"""
        print("⚠️ 2시간 무응답 5분 전: 사전 경고 텔레그램 메시지 전송 및 5분 후 절전 예약")
        if self.last_chat_id:
            try:
                self.send_message(
                    self.last_chat_id,
                    "⚠️ <b>[자동 절전 사전 안내]</b>\n2시간 동안 추가 대화가 없어 5분 뒤 저전력(절전) 모드로 전환됩니다."
                )
            except Exception as e:
                print(f"⚠️ 사전 경고 텔레그램 메시지 전송 실패: {e}")

        # 경고 메시지 발송 5분 후 절전 모드 진입 타이머 가동
        self.sleep_timer = threading.Timer(WARN_BEFORE_SECONDS, self.enter_sleep_mode)
        self.sleep_timer.daemon = True
        self.sleep_timer.start()

    def enter_sleep_mode(self):
        """2시간 동안 추가 메시지가 없으면 윈도우 절전 모드 진입"""
        print("=" * 65)
        print("🌙 2시간 동안 추가 메시지가 수신되지 않아 PC를 절전 모드로 전환합니다.")
        print("=" * 65)

        # 윈도우 절전 모드 진입 명령어 실행
        cmd = "rundll32.exe powrprof.dll,SetSuspendState Sleep"
        try:
            subprocess.run(cmd, shell=True)
        except Exception as e:
            print(f"❌ 절전 모드 진입 명령 실패: {e}")

    def get_updates(self):
        url = f"{self.api_url}/getUpdates?offset={self.offset}&timeout=20"
        try:
            resp = requests.get(url, timeout=25)
            if resp.status_code == 200:
                return resp.json().get("result", [])
        except Exception as e:
            print(f"⚠️ 연결 대기 중 오류: {e}")
        return []

    def send_message(self, chat_id: int, text: str):
        url = f"{self.api_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
        try:
            requests.post(url, json=payload, timeout=10)
            print(f"✅ 스마트폰 텔레그램으로 답장 완료! (Chat ID: {chat_id})")
        except Exception as e:
            print(f"❌ 답장 전송 실패: {e}")

    def run(self):
        print("=" * 65)
        print("🤖 [철물 자재 검색, 최저가 & 카카오내비 연동 텔레그램 봇 실행 중]")
        print("=" * 65)
        print("📲 스마트폰 텔레그램 앱에서 자재명, 최저가 또는 주소를 전송하세요.")
        print("   예시 1: 앙코르앵글, 광주 북구 첨단중앙로 123 (자재+내비 연동)")
        print("   예시 2: 세파볼트 최저가 (네이버 쇼핑 최저가 TOP 3 검색)")
        print(f"🌙 2시간 무소음 자동 절전 기능 활성화 ({SLEEP_TIMEOUT_SECONDS}초 무응답 시 Windows 절전, 5분 전 사전 경고)")
        print("=" * 65 + "\n")

        # 봇 시작 시 최초 절전 타이머 가동
        self.reset_sleep_timer()

        try:
            while True:
                updates = self.get_updates()
                for update in updates:
                    self.offset = update["update_id"] + 1
                    message = update.get("message", {})
                    chat_id = message.get("chat", {}).get("id")
                    user_text = message.get("text", "").strip()

                    if chat_id and user_text:
                        print(f"📩 스마트폰 메시지 수신: '{user_text}' (Chat ID: {chat_id})")
                        self.last_chat_id = chat_id

                        # 메시지가 올 때마다 타이머를 2시간으로 리셋/연장
                        self.reset_sleep_timer()

                        reply = format_telegram_reply(user_text)
                        self.send_message(chat_id, reply)

                time.sleep(1)
        finally:
            if self.warn_timer is not None:
                self.warn_timer.cancel()
            if self.sleep_timer is not None:
                self.sleep_timer.cancel()


if __name__ == "__main__":
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

    if not bot_token:
        print("=" * 65)
        print("🔑 TELEGRAM_BOT_TOKEN 이 설정되지 않았습니다.")
        print("💡 텔레그램 앱에서 @BotFather 검색 -> /newbot 으로 30초 만에 토큰 발급!")
        print("=" * 65)
        bot_token = input("👉 텔레그램 봇 토큰(HTTP API Token)을 입력하세요: ").strip()

    if bot_token:
        bot = TelegramHardwareBot(bot_token)
        bot.run()
    else:
        print("❌ 토큰이 없어 봇을 시작할 수 없습니다.")
