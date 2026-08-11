@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
title PC 카카오톡 - 텔레그램 실시간 연동 봇
cd /d "C:\Users\picaf\Desktop"
python "C:\Users\picaf\Desktop\kakao_to_tele.py"
pause
