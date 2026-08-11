# -*- coding: utf-8 -*-
"""
네이버 블로그 자동 포스팅 및 임시저장 전용 봇 (Naver Blog Automation Bot)
- Playwright 기반 네이버 자동 로그인 및 스마트에디터 원클릭 포스팅/임시저장
- 저품질 방지를 위해 '임시저장(Draft)' 모드 및 '실시간 발행(Publish)' 모드 모두 지원
"""

import os
import time
import tempfile
from playwright.sync_api import sync_playwright


def run_naver_blog_bot(
    naver_id: str,
    naver_pw: str,
    title: str,
    content: str,
    image_paths: list = None,
    mode: str = "draft"  # "draft" (임시저장-안전) 또는 "publish" (바로발행)
) -> dict:
    """
    Playwright를 사용하여 네이버 블로그 스마트에디터에 자동으로 글과 사진을 등록합니다.
    """
    if not (naver_id and naver_pw):
        return {"success": False, "error": "네이버 아이디와 비밀번호가 설정되지 않았습니다."}

    if image_paths is None:
        image_paths = []

    try:
        with sync_playwright() as p:
            # 브라우저 실행
            browser = p.chromium.launch(headless=False, args=["--no-sandbox", "--disable-setuid-sandbox"])
            context = browser.new_context(viewport={"width": 1280, "height": 900})
            page = context.new_page()

            # 1. 네이버 로그인 페이지 이동
            page.goto("https://nid.naver.com/nidlogin.login")
            page.wait_for_timeout(1000)

            # 아이디 / 비밀번호 입력 (클립보드 스타일 딜레이 대입)
            page.fill("#id", naver_id)
            page.wait_for_timeout(500)
            page.fill("#pw", naver_pw)
            page.wait_for_timeout(500)

            # 로그인 버튼 클릭
            page.click("#log\.login")
            page.wait_for_timeout(2000)

            # 2차 인증이나 캡차 요청 여부 확인
            if "nidlogin" in page.url:
                browser.close()
                return {
                    "success": False,
                    "error": "네이버 2차 보안인증(OTP/기기등록)이 필요합니다. 보안인증을 해제하시거나 1회 수동 로그인해 주세요."
                }

            # 2. 네이버 블로그 스마트 에디터 이동
            blog_editor_url = f"https://blog.naver.com/{naver_id}?Redirect=Write"
            page.goto(blog_editor_url)
            page.wait_for_timeout(3000)

            # 프레임 전환 (mainFrame)
            frame = page.frame(name="mainFrame")
            if not frame:
                frame = page

            # 도움말 팝업 닫기 (있을 경우)
            try:
                frame.click(".se-popup-close-button", timeout=2000)
            except Exception:
                pass

            # 3. 제목 및 본문 입력
            # 제목 입력
            try:
                frame.click(".se-ff-nanumgothic.se-fs32", timeout=3000)
                frame.type(".se-ff-nanumgothic.se-fs32", title)
            except Exception:
                # 일반 제목 클립보드
                frame.type(".se-documentTitle", title)

            page.wait_for_timeout(1000)

            # 본문 입력
            try:
                frame.click(".se-main-container", timeout=3000)
                frame.type(".se-main-container", content)
            except Exception:
                pass

            page.wait_for_timeout(1500)

            # 4. 사진 첨부 (있을 경우)
            if image_paths and os.path.exists(image_paths[0]):
                try:
                    # 파일 업로더 파일 세팅
                    with page.expect_file_chooser() as fc_info:
                        frame.click(".se-image-toolbar-button", timeout=3000)
                    file_chooser = fc_info.value
                    file_chooser.set_files([p for p in image_paths if os.path.exists(p)])
                    page.wait_for_timeout(2000)
                except Exception as e:
                    print(f"사진 첨부 예외: {e}")

            # 5. 임시저장 vs 바로발행 처리
            if mode == "draft":
                try:
                    frame.click(".se-save-button", timeout=3000)
                    page.wait_for_timeout(2000)
                    browser.close()
                    return {
                        "success": True,
                        "mode": "draft",
                        "msg": f"🎉 네이버 블로그에 글이 성공적으로 [임시저장] 되었습니다! (블로그에서 [발행]만 누르시면 저품질 제재 없이 가장 안전합니다.)"
                    }
                except Exception as e:
                    browser.close()
                    return {"success": False, "error": f"임시저장 실패: {e}"}

            else:  # publish 바로 발행
                try:
                    frame.click(".se-publish-btn", timeout=3000)
                    page.wait_for_timeout(1500)
                    frame.click(".confirm_btn", timeout=3000)
                    page.wait_for_timeout(3000)
                    browser.close()
                    return {
                        "success": True,
                        "mode": "publish",
                        "msg": "🎉 네이버 블로그 포스팅이 즉시 자동 발행되었습니다!"
                    }
                except Exception as e:
                    browser.close()
                    return {"success": False, "error": f"자동 발행 실패: {e}"}

    except Exception as e:
        return {"success": False, "error": f"네이버 봇 실행 실패: {e}"}
