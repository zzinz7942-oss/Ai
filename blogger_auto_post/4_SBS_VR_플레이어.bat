@echo off
chcp 65001 > nul
title SBS 3D / VR 비디오 실시간 변환 플레이어
cd /d "%~dp0"
python sbs_vr_player.py
pause
