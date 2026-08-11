# -*- coding: utf-8 -*-
"""
과일가게 맞춤형 마케팅 홍보카드 & 캡션 자동 생성기 (Real Human Shopkeeper Edition)
1. 챗봇/AI 안내 문구 100% 완전 삭제 (오직 사장님이 직접 쓴 듯한 자연스러운 톤)
2. 고객 혜택/이벤트 미입력 또는 '일 서비스!' 같은 오타 시 혜택 섹션 완전 제거
3. 스마트폰 캡처 테두리 100% 크롭 + 간판 메인 배치 + 무한 자동 슬라이드쇼
"""

import os
import tempfile
import base64
import requests
from PIL import Image
from playwright.sync_api import sync_playwright

from config import get_config, GEMINI_API_KEY
from services.omniroute_service import generate_ai_text_with_fallback
from image_cropper import auto_crop_phone_screenshot


def is_valid_event_info(event_info: str) -> bool:
    """이벤트 혜택 문구가 유효한지 검사 (공백이나 '일 서비스!' 오타 시 False)"""
    if not event_info:
        return False
    cleaned = event_info.strip()
    if len(cleaned) < 2 or cleaned in ["일 서비스!", "서비스!", "일 서비스", "없음"]:
        return False
    return True


def generate_fruit_marketing_captions(
    shop_name: str,
    location: str,
    today_fruits: str,
    event_info: str,
    phone_number: str = "",
    price_market_tag: str = "당일 새벽 경매 시세 적용"
) -> dict:
    """
    100% 과일가게 사장님이 직접 타자 친 듯한 사람 냄새 나는 홍보 문구 3종을 생성합니다.
    """
    valid_event = is_valid_event_info(event_info)
    event_prompt = f"고객 혜택: {event_info}" if valid_event else "고객 혜택: 없음 (혜택/이벤트 문구는 절대로 작성하지 마세요)"

    prompt = (
        f"당신은 {shop_name}을 운영하는 친절하고 정직한 과일가게 사장님입니다. "
        f"AI 챗봇이나 마케터 같은 딱딱하고 과장된 로봇 멘트(예: '전문가 챗봇입니다', '인생과일 픽픽픽' 등)는 절대로 쓰지 말고, "
        f"실제 과일가게 사장님이 단골 주민들에게 정답게 건네는 진솔하고 먹음직스러운 3가지 채널별 문구를 작성해 주세요.\n\n"
        f"가게 상호명: {shop_name}\n"
        f"위치/주소: {location}\n"
        f"연락처: {phone_number}\n"
        f"오늘의 추천 과일 및 당일 시세: {today_fruits} ({price_market_tag})\n"
        f"{event_prompt}\n\n"
        f"작성 규칙:\n"
        f"1. AI 챗봇 소개글이나 인사말은 일절 금지합니다. 곧바로 본문으로 시작하세요.\n"
        f"2. {valid_event}가 거짓이면 혜택/이벤트 관련 문장은 1자도 적지 마세요.\n"
        f"3. 3가지 버전 작성:\n"
        f"   - [당근마켓 동네생활 톤] (동네 이웃들에게 솔직하고 친근한 인사)\n"
        f"   - [인스타그램/스레드 톤] (신선하고 과즙 넘치는 인스타 감성 문구)\n"
        f"   - [네이버 블로그/카톡 공유용 톤] (오시는 길 상세 안내 및 예약 전화 안내)\n"
    )

    ai_res = generate_ai_text_with_fallback(prompt, system_instruction="과일가게 사장님의 정겨운 말투로 작성합니다.")
    caption_text = ai_res.get("text", "") if ai_res.get("success") else ""

    # AI 챗봇 인사말 자동 필터링
    filtered_lines = []
    for line in caption_text.split('\n'):
        if any(bad in line for bad in ["챗봇", "마케터입니다", "작성해 드립니다", "AI가"]):
            continue
        filtered_lines.append(line)
    caption_text = "\n".join(filtered_lines).strip()

    if not caption_text:
        event_block_danggeun = f"\n\n🎁 특별혜택: {event_info}" if valid_event else ""
        event_block_blog = f"\n■ 🎁 고객 혜택: {event_info}" if valid_event else ""

        caption_text = f"""[당근마켓 동네생활 톤]
안녕하세요 동네 주민 여러분! 🍓 {shop_name} 사장입니다.
오늘 아침 도매시장에서 진짜 당도 높은 꿀과일만 깐깐하게 골라왔습니다! ({price_market_tag})

📍 위치: {location}
📞 주문/예약: {phone_number if phone_number else '매장 방문'}

🛒 오늘의 당도보장 추천 라인업:
{today_fruits}{event_block_danggeun}

직접 오셔서 맛도 보시고 편하게 들러주세요! 감사드립니다. 😊

---

[인스타그램/스레드 톤]
오늘 입고된 과일 당도 진짜 최고네요... 🔥🍓 과즙 팡팡!
한 입 베어 물면 입안 가득 달콤한 {shop_name} 과일 소식! 🎉

📍 위치: {location}
📞 전화 주문: {phone_number}

🛒 오늘의 추천 과일:
{today_fruits}

👇 찾아오시는 길
{location}

#과일가게 #{shop_name.replace(' ', '')} #동네과일맛집 #당도보장 #광산구과일

---

[네이버 블로그 / 카톡 공유 톤]
안녕하세요, 신선하고 맛있는 과일 전문점 [{shop_name}]입니다.
저희 가게는 매일 아침 새벽 경매 시장에서 엄선한 고당도 프리미엄 과일만 직접 공수해 오고 있습니다.

■ 매장 위치: {location}
■ 주문/예약 문의: {phone_number}
■ 오늘의 추천 과일 ({price_market_tag}):
{today_fruits}{event_block_blog}

방문하시기 전 전화나 문자로 수량 예약도 가능하니 편하게 문의해 주세요!
"""
    return {
        "success": True,
        "captions": caption_text
    }


