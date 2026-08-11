@echo off
chcp 65001 > nul
title 스마트폰 무선 숏폼 녹화 (recorded_shorts 자동 저장)
cd /d "%~dp0"
python run_scrcpy_record.py -r
pause
