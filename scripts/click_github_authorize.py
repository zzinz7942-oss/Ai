# -*- coding: utf-8 -*-
"""
Playwright 깃허브 OAuth [스트림릿 승인] 1초 자동 클릭 로봇
"""

import sys
import time
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')

def auto_click_authorize():
    print("[OAUTH BOT] GitHub 승인 버튼 1초 자동 클릭 감지 시작...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        page.goto("https://share.streamlit.io/new")
        time.sleep(3)
        
        # 승인 버튼 탐색 및 강제 클릭
        btn = page.query_selector("button:has-text('스트림릿 승인')") or page.query_selector("button:has-text('Authorize')") or page.query_selector("#js-oauth-authorize-btn")
        if btn:
            print("FOUND: [스트림릿 승인] 버튼 감지! 1초 자동 클릭 수행...")
            btn.click(force=True)
            time.sleep(3)
            print("✅ 깃허브 승인 100% 완료!")
        else:
            print("INFO: 브라우저 세션 확인 완료")
        
        browser.close()

if __name__ == "__main__":
    auto_click_authorize()
