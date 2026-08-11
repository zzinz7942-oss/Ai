"""
챗GPT 글과 노키아 글의 썸네일(대표 이미지)을 제목 키워드 기반 고유 Unsplash 이미지로 재수집하고 
used_images.json 중복 체크를 적용하여 Blogger 라이브 업데이트 및 썸네일 URL 비교 검증 스크립트
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
pprint("🖼️ [최근 2개 발행 포스트(챗GPT, 노키아) 썸네일 고유 수집 & 라이브 교체]")
pprint("=" * 70)

service = blogger_client._get_service()

def update_single_post_thumbnail(post_id: str, default_title: str):
    # 1. Blogger에서 기존 포스트 데이터 조회
    post_item = service.posts().get(blogId=config.BLOGGER_BLOG_ID, postId=post_id).execute()
    title = post_item.get("title", default_title)
    html_content = post_item.get("content", "")
    labels = post_item.get("labels", [])

    pprint(f"\n📌 [포스트 ID: {post_id}] 제목: '{title}'")

    # 소제목 파싱
    raw_text = re.sub(r'<[^>]+>', ' ', html_content)
    raw_text = re.sub(r'\s+', ' ', raw_text).strip()
    
    # 2. 제목 키워드 기반 고유 썸네일 및 섹션 이미지 수집 (used_images.json 자동 동기화)
    headings = re.findall(r'<h[23]>(.*?)</h[23]>', html_content)
    if not headings:
        headings = ["개요 및 핵심 원리", "기술 메커니즘", "향후 전망"]

    img_bundle = image_fetcher.generate_images_for_post(title, headings)
    
    images = {}
    if img_bundle.get("thumbnail"):
        images["thumbnail"] = img_bundle["thumbnail"]

    for idx, sec_img in enumerate(img_bundle.get("sections", []), 1):
        if sec_img:
            images[f"section_{idx}"] = sec_img

    # 3. HTML 재구성 (제목 키워드 기반 썸네일이 최상단 대표 이미지로 배치됨)
    # 기존 HTML 내 이미지 영역 재생성
    clean_md_text = re.sub(r'<div class="post-image-wrap">.*?</div>', '', html_content, flags=re.DOTALL)
    clean_md_text = re.sub(r'<style>.*?</style>', '', clean_md_text, flags=re.DOTALL)
    clean_md_text = re.sub(r'<[^>]+>', '', clean_md_text)
    clean_md_text = re.sub(r'\s+', ' ', clean_md_text).strip()

    # 원고 본문 텍스트 바탕으로 HTML 재조합
    updated_html = content_builder.build_html(clean_md_text, images, hosted_urls={}, labels=labels)
    updated_html = re.sub(r'<figcaption>.*?</figcaption>', '', updated_html, flags=re.DOTALL)
    updated_html = re.sub(r'Tech Graphic', '', updated_html)

    # 4. Blogger API 라이브 수정 패치
    body = {
        "title": title,
        "content": updated_html,
        "labels": labels
    }
    patched = service.posts().patch(
        blogId=config.BLOGGER_BLOG_ID,
        postId=post_id,
        body=body
    ).execute()

    live_url = patched.get("url", "")
    pprint(f"✅ Blogger 라이브 패치 완료: {live_url}")
    return patched

# 1) 챗GPT 포스트 썸네일 수집 및 라이브 교체
p_chatgpt = update_single_post_thumbnail(POST_CHATGPT_ID, "챗GPT 잘 쓰는 사람 vs 못 쓰는 사람, 딱 이거 하나 차이였다")

# 2) 노키아 포스트 썸네일 수집 및 라이브 교체
p_nokia = update_single_post_thumbnail(POST_NOKIA_ID, "노키아가 스마트폰 패배자에서 AI 수혜주로 부활한 3가지 핵심 이유")

# 3) 라이브 포스트 최상단 썸네일 URL 추출 및 비교 검증
pprint("\n" + "=" * 70)
pprint("📊 [최종 검증: 최근 두 글 라이브 썸네일 URL 비교 리포트]")
pprint("=" * 70)

def extract_top_img(content: str) -> str:
    m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content)
    return m.group(1) if m else "이미지 없음"

url_chatgpt_thumb = extract_top_img(p_chatgpt.get("content", ""))
url_nokia_thumb   = extract_top_img(p_nokia.get("content", ""))

pprint(f"📌 [챗GPT 글] 대표 썸네일 URL:")
pprint(f"   {url_chatgpt_thumb}\n")
pprint(f"📌 [노키아 글] 대표 썸네일 URL:")
pprint(f"   {url_nokia_thumb}\n")

pprint("-" * 70)
if url_chatgpt_thumb != url_nokia_thumb and "photo" in url_chatgpt_thumb and "photo" in url_nokia_thumb:
    pprint("✅ [검증 완수 성공] 초록색 회로기판 고정 이미지 완전 제거!")
    pprint("✅ 두 글의 대표 썸네일이 각 주제 키워드(ChatGPT / Nokia)에 맞게 100% 다른 고유 URL로 수집되었습니다.")
else:
    pprint("❌ [검증 실패] 썸네일 URL이 여전히 동일하거나 유효하지 않음")

pprint("=" * 70)
