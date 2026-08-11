# -*- coding: utf-8 -*-
"""
네이버 블로그 마케팅 전용 포스팅 생성기 (Real Human Shopkeeper Edition)
- AI 챗봇 소개글 100% 완전 제거
- 고객 혜택/이벤트 미입력 및 오타('일 서비스!') 시 블로그 본문에서 혜택 섹션 100% 제외
"""

import os
from config import get_config, GEMINI_API_KEY
from services.omniroute_service import generate_ai_text_with_fallback
from fruit_shop_marketing import is_valid_event_info


def generate_naver_blog_post(
    shop_name: str,
    location: str,
    today_fruits: str,
    event_info: str,
    phone_number: str = "",
    price_market_tag: str = "당일 새벽 경매 최상급"
) -> dict:
    """
    진짜 과일가게 사장님이 작성한 듯한 네이버 블로그 SEO 맞춤 포스팅을 작성합니다.
    """
    valid_event = is_valid_event_info(event_info)
    event_prompt = f"고객 특별 혜택: {event_info}" if valid_event else "고객 혜택: 없음 (이벤트/혜택에 관한 텍스트는 절대로 작성하지 마세요)"

    prompt = (
        f"당신은 {shop_name}을 운영하는 친절하고 정직한 과일가게 사장님입니다. "
        f"AI 챗봇이나 마케터 인사말(예: '안녕하세요 마케터입니다', '챗봇입니다' 등)은 절대로 쓰지 말고, "
        f"실제 과일가게 사장님이 블로그 이웃들에게 작성하듯 자연스럽고 신선한 네이버 블로그 전용 포스팅을 작성해 주세요.\n\n"
        f"가게 상호명: {shop_name}\n"
        f"위치/주소: {location}\n"
        f"연락처: {phone_number}\n"
        f"오늘의 추천 과일 및 당일 시세: {today_fruits} ({price_market_tag})\n"
        f"{event_prompt}\n\n"
        f"작성 규칙:\n"
        f"1. AI 챗봇 소개글이나 안내 멘트는 일절 금지합니다.\n"
        f"2. {valid_event}가 거짓이면 혜택/이벤트 관련 문단은 완전히 빠뜨리고 작성하세요.\n"
        f"3. 작성 형식:\n"
        f"   - [블로그 제목]: 지역명 + 매장명 + 추천 과일 포함된 자연스러운 제목\n"
        f"   - [블로그 본문]: 인사 ➔ 오시는 길 안내 ➔ 오늘의 꿀과일 라인업 ➔ 전화 주문 안내 ➔ 마무리 인사\n"
        f"   - [네이버 블로그 태그]: 검색용 태그 8개\n"
    )

    ai_res = generate_ai_text_with_fallback(prompt, system_instruction="과일가게 사장님이 직접 쓴 블로그 글로 작성합니다.")
    blog_text = ai_res.get("text", "") if ai_res.get("success") else ""

    # AI 챗봇 메타 안내글 자동 제거
    filtered_lines = []
    for line in blog_text.split('\n'):
        if any(bad in line for bad in ["챗봇", "마케터입니다", "작성해 드립니다", "AI가", "안녕하세요! 오프라인"]):
            continue
        filtered_lines.append(line)
    blog_text = "\n".join(filtered_lines).strip()

    if not blog_text:
        event_block = f"\n■ 🎁 고객님을 위한 특별 혜택\n- {event_info.strip()}\n" if valid_event else ""

        blog_text = f"""[블로그 제목]
[{location.split()[0]} 과일가게] {shop_name} 오늘 입고된 당도 보장 꿀과일 시세 및 오시는 길 🍓🍎

[블로그 본문]
안녕하세요! 정직하고 신선한 과일만 고집하는 [{shop_name}] 사장입니다.😊

오늘 새벽 도매시장에서 직접 눈으로 보고 엄선한 고당도 프리미엄 과일들이 입고되어 소식 전해드립니다!

■ 📍 위치 및 찾아오시는 길
- 주소: {location}
- 네이버 지도에서 '{shop_name}'을 검색하시면 편리하게 길을 찾으실 수 있습니다.

■ 🛒 오늘의 추천 과일 라인업 ({price_market_tag})
{today_fruits}
{event_block}
■ 📞 예약 및 주문 문의
- 대표 전화: {phone_number if phone_number else '매장 직접 방문'}
- 방문하시기 전 전화나 문자로 수량 예약해 주시면 신선하게 준비해 놓겠습니다.

달콤하고 신선한 과일이 생각나실 땐 언제든 부담 없이 들러주세요! 
감사합니다. ❤️

[네이버 블로그 태그]
#{shop_name.replace(' ', '')} #동네과일가게 #과일맛집 #당도보장과일 #지역과일가게 #오늘의과일시세 #과일선물세트 #프리미엄과일
"""
    return {
        "success": True,
        "blog_post": blog_text
    }
