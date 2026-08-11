# -*- coding: utf-8 -*-
"""
Threads 자동 업로드 스크립트
Meta Threads API를 사용하여 텍스트 및 이미지를 자동으로 업로드합니다.
"""

import sys
import io
import requests
import time


def _setup_utf8_stdout():
    """Windows 콘솔에서 UTF-8 출력을 설정합니다."""
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ─────────────────────────────────────────────
# 🔑 인증 정보 설정
# ─────────────────────────────────────────────
ACCESS_TOKEN = "THAAW3tcaAYsZABYmI3dklLaDQ2SThBTURNMGJnTXFRZAVZAHZAzZAnZAWlkazYyWFJiX3htUHJ5alBfZAjRQdTNNTlctbHhJZAzJwZAlNZAZAGg0MXFBOVljQmJUcWFyaWdBbUhtSmh3UEduSXRXLVhMWThILV9IMHZAKeHdORFUyQTlkWGgwY2lXVWpRMkJHT3d6X25yZA2cZD"
USER_ID      = "26764051783271031"

BASE_URL = f"https://graph.threads.net/v1.0/{USER_ID}"


# ─────────────────────────────────────────────
# 📝 텍스트 전용 포스트 업로드
# ─────────────────────────────────────────────
def post_text(text: str) -> dict:
    """
    텍스트 전용 쓰레드 포스트를 업로드합니다.
    :param text: 게시할 텍스트 내용
    :return: API 응답 딕셔너리
    """
    print(f"\n📝 텍스트 포스트 업로드 중...\n내용: {text[:50]}{'...' if len(text) > 50 else ''}")

    # Step 1: 미디어 컨테이너 생성
    container_id = _create_text_container(text)
    if not container_id:
        return {"success": False, "error": "컨테이너 생성 실패"}

    # Step 2: 컨테이너 게시
    return _publish_container(container_id)


# ─────────────────────────────────────────────
# 🖼️ 이미지 + 텍스트 포스트 업로드
# ─────────────────────────────────────────────
def post_image(image_url: str, caption: str = "") -> dict:
    """
    이미지(공개 URL)와 선택적 캡션을 포함한 쓰레드 포스트를 업로드합니다.
    :param image_url: 공개적으로 접근 가능한 이미지 URL
    :param caption:   이미지에 첨부할 텍스트 (선택)
    :return: API 응답 딕셔너리
    """
    print(f"\n🖼️  이미지 포스트 업로드 중...\nURL: {image_url}")

    # Step 1: 이미지 미디어 컨테이너 생성
    container_id = _create_image_container(image_url, caption)
    if not container_id:
        return {"success": False, "error": "컨테이너 생성 실패"}

    # Step 2: 처리 완료 대기 (이미지 처리 시간)
    print("⏳ 이미지 처리 대기 중 (5초)...")
    time.sleep(5)

    # Step 3: 컨테이너 게시
    return _publish_container(container_id)


# ─────────────────────────────────────────────
# 🔧 내부 헬퍼 함수들
# ─────────────────────────────────────────────
def _create_text_container(text: str) -> str | None:
    """텍스트 전용 미디어 컨테이너를 생성하고 container_id를 반환합니다."""
    url = f"{BASE_URL}/threads"
    params = {
        "media_type": "TEXT",
        "text": text,
        "access_token": ACCESS_TOKEN,
    }

    response = requests.post(url, params=params)
    data = response.json()

    if response.status_code == 200 and "id" in data:
        print(f"✅ 컨테이너 생성 성공 | ID: {data['id']}")
        return data["id"]
    else:
        print(f"❌ 컨테이너 생성 실패: {data}")
        return None


def _create_image_container(image_url: str, caption: str = "") -> str | None:
    """이미지 미디어 컨테이너를 생성하고 container_id를 반환합니다."""
    url = f"{BASE_URL}/threads"
    params = {
        "media_type": "IMAGE",
        "image_url": image_url,
        "access_token": ACCESS_TOKEN,
    }
    if caption:
        params["text"] = caption

    response = requests.post(url, params=params)
    data = response.json()

    if response.status_code == 200 and "id" in data:
        print(f"✅ 이미지 컨테이너 생성 성공 | ID: {data['id']}")
        return data["id"]
    else:
        print(f"❌ 이미지 컨테이너 생성 실패: {data}")
        return None


