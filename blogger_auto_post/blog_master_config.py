"""
blog_master_config.py
- 프로젝트 유일한 통합 단일 표준 모듈 (Single Source of Truth)
- 9대 마스터 하드 게이트 검증 및 라이브 실시간 검증(verify_live_post) 파이프라인
- 강화된 문단 중복 검사, 브랜드 나열 우회 검지, 이미지 관련성 검증(validate_image_relevance) 포함
"""

import os
import sys
import json
import re
import requests
from pathlib import Path
from typing import Tuple, List, Dict, Optional

MIN_CHAR_COUNT = 4000          # 애드센스 통과 위해 최소 확보할 실질 분량 (공백 포함)
MAX_CHAR_COUNT = 8000          # 이 이상은 반복/뻥튀기 의심 구간
MIN_IMAGE_COUNT = 3            # 썸네일 제외, 본문에 최소 삽입할 이미지 수
MAX_TEMPLATE_SECTIONS = 1      # 체크리스트/FAQ/부록 등 범용 템플릿 섹션 허용 개수

FIXABLE_ISSUES = ["image_count", "char_count", "title_match", "ymyl_disclaimer", "image_relevance", "specificity"]

BANNED_VAGUE_PHRASES = [
    "글로벌 리딩 기업", "혁신 자이언트 기업", "선도적 기업들",
    "통신 장비 제조 기업들", "글로벌 산업 분석 기관", "주요 기업들",
    "관련 기업들", "업계 관계자", "전문가들에 따르면",
    "글로벌 시장 분석가들", "일부 기업", "특정 기업",
    "OO기업", "OO 기업", "A사", "B씨", "C사"
]

BANNED_PROMOTIONAL_PHRASES = [
    "절호의 기회", "무조건 사야", "100% 보장", "인생 역전", 
    "대박", "급등 직전", "무료 증정", "지금 당장 매수", 
    "천기누설", "폭등 예고", "손실 없는", "확실한 수익"
]

TOPIC_ENTITY_WHITELIST = {
    "반도체": ["삼성전자", "TSMC", "SK하이닉스", "ASML", "엔비디아", "인텔", "AMD", "마이크론"],
    "엔비디아": ["엔비디아", "NVIDIA", "젠슨 황", "블랙웰", "H100", "H200", "NVLink"],
    "노키아": ["노키아", "벨 연구소", "알카텔-루슨트", "FP5", "7750 SR", "1830 PSS", "엔비디아"],
    "챗gpt": ["OpenAI", "ChatGPT", "GPT-4o", "GPT-4", "샘 알트만"],
    "배터리": ["LG에너지솔루션", "삼성SDI", "SK온", "CATL", "파나소닉"],
    "전기차": ["LG에너지솔루션", "삼성SDI", "SK온", "CATL", "테슬라", "현대차"],
    "2차전지": ["LG에너지솔루션", "삼성SDI", "SK온", "CATL", "파나소닉"]
}

MASTER_SYSTEM_PROMPT = """
너는 애드센스 승인 기준을 통과하는 고품질 블로그 글만 작성하는 전문 에디터다. 아래 규칙을 절대적으로 지켜라.

[구체적 명칭 필수 규칙]
- 제목에 특정 산업/기업 관련 키워드가 있으면, 반드시 실제 존재하는 회사명, 제품명, 서비스명을 최소 2개 이상 구체적으로 언급해야 한다.
- "글로벌 리딩 기업", "주요 기업들", "관련 기업들" 등 뭉뚱그리는 표현은 절대 금지한다.
- 주제와 무관한 브랜드명(Apple, Nike, Qualcomm 등)을 나열식으로 삽입하여 검증을 우회하지 마라.

[분량 및 사실 검증 규칙]
- 실질 정보 본문이 최소 4,000자 이상 8,000자 이하여야 한다.
- 문단 반복 및 제목/부록 텍스트 중복 표기를 절대 금지한다.
- 금융/주식/건강 관련 포스팅은 YMYL 면책조항을 본문 하단에 반드시 표기하라.
"""

LOGS_DIR = Path(__file__).parent / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
MASTER_CHECKPOINT_PATH = LOGS_DIR / "master_verified_posts.json"


