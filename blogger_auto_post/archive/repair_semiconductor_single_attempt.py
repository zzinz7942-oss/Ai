"""
반도체 포스트 (ID: 8709539800043420726) max_retries=1 단 1회 보완 실행 및 검증 스크립트
"""

import sys
import os
import json
import re
import time
from pathlib import Path

os.environ["PYTHONUNBUFFERED"] = "1"
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def pprint(*args, **kwargs):
    kwargs["flush"] = True
    print(*args, **kwargs)

import config
import audit_published_posts
import ai_reviewer
import content_builder
import image_fetcher
import blogger_client

TARGET_POST_ID = "8709539800043420726"

pprint("=" * 70)
pprint(f"🛠️ [반도체 포스트 단 1회(max_retries=1) 보완 시도] Post ID: {TARGET_POST_ID}")
pprint("=" * 70)

# 1. Blogger에서 해당 포스트 수신
service = blogger_client._get_service()
try:
    post_raw = service.posts().get(blogId=config.BLOGGER_BLOG_ID, postId=TARGET_POST_ID).execute()
except Exception as e:
    pprint(f"  ❌ 포스트 조회 실패 ({e})")
    sys.exit(1)

semicon_post = audit_published_posts.audit_single_post(post_raw)
title = semicon_post["title"]

pprint(f"📌 대상 포스트 제목: '{title}' (ID: {TARGET_POST_ID})")

# 2. max_retries=1 보완 실행 (재시도 없이 단 1회 실행)
pprint("\n🚀 max_retries=1 지정 repair_post() 1회 단독 실행 중...")
start_time = time.time()
res = audit_published_posts.repair_post(semicon_post, max_retries=1)
elapsed = round(time.time() - start_time, 2)

# 3. 결과 출력
pprint("\n" + "=" * 70)
pprint("📊 [단 1회 시도 최종 결과 리포트]")
pprint(f"  - 소요 시간   : {elapsed}초")
if res.get("success"):
    m = res.get("metrics", {})
    pprint(f"  - 최종 상태   : ✅ 100% 6대 검증 통과 완료 & Blogger 저장 성공")
    pprint(f"  - 순수 글자 수: {m.get('char_count', 0):,}자")
    pprint(f"  - 이미지 개수 : {m.get('image_count', 0)}개")
    pprint(f"  - 해시태그 수 : {m.get('hashtag_count', 0)}개")
    pprint(f"  - 체크포인트 : VERIFIED_AND_SAVED 기록 완료")
else:
    pprint(f"  - 최종 상태   : 🛑 실패 (사유: {res.get('error')})")
    pprint("  - 재시도 없이 즉시 중단되었습니다. 라이브 포스트는 기존대로 보존되었습니다.")
pprint("=" * 70)
