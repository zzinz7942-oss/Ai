# -*- coding: utf-8 -*-
"""
24시간 본체 OFF 무인 자동 댓글 & 톡 문의 AI 답변 서비스
- 네이버, 인스타그램, 당근마켓, 스레드에 손님 댓글/문의가 올라오면 사장님 말투로 1초 자동 답장
"""

import os
from services.omniroute_service import generate_ai_text

def generate_auto_reply(customer_message: str, today_fruits_info: str = "복숭아 1팩 16,000원, 아오리사과 1팩 10,000원, 샤인머스캣 27,000원") -> str:
    """
    손님의 문의/댓글에 대해 과일대장 사장님 톤으로 정겹고 친절한 1초 답장 생성
    """
    prompt = f"""
[역할]
너는 광산구 송정동 도매 직송 과일 전문점 '과일대장'의 친절하고 정겨운 사장님이다.

[오늘 매장 정보 및 과일 시세]
- 위치: 광주광역시 광산구 광산로89번길 29 (광산역 도보 3분)
- 전화번호: 010-7789-1905
- 오늘 과일 시세: {today_fruits_info}

[손님 문의/댓글]
"{customer_message}"

[답변 작성 지침]
1. AI 챗봇티를 100% 제거하고, 진짜 동네 과일가게 사장님이 정겹게 답장하듯 써라.
2. 2~3줄 이내로 명쾌하고 친절하게 과일 가격, 맛, 매장 위치를 안내하라.
3. 이모지(🍑, 🍏, 🍇, 😊)를 적절히 섞어 따뜻하게 작성하라.
"""
    try:
        reply = generate_ai_text(prompt)
        return reply.strip()
    except Exception as e:
        return f"안녕하세요! 과일대장 사장입니다 😊 오늘 복숭아랑 샤인머스캣 당도 최고입니다! 문의는 010-7789-1905로 편하게 주세요 🍑"

if __name__ == "__main__":
    test_msg = "오늘 샤인머스캣 얼마인가요? 주차 되나요?"
    print("손님 문의:", test_msg)
    print("AI 사장님 답장:", generate_auto_reply(test_msg))
