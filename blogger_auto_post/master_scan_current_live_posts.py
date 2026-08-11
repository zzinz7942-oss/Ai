"""
blog_master_config.py 단일 표준 기반 전체 라이브 포스트 전수 실시간 재스캔 스크립트
- 절대 삭제/수정 API 호출 금지 (보고 전용)
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
import blog_master_config
import blogger_client

service = blogger_client._get_service()

pprint("=" * 70)
pprint("🔍 [blog_master_config 단일 표준] 구글 블로그 라이브 포스트 전수 재스캔")
pprint("=" * 70)

# Blogger API 전체 포스트 수집
posts_res = service.posts().list(blogId=config.BLOGGER_BLOG_ID, fetchBodies=True, maxResults=500).execute()
items = posts_res.get("items", [])

total_count = len(items)
pprint(f"📌 현재 라이브 포스트 개수: 총 {total_count}개 수집 완료 (삭제 조치 없이 검증 목록만 생성합니다)\n")

scan_results = []
pass_count = 0
fail_count = 0

for idx, p in enumerate(items, 1):
    post_id = p["id"]
    title = p.get("title", "")
    content = p.get("content", "")
    url = p.get("url", "")

    image_urls = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', content)

    # 8대 하드 게이트 검증 수행 (삭제 조치 0건, pure inspection)
    val = blog_master_config.run_full_validation(title, content, image_urls)
    passed = val.get("passed", False)

    if passed:
        pass_count += 1
    else:
        fail_count += 1

    fail_reasons = []
    details = val.get("details", {})
    for c_name, c_val in details.items():
        if isinstance(c_val, (tuple, list)) and len(c_val) == 2:
            c_pass, c_msg = c_val
            if not c_pass:
                fail_reasons.append(f"{c_name}: {c_msg}")

    scan_results.append({
        "index": idx,
        "id": post_id,
        "title": title,
        "url": url,
        "passed": passed,
        "status": "PASS" if passed else "FAIL",
        "fail_reasons": fail_reasons
    })

pprint("=" * 70)
pprint("📊 [blog_master_config 기준 전체 라이브 포스트 최종 전수 검증 리포트]")
pprint("=" * 70)

pprint(f"▶ 총 게시물 수: {total_count}개")
pprint(f"🟢 PASS (8대 마스터 100% 충족) : {pass_count}개 ({pass_count/total_count*100:.1f}%)")
pprint(f"🔴 FAIL (보완 대상)             : {fail_count}개 ({fail_count/total_count*100:.1f}%)\n")

pprint(f"{'번호':<4} | {'상태':<6} | {'포스트 ID':<20} | {'제목':<45} | {'실패 사유'}")
pprint("-" * 110)

for item in scan_results:
    st_icon = "🟢 PASS" if item["passed"] else "🔴 FAIL"
    reasons_str = "; ".join(item["fail_reasons"]) if item["fail_reasons"] else "없음 (100% 충족)"
    title_short = item["title"][:42] + ("..." if len(item["title"]) > 42 else "")
    pprint(f"{item['index']:<4} | {st_icon:<6} | {item['id']:<20} | {title_short:<45} | {reasons_str}")

pprint("=" * 70)
