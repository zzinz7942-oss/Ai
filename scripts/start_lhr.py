# -*- coding: utf-8 -*-
import subprocess
import time
import re

def get_lhr_url():
    cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-R", "80:localhost:8502", "nokey@localhost.run"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    for _ in range(30):
        line = proc.stdout.readline()
        if "lhr.life" in line:
            urls = re.findall(r'https://[a-zA-Z0-9\.\-]+\.lhr\.life', line)
            if urls:
                return urls[0]
        time.sleep(0.5)
    return "FAILED"

if __name__ == "__main__":
    url = get_lhr_url()
    print("LHR_LIVE_URL:", url)
