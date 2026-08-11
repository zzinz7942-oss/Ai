# -*- coding: utf-8 -*-
"""
마케팅 콘텐츠 생성 서비스 (Content Generator Service)
- 상품 정보, 파트너스 링크, 특징을 결합하여 SNS 맞춤형 홍보 캡션 자동 생성
- Gemini API / OpenAI API 기반 마케팅 문구 및 해시태그 생성
"""

import json
from config import get_config, GEMINI_API_KEY, OPENAI_API_KEY


from services.omniroute_service import generate_ai_text_with_fallback


def generate_marketing_caption(product_name: str, product_price: int = 0, deeplink_url: str = "", summary: str = "", category: str = "") -> str:
    """
    OmniRoute 멀티 AI 라우터(Gemini -> OpenAI -> OmniRoute -> 템플릿)를 사용하여 인스타/스레드용 마케팅 캡션을 생성합니다.
    """
    link_instruction = f"4. 마지막 부분에 '👇 구매/정보 링크'와 함께 {deeplink_url} 링크를 명확히 포함해줘.\n" if deeplink_url else "4. 마지막 부분에 관련 문의나 프로필 링크 안내 문구를 넣어줘.\n"
    price_info = f"{product_price:,}원" if product_price else "가격 문의 / 상세 정보 참조"

    prompt = (
        f"다음 콘텐츠/상품 정보를 바탕으로 인스타그램 및 쓰레드(Threads)에 올릴 매력적인 마케팅 캡션을 작성해줘.\n\n"
        f"제목/상품명: {product_name}\n"
        f"가격/정보: {price_info}\n"
        f"주요 특징/요약: {summary}\n"
        f"링크: {deeplink_url if deeplink_url else '없음'}\n\n"
        f"작성 규칙:\n"
        f"1. 이모지를 풍부하게 사용하여 시각적으로 눈에 띄게 작성해줘.\n"
        f"2. 첫 줄에 호기심을 유발하는 강력한 후킹 문구를 넣어줘.\n"
        f"3. 핵심 장점 3~4가지를 체크표시(✅) 목록으로 정리해줘.\n"
        f"{link_instruction}"
        f"5. 관련 인기 트렌드 해시태그 6~8개를 맨 아래에 추가해줘.\n"
        f"6. 자연스럽고 정보 공유형 톤앤매너로 작성해줘."
    )

    # OmniRoute 멀티 프로바이더 폴백 시도
    ai_res = generate_ai_text_with_fallback(prompt, system_instruction="인스타그램/스레드 전문 마케터 챗봇입니다.")
    if ai_res.get("success") and ai_res.get("text"):
        print(f"✅ AI 문구 생성 성공 (프로바이더: {ai_res.get('provider')})")
        return ai_res["text"].strip()

    # Fallback 기본 마케팅 템플릿
    formatted_price = f"{product_price:,}원" if product_price else "상세 정보 참조"
    link_section = f"\n👇 구매/상세 링크\n{deeplink_url}" if deeplink_url else "\n💬 자세한 내용은 댓글이나 DM으로 문의주세요!"

    template = f"""요즘 SNS에서 핫한 인스타 꿀정보 추천! 🔥✨

{product_name}

이거 하나 알고 가시면 삶의 질이 훨씬 상승합니다...😍

✅ 추천 핵심 포인트
- {summary if summary else '꼭 알아두어야 할 핵심 정보 및 유용 꿀팁'}
- 참고 가격/정보: {formatted_price}
- 빠른 확인 및 적용 가능

놓치지 마시고 지금 바로 확인해보세요! 🚀
{link_section}

#꿀정보 #트렌드추천 #인스타꿀템 #{category.replace(' ', '') if category else '인기정보'} #추천정보
"""
    return template.strip()
