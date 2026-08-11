# -*- coding: utf-8 -*-
"""
HTML 카드뉴스 → 스크린샷(PNG) → Threads 자동 업로드
Playwright로 각 카드를 개별 PNG로 캡처 → catbox.moe → Threads 게시
"""

import sys
import os
import time

from playwright.sync_api import sync_playwright
from threads_uploader import post_local_image

# ─────────────────────────────────────────────
# 설정
# ─────────────────────────────────────────────
HTML_PATH   = r"C:\Users\picaf\Downloads\travel_subsidy_illustrated_v2.html"
OUTPUT_DIR  = r"C:\Users\picaf\Desktop\Ai\card_screenshots"
TOTAL_CARDS = 8

# 각 카드별 캡션 (Threads 포스트 텍스트)
CAPTIONS = [
    "국내 여행 갈 때 이거 안 알아보면 정말 호구 잡힙니다 ✈️ [1/8]",
    "매년 수백억 풀리는 여행 지원금, 왜 아무도 안 알려줄까 [2/8]",
    "강원 · 경상도 체류형 지원금 & 숙박 할인 꿀팁 [3/8]",
    "전라 · 제주 숙박 할인 & 투어 패스 총정리 [4/8]",
    "충청 · 경기 시티투어 & 지역상품권 꿀팁 [5/8]",
    "지원금 신청, 이것만은 절대 놓치지 마세요 [6/8]",
    "지역별 핵심 혜택 한눈에 보기 [7/8]",
    "다음 여행 전에 이 카드 다시 꺼내 보세요 — 저장 필수! [8/8]",
]


# ─────────────────────────────────────────────
# Step 1: HTML → 카드별 PNG 스크린샷
# ─────────────────────────────────────────────
def html_to_screenshots(html_path: str, output_dir: str, total: int) -> list[str]:
    """
    HTML 카드뉴스의 각 카드를 개별 PNG 파일로 캡처합니다.
    :param html_path:  HTML 파일 경로
    :param output_dir: 스크린샷 저장 디렉토리
    :param total:      총 카드 수
    :return: 생성된 PNG 파일 경로 리스트
    """
    os.makedirs(output_dir, exist_ok=True)
    screenshots = []

    print("=" * 50)
    print("   📸 HTML → PNG 스크린샷 변환 시작")
    print("=" * 50)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": 500, "height": 500},
            device_scale_factor=2,  # 고해상도 (840x840 실제 픽셀)
        )

        # HTML 파일 로드
        file_url = f"file:///{html_path.replace(os.sep, '/')}"
        page.goto(file_url)
        page.wait_for_load_state("networkidle")

        for i in range(total):
            # JavaScript로 해당 카드만 활성화
            page.evaluate(f"""() => {{
                const cards = document.querySelectorAll('.cd');
                cards.forEach((c, idx) => {{
                    c.classList.toggle('active', idx === {i});
                }});
            }}""")
            page.wait_for_timeout(300)

            # .cf 컨테이너 (420x420 카드 영역) 스크린샷
            card_container = page.query_selector(".cf")
            if card_container:
                file_path = os.path.join(output_dir, f"card_{i + 1}.png")
                card_container.screenshot(path=file_path)
                file_size_kb = os.path.getsize(file_path) / 1024
                print(f"  ✅ 카드 {i + 1}/{total} 저장 완료 ({file_size_kb:.0f}KB) → {file_path}")
                screenshots.append(file_path)
            else:
                print(f"  ❌ 카드 {i + 1} 컨테이너(.cf)를 찾을 수 없습니다")

        browser.close()

    print(f"\n📸 총 {len(screenshots)}장 스크린샷 완료!\n")
    return screenshots


# ─────────────────────────────────────────────
# Step 2: 스크린샷 → Threads 일괄 업로드
# ─────────────────────────────────────────────
def batch_upload_to_threads(screenshots: list[str], captions: list[str]):
    """
    스크린샷 리스트를 Threads에 순서대로 업로드합니다.
    :param screenshots: PNG 파일 경로 리스트
    :param captions:    각 이미지에 첨부할 캡션 리스트
    """
    print("=" * 50)
    print("   🚀 Threads 일괄 업로드 시작")
    print("=" * 50)

    results = []
    for idx, file_path in enumerate(screenshots):
        caption = captions[idx] if idx < len(captions) else ""
        print(f"\n{'─' * 40}")
        print(f"  [{idx + 1}/{len(screenshots)}] 업로드 중...")

        result = post_local_image(file_path, caption)
        results.append(result)

        # API 과부하 방지 (카드 사이 대기)
        if idx < len(screenshots) - 1:
            print("  ⏳ 다음 카드까지 8초 대기...")
            time.sleep(8)

    # 결과 요약
    print("\n" + "=" * 50)
    print("   📊 업로드 결과 요약")
    print("=" * 50)
    success = sum(1 for r in results if r.get("success"))
    fail = len(results) - success
    print(f"  ✅ 성공: {success}건")
    print(f"  ❌ 실패: {fail}건")
    for idx, r in enumerate(results):
        status = "✅" if r.get("success") else "❌"
        post_id = r.get("post_id", "N/A")
        print(f"  {status} 카드 {idx + 1}: {post_id}")

    return results


# ─────────────────────────────────────────────
# ▶️ 실행
# ─────────────────────────────────────────────
if __name__ == "__main__":
    # Step 1: HTML → PNG 스크린샷
    screenshots = html_to_screenshots(HTML_PATH, OUTPUT_DIR, TOTAL_CARDS)

    if not screenshots:
        print("❌ 스크린샷 생성 실패. 종료합니다.")
        sys.exit(1)

    # Step 2: 스크린샷 → Threads 업로드
    batch_upload_to_threads(screenshots, CAPTIONS)
