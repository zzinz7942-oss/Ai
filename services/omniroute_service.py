# -*- coding: utf-8 -*-
"""
OmniRoute - 절대 뻗지 않는 AI 자동 폴백 서비스
하나가 뻗으면 즉시 다음으로 전환, 마지막은 로컬 Ollama

폴백 체인:
  1. Gemini 2.5 Flash     (구글 무료)
  2. Groq                 (Llama 4, 무료/초고속)
  3. NVIDIA NIM           (DeepSeek V4 / Nemotron, 무료 크레딧)
  4. Mistral AI           (Mistral Large, 월 10억 토큰 무료)
  5. OpenRouter           (NVIDIA Nemotron 120B 등, 무료)
  6. Ollama 로컬          (PC 설치 모델, 완전 오프라인 최후 안전망)
"""

import os
import json
import urllib.request
import urllib.error
import requests
from config import (
    get_config, GEMINI_API_KEY, 
    GROQ_API_KEY, OPENROUTER_API_KEY, NVIDIA_API_KEY, MISTRAL_API_KEY
)

# ── Ollama 로컬 설정 ───────────────────────────────────────────────────
OLLAMA_HOST  = os.environ.get("OLLAMA_HOST",  "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3")

# ── 각 서비스 모델 우선순위 ────────────────────────────────────────────
GROQ_MODELS = [
    "llama-4-scout-17b-16e-instruct",
    "llama-4-maverick-17b-128e-instruct",
    "llama-3.3-70b-versatile",
    "compound-beta",
]
NVIDIA_MODELS = [
    "meta/llama-3.1-8b-instruct",
    "meta/llama-3.3-70b-instruct",
    "mistralai/mixtral-8x22b-instruct-v0.1",
]
MISTRAL_MODELS = [
    "mistral-large-latest",
    "codestral-latest",
    "open-mistral-7b",
]
OPENROUTER_MODELS = [
    "nvidia/nemotron-3-super-120b-a12b:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "google/gemma-4-31b-it:free",
    "google/gemma-4-26b-a4b-it:free",
    "openrouter/free",
]


# ── 공통 urllib 호출 (Windows cp949 인코딩 문제 완전 우회) ────────────
def _http_post(url: str, headers: dict, payload: dict, timeout: int = 25) -> dict:
    """urllib로 POST 요청. requests의 latin-1 헤더 인코딩 문제를 우회."""
    body = json.dumps(payload, ensure_ascii=True).encode("ascii")
    req  = urllib.request.Request(url, data=body, method="POST")
    for k, v in headers.items():
        req.add_header(k, v)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
            return {"ok": True, "data": data}
    except urllib.error.HTTPError as e:
        body_txt = e.read().decode("utf-8", errors="replace")[:120]
        return {"ok": False, "status": e.code, "error": body_txt}
    except Exception as ex:
        return {"ok": False, "error": str(ex)}


def _extract_text(data: dict) -> str:
    return data["choices"][0]["message"]["content"].strip()


# ── 1. Gemini ──────────────────────────────────────────────────────────
def _try_gemini(prompt: str, system_instruction: str) -> dict:
    key = get_config(GEMINI_API_KEY)
    if not key:
        return {"success": False, "error": "GEMINI_API_KEY 없음"}
    try:
        import google.generativeai as genai
        genai.configure(api_key=key)
        for m in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-flash-latest"]:
            try:
                model = genai.GenerativeModel(m)
                res   = model.generate_content(f"{system_instruction}\n\n{prompt}")
                if res and res.text:
                    return {"success": True, "provider": f"Gemini ({m})", "text": res.text.strip()}
            except Exception as e:
                err = str(e).lower()
                if any(k in err for k in ["429", "quota", "rate limit", "resource_exhausted"]):
                    break  # 한도 초과 → 즉시 다음 프로바이더
        return {"success": False, "error": "Gemini 모든 모델 실패"}
    except Exception as e:
        return {"success": False, "error": f"Gemini: {e}"}


# ── 2. Groq ────────────────────────────────────────────────────────────
def _try_groq(prompt: str, system_instruction: str) -> dict:
    key = get_config(GROQ_API_KEY)
    if not key:
        return {"success": False, "error": "GROQ_API_KEY 없음"}
    headers = {"Authorization": f"Bearer {key}"}
    for model in GROQ_MODELS:
        payload = {"model": model, "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user",   "content": prompt}
        ], "max_tokens": 1500}
        res = _http_post("https://api.groq.com/openai/v1/chat/completions", headers, payload)
        if res["ok"]:
            return {"success": True, "provider": f"Groq ({model})", "text": _extract_text(res["data"])}
        if res.get("status") == 429:
            continue  # 다음 모델 시도
    return {"success": False, "error": "Groq 모든 모델 한도 초과"}


# ── 3. NVIDIA NIM ──────────────────────────────────────────────────────
def _try_nvidia(prompt: str, system_instruction: str) -> dict:
    key = get_config(NVIDIA_API_KEY)
    if not key:
        return {"success": False, "error": "NVIDIA_API_KEY 없음"}
    headers = {"Authorization": f"Bearer {key}"}
    for model in NVIDIA_MODELS:
        payload = {"model": model, "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user",   "content": prompt}
        ], "max_tokens": 1500, "temperature": 0.7}
        res = _http_post("https://integrate.api.nvidia.com/v1/chat/completions", headers, payload, timeout=30)
        if res["ok"]:
            return {"success": True, "provider": f"NVIDIA NIM ({model})", "text": _extract_text(res["data"])}
        if res.get("status") in [429, 402]:
            continue
    return {"success": False, "error": "NVIDIA NIM 크레딧 소진 또는 모델 오류"}