def create_fruit_promo_card_html(
    shop_name: str,
    location: str,
    today_fruits: str,
    event_info: str,
    image_paths: list = None,
    phone_number: str = "",
    price_market_tag: str = "당일 새벽 경매 최상급"
) -> str:
    """
    스마트폰 테두리 100% 크롭 + 간판 메인 배치 + 이벤트 없을 시 혜택 섹션 완전 제거 HTML
    """
    if image_paths is None:
        image_paths = []

    clean_image_paths = [auto_crop_phone_screenshot(p) for p in image_paths if os.path.exists(p)]

    store_front_html = ""
    fruit_slides_html = ""

    if clean_image_paths:
        main_path = clean_image_paths[0]
        try:
            with open(main_path, "rb") as f:
                b64_main = base64.b64encode(f.read()).decode("utf-8")
            store_front_html = f'''
            <div style="width:100%; text-align:center; background:#FFF1F2; border-radius:16px; overflow:hidden; border:2px solid #FECDD3; margin-bottom:16px;">
                <div style="background:#E11D48; color:white; padding:6px 12px; font-weight:800; font-size:0.95rem;">🏬 우리동네 과일가게 매장 전경</div>
                <img src="data:image/png;base64,{b64_main}" style="width:100%; max-height:280px; object-fit:contain; display:block;" />
            </div>
            '''
        except Exception:
            pass

        fruit_imgs_b64 = []
        for p in clean_image_paths[1:]:
            try:
                with open(p, "rb") as f:
                    fruit_imgs_b64.append(base64.b64encode(f.read()).decode("utf-8"))
            except Exception:
                pass

        if fruit_imgs_b64:
            slide_elements = "".join([
                f'<div class="auto-slide"><img src="data:image/png;base64,{b64}" style="width:100%; max-height:320px; object-fit:contain; border-radius:12px; display:block; margin:0 auto;" /></div>'
                for b64 in fruit_imgs_b64
            ])

            fruit_slides_html = f'''
            <div style="margin-top:16px; margin-bottom:16px;">
                <div style="font-size:1.15rem; font-weight:900; color:#E11D48; margin-bottom:8px;">✨ 갓 입고된 꿀과일 실물 진열</div>
                <div class="slideshow-container" style="position:relative; width:100%; border-radius:14px; overflow:hidden; border:1px solid #E2E8F0; background:#F8FAFC; padding:10px 0;">
                    {slide_elements}
                </div>
            </div>
            <script>
                (function() {{
                    let slides = document.querySelectorAll('.auto-slide');
                    if (slides.length > 0) {{
                        let currentIdx = 0;
                        function showNextSlide() {{
                            slides.forEach((s, idx) => {{
                                s.style.display = (idx === currentIdx) ? 'block' : 'none';
                            }});
                            currentIdx = (currentIdx + 1) % slides.length;
                        }}
                        showNextSlide();
                        setInterval(showNextSlide, 2500);
                    }}
                }})();
            </script>
            '''

    formatted_fruits = today_fruits.replace('\n', '<br>') if today_fruits else ""
    naver_map_url = f"https://map.naver.com/v5/search/{requests.utils.quote(location)}" if location else "#"
    phone_badge = f'<div style="background:#EFF6FF; border:1px solid #BFDBFE; color:#1D4ED8; padding:10px 14px; border-radius:12px; font-weight:800; font-size:1.05rem; margin-bottom:14px; display:flex; align-items:center; justify-content:space-between;"><span>📞 전화/문자 주문: {phone_number}</span> <a href="tel:{phone_number}" style="background:#2563EB; color:white; padding:4px 10px; border-radius:6px; text-decoration:none; font-size:0.85rem;">바로통화</a></div>' if phone_number else ""

    # 이벤트 혜택 섹션 처리 (유효하지 않으면 아예 출력 안 함)
    event_section_html = ""
    if is_valid_event_info(event_info):
        event_section_html = f'''
        <div class="section-title">🎁 고객 특별 혜택</div>
        <div class="special-box">
            <span class="badge">SPECIAL</span> {event_info.strip()}
        </div>
        '''

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@600;700;800;900&display=swap');
        body {{
            margin: 0; padding: 16px; background: #0F172A;
            font-family: 'Pretendard', sans-serif; display: flex; justify-content: center;
        }}
        .card {{
            width: 450px; background: #ffffff; border-radius: 24px;
            box-shadow: 0 25px 50px rgba(0,0,0,0.35); overflow: hidden; padding: 24px; color: #1E293B; box-sizing: border-box;
        }}
        .header {{
            background: linear-gradient(135deg, #E11D48 0%, #F43F5E 100%);
            color: white; padding: 8px 16px; border-radius: 20px; font-size: 1.1rem; font-weight: 800;
            display: inline-block; margin-bottom: 12px; letter-spacing: -0.5px;
        }}
        .price-badge {{
            background: #FEF3C7; color: #92400E; border: 1px solid #FDE68A; padding: 4px 10px;
            border-radius: 8px; font-size: 0.85rem; font-weight: 800; float: right;
        }}
        .shop-title {{ font-size: 2rem; font-weight: 900; margin-bottom: 10px; color: #0F172A; letter-spacing: -1px; }}
        .location-box {{
            background: #FFF1F2; border: 1px solid #FECDD3; padding: 12px 16px; border-radius: 14px;
            color: #BE123C; font-size: 0.98rem; font-weight: 700; margin-bottom: 14px; line-height: 1.5;
        }}
        .map-btn {{
            display: inline-block; background: #03C75A; color: white; text-decoration: none; padding: 7px 16px;
            border-radius: 8px; font-size: 0.9rem; font-weight: 800; margin-top: 8px; box-shadow: 0 4px 10px rgba(3,199,90,0.3);
        }}
        .section-title {{ font-size: 1.15rem; font-weight: 900; color: #E11D48; margin-top: 16px; margin-bottom: 10px; }}
        .item-list {{ background: #F8FAFC; padding: 16px; border-radius: 14px; font-size: 1.08rem; line-height: 1.7; font-weight: 700; border: 1px solid #E2E8F0; color:#334155; }}
        .special-box {{ background: #FFFBEB; color: #92400E; border: 1.5px solid #FDE68A; padding: 16px; border-radius: 14px; font-size: 1.05rem; font-weight: 800; line-height: 1.5; }}
        .badge {{ background: #FFEDD5; color: #C2410C; padding: 4px 10px; border-radius: 20px; font-weight: 800; font-size: 0.85rem; margin-right: 6px; }}
        .auto-slide {{ display: none; animation: fadeIn 0.8s ease-in-out; }}
        @keyframes fadeIn {{
            from {{ opacity: 0.3; }}
            to {{ opacity: 1; }}
        }}
    </style>
</head>
<body>
    <div class="card" id="fruit-card">
        <span class="price-badge">📉 {price_market_tag}</span>
        <div class="header">🍓 오늘의 당도보장 꿀과일소식</div>
        <div class="shop-title">{shop_name}</div>
        
        {store_front_html}

        <div class="location-box">
            📍 <b>매장 위치 / 찾아오시는 길:</b><br>{location}<br>
            <a href="{naver_map_url}" target="_blank" class="map-btn">🗺️ 네이버 지도에서 길찾기 열기</a>
        </div>
        
        {phone_badge}

        {fruit_slides_html}

        <div class="section-title">🛒 오늘의 추천 과일 & 당일 시세가</div>
        <div class="item-list">
            {formatted_fruits}
        </div>

        {event_section_html}
    </div>
</body>
</html>
"""
    return html_content


def capture_fruit_card_png(html_content: str, output_png_path: str) -> str:
    """Playwright PNG 스크린샷 캡처"""
    temp_html = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
    temp_html.write(html_content.encode("utf-8"))
    temp_html.close()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 540, "height": 1300}, device_scale_factor=2)
            page.goto(f"file:///{temp_html.name.replace(os.sep, '/')}")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(600)
            card = page.query_selector("#fruit-card")
            if card:
                card.screenshot(path=output_png_path)
            else:
                page.screenshot(path=output_png_path)
            browser.close()
        return output_png_path
    except Exception as e:
        print(f"PNG 스크린샷 실패: {e}")
        return ""
