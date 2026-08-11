"""
구글 블로그 전체 포스트 전수 실시간 심층 분석 스크립트
- 애드센스 승인/거절 관점에서의 위험 요소(Thin Content, 뭉뚱그린 표현, 가짜 출처, YMYL 면책 누락, 과장 마케팅 어휘, 이미지 중복) 전수 진단
"""

import sys
import os
import json
import re

os.environ["PYTHONUNBUFFERED"] = "1"
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def pprint(*args, **kwargs):
    kwargs["flush"] = True
    print(*args, **kwargs)

import config
import blog_content_standards
import blogger_client

service = blogger_client._get_service()

pprint("=" * 70)
pprint("🔍 [구글 블로그 전체 포스트 전수 애드센스 위험도 실시간 심층 분석]")
pprint("=" * 70)

# Blogger API 전체 포스트 수집
posts_res = service.posts().list(blogId=config.BLOGGER_BLOG_ID, fetchBodies=True, maxResults=500).execute()
items = posts_res.get("items", [])

total_count = len(items)
pprint(f"📌 블로그 내 전체 발행 포스트 개수: {total_count}개 수집 완료\n")

safe_posts = []
warning_posts = []
high_risk_posts = []

for idx, p in enumerate(items, 1):
    post_id = p["id"]
    title = p.get("title", "")
    content = p.get("content", "")
    url = p.get("url", "")

    # HTML 태그 제거 순수 텍스트 및 이미지 추출
    raw_text = re.sub(r'<[^>]+>', ' ', content)
    raw_text = re.sub(r'\s+', ' ', raw_text).strip()
    char_count = len(raw_text)

    image_urls = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', content)
    unique_images = set(image_urls)

    # 8대 마스터 게이트 검증 수행
    val_res = blog_content_standards.run_full_validation(title, content, list(unique_images))
    passed = val_res["passed"]
    details = val_res["details"]

    failed_checks = [c_name for c_name, (c_pass, c_msg) in details.items() if not c_pass]

    p_info = {
        "index": idx,
        "id": post_id,
        "title": title,
        "url": url,
        "char_count": char_count,
        "image_count": len(unique_images),
        "failed_checks": failed_checks,
        "details": details
    }

    if passed:
        safe_posts.append(p_info)
    else:
        # 실패 항목 중 치명적 항목(char_count, specificity, unsourced_stats, ymyl_disclaimer, promotional_tone) 포함 시 HIGH RISK
        critical_fails = {"char_count", "specificity", "unsourced_stats", "ymyl_disclaimer", "promotional_tone"}.intersection(set(failed_checks))
        if critical_fails:
            high_risk_posts.append(p_info)
        else:
            warning_posts.append(p_info)

pprint("=" * 70)
pprint("📊 [애드센스 승인/위험도 전수 심층 분석 종합 리포트]")
pprint("=" * 70)

pprint(f"▶ 전체 분석 게시물 수     : {total_count}개")
pprint(f"🟢 SAFE (승인 안전군)       : {len(safe_posts)}개 ({len(safe_posts)/total_count*100:.1f}%)")
pprint(f"🟡 WARNING (보완 권장군)   : {len(warning_posts)}개 ({len(warning_posts)/total_count*100:.1f}%)")
pprint(f"🔴 HIGH RISK (애드센스 위험군): {len(high_risk_posts)}개 ({len(high_risk_posts)/total_count*100:.1f}%)\n")

if high_risk_posts:
    pprint("🔴 [🔴 HIGH RISK 위험군 포스트 상세 분석 - 애드센스 거절/감점 주요 요인]")
    pprint("-" * 70)
    for hp in high_risk_posts:
        pprint(f"📌 [{hp['index']}] {hp['title']} (ID: {hp['id']})")
        pprint(f"    - URL          : {hp['url']}")
        pprint(f"    - 순수 글자수  : {hp['char_count']:,}자 (미달 여부: {'미달' if hp['char_count'] < 4000 else '정상'})")
        pprint(f"    - 고유 이미지  : {hp['image_count']}개")
        pprint(f"    - 실패한 게이트: {hp['failed_checks']}")
        for f_check in hp['failed_checks']:
            pprint(f"      👉 [{f_check}]: {hp['details'][f_check][1]}")
        pprint("")

if warning_posts:
    pprint("🟡 [🟡 WARNING 보완 권장군 포스트 상세 분석]")
    pprint("-" * 70)
    for wp in warning_posts:
        pprint(f"📌 [{wp['index']}] {wp['title']} (ID: {wp['id']})")
        pprint(f"    - URL          : {wp['url']}")
        pprint(f"    - 실패한 게이트: {wp['failed_checks']}")
        for f_check in wp['failed_checks']:
            pprint(f"      👉 [{f_check}]: {wp['details'][f_check][1]}")
        pprint("")

if safe_posts:
    pprint("🟢 [🟢 SAFE 승인 안전군 포스트 요약]")
    pprint("-" * 70)
    for sp in safe_posts:
        pprint(f"  ✅ [PASS] {sp['title']} (글자수: {sp['char_count']:,}자, 이미지: {sp['image_count']}개)")

pprint("=" * 70)
