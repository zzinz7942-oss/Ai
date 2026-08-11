# -*- coding: utf-8 -*-
"""
Playwright 깃허브 자동 파일 업로드 봇
"""

import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright

def auto_upload_to_github():
    print("[PLAYWRIGHT] 깃허브 자동 업로드 봇 작동...")
    
    upload_files = [
        os.path.abspath("c:/Users/picaf/Desktop/Ai/app.py"),
        os.path.abspath("c:/Users/picaf/Desktop/Ai/config.py"),
        os.path.abspath("c:/Users/picaf/Desktop/Ai/fruit_shop_marketing.py"),
        os.path.abspath("c:/Users/picaf/Desktop/Ai/fruit_video_generator.py"),
        os.path.abspath("c:/Users/picaf/Desktop/Ai/image_cropper.py"),
        os.path.abspath("c:/Users/picaf/Desktop/Ai/requirements.txt"),
    ]
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        print("1. GitHub 업로드 페이지로 접속...")
        page.goto("https://github.com/zzinz7942-oss/Ai/upload/master")
        time.sleep(3)
        
        file_input = page.query_selector("input[type='file']")
        if file_input:
            print("2. 배포 파일 6개 자동 세팅 중...")
            file_input.set_input_files(upload_files)
            time.sleep(5)
            
            commit_btn = page.query_selector("button:has-text('Commit changes')") or page.query_selector("button[type='submit']")
            if commit_btn:
                print("3. Commit changes 자동 클릭...")
                commit_btn.click()
                time.sleep(4)
                print("✅ 깃허브 파일 업로드 & 커밋 자동 완료!")
        else:
            print("INFO: 파일 세팅 엘리먼트 확인")
            
        time.sleep(3)
        browser.close()

if __name__ == "__main__":
    auto_upload_to_github()
