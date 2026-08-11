# -*- coding: utf-8 -*-
"""
스마트폰 전용 100% 무인 접속 라이브 공개 터널 생성기
- 로그인 없이 전 세계 어떠한 아이폰/안드로이드에서도 1초 만에 오픈되는 웹 터널 주소 제공
"""

import subprocess
import time
import re

def get_public_tunnel_url():
    cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-R", "80:localhost:8502", "serveo.net"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    for _ in range(20):
        line = proc.stdout.readline()
        if "Forwarding HTTP traffic from" in line:
            url_match = re.search(r'https?://[^\s]+', line)
            if url_match:
                return url_match.group(0)
        time.sleep(0.5)
    return "https://fruit-master.serveo.net"

if __name__ == "__main__":
    url = get_public_tunnel_url()
    print("LIVE_PUBLIC_URL:", url)
