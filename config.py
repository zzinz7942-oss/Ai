# -*- coding: utf-8 -*-
"""
설정 및 환경 변수 로더 모듈
"""

import os
from dotenv import load_dotenv
import streamlit as st

# .env 로드 (UTF-8 BOM 및 시스템 환경변수 오버라이드 대응)
load_dotenv(override=True, encoding='utf-8-sig')

# 기본 Threads 토큰 및 유저 ID 폴백
DEFAULT_THREADS_TOKEN = "THAAW3tcaAYsZABYmI3dklLaDQ2SThBTURNMGJnTXFRZAVZAHZAzZAnZAWlkazYyWFJiX3htUHJ5alBfZAjRQdTNNTlctbHhJZAzJwZAlNZAZAGg0MXFBOVljQmJUcWFyaWdBbUhtSmh3UEduSXRXLVhMWThILV9IMHZAKeHdORFUyQTlkWGgwY2lXVWpRMkJHT3d6X25yZA2cZD"
DEFAULT_THREADS_USER_ID = "26764051783271031"


def get_config(key: str, default: str = "") -> str:
    """
    st.session_state, os.environ, 또는 기본 폴백값에서 설정값을 가져옵니다.
    """
    if f"cfg_{key}" in st.session_state and st.session_state[f"cfg_{key}"]:
        return st.session_state[f"cfg_{key}"]
    
    val = os.getenv(key, "")
    if val:
        return val
    
    # Threads 기본값 자동 적용
    if key == THREADS_ACCESS_TOKEN:
        return DEFAULT_THREADS_TOKEN
    elif key == THREADS_USER_ID:
        return DEFAULT_THREADS_USER_ID

    return default


def set_config(key: str, value: str):
    """
    Streamlit 세션 상태 및 환경 변수에 설정값을 저장합니다.
    """
    st.session_state[f"cfg_{key}"] = value
    os.environ[key] = value

    # .env 파일 생성/업데이트
    env_file = ".env"
    env_vars = {}
    if os.path.exists(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.strip().split("=", 1)
                    env_vars[k.strip()] = v.strip()
    
    env_vars[key] = value

    with open(env_file, "w", encoding="utf-8") as f:
        for k, v in env_vars.items():
            f.write(f"{k}={v}\n")


# 주요 키 이름 정의
COUPANG_ACCESS_KEY = "COUPANG_ACCESS_KEY"
COUPANG_SECRET_KEY = "COUPANG_SECRET_KEY"
COUPANG_SUB_ID = "COUPANG_SUB_ID"

THREADS_ACCESS_TOKEN = "THREADS_ACCESS_TOKEN"
THREADS_USER_ID = "THREADS_USER_ID"

INSTAGRAM_USERNAME = "INSTAGRAM_USERNAME"
INSTAGRAM_PASSWORD = "INSTAGRAM_PASSWORD"

GEMINI_API_KEY = "GEMINI_API_KEY"
OPENAI_API_KEY = "OPENAI_API_KEY"
GROQ_API_KEY = "GROQ_API_KEY"          # 무료: https://console.groq.com
OPENROUTER_API_KEY = "OPENROUTER_API_KEY"  # 무료: https://openrouter.ai
NVIDIA_API_KEY = "NVIDIA_API_KEY"      # 무료: https://build.nvidia.com
MISTRAL_API_KEY = "MISTRAL_API_KEY"    # 무료: https://console.mistral.ai (월 10억 토큰)

NAVER_ID = "NAVER_ID"
NAVER_PW = "NAVER_PW"
