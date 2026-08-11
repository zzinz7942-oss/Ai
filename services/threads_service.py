# -*- coding: utf-8 -*-
"""
Threads 포스팅 서비스 (Threads Service)
- Meta Threads API 연동
- 텍스트 포스트 게시
- 로컬 이미지 (catbox.moe 업로드 후) 게시
"""

import os
import time
import requests
from typing import Optional
from config import get_config, THREADS_ACCESS_TOKEN, THREADS_USER_ID


def upload_to_catbox(file_path: str) -> Optional[str]:
    """
    로컬 이미지 파일을 catbox.moe에 업로드하고 공개 URL을 반환합니다.
    """
    if not os.path.exists(file_path):
        return None

    url = "https://catbox.moe/user/api.php"
    try:
        with open(file_path, "rb") as f:
            files = {"fileToUpload": (os.path.basename(file_path), f)}
            data = {"reqtype": "fileupload"}
            response = requests.post(url, data=data, files=files, timeout=60)

        if response.status_code == 200 and response.text.startswith("https://"):
            return response.text.strip()
    except Exception as e:
        print(f"Catbox 업로드 오류: {e}")
    
    return None


def post_to_threads(text: str, image_path: Optional[str] = None) -> dict:
    """
    Threads에 텍스트 또는 이미지+텍스트 포스트를 업로드합니다.
    """
    access_token = get_config(THREADS_ACCESS_TOKEN)
    user_id = get_config(THREADS_USER_ID)

    if not access_token or not user_id:
        return {
            "success": False,
            "error": "Threads Access Token 및 User ID 설정이 필요합니다."
        }

    base_url = f"https://graph.threads.net/v1.0/{user_id}"

    try:
        container_id = None

        if image_path and os.path.exists(image_path):
            # 1. 로컬 이미지 -> catbox.moe 업로드
            public_url = upload_to_catbox(image_path)
            if not public_url:
                return {"success": False, "error": "이미지 호스팅 업로드에 실패했습니다."}

            # 2. 이미지 미디어 컨테이너 생성
            url = f"{base_url}/threads"
            params = {
                "media_type": "IMAGE",
                "image_url": public_url,
                "text": text,
                "access_token": access_token
            }
            res = requests.post(url, params=params)
            data = res.json()
            if res.status_code == 200 and "id" in data:
                container_id = data["id"]
                # 이미지 처리 대기
                time.sleep(5)
            else:
                return {"success": False, "error": f"Threads 컨테이너 생성 실패: {data}"}
        else:
            # 텍스트 컨테이너 생성
            url = f"{base_url}/threads"
            params = {
                "media_type": "TEXT",
                "text": text,
                "access_token": access_token
            }
            res = requests.post(url, params=params)
            data = res.json()
            if res.status_code == 200 and "id" in data:
                container_id = data["id"]
            else:
                return {"success": False, "error": f"Threads 컨테이너 생성 실패: {data}"}

        # 3. 컨테이너 게시 (Publish)
        pub_url = f"{base_url}/threads_publish"
        pub_params = {
            "creation_id": container_id,
            "access_token": access_token
        }
        pub_res = requests.post(pub_url, params=pub_params)
        pub_data = pub_res.json()

        if pub_res.status_code == 200 and "id" in pub_data:
            post_id = pub_data["id"]
            return {
                "success": True,
                "post_id": post_id,
                "post_url": f"https://www.threads.net/post/{post_id}"
            }
        else:
            return {"success": False, "error": f"Threads 게시 실패: {pub_data}"}

    except Exception as e:
        return {"success": False, "error": f"Threads 업로드 예외: {str(e)}"}
