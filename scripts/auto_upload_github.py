# -*- coding: utf-8 -*-
"""
안티그래피티 전용 깃허브 자동 파일 업로드 & 배포 자동화
"""

import os
import sys

def prepare_deployment_files():
    print("[AUTOUPLOAD] Preparing clean file list for cloud deployment...")
    essential_files = [
        "app.py",
        "config.py",
        "fruit_shop_marketing.py",
        "fruit_video_generator.py",
        "image_cropper.py",
        "requirements.txt",
        ".streamlit/config.toml"
    ]
    
    for f in essential_files:
        full_p = os.path.join("c:/Users/picaf/Desktop/Ai", f)
        if os.path.exists(full_p):
            print(f"  - {f}: OK ({os.path.getsize(full_p)} bytes)")
        else:
            print(f"  - {f}: MISSING")

if __name__ == "__main__":
    prepare_deployment_files()
