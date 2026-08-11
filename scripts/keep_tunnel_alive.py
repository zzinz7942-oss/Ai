# -*- coding: utf-8 -*-
"""
24시간 365일 무한 하트비트 재연결 SSH 공개 터널 데몬
- ServerAliveInterval=10 으로 타임아웃 방지
- 끊길 시 1초 만에 자동 재연결
"""

import subprocess
import time
import re

def run_persistent_tunnel():
    cmd = [
        "ssh",
        "-o", "StrictHostKeyChecking=no",
        "-o", "ServerAliveInterval=10",
        "-o", "ServerAliveCountMax=99999",
        "-R", "80:localhost:8502",
        "nokey@localhost.run"
    ]
    
    while True:
        try:
            print("[TUNNEL] Starting SSH tunnel with 10s keepalive...")
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            
            for _ in range(30):
                line = proc.stdout.readline()
                if "lhr.life" in line:
                    urls = re.findall(r'https://[a-zA-Z0-9\.\-]+\.lhr\.life', line)
                    if urls:
                        print(f"LIVE_PUBLIC_URL: {urls[0]}")
                        with open("c:/Users/picaf/Desktop/Ai/live_url.txt", "w", encoding="utf-8") as f:
                            f.write(urls[0])
            
            proc.wait()
        except Exception as e:
            print(f"[TUNNEL ERROR] {e}")
        
        time.sleep(2)

if __name__ == "__main__":
    run_persistent_tunnel()
