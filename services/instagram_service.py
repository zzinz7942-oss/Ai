# -*- coding: utf-8 -*-
"""
인스타그램 포스팅 서비스 (Instagram Service)
- instagrapi 라이브러리를 사용한 로그인 및 피드/릴스 자동 게시
"""

import os
from config import get_config, INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD


def post_to_instagram(caption: str, image_path: str | None = None, video_path: str | None = None) -> dict:
    """
    instagrapi를 사용하여 인스타그램 피드에 이미지 또는 비디오를 게시합니다.
    """
    username = get_config(INSTAGRAM_USERNAME)
    password = get_config(INSTAGRAM_PASSWORD)

    if not username or not password:
        return {
            "success": False,
            "error": "인스타그램 아이디(Username) 및 비밀번호(Password) 설정이 필요합니다."
        }

    try:
        from instagrapi import Client
        cl = Client()
        
        # 세션 캐싱 및 로그인
        session_file = "insta_session.json"
        if os.path.exists(session_file):
            try:
                cl.load_settings(session_file)
            except Exception:
                pass
        
        cl.login(username, password)
        cl.dump_settings(session_file)

        media = None
        if video_path and os.path.exists(video_path):
            media = cl.clip_upload(video_path, caption=caption)
        elif image_path and os.path.exists(image_path):
            media = cl.photo_upload(image_path, caption=caption)
        else:
            return {"success": False, "error": "게시할 미디어 파일(이미지/비디오)이 필요합니다."}

        if media and hasattr(media, 'code'):
            return {
                "success": True,
                "media_id": media.pk,
                "post_url": f"https://www.instagram.com/p/{media.code}/"
            }
        else:
            return {"success": True, "media_id": str(media), "post_url": "https://www.instagram.com/"}

    except Exception as e:
        return {"success": False, "error": f"인스타그램 게시 실패: {str(e)}"}
