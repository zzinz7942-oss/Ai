"""
방금 발행했던 반도체/엔비디아 글(ID: 3066707558046314468)을 신규 6대 검증 함수(validate_specificity, validate_unsourced_stats)에 
넣어 실제로 실패(FAIL)로 정확히 검출되는지 실시간 테스트하는 스크립트
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

POST_ID = "3066707558046314468"

pprint("=" * 70)
pprint("🔬 [신규 6대 검증 함수(specificity / unsourced_stats) 실전 검출 테스트]")
pprint("=" * 70)

service = blogger_client._get_service()

pprint(f"📌 Blogger API에서 포스트(ID: {POST_ID}) 원본 HTML 수집 중...")
post_item = service.posts().get(blogId=config.BLOGGER_BLOG_ID, postId=POST_ID).execute()

title = post_item.get("title", "")
content = post_item.get("content", "")
image_urls = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', content)

pprint(f"📌 수집된 포스트 제목: '{title}'")

# 신규 run_full_validation() 수행
val_result = blog_content_standards.run_full_validation(title, content, image_urls)

pprint("\n" + "=" * 70)
pprint(f"📊 [신규 6대 검증 마스터 결과 리포트]")
pprint("=" * 70)
pprint(f"📌 전체 검증 통과 여부 (passed): {val_result['passed']}")
pprint("\n📋 details 전체 항목 상세:")

for c_name, (c_pass, c_msg) in val_result["details"].items():
    icon = "✅ PASS" if c_pass else "❌ FAIL (검출성공)"
    pprint(f"   {icon} [{c_name}]: {c_msg}")

pprint("\n" + "=" * 70)
if not val_result["passed"]:
    pprint("✅ [검증 로직 정상 동작 확인] 뭉뚱그린 표현/출처 검증 미달이 정상적으로 FAIL로 감지되었습니다!")
else:
    pprint("❌ [오류] 뭉뚱그린 표현이 FAIL로 감지되지 않았습니다.")
pprint("=" * 70)
