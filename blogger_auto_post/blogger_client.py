"""
Google Blogger API 클라이언트
- Pure Console OAuth 2.0 인증
- 포스트 생성 및 수정, 이미지 업로드
"""

import json
import base64
import mimetypes
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlparse

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

import config


def _get_credentials() -> Credentials:
    creds = None
    token_path = Path(getattr(config, "GOOGLE_TOKEN_FILE", str(Path(__file__).parent / "token.json")))

    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(
                str(token_path), config.BLOGGER_SCOPES
            )
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"  ⚠️ 기존 토큰 갱신 실패 ({e}). 새 인증을 진행합니다.")
                creds = None

        if not creds or not creds.valid:
            secrets_path = Path(__file__).parent / "client_secrets.json"
            if secrets_path.exists():
                try:
                    from google_auth_oauthlib.flow import InstalledAppFlow
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(secrets_path), config.BLOGGER_SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                    with open(token_path, "w", encoding="utf-8") as f:
                        f.write(creds.to_json())
                    print("  ✅ 새 OAuth 인증 완료 및 token.json 저장 성공!")
                except Exception as e:
                    print(f"  ⚠️ OAuth 인증 실패: {e}")

    return creds


def _get_service():
    creds = _get_credentials()
    return build("blogger", "v3", credentials=creds)


def upload_image_to_blogger(local_path: Path) -> Optional[str]:
    try:
        from googleapiclient.http import MediaFileUpload
        from googleapiclient.discovery import build as gdrive_build

        creds = _get_credentials()
        drive = gdrive_build("drive", "v3", credentials=creds)

        mime, _ = mimetypes.guess_type(str(local_path))
        mime = mime or "image/jpeg"

        file_meta = {"name": local_path.name}
        media = MediaFileUpload(str(local_path), mimetype=mime)
        uploaded = drive.files().create(
            body=file_meta,
            media_body=media,
            fields="id",
        ).execute()

        file_id = uploaded.get("id")

        drive.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"},
        ).execute()

        public_url = f"https://drive.google.com/uc?export=view&id={file_id}"
        print(f"  ☁️  Drive 업로드 완료: {local_path.name} → {public_url}")
        return public_url

    except Exception as e:
        print(f"  ⚠️  이미지 업로드 실패 ({local_path.name}): {e}")
        return None


def upload_post(
    title: str,
    html_content: str,
    labels: Optional[list] = None,
    status: str = getattr(config, "POST_STATUS", "DRAFT"),
    blog_id: str = getattr(config, "BLOGGER_BLOG_ID", ""),
) -> dict:
    labels = labels or getattr(config, "POST_LABELS", ["IT", "기술"])
    if not blog_id:
        raise ValueError("BLOGGER_BLOG_ID 가 설정되지 않았습니다.")

    service = _get_service()
    body = {
        "kind": "blogger#post",
        "title": title,
        "content": html_content,
        "labels": labels,
    }

    is_draft = status.upper() == "DRAFT"
    result = (
        service.posts()
        .insert(blogId=blog_id, body=body, isDraft=is_draft)
        .execute()
    )

    post_url = result.get("url", "(URL 없음)")
    post_id = result.get("id", "")
    status_label = "임시저장" if is_draft else "발행 완료"

    print(f"\n  ✅ 포스트 {status_label}!")
    print(f"     제목  : {title}")
    print(f"     ID    : {post_id}")
    print(f"     URL   : {post_url}")

    return result


def update_post(
    post_id: str,
    title: str,
    html_content: str,
    labels: Optional[list] = None,
    status: str = getattr(config, "POST_STATUS", "DRAFT"),
    blog_id: str = getattr(config, "BLOGGER_BLOG_ID", ""),
) -> dict:
    labels = labels or getattr(config, "POST_LABELS", ["IT", "기술"])
    if not blog_id:
        raise ValueError("BLOGGER_BLOG_ID 가 설정되지 않았습니다.")

    service = _get_service()

    body = {
        "kind": "blogger#post",
        "id": post_id,
        "title": title,
        "content": html_content,
        "labels": labels,
    }

    print(f"\n  🔄 포스트 수정 중 (ID: {post_id})...")
    result = (
        service.posts()
        .patch(blogId=blog_id, postId=post_id, body=body)
        .execute()
    )

    if status.upper() == "LIVE":
        try:
            service.posts().publish(blogId=blog_id, postId=post_id).execute()
        except Exception:
            pass

    post_url = result.get("url", "(URL 없음)")
    print(f"  ✅ 포스트 수정 완료! (ID: {post_id})")

    return result


def get_blog_info(blog_id: str = getattr(config, "BLOGGER_BLOG_ID", "")) -> dict:
    service = _get_service()
    info = service.blogs().get(blogId=blog_id).execute()
    print(f"  📝 블로그 이름: {info.get('name')}")
    print(f"  🔗 블로그 URL : {info.get('url')}")
    return info


def list_all_posts(blog_id: str = getattr(config, "BLOGGER_BLOG_ID", ""), fetch_bodies: bool = True) -> list:
    """블로그에 등록된 모든 게시물 목록 조회"""
    if not blog_id:
        return []
    try:
        service = _get_service()
        result = service.posts().list(blogId=blog_id, fetchBodies=fetch_bodies).execute()
        return result.get("items", [])
    except Exception as e:
        print(f"  ⚠️ 게시물 목록 조회 실패 ({e})")
        return []


def delete_post(post_id: str, blog_id: str = getattr(config, "BLOGGER_BLOG_ID", "")) -> bool:
    """지정한 게시물 삭제"""
    if not blog_id or not post_id:
        return False
    try:
        service = _get_service()
        service.posts().delete(blogId=blog_id, postId=post_id).execute()
        print(f"  🗑️ 게시물 삭제 완료 (ID: {post_id})")
        return True
    except Exception as e:
        print(f"  ⚠️ 게시물 삭제 실패 (ID: {post_id}): {e}")
        return False

