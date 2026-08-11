@echo off
chcp 65001 > nul
title 360도 VR 비디오 데스크톱 플레이어
cd /d "%~dp0"
python player_360.py
pause
