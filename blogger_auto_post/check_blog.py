"""
check_blog.py
Blogger API를 통해 현재 연동된 블로그 정보 및 최근 포스팅 목록(발행/임시저장)을 조회하여 확인하는 스크립트
"""

import sys
import os
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import config
import blogger_client

def check_recent_posts():
    print("=" * 60)
    print("🔍 [Google Blogger 연동 및 최근 포스팅 조회 중...]")
    print("=" * 60)

    try:
        service = blogger_client._get_service()
        if not service:
            print("❌ Blogger API 인증 서비스 생성에 실패했습니다. token.json 또는 client_secrets.json을 확인해주세요.")
            return

        # 1. 로그인 계정 정보 확인
        try:
            user_info = service.users().get(userId='self').execute()
            print(f"👤 로그인 계정: {user_info.get('displayName')} ({user_info.get('id')})")
        except Exception as e:
            print(f"⚠️ 사용자 계정 정보 조회 실패: {e}")

        # 2. 연동된 블로그 목록 확인
        blog_id = getattr(config, "BLOGGER_BLOG_ID", "").strip()
        if blog_id:
            try:
                blog_info = service.blogs().get(blogId=blog_id).execute()
                print(f"📝 설정된 블로그: {blog_info.get('name')} (ID: {blog_id})")
                print(f"🔗 블로그 URL : {blog_info.get('url')}")
            except Exception as e:
                print(f"⚠️ 설정된 블로그 정보 조회 실패 (ID: {blog_id}): {e}")
        else:
            print("⚠️ BLOGGER_BLOG_ID 가 설정되어 있지 않습니다.")

        # 3. 최근 게시글 목록 조회 (LIVE 및 DRAFT 포함)
        print("\n--- 📋 최근 게시글 목록 (최대 10개) ---")
        try:
            posts_res = service.posts().list(
                blogId=blog_id,
                maxResults=10,
                status=["LIVE", "DRAFT"],
                fetchBodies=False
            ).execute()

            items = posts_res.get("items", [])
            if items:
                for idx, post in enumerate(items, 1):
                    p_title = post.get('title', '(제목 없음)')
                    p_url = post.get('url', '(URL 없음 / DRAFT)')
                    p_status = post.get('status', 'LIVE')
                    p_date = post.get('published') or post.get('updated', '')
                    p_id = post.get('id')
                    
                    print(f"{idx}. [{p_status}] {p_title}")
                    print(f"   - ID  : {p_id}")
                    print(f"   - URL : {p_url}")
                    print(f"   - 일시: {p_date}")
                    print("-" * 50)
            else:
                print("ℹ️ 등록된 게시글이 없습니다.")
        except Exception as e:
            print(f"❌ 게시글 목록 조회 실패: {e}")

    except Exception as e:
        print(f"❌ 블로그 조회 중 전체 오류 발생: {e}")

    print("=" * 60)

if __name__ == "__main__":
    check_recent_posts()
