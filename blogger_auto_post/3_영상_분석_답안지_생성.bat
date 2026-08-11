@echo off
chcp 65001 > nul
title 숏폼 영상 AI 분석 및 제작 답안지 생성기
cd /d "%~dp0"
python video_analyzer.py
pause
