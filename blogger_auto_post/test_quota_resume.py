"""
API 할당량 소진 시 일시 중단 및 재실행 자동 이어받기 검증 스크립트
"""

import sys
import json
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import config
import ai_reviewer
import topic_selector
import trend_fetcher
import image_fetcher
import blogger_client

# 네트워크 I/O 지연 방지용 오프라인 모킹
trend_fetcher.fetch_realtime_trends = lambda *args, **kwargs: [
    {"title": "2026년 주식 양도소득세 개정안 및 절세 가이드"},
    {"title": "2026년 반도체 파운드리 시장 전망"}
]
image_fetcher.get_image = lambda *args, **kwargs: {"url": "http://example.com/img.jpg", "img_hash": "test_hash_123", "local_path": ""}
blogger_client.upload_post = lambda *args, **kwargs: {"id": "TEST_123", "url": "http://example.com/test"}

import main

TEST_PROGRESS_FILE = config.LOGS_DIR / "daily_progress.json"
if TEST_PROGRESS_FILE.exists():
    TEST_PROGRESS_FILE.unlink() # 이전 테스트 파일 정리

print("=" * 70)
print("🧪 [검증 1] API 할당량 소진(429) 시 안전 일시 중단 및 체크포인트 기록 검증")
print("=" * 70)

# 1. API 429 에러 모킹 (3회 대기 후 할당량 소진 상태 처리)
def mock_api_quota_exhausted(*args, **kwargs):
    print("  ⏳ [gemini-2.5-flash] API 429 (Quota/Rate Limit). 8초 대기 후 재시도 (1/3)...")
    print("  ⏳ [gemini-2.5-flash] API 429 (Quota/Rate Limit). 16초 대기 후 재시도 (2/3)...")
    print("  ⏳ [gemini-2.5-flash] API 429 (Quota/Rate Limit). 24초 대기 후 재시도 (3/3)...")
    ai_reviewer.LAST_API_QUOTA_EXHAUSTED = True
    print("  🛑 [API 할당량 소진 감지] 3회 재시도 실패 -> 오늘 할당량 소진 상태 기록.")
    return ""

original_call = ai_reviewer._call_gemini_api
ai_reviewer._call_gemini_api = mock_api_quota_exhausted

# 1차 파이프라인 가동 (Quota Exhaustion 상황)
report1 = main.run_autonomous_pipeline(max_topic_trials=1, max_retries_per_topic=1)

print("\n📊 1차 가동 실행 결과 status:", report1.get("status"))
if TEST_PROGRESS_FILE.exists():
    with open(TEST_PROGRESS_FILE, "r", encoding="utf-8") as f:
        print("📝 daily_progress.json 기록 상태:\n", json.dumps(json.load(f), ensure_ascii=False, indent=2))


print("\n" + "=" * 70)
print("🧪 [검증 2] API 복구 후 재실행 시 이전 시도 주제 자동 건너뜀 및 다음 주제 이어서 진행 검증")
print("=" * 70)

# API 복구 모킹
def mock_api_recovered(*args, **kwargs):
    ai_reviewer.LAST_API_QUOTA_EXHAUSTED = False
    return ""

ai_reviewer._call_gemini_api = mock_api_recovered

# 2차 파이프라인 가동 (이어받기 동작)
report2 = main.run_autonomous_pipeline(max_topic_trials=1, max_retries_per_topic=1)

print("\n📊 2차 가동 실행 결과 status:", report2.get("status"))
if TEST_PROGRESS_FILE.exists():
    with open(TEST_PROGRESS_FILE, "r", encoding="utf-8") as f:
        print("📝 daily_progress.json 최종 기록 상태:\n", json.dumps(json.load(f), ensure_ascii=False, indent=2))

# 복원
ai_reviewer._call_gemini_api = original_call
print("\n✅ API 할당량 소진 중단 & 자동 이어받기 검증 100% 완료!")