def load_master_verified_posts() -> Dict[str, Dict]:
    if MASTER_CHECKPOINT_PATH.exists():
        try:
            with open(MASTER_CHECKPOINT_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_master_verified_post(post_id: str, title: str, live_url: str, details: dict):
    posts = load_master_verified_posts()
    posts[post_id] = {
        "title": title,
        "live_url": live_url,
        "status": "PASS",
        "details": details
    }
    try:
        with open(MASTER_CHECKPOINT_PATH, "w", encoding="utf-8") as f:
            json.dump(posts, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ 마스터 체크포인트 저장 실패: {e}")


def is_post_master_passed(post_id: str) -> bool:
    posts = load_master_verified_posts()
    return post_id in posts and posts[post_id].get("status") == "PASS"


# 9대 마스터 하드 게이트 검증 개별 함수 ------------------------------------------

def validate_char_count(body_text: str) -> Tuple[bool, str]:
    clean_text = re.sub(r'<[^>]+>', ' ', body_text or "")
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    count = len(clean_text)
    if count < MIN_CHAR_COUNT:
        return False, f"글자수 부족: {count:,}자 (최소 {MIN_CHAR_COUNT:,}자 필요)"
    if count > MAX_CHAR_COUNT:
        return False, f"글자수 과다(반복 의심): {count:,}자 (최대 {MAX_CHAR_COUNT:,}자 권장)"
    return True, f"글자수 통과: {count:,}자"


def validate_no_duplicate_sections(body_text: str, min_len: int = 100) -> Tuple[bool, str]:
    """전체 문서 내 모든 문단 쌍을 비교 (연속 여부 무관) + 핑거프린트 정밀 비교"""
    clean_text = re.sub(r'<[^>]+>', ' ', body_text or "")
    paras = [p.strip() for p in clean_text.split("\n\n") if len(p.strip()) > min_len]
    seen = {}
    for i, p in enumerate(paras):
        fp = re.sub(r'\s+', '', p[:150])  # 핑거프린트 150자 확장
        if fp in seen:
            return False, f"문단 반복 발견 ({seen[fp]+1}번째와 {i+1}번째 문단 거의 동일): '{p[:40]}...'"
        seen[fp] = i

    # 부록/제목의 "2026년 2026년" 식 연도 중복 검사
    if re.search(r'202[4-6]년\s+202[4-6]년', body_text):
        return False, "동일 연도 중복 표기 발견 ('2026년 2026년')"
    return True, "중복 문단 없음"


def validate_image_count(image_urls: list) -> Tuple[bool, str]:
    unique_urls = set(u for u in image_urls if u)
    if len(unique_urls) < MIN_IMAGE_COUNT:
        return False, f"이미지 부족/중복: 고유 이미지 {len(unique_urls)}개 (최소 {MIN_IMAGE_COUNT}개 필요)"
    return True, f"이미지 통과: 고유 {len(unique_urls)}개"


def validate_image_relevance(title: str, image_urls: list) -> Tuple[bool, str]:
    """이미지 URL/alt 텍스트가 주제와 명백히 무관한지 정밀 체크"""
    off_topic_terms = ["solar", "roof", "mountain", "hiker", "climbing", "gym", "shoes", "running", "workout"]
    irrelevant = []
    for url in image_urls:
        url_lower = (url or "").lower()
        if any(term in url_lower for term in off_topic_terms):
            irrelevant.append(url)
    if irrelevant:
        return False, f"주제 무관 이미지 감지 ({len(irrelevant)}개): {irrelevant}"
    return True, "이미지 관련성 확인 통과"


def validate_title_body_match(title: str, body_text: str) -> Tuple[bool, str]:
    clean_text = re.sub(r'<[^>]+>', ' ', body_text or "")
    match = re.search(r'(\d+)가지|\b(\d+)곳|\b(\d+)개', title)
    if match:
        expected = int(match.group(1) or match.group(2) or match.group(3))
        h2_matches = re.findall(r'<h[23]>\s*\d+\.\s*', body_text or "")
        md_matches = re.findall(r'^\d+\.\s', clean_text, re.MULTILINE)
        md_h2_matches = re.findall(r'^##\s*\d+\.', body_text or "", re.MULTILINE)
        section_count = max(len(h2_matches), len(md_matches), len(md_h2_matches))
        if section_count > 0 and section_count != expected:
            return False, f"제목은 '{expected}가지/개/곳'인데 본문 섹션은 {section_count}개"
    return True, "제목-본문 구조 일치"


def validate_specificity(title: str, body_text: str) -> Tuple[bool, str]:
    # 1. 뭉뚱그린 표현 검사
    found_vague = [p for p in BANNED_VAGUE_PHRASES if p in body_text]
    if found_vague:
        return False, f"뭉뚱그린 표현 발견: {found_vague}"

    # 2. 주제와 무관한 브랜드명 나열식 우회 감지
    OFF_TOPIC_BRAND_DUMPS = re.compile(
        r'(Apple|Samsung|Nike|Qualcomm|TSMC|OpenAI)[,\s]+(Apple|Samsung|Nike|Qualcomm|TSMC|OpenAI)[,\s]+'
    )
    if OFF_TOPIC_BRAND_DUMPS.search(body_text):
        return False, "주제와 무관한 브랜드명을 나열식으로 삽입한 것으로 의심됨 (specificity 우회 시도)"

    title_lower = title.lower()
    matched_topic = None
    for topic_key in TOPIC_ENTITY_WHITELIST:
        if topic_key in title_lower or topic_key in title:
            matched_topic = topic_key
            break

    if matched_topic:
        whitelist = TOPIC_ENTITY_WHITELIST[matched_topic]
        found_entities = [name for name in whitelist if name in body_text]
        if len(found_entities) < 2:
            return False, f"실제 고유명사 부족 ({len(found_entities)}개만 등장): {found_entities}"
        return True, f"고유명사 통과: {found_entities}"
    else:
        proper_nouns = set(re.findall(r'\b[A-Z][a-zA-Z0-9]{2,}\b', body_text))
        if len(proper_nouns) < 3:
            return False, f"추정 영문 고유명사 부족 ({len(proper_nouns)}개 등장): {proper_nouns}"
        return True, f"추정 고유명사 통과: {proper_nouns}"


def validate_unsourced_stats(body_text: str) -> Tuple[bool, str]:
    clean_body = re.sub(r'<[^>]+>', ' ', body_text or "")
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', clean_body) if len(s.strip()) > 15]

    fake_citation_pattern = re.compile(
        r'(?:202[4-6]년|[1-4]분기|[1-12]월)\s+.*?(?:공시|발표|보고서|IR|실적)\s*(?:에\s*따르면|에\s*의하면)'
    )
    fake_citations = [s[:70] for s in sentences if fake_citation_pattern.search(s)]

    if fake_citations:
        return False, f"가짜 특정 출처 날조 감지 ({len(fake_citations)}건): {fake_citations[:2]}"
    return True, "허위 출처 날조 없음"


def validate_ymyl_disclaimer(title: str, body_text: str) -> Tuple[bool, str]:
    ymyl_keywords = ["주식", "투자", "수혜주", "재테크", "비트코인", "대출", "세금", "건강", "의료", "증권", "배터리", "부동산", "ETF"]
    is_ymyl = any(kw in title for kw in ymyl_keywords) or any(kw in body_text[:500] for kw in ymyl_keywords)
    
    if is_ymyl:
        disclaimer_patterns = ["면책", "투자의 책임", "참고용", "권유가 아닙니다", "주의사항", "전문가와 상의", "책임은 본인"]
        has_disclaimer = any(p in body_text for p in disclaimer_patterns)
        if not has_disclaimer:
            return False, "YMYL(금융/주식/건강) 필수 면책조항 문구 누락"
        return True, "YMYL 면책조항 통과"
    return True, "비(非) YMYL 포스팅 (면책 예외)"


def validate_promotional_tone(body_text: str) -> Tuple[bool, str]:
    found_promo = [phrase for phrase in BANNED_PROMOTIONAL_PHRASES if phrase in body_text]
    if found_promo:
        return False, f"과장/선동성 마케팅 어휘 발견: {found_promo}"
    return True, "과장/선동 어휘 없음"


def run_full_validation(title: str, body_text: str, image_urls: list) -> dict:
    checks = {
        "char_count": validate_char_count(body_text),
        "no_duplicate": validate_no_duplicate_sections(body_text),
        "image_count": validate_image_count(image_urls),
        "image_relevance": validate_image_relevance(title, image_urls),
        "title_match": validate_title_body_match(title, body_text),
        "specificity": validate_specificity(title, body_text),
        "unsourced_stats": validate_unsourced_stats(body_text),
        "ymyl_disclaimer": validate_ymyl_disclaimer(title, body_text),
        "promotional_tone": validate_promotional_tone(body_text),
    }
    all_passed = all(result[0] for result in checks.values())
    return {"passed": all_passed, "details": checks}


def verify_live_post(live_url: str, title: str = "") -> dict:
    if not live_url:
        return {"passed": False, "reason": "라이브 URL 누락"}

    try:
        resp = requests.get(live_url, timeout=10)
        if resp.status_code != 200:
            return {"passed": False, "reason": f"라이브 접속 실패 (Status: {resp.status_code})"}
        
        html = resp.text
        body_match = re.search(r'<div[^>]*class=["\'][^"\']*post-body[^"\']*["\'][^>]*>(.*?)<div[^>]*class=["\'][^"\']*(?:post-footer|blog-pager)[^"\']*["\']', html, re.DOTALL | re.IGNORECASE)
        if body_match:
            html = body_match.group(1)

        html_clean = re.sub(r'<(style|script)[^>]*>.*?</\1>', ' ', html, flags=re.DOTALL | re.IGNORECASE)
        clean_text = re.sub(r'<[^>]+>', ' ', html_clean)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        live_images = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', html)
        
        val = run_full_validation(title, html_clean, live_images)
        val["live_url"] = live_url
        val["live_char_count"] = len(clean_text)
        val["live_image_count"] = len(set(live_images))
        return val
    except Exception as e:
        return {"passed": False, "reason": f"라이브 재검증 예외: {e}"}


def run_full_validation_with_live_check(title: str, body_text: str, image_urls: list, live_url: str = None, post_id: str = None) -> dict:
    raw_val = run_full_validation(title, body_text, image_urls)
    
    if not raw_val["passed"]:
        return raw_val

    if live_url:
        live_val = verify_live_post(live_url, title)
        if not live_val["passed"]:
            return {"passed": False, "stage": "LIVE_CHECK_FAILED", "details": live_val}
        
        if post_id:
            save_master_verified_post(post_id, title, live_url, raw_val["details"])
        return {"passed": True, "live_verified": True, "details": raw_val["details"], "live_url": live_url}

    if post_id:
        save_master_verified_post(post_id, title, live_url or "", raw_val["details"])
    return raw_val