def _publish_container(container_id: str) -> dict:
    """생성된 컨테이너를 Threads에 실제로 게시합니다."""
    url = f"{BASE_URL}/threads_publish"
    params = {
        "creation_id": container_id,
        "access_token": ACCESS_TOKEN,
    }

    response = requests.post(url, params=params)
    data = response.json()

    if response.status_code == 200 and "id" in data:
        post_id = data["id"]
        print(f"🎉 업로드 완료! 포스트 ID: {post_id}")
        print(f"🔗 확인: https://www.threads.net/post/{post_id}")
        return {"success": True, "post_id": post_id}
    else:
        print(f"❌ 게시 실패: {data}")
        return {"success": False, "error": data}


# ─────────────────────────────────────────────
# 📤 로컬 이미지 → catbox.moe 업로드
# ─────────────────────────────────────────────
def upload_to_catbox(file_path: str) -> str | None:
    """
    로컬 이미지 파일을 catbox.moe에 업로드하고 공개 URL을 반환합니다.
    API 키 불필요, 무료, 직접 HTTPS URL 반환.
    :param file_path: 로컬 이미지 파일 경로
    :return: 공개 URL (예: https://files.catbox.moe/xxxxx.png) 또는 None
    """
    import os
    if not os.path.exists(file_path):
        print(f"❌ 파일을 찾을 수 없습니다: {file_path}")
        return None

    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    print(f"📤 catbox.moe 업로드 중... ({file_size_mb:.1f}MB)")

    url = "https://catbox.moe/user/api.php"
    with open(file_path, "rb") as f:
        files = {"fileToUpload": (os.path.basename(file_path), f)}
        data = {"reqtype": "fileupload"}
        response = requests.post(url, data=data, files=files, timeout=60)

    if response.status_code == 200 and response.text.startswith("https://"):
        public_url = response.text.strip()
        print(f"✅ 업로드 성공: {public_url}")
        return public_url
    else:
        print(f"❌ catbox.moe 업로드 실패: {response.status_code} {response.text}")
        return None


# ─────────────────────────────────────────────
# 🖼️ 로컬 이미지 → Threads 포스트
# ─────────────────────────────────────────────
def post_local_image(file_path: str, caption: str = "") -> dict:
    """
    로컬 이미지 파일을 Threads에 업로드합니다.
    1) catbox.moe에 업로드하여 공개 URL 확보
    2) 공개 URL로 Threads에 이미지 포스트 게시
    :param file_path: 로컬 이미지 파일 경로 (JPEG/PNG)
    :param caption:   이미지에 첨부할 텍스트 (선택)
    :return: API 응답 딕셔너리
    """
    print(f"\n🖼️  로컬 이미지 → Threads 업로드 중...\n파일: {file_path}")

    # Step 1: catbox.moe에 업로드
    public_url = upload_to_catbox(file_path)
    if not public_url:
        return {"success": False, "error": "이미지 호스팅 업로드 실패"}

    # Step 2: 공개 URL로 Threads에 게시
    return post_image(public_url, caption)


# ─────────────────────────────────────────────
# ▶️  실행 예시
# ─────────────────────────────────────────────
if __name__ == "__main__":
    _setup_utf8_stdout()
    print("=" * 50)
    print("   🚀 Threads 자동 업로더 시작")
    print("=" * 50)

    # ── 예시 1: 텍스트 포스트 ──────────────────
    result1 = post_text(
        "안녕하세요! 파이썬으로 자동 업로드한 첫 번째 쓰레드 포스트입니다 🐍✨"
    )
    print(f"\n결과: {result1}")

    print("\n" + "─" * 50)

    # ── 예시 2: 이미지 + 캡션 포스트 ──────────
    # Wikipedia의 실제 JPEG 이미지 (Threads API 호환 확인된 도메인)
    result2 = post_image(
        image_url="https://upload.wikimedia.org/wikipedia/commons/a/a7/Camponotus_flavomarginatus_ant.jpg",
        caption="파이썬으로 자동 업로드한 이미지 포스트입니다! 🐍"
    )
    print(f"\n결과: {result2}")
