"""
Blogger에 이미 발행된 모든 글의 <img> src URL을 파싱하여 used_images.json에 초기 저장하는 스크립트
"""

import sys
import os
import json
import re
from pathlib import Path

os.environ["PYTHONUNBUFFERED"] = "1"
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import config
import blogger_client

ROOT_USED_IMAGES_PATH = Path("c:/Users/picaf/Desktop/Ai/blogger_auto_post/used_images.json")
LOGS_USED_IMAGES_PATH = config.USED_IMAGES_PATH

print("🔍 Blogger API에서 이미 발행된 모든 포스트 수집 중...")
service = blogger_client._get_service()

used_urls = set()

# 기존 used_images.json 파일이 있으면 먼저 불러오기
for p in [ROOT_USED_IMAGES_PATH, LOGS_USED_IMAGES_PATH]:
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, str):
                            used_urls.add(item)
                        elif isinstance(item, dict) and "url" in item:
                            used_urls.add(item["url"])
        except Exception as e:
            print(f"  ⚠️ {p} 읽기 오류: {e}")

page_token = None
total_posts = 0

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

        total_posts += len(items)
        for item in items:
            body = item.get("content", "")
            img_srcs = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', body, re.IGNORECASE)
            for src in img_srcs:
                if src.startswith("http"):
                    used_urls.add(src)

        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    except Exception as e:
        print(f"  ⚠️ Blogger API 수집 중 예외 발생: {e}")
        break

print(f"✅ 총 {total_posts}개 발행 글에서 {len(used_urls)}개의 이미지 URL을 파싱하여 used_images.json 구축 완료!")

# 루트 및 logs 폴더 모두 저장
used_list = sorted(list(used_urls))
with open(ROOT_USED_IMAGES_PATH, "w", encoding="utf-8") as f:
    json.dump(used_list, f, ensure_ascii=False, indent=2)

with open(LOGS_USED_IMAGES_PATH, "w", encoding="utf-8") as f:
    json.dump(used_list, f, ensure_ascii=False, indent=2)

print(f"💾 {ROOT_USED_IMAGES_PATH.resolve()} 저장 완료 ({len(used_list)}개 저장됨)")
