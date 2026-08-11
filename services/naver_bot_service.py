# -*- coding: utf-8 -*-
"""
네이버 블로그 자동 포스팅 및 임시저장 전용 봇 (Naver Blog Automation Bot)
- Cloud 환경 호환성을 위해 더미 처리됨 (Playwright 제거)
"""

def run_naver_blog_bot(
    naver_id: str,
    naver_pw: str,
    title: str,
    content: str,
    image_paths: list = None,
    mode: str = "draft"
) -> dict:
    return {"success": False, "error": "Cloud 서버(Linux)에서는 네이버 봇(Playwright) 사용이 제한됩니다. 로컬 환경에서 실행해주세요."}
