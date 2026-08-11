# -*- coding: utf-8 -*-
"""
OmniRoute & Multi-AI Provider Fallback Service
- Gemini, OpenAI, OmniRoute (http://localhost:20128/v1) 자동 폴백 생성기
- API 429/Rate Limit/오류 발생 시 백업 AI 프로바이더로 자동 전환
"""

import os
import requests
import json
from config import get_config, GEMINI_API_KEY, OPENAI_API_KEY


def generate_ai_text_with_fallback(prompt: str, system_instruction: str = "") -> dict:
    """
    여러 AI 프로바이더(Gemini ➔ OpenAI ➔ OmniRoute ➔ Fallback) 순으로 자동 폴백 텍스트 생성을 수행합니다.
    """
    errors = []
    # 무조건 100% 한국어 답변 강제 고정
    kr_lock = "당신은 한국어로만 소통하는 AI입니다. 이미지가 제공되더라도 절대로 영어로 답변하지 말고 무조건 100% 정교한 한국어로만 답변해 주세요."
    if system_instruction:
        system_instruction = f"{kr_lock}\n{system_instruction}"
    else:
        system_instruction = kr_lock

    # 1. Gemini API 시도
    g_key = get_config(GEMINI_API_KEY)
    if g_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=g_key)
            model_names = ['gemini-2.5-flash', 'gemini-3.6-flash', 'gemini-flash-latest']
            for m in model_names:
                try:
                    model = genai.GenerativeModel(m)
                    full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
                    res = model.generate_content(full_prompt)
                    if res and res.text:
                        return {"success": True, "provider": f"Gemini ({m})", "text": res.text.strip()}
                except Exception as e:
                    errors.append(f"Gemini({m}): {e}")
        except Exception as e:
            errors.append(f"Gemini Config: {e}")

    # 2. OpenAI API 시도
    o_key = get_config(OPENAI_API_KEY)
    if o_key:
        try:
            headers = {"Authorization": f"Bearer {o_key}", "Content-Type": "application/json"}
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_instruction or "You are a helpful AI assistant."},
                    {"role": "user", "content": prompt}
                ]
            }
            res = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=10)
            if res.status_code == 200:
                data = res.json()
                text = data["choices"][0]["message"]["content"]
                return {"success": True, "provider": "OpenAI (gpt-4o-mini)", "text": text.strip()}
            else:
                errors.append(f"OpenAI: {res.status_code} {res.text}")
        except Exception as e:
            errors.append(f"OpenAI Exec: {e}")

    # 3. OmniRoute Local Gateway Proxy (http://localhost:20128/v1) 시도
    try:
        omni_url = "http://localhost:20128/v1/chat/completions"
        payload = {
            "model": "claude-3-5-sonnet",
            "messages": [
                {"role": "system", "content": system_instruction or "You are an AI assistant."},
                {"role": "user", "content": prompt}
            ]
        }
        res = requests.post(omni_url, json=payload, timeout=5)
        if res.status_code == 200:
            data = res.json()
            text = data["choices"][0]["message"]["content"]
            return {"success": True, "provider": "OmniRoute Gateway (Local)", "text": text.strip()}
    except Exception as e:
        errors.append(f"OmniRoute: {e}")

    return {
        "success": False,
        "error": f"모든 AI 프로바이더 호출 실패 ({'; '.join(errors)})",
        "errors": errors
    }
