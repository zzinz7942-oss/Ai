# -*- coding: utf-8 -*-
import subprocess
import time
import re

def get_pinggy_url():
    cmd = ["ssh", "-p", "443", "-o", "StrictHostKeyChecking=no", "-R", "0:localhost:8502", "free@a.pinggy.io"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    for _ in range(30):
        line = proc.stdout.readline()
        if "pinggy.link" in line or "pinggy.io" in line:
            urls = re.findall(r'https://[a-zA-Z0-9\.\-]+\.pinggy\.[a-z]+', line)
            if urls:
                return urls[0]
        time.sleep(0.5)
    return "FAILED"

if __name__ == "__main__":
    url = get_pinggy_url()
    print("PINGGY_LIVE_URL:", url)