# ── 4. Mistral ─────────────────────────────────────────────────────────
def _try_mistral(prompt: str, system_instruction: str) -> dict:
    key = get_config(MISTRAL_API_KEY)
    if not key:
        return {"success": False, "error": "MISTRAL_API_KEY 없음"}
    headers = {"Authorization": f"Bearer {key}"}
    for model in MISTRAL_MODELS:
        payload = {"model": model, "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user",   "content": prompt}
        ], "temperature": 0.7}
        res = _http_post("https://api.mistral.ai/v1/chat/completions", headers, payload, timeout=45)
        if res["ok"]:
            return {"success": True, "provider": f"Mistral ({model})", "text": _extract_text(res["data"])}
        if res.get("status") == 429:
            continue
    return {"success": False, "error": "Mistral 모든 모델 한도 초과"}


# ── 5. OpenRouter ──────────────────────────────────────────────────────
def _try_openrouter(prompt: str, system_instruction: str) -> dict:
    key = get_config(OPENROUTER_API_KEY)
    if not key:
        return {"success": False, "error": "OPENROUTER_API_KEY 없음"}
    headers = {
        "Authorization":  f"Bearer {key}",
        "HTTP-Referer":   "https://ai-marketing-bot.local",
        "X-Title":        "AI Marketing Bot",
    }
    for model in OPENROUTER_MODELS:
        payload = {"model": model, "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user",   "content": prompt}
        ]}
        res = _http_post("https://openrouter.ai/api/v1/chat/completions", headers, payload, timeout=45)
        if res["ok"]:
            return {"success": True, "provider": f"OpenRouter ({model})", "text": _extract_text(res["data"])}
        if res.get("status") in [429, 402, 404]:
            continue
    return {"success": False, "error": "OpenRouter 모든 무료 모델 소진"}


# ── 6. Ollama 로컬 (최후 안전망) ──────────────────────────────────────
def _try_ollama(prompt: str, system_instruction: str) -> dict:
    """Ollama 로컬 모델 — 인터넷 없어도 동작하는 최후 안전망."""
    try:
        messages = [{"role": "system", "content": system_instruction},
                    {"role": "user",   "content": prompt}]
        payload  = {"model": OLLAMA_MODEL, "messages": messages, "stream": False}
        res      = requests.post(f"{OLLAMA_HOST}/v1/chat/completions", json=payload, timeout=90)
        if res.status_code == 200:
            return {"success": True, "provider": f"Ollama 로컬 ({OLLAMA_MODEL})",
                    "text": res.json()["choices"][0]["message"]["content"].strip()}
        return {"success": False, "error": f"Ollama HTTP {res.status_code}"}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": f"Ollama 미실행 ({OLLAMA_HOST}) — 'ollama serve' 실행 필요"}
    except Exception as e:
        return {"success": False, "error": f"Ollama: {e}"}


def check_ollama_status() -> dict:
    """Ollama 서버 상태 및 설치된 모델 목록 반환."""
    try:
        res = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=3)
        if res.status_code == 200:
            models = [m["name"] for m in res.json().get("models", [])]
            return {"running": True, "models": models}
    except Exception:
        pass
    return {"running": False, "models": []}


# ── 메인: 절대 뻗지 않는 폴백 체인 ───────────────────────────────────
def generate_ai_text_with_fallback(prompt: str, system_instruction: str = "") -> dict:
    """
    하나가 뻗으면 즉시 다음으로 자동 전환.
    모든 클라우드 서비스 장애 시 → Ollama 로컬로 최종 폴백.
    """
    kr_lock = (
        "당신은 한국어로만 소통하는 AI입니다. "
        "절대로 영어로 답변하지 말고 무조건 100% 정교한 한국어로만 답변해 주세요."
    )
    sys_inst = f"{kr_lock}\n{system_instruction}" if system_instruction else kr_lock

    errors = []

    # 폴백 체인 정의 (함수, 이름) 순서대로
    chain = [
        (_try_gemini,      "Gemini"),
        (_try_groq,        "Groq"),
        (_try_nvidia,      "NVIDIA NIM"),
        (_try_mistral,     "Mistral"),
        (_try_openrouter,  "OpenRouter"),
        (_try_ollama,      "Ollama 로컬"),  # 최후 안전망
    ]

    for fn, name in chain:
        try:
            res = fn(prompt, sys_inst)
            if res.get("success"):
                if name != "Gemini":
                    print(f"  ✅ [{name}] 로 자동 전환 성공")
                return res
            err = res.get("error", "알 수 없는 오류")
            errors.append(f"{name}: {err}")
            print(f"  ⚠️  [{name}] 실패 → 다음 프로바이더 시도... ({err[:50]})")
        except Exception as e:
            errors.append(f"{name}: 예외 - {e}")
            print(f"  ⚠️  [{name}] 예외 → 다음 프로바이더 시도... ({e})")

    # 모든 프로바이더 실패
    return {
        "success": False,
        "error": "⚠️ 모든 AI 프로바이더 호출 실패\n" + "\n".join(f"  - {e}" for e in errors),
        "errors": errors,
    }
