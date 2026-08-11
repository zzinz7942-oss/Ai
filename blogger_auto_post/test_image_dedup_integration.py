"""
통합된 generate_images_for_post 이미지 수집 & 키워드 추출 & used_images.json 중복 배제 실전 검증 스크립트
"""

import sys
import os
import json

os.environ["PYTHONUNBUFFERED"] = "1"
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def pprint(*args, **kwargs):
    kwargs["flush"] = True
    print(*args, **kwargs)

import image_fetcher

pprint("=" * 70)
pprint("🧪 [통합 이미지 고유 수집 & used_images.json 중복 배제 실전 검증 테스트]")
pprint("=" * 70)

# 테스트 포스트 제목 및 소제목 정의
test_title = "2026년 차세대 2차전지 배터리 주식과 엔비디아 AI 전망"
test_sections = [
    "1. 2차전지 배터리 시장 2026년 기술 동향",
    "2. 엔비디아 AI 반도체 수혜주 수율 분석",
    "3. 전기차 배터리 패러다임 변화"
]

pprint(f"📌 테스트 포스트 제목: '{test_title}'")
pprint(f"📌 테스트 소제목 {len(test_sections)}개:")
for idx, sec in enumerate(test_sections, 1):
    pprint(f"   - 소제목 {idx}: {sec}")

pprint("\n🚀 generate_images_for_post() 실행 중...")
result = image_fetcher.generate_images_for_post(test_title, test_sections)

pprint("\n" + "=" * 70)
pprint("📊 [수집 결과 분석 리포트]")
pprint("=" * 70)

thumb = result.get("thumbnail")
sections_imgs = result.get("sections", [])

all_urls = []

if thumb:
    pprint(f"📸 [썸네일 이미지]:")
    pprint(f"   - URL   : {thumb.get('url')}")
    pprint(f"   - ALT   : {thumb.get('alt')}")
    pprint(f"   - CREDIT: {thumb.get('credit')}")
    all_urls.append(thumb.get('url'))

for idx, img in enumerate(sections_imgs, 1):
    if img:
        pprint(f"\n📸 [섹션 {idx} 이미지]:")
        pprint(f"   - URL   : {img.get('url')}")
        pprint(f"   - ALT   : {img.get('alt')}")
        pprint(f"   - CREDIT: {img.get('credit')}")
        all_urls.append(img.get('url'))

# 중복 대조 검증
unique_urls = set(all_urls)
pprint("\n" + "-" * 70)
pprint(f"🔍 총 수집 이미지 개수 : {len(all_urls)}개")
pprint(f"🔍 중복 없는 고유 URL  : {len(unique_urls)}개")

if len(all_urls) == len(unique_urls):
    pprint("✅ [검증 성공] 단 한 건의 이미지 URL 중복 없이 100% 고유 이미지 수집 완수!")
else:
    pprint("❌ [검증 실패] 글 내부 이미지 URL 중복 발생!")

# used_images.json 기록 확인
used_in_file = image_fetcher.load_used_images()
pprint(f"💾 used_images.json 현재 저장된 총 이미지 URL 개수: {len(used_in_file):,}개")

saved_all = all(u in used_in_file for u in all_urls)
if saved_all:
    pprint("✅ [저장소 검증 성공] 수집된 모든 이미지 URL이 used_images.json에 100% 자동 기록됨!")
else:
    pprint("❌ [저장소 검증 실패] 일부 URL이 used_images.json에 누락됨")

pprint("=" * 70)
