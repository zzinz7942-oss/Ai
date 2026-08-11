@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
title 유튜브 VR 실시간 캡처 플레이어
cd /d "%~dp0"
python yt_vr_player.py
