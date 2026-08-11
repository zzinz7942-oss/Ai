"""
설정 확인 스크립트
실행하면 .env 파일의 키, OAuth 자격증명, 어조/스타일 설정 및 AI 자기검토가 올바른지 점검합니다.

실행 방법:
    python setup_check.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg):    print(f"  {GREEN}✅ {msg}{RESET}")
def warn(msg):  print(f"  {YELLOW}⚠️  {msg}{RESET}")
def fail(msg):  print(f"  {RED}❌ {msg}{RESET}")
def info(msg):  print(f"  {CYAN}ℹ️  {msg}{RESET}")

ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(ENV_PATH)

print()
print(f"{BOLD}{'=' * 55}{RESET}")
print(f"{BOLD}   📋 Google Blogger 자동 업로드 — 설정 확인{RESET}")
print(f"{BOLD}{'=' * 55}{RESET}\n")

all_ok = True

# ─── .env 파일 존재 여부 ─────────────────────────────────────
print(f"{BOLD}[1] .env 파일{RESET}")
if ENV_PATH.exists():
    ok(f".env 파일 발견: {ENV_PATH}")
else:
    fail(".env 파일이 없습니다.")
    all_ok = False

# ─── 이미지 수집 API 키 ─────────────────────────────────
print(f"\n{BOLD}[2] 이미지 수집 API 키{RESET}")
unsplash_key = os.getenv("UNSPLASH_ACCESS_KEY", "").strip()
if unsplash_key:
    ok("UNSPLASH_ACCESS_KEY 입력됨")
else:
    warn("UNSPLASH_ACCESS_KEY 비어 있음 (Pexels API로 자동 Fallback 가능)")

# ─── Blogger Blog ID ─────────────────────────────────────────
print(f"\n{BOLD}[3] Blogger Blog ID{RESET}")
blog_id = os.getenv("BLOGGER_BLOG_ID", "").strip()
if blog_id and blog_id.isdigit():
    ok(f"BLOGGER_BLOG_ID 입력됨: {blog_id[:6]}...")
else:
    fail("BLOGGER_BLOG_ID 비어 있거나 올바르지 않음")
    all_ok = False

# ─── Google OAuth 파일 ───────────────────────────────────────
print(f"\n{BOLD}[4] Google OAuth 클라이언트 시크릿 파일{RESET}")
secrets_path = Path(__file__).parent / "client_secrets.json"
if secrets_path.exists():
    ok("client_secrets.json 파일 발견")
else:
    fail("client_secrets.json 파일이 없습니다.")
    all_ok = False

# ─── 🤖 AI 자기검토 API 키 ────────────────────────────────────
print(f"\n{BOLD}[5] 🤖 AI 자기검토 (Gemini API){RESET}")
google_key = os.getenv("GOOGLE_API_KEY", "").strip()
if google_key:
    ok(f"GOOGLE_API_KEY 입력됨 (AI 자동 자기검토 & 클리셰 제거 동작 가능)")
else:
    warn("GOOGLE_API_KEY 비어 있음 (--skip-review 처리됨)")

# ─── 작성자 어조 & 스타일 ─────────────────────────────────────
print(f"\n{BOLD}[6] ✍️ 작성자 어조 & 페르소나 설정{RESET}")
tone = os.getenv("WRITER_TONE", "").strip()
persona = os.getenv("WRITER_PERSONA", "").strip()
trend_on = os.getenv("ENABLE_TREND_REFLECT", "true").strip()

if tone:
    ok(f"어조 설정됨: {tone[:35]}...")
else:
    warn("WRITER_TONE 미설정 (기본값 적용)")

if persona:
    ok(f"페르소나 설정됨: {persona}")
else:
    warn("WRITER_PERSONA 미설정 (기본값 적용)")

ok(f"실시간 트렌드 자동 반영: {trend_on.upper()}")

# ─── 결과 요약 ───────────────────────────────────────────────
print()
print(f"{BOLD}{'=' * 55}{RESET}")
if all_ok:
    print(f"{GREEN}{BOLD}  🎉 모든 필수 설정 완료! 바로 실행할 수 있습니다.{RESET}")
    print(f"{CYAN}  포스트 업로드 (AI 자기검토 포함): python main.py --no-drive{RESET}")
    print(f"{CYAN}  기존 글 수정 (AI 자기검토 포함): python main.py --no-drive --edit <POST_ID>{RESET}")
    print(f"{CYAN}  AI 자기검토 스킵: python main.py --no-drive --skip-review{RESET}")
else:
    print(f"{RED}{BOLD}  ⚠️ 일부 필수 설정이 누락되었습니다.{RESET}")
print(f"{BOLD}{'=' * 55}{RESET}\n")
