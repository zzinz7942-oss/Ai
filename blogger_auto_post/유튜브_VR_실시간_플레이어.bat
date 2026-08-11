@echo off
chcp 65001 > nul
title 유튜브 VR 실시간 캡처 플레이어
cd /d "%~dp0"
python youtube_vr_player.py
pause
