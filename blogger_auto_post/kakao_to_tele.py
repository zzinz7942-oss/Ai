"""
kakao_to_tele.py
PC 카카오톡 특정 채팅방('철물점 주문방')의 메시지를 pywin32로 실시간 감지하여
스마트폰 텔레그램 봇으로 자동 전달(포워딩)하는 백그라운드 파이썬 스크립트
"""

import os
import re
import sys
import time
import argparse
from pathlib import Path
from dotenv import load_dotenv

# UTF-8 인코딩 강제 설정 (CMD 한글 깨짐 방지)
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUTF8"] = "1"

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

import requests
import win32gui
import win32con
import win32api
import win32clipboard

ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(ENV_PATH)

# ==============================================================================
# 💬 [설정 변수] 모니터링할 카카오톡 채팅방 제목 및 텔레그램 정보
# ==============================================================================
TARGET_CHATROOM_NAME = "철물점 주문방"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


def find_kakaotalk_window(room_title_keyword: str) -> int:
    """PC 카카오톡 특정 채팅방 핸들(HWND) 탐색"""
    hwnd_target = 0

    def _enum_windows_callback(hwnd, extra):
        nonlocal hwnd_target
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            class_name = win32gui.GetClassName(hwnd)
            if "EVA_Window" in class_name or "KakaoTalk" in class_name:
                if room_title_keyword in title:
                    hwnd_target = hwnd
                    return False
        return True

    win32gui.EnumWindows(_enum_windows_callback, None)
    return hwnd_target


def get_child_controls(parent_hwnd: int) -> list:
    """채팅방 창 내부 자식 컨트롤 핸들 수집"""
    child_controls = []

    def _enum_child_callback(hwnd, extra):
        child_controls.append((hwnd, win32gui.GetClassName(hwnd), win32gui.GetWindowText(hwnd)))
        return True

    win32gui.EnumChildWindows(parent_hwnd, _enum_child_callback, None)
    return child_controls


def read_chat_text_via_clipboard(hwnd_target: int) -> str:
    """pywin32를 이용해 카카오톡 채팅방 메시지 영역 텍스트 추출"""
    try:
        children = get_child_controls(hwnd_target)
        list_ctrl_hwnd = 0
        for child_hwnd, class_name, _ in children:
            if "ListControl" in class_name or "Edit" in class_name or "RichEdit" in class_name:
                list_ctrl_hwnd = child_hwnd
                break

        if not list_ctrl_hwnd:
            list_ctrl_hwnd = hwnd_target

        buf_size = 65536
        buffer = win32gui.PyMakeBuffer(buf_size)
        length = win32gui.SendMessage(list_ctrl_hwnd, win32con.WM_GETTEXT, buf_size, buffer)
        text_res = buffer[:length].tobytes().decode('utf-8', errors='replace').strip()

        if text_res:
            return text_res

        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.CloseClipboard()

        win32gui.SendMessage(list_ctrl_hwnd, win32con.WM_COMMAND, 1, 0)
        time.sleep(0.05)

        win32clipboard.OpenClipboard()
        if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
            clip_data = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()
            return clip_data.strip() if clip_data else ""
        win32clipboard.CloseClipboard()

    except Exception:
        pass

    return ""


def send_telegram_notification(bot_token: str, chat_id: str, kakao_msg: str, room_name: str):
    """카카오톡 메시지를 스마트폰 텔레그램으로 전송"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    formatted_html = f"""💬 <b>[카카오톡 '{room_name}' 새 주문 메시지]</b>

📩 <b>수신 내용</b>:
{kakao_msg}

----------------------------------------
💡 <i>스마트폰 텔레그램에서 이 메시지의 자재명과 주소를 봇에게 전송하면 카카오내비 연동 결과가 전송됩니다.</i>"""

    payload = {
        "chat_id": chat_id,
        "text": formatted_html,
        "parse_mode": "HTML"
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            print(f"✅ 텔레그램 답장 완료! -> Chat ID: {chat_id}")
        else:
            print(f"⚠️ 텔레그램 전송 오류 (HTTP {resp.status_code}): {resp.text}")
    except Exception as e:
        print(f"❌ 텔레그램 전송 실패: {e}")


def get_latest_telegram_chat_id(bot_token: str) -> str:
    """텔레그램 봇 /getUpdates 에서 최신 사용자 Chat ID 자동 추출"""
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            results = resp.json().get("result", [])
            if results:
                last_msg = results[-1].get("message", {})
                chat_id = last_msg.get("chat", {}).get("id")
                if chat_id:
                    print(f"✅ 텔레그램 Chat ID 자동 감지 성공: {chat_id}")
                    return str(chat_id)
    except Exception:
        pass
    return ""


class KakaoToTelegramRelay:
    def __init__(self, room_name: str, bot_token: str, chat_id: str = ""):
        self.room_name = room_name
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.last_processed_msg = ""

    def run(self):
        print("=" * 65)
        print(f"📱 [PC 카카오톡 '{self.room_name}' -> 텔레그램 실시간 중계 봇]")
        print("=" * 65)

        if not self.bot_token:
            print("❌ TELEGRAM_BOT_TOKEN 이 설정되지 않았습니다.")
            return

        if not self.chat_id:
            print("🔍 텔레그램 Chat ID 자동 탐지 시도 중...")
            self.chat_id = get_latest_telegram_chat_id(self.bot_token)
            if not self.chat_id:
                print("⚠️ Chat ID를 자동으로 찾지 못했습니다.")
                print("💡 스마트폰 텔레그램 앱에서 내 봇에게 아무 메시지나 보낸 후 다시 실행하세요.")
                self.chat_id = input("👉 텔레그램 Chat ID를 입력하세요: ").strip()

        print(f"📍 모니터링 대상 카카오톡 채팅방: '{self.room_name}'")
        print(f"📍 텔레그램 수신 Chat ID : {self.chat_id}")
        print("🔄 카카오톡 새 메시지 감지 대기 중...\n")

        while True:
            hwnd = find_kakaotalk_window(self.room_name)

            if not hwnd:
                print(f"⚠️ 카카오톡 채팅방 '{self.room_name}' 창을 찾을 수 없습니다. PC에서 채팅방을 열어주세요.", end="\r")
                time.sleep(3)
                continue

            current_text = read_chat_text_via_clipboard(hwnd)

            if current_text and current_text != self.last_processed_msg:
                lines = [line.strip() for line in current_text.split('\n') if line.strip()]
                latest_line = lines[-1] if lines else current_text

                if latest_line and latest_line != self.last_processed_msg:
                    print(f"\n📩 [카카오톡 새 메시지 수신]: {latest_line}")
                    send_telegram_notification(self.bot_token, self.chat_id, latest_line, self.room_name)
                    self.last_processed_msg = latest_line

            time.sleep(2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KakaoTalk PC to Telegram Relay Bot")
    parser.add_argument("--room", "-r", type=str, default=TARGET_CHATROOM_NAME, help="모니터링할 카카오톡 채팅방 이름")
    parser.add_argument("--token", "-t", type=str, default=TELEGRAM_BOT_TOKEN, help="텔레그램 봇 토큰")
    parser.add_argument("--chatid", "-c", type=str, default=TELEGRAM_CHAT_ID, help="텔레그램 수신 Chat ID")

    args = parser.parse_args()

    bot_token = args.token or os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not bot_token:
        bot_token = input("👉 텔레그램 봇 토큰(HTTP API Token)을 입력하세요: ").strip()

    relay = KakaoToTelegramRelay(
        room_name=args.room,
        bot_token=bot_token,
        chat_id=args.chatid
    )
    relay.run()
