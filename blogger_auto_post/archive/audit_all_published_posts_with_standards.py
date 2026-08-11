"""
Blogger API에 발행된 모든 포스트를 blog_content_standards.py 기준으로 전수 감사 스캔하여
미달 포스트 목록 및 결격 사유 리포트를 생성하는 스크립트
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
import blogger_client
import blog_content_standards

pprint("=" * 70)
pprint("🔍 [Blogger API 발행 포스트 blog_content_standards.py 마스터 전수 감사]")
pprint("=" * 70)

service = blogger_client._get_service()

page_token = None
total_scanned = 0
passed_posts = []
failing_posts = []

while True:
    try:
        resp = service.posts().list(
            blogId=config.BLOGGER_BLOG_ID,
            maxResults=50,
            pageToken=page_token,
            fetchBodies=True
        ).execute()

        items = resp.get("items", [])
        if not items:
            break

        for item in items:
            total_scanned += 1
            post_id = item.get("id")
            title = item.get("title", "")
            content = item.get("content", "")
            url = item.get("url", "")

            # 이미지 URL 추출
            image_urls = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', content)

            # 순수 텍스트 파싱
            raw_text = re.sub(r'<[^>]+>', ' ', content)
            raw_text = re.sub(r'\s+', ' ', raw_text).strip()

            # 마스터 검증 수행
            val_res = blog_content_standards.run_full_validation(title, content, image_urls)
            passed = val_res["passed"]
            details = val_res["details"]

            fail_list = []
            for c_name, (c_pass, c_msg) in details.items():
                if not c_pass:
                    fail_list.append(c_msg)

            post_info = {
                "id": post_id,
                "title": title,
                "url": url,
                "char_count": len(raw_text.replace(" ", "").replace("\n", "")),
                "image_count": len(set(image_urls)),
                "passed": passed,
                "fail_reasons": fail_list
            }

            if passed:
                passed_posts.append(post_info)
            else:
                failing_posts.append(post_info)

        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    except Exception as e:
        pprint(f"  ⚠️ 감사 중 예외 발생: {e}")
        break

pprint(f"\n📊 [전수 감사 결과 통계]")
pprint(f"  - 총 검사 포스트 수 : {total_scanned}개")
pprint(f"  - 마스터 기준 통과  : {len(passed_posts)}개")
pprint(f"  - 마스터 기준 미달  : {len(failing_posts)}개")

pprint("\n" + "=" * 70)
pprint("🚨 [마스터 기준 미달 발행글 목록 및 결격 사유 상세 리포트]")
pprint("=" * 70)

for idx, p in enumerate(failing_posts, 1):
    pprint(f"\n[{idx}] {p['title']} (ID: {p['id']})")
    pprint(f"    - URL      : {p['url']}")
    pprint(f"    - 순수글자 : {p['char_count']:,}자 | 고유이미지: {p['image_count']}개")
    pprint(f"    - 결격 사유:")
    for reason in p["fail_reasons"]:
        pprint(f"      ❌ {reason}")

pprint("=" * 70)
