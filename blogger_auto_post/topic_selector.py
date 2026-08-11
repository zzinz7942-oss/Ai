"""
주제 선정 및 중복 검수 모듈 (Topic Selector & Similarity Filter)
- 고CPC / 저경쟁 카테고리(재테크, IT/가전, 건강, 생활정보, 시사) 후보 3~5개 추출
- 최근 7일 이내 발행 글(published_log.json)과 주제 유사도 70% 이상 시 제외
- 선정된 주제 및 발행 기록 관리
"""

import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Tuple, Optional

import config
import trend_fetcher


def load_published_logs() -> List[Dict]:
    """최근 발행 로그(published_log.json) 읽기"""
    if not config.PUBLISHED_LOG_PATH.exists():
        return []
    try:
        with open(config.PUBLISHED_LOG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"  ⚠️ published_log.json 읽기 오류 ({e})")
        return []


def save_published_log(post_info: Dict):
    """신규 발행 포스트 정보 누적 기록"""
    logs = load_published_logs()
    logs.append(post_info)
    try:
        with open(config.PUBLISHED_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
        print(f"  📝 발행 로그 저장 완료: {post_info.get('topic') or post_info.get('title')}")
    except Exception as e:
        print(f"  ⚠️ published_log.json 저장 오류 ({e})")


def extract_keywords(text: str) -> set:
    """텍스트에서 주요 명사/단어 키워드 추출"""
    words = re.findall(r'[\w가-힣]{2,}', text.lower())
    stop_words = {"방법", "가이드", "정리", "2026년", "꿀팁", "추천", "필수", "분석", "총정리", "노하우", "핵심", "비교"}
    return {w for w in words if w not in stop_words and not w.isdigit()}


def calculate_topic_similarity(topic_a: str, topic_b: str) -> float:
    """두 주제 간의 키워드 자카드 유사도(%) 계산"""
    set_a = extract_keywords(topic_a)
    set_b = extract_keywords(topic_b)

    if not set_a or not set_b:
        return 0.0

    intersection = set_a.intersection(set_b)
    union = set_a.union(set_b)
    similarity = (len(intersection) / len(union)) * 100.0
    return round(similarity, 1)


def is_topic_too_similar(candidate_topic: str, days: int = 7, max_similarity: float = 70.0) -> Tuple[bool, float, str]:
    """
    최근 N일 이내 발행된 주제들과 비교하여 max_similarity % 이상 유사한 지 검사.
    반환: (is_similar, highest_sim_percent, matched_previous_topic)
    """
    logs = load_published_logs()
    cutoff_time = datetime.now() - timedelta(days=days)

    max_sim = 0.0
    matched_topic = ""

    for item in logs:
        pub_time_str = item.get("published_at") or item.get("timestamp")
        if pub_time_str:
            try:
                pub_dt = datetime.fromisoformat(pub_time_str)
                if pub_dt < cutoff_time:
                    continue
            except Exception:
                pass

        prev_topic = item.get("topic") or item.get("title", "")
        sim = calculate_topic_similarity(candidate_topic, prev_topic)
        if sim > max_sim:
            max_sim = sim
            matched_topic = prev_topic

    is_similar = max_sim >= max_similarity
    return is_similar, max_sim, matched_topic


DAILY_PROGRESS_PATH = config.LOGS_DIR / "daily_progress.json"


def load_daily_progress() -> Dict:
    if not DAILY_PROGRESS_PATH.exists():
        return {"date": datetime.now().strftime("%Y-%m-%d"), "attempted_topics": [], "completed_topics": []}
    try:
        with open(DAILY_PROGRESS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if data.get("date") != datetime.now().strftime("%Y-%m-%d"):
                return {"date": datetime.now().strftime("%Y-%m-%d"), "attempted_topics": [], "completed_topics": []}
            return data
    except Exception:
        return {"date": datetime.now().strftime("%Y-%m-%d"), "attempted_topics": [], "completed_topics": []}


def mark_topic_attempted(topic: str):
    prog = load_daily_progress()
    if topic not in prog["attempted_topics"]:
        prog["attempted_topics"].append(topic)
    try:
        with open(DAILY_PROGRESS_PATH, "w", encoding="utf-8") as f:
            json.dump(prog, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"  ⚠️ daily_progress.json 저장 오류 ({e})")


def mark_topic_completed(topic: str):
    prog = load_daily_progress()
    if topic not in prog["completed_topics"]:
        prog["completed_topics"].append(topic)
    try:
        with open(DAILY_PROGRESS_PATH, "w", encoding="utf-8") as f:
            json.dump(prog, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"  ⚠️ daily_progress.json 저장 오류 ({e})")


def get_candidate_topics(count_per_category: int = 1) -> List[Dict]:
    """
    고CPC 카테고리별 실시간 트렌드를 반영하여 후보 주제 3~5개 생성
    """
    candidates = []
    
    for category in config.TARGET_CATEGORIES:
        cat_name = category["name"]
        keywords = category["keywords"]
        
        # 카테고리 대표 키워드로 실시간 이슈 탐색
        seed_kw = keywords[int(time.time()) % len(keywords)]
        trends = trend_fetcher.fetch_realtime_trends(topic_keyword=seed_kw, max_count=2)
        
        if trends:
            for t in trends[:count_per_category]:
                clean_title = re.sub(r'\s*-\s*.*$', '', t["title"])  # 언론사명 제거
                candidates.append({
                    "category": cat_name,
                    "topic": clean_title,
                    "keyword": seed_kw,
                    "trend_ref": t["title"]
                })
        else:
            # RSS 수집 실패 시 기본 고CPC 주제 파생
            candidates.append({
                "category": cat_name,
                "topic": f"2026년 {seed_kw} 핵심 실전 가이드 및 비용 절감 혜택",
                "keyword": seed_kw,
                "trend_ref": f"{seed_kw} 관련 2026 최신 정책"
            })
            
    return candidates


def select_best_topic() -> Optional[Dict]:
    """
    후보 주제 3~5개 중 최근 7일 발행 글 및 오늘 처리/시도된 주제 제외 최적 고CPC 주제 선정
    """
    print("\n🎯 [1. 주제 선정] 고CPC/저경쟁 카테고리 실시간 트렌드 수집 중...")
    candidates = get_candidate_topics()
    daily_prog = load_daily_progress()
    today_handled = set(daily_prog.get("attempted_topics", []) + daily_prog.get("completed_topics", []))
    
    print(f"  총 {len(candidates)}개 후보 주제 검수 시작:")
    
    valid_candidates = []
    for idx, cand in enumerate(candidates, 1):
        topic = cand["topic"]
        if topic in today_handled:
            print(f"   ⏭️ 후보 {idx}: [{cand['category']}] '{topic[:30]}...' (오늘 이미 처리/시도됨, 건너뜀)")
            continue

        is_sim, sim_val, prev_match = is_topic_too_similar(topic, days=7, max_similarity=config.TOPIC_SIMILARITY_MAX)
        
        if is_sim:
            print(f"   ❌ 후보 {idx}: [{cand['category']}] '{topic[:30]}...' (유사도 {sim_val}% >= 70%, 중복 제외: '{prev_match[:20]}')")
        else:
            print(f"   ✅ 후보 {idx}: [{cand['category']}] '{topic[:30]}...' (유사도 {sim_val}% < 70%, 통과)")
            valid_candidates.append(cand)
            
    if not valid_candidates:
        print("  ⚠️ 유효 후보가 모두 사용되었거나 7일 이내 중복입니다. 신규 예비 주제를 생성합니다.")
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M")
        fallback_topic = {
            "category": "재테크/금융",
            "topic": f"2026년 자산 관리 및 절세 혜택 총정리 ({timestamp_str})",
            "keyword": "절세",
            "trend_ref": "2026년 금융 세제 개정안"
        }
        return fallback_topic

    # 유효 후보 중 첫 번째 선택
    selected = valid_candidates[0]
    print(f"  🏆 최종 채택 주제: [{selected['category']}] {selected['topic']}")
    return selected

