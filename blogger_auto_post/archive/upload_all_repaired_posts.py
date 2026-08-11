"""
최종 정제 완료된 챗GPT 포스트 및 노키아 포스트를 100% 실시간 Unsplash API 이미지와 함께 
구글 블로그(Blogger) API에 라이브 업로드 완수 스크립트
"""

import sys
import os
import json
import re
import time

os.environ["PYTHONUNBUFFERED"] = "1"
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def pprint(*args, **kwargs):
    kwargs["flush"] = True
    print(*args, **kwargs)

import config
import ai_reviewer
import content_builder
import image_fetcher
import blogger_client
import audit_published_posts

POST_CHATGPT_ID = "6382120232107273778"
POST_NOKIA_ID   = "1458913389770687536"

pprint("=" * 70)
pprint("🚀 [최종 정제 포스트 실시간 Unsplash API 이미지 탑재 & 라이브 업로드]")
pprint("=" * 70)

service = blogger_client._get_service()

def upload_live_post(post_id: str):
    post_item = service.posts().get(blogId=config.BLOGGER_BLOG_ID, postId=post_id).execute()
    title = post_item.get("title", "")
    html_content = post_item.get("content", "")
    labels = post_item.get("labels", [])

    pprint(f"\n📌 [포스트 라이브 업로드] ID: {post_id} | 제목: '{title}'")

    # 소제목 파싱
    headings = re.findall(r'<h[23]>(.*?)</h[23]>', html_content)
    if not headings:
        headings = ["개요 및 배경", "핵심 작동 메커니즘", "실전 활용 가이드"]

    # 100% 실시간 Unsplash API 이미지 수집 (used_images.json 중복 체크)
    img_bundle = image_fetcher.generate_images_for_post(title, headings)

    images = {}
    if img_bundle.get("thumbnail"):
        images["thumbnail"] = img_bundle["thumbnail"]

    for idx, sec_img in enumerate(img_bundle.get("sections", []), 1):
        if sec_img:
            images[f"section_{idx}"] = sec_img

    # 본문 텍스트 추출 및 HTML 재구성
    clean_text = re.sub(r'<div class="post-image-wrap">.*?</div>', '', html_content, flags=re.DOTALL)
    clean_text = re.sub(r'<style>.*?</style>', '', clean_text, flags=re.DOTALL)
    clean_text = re.sub(r'<[^>]+>', '', clean_text)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()

    final_html = content_builder.build_html(clean_text, images, hosted_urls={}, labels=labels)
    final_html = re.sub(r'<figcaption>.*?</figcaption>', '', final_html, flags=re.DOTALL)
    final_html = re.sub(r'Tech Graphic', '', final_html)

    body = {
        "title": title,
        "content": final_html,
        "labels": labels
    }

    updated_post = service.posts().patch(
        blogId=config.BLOGGER_BLOG_ID,
        postId=post_id,
        body=body
    ).execute()

    live_url = updated_post.get("url", "")
    
    raw_html_text = re.sub(r'<[^>]+>', ' ', final_html)
    raw_html_text = re.sub(r'\s+', ' ', raw_html_text).strip()

    audit_published_posts.save_repaired_checkpoint(
        post_id=post_id,
        title=title,
        char_count=len(raw_html_text),
        image_count=len(images)
    )

    pprint(f"✅ 라이브 업로드 성공!")
    pprint(f"   - 라이브 URL  : {live_url}")
    pprint(f"   - 탑재 이미지 : {len(images)}개 (100% Live Unsplash API 수집)")
    pprint(f"   - 순수 글자수 : {len(raw_html_text):,}자")
    return live_url, len(images), len(raw_html_text)

# 1. 챗GPT 포스트 라이브 업로드
url_chatgpt, img_chatgpt, char_chatgpt = upload_live_post(POST_CHATGPT_ID)

# 2. 노키아 포스트 라이브 업로드
url_nokia, img_nokia, char_nokia = upload_live_post(POST_NOKIA_ID)

# 최종 요약 보고
pprint("\n" + "=" * 70)
pprint("🎉 [최종 라이브 업로드 완수 리포트]")
pprint("=" * 70)
pprint(f"1. 챗GPT 포스트:")
pprint(f"   - URL : {url_chatgpt}")
pprint(f"   - 이미지 : {img_chatgpt}개 (LIVE API 수집)")
pprint(f"   - 글자수 : {char_chatgpt:,}자")

pprint(f"\n2. 노키아 포스트:")
pprint(f"   - URL : {url_nokia}")
pprint(f"   - 이미지 : {img_nokia}개 (LIVE API 수집)")
pprint(f"   - 글자수 : {char_nokia:,}자")
pprint("=" * 70)
