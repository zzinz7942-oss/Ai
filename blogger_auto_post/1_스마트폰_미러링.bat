@echo off
chcp 65001 > nul
title 스마트폰 무선 미러링 (미러링 전용)
cd /d "%~dp0"
python run_scrcpy_record.py
pause
