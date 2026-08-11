# -*- coding: utf-8 -*-
"""
투명 가스레인지 가림막 홍보 포스트 → Threads 업로드
1) 홍보 카드 HTML → PNG 스크린샷
2) catbox.moe → 공개 URL
3) Threads API → 이미지 + 텍스트 포스트 게시
"""

import sys
import os
import time

from playwright.sync_api import sync_playwright
from threads_uploader import post_local_image

# ─────────────────────────────────────────────
# 설정
# ─────────────────────────────────────────────
HTML_PATH  = r"C:\Users\picaf\Desktop\Ai\promo_card.html"
OUTPUT_PNG = r"C:\Users\picaf\Desktop\Ai\promo_screenshot.png"

PROMO_TEXT = """매번 요리할 때마다 기름 튀어서 주변 청소하느라 짜증나시는 분? 🍳

저도 진짜 스트레스 받다가 이거 하나 설치하고 세상 편해졌습니다.

✅ 투명이라 주방 인테리어 안 망침
✅ 기름 튀어도 닦으면 끝 (세척 개쉬움)
✅ 가스레인지 / 인덕션 둘 다 OK
✅ 52% 할인 중 — 15,400원 (원가 32,500원)

한 달에 200명 넘게 사가는 이유가 있더라구요.
리뷰 168개, 별점 4.5 이상 ⭐

👇 구매 링크
https://link.coupang.com/a/f6ybVfPYt2

#주방꿀템 #가스레인지가림막 #인덕션가림막 #기름튀김방지 #자취꿀템 #주방정리"""


# ─────────────────────────────────────────────
# Step 1: HTML → PNG 스크린샷
# ─────────────────────────────────────────────
def capture_promo_card(html_path: str, output_path: str) -> str:
    print("=" * 50)
    print("   📸 홍보 카드 스크린샷 캡처")
    print("=" * 50)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": 540, "height": 540},
            device_scale_factor=2,  # 고해상도 (1080x1080)
        )

        file_url = f"file:///{html_path.replace(os.sep, '/')}"
        page.goto(file_url)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)  # 폰트 로딩 대기

        card = page.query_selector(".card")
        if card:
            card.screenshot(path=output_path)
            file_size_kb = os.path.getsize(output_path) / 1024
            print(f"  ✅ 캡처 완료 ({file_size_kb:.0f}KB) → {output_path}")
        else:
            page.screenshot(path=output_path)
            print(f"  ✅ 전체 페이지 캡처 → {output_path}")

        browser.close()

    return output_path


# ─────────────────────────────────────────────
# Step 2: Threads 업로드
# ─────────────────────────────────────────────
if __name__ == "__main__":
    # 카드 캡처
    screenshot = capture_promo_card(HTML_PATH, OUTPUT_PNG)

    # Threads 업로드
    print("\n" + "=" * 50)
    print("   🚀 Threads 홍보 포스트 업로드")
    print("=" * 50)

    result = post_local_image(screenshot, PROMO_TEXT)
    print(f"\n최종 결과: {result}")
