"""
blog_content_standards.py
- 애드센스 승인율 100% 보장 콘텐츠 단일 표준 검증 및 8대 마스터 하드 게이트 모듈
1. char_count: 실질 정보 글자수 (4,000자 ~ 8,000자)
2. no_duplicate: 문단 핑거프린트 중복 차단
3. image_count: 고유 이미지 3개 이상
4. title_match: 제목-본문 구조 일치
5. specificity: 범용 뭉뚱그리기 표현 차단 및 고유명사 필수 수록
6. unsourced_stats: 특정 분기/자료 허위 날조 출처 차단
7. ymyl_disclaimer: YMYL(금융/주식/의료/세금 등) 면책조항 표기 필수 검증 (신규)
8. promotional_tone: 과장/선동/대박형 마케팅 어휘 금지 검증 (신규)
"""

import re
from typing import Tuple, List, Dict

MIN_CHAR_COUNT = 4000          # 애드센스 통과 위해 최소 확보할 실질 분량 (공백 포함)
MAX_CHAR_COUNT = 8000          # 이 이상은 반복/뻥튀기 의심 구간 (지금까지 문제는 다 여기서 터짐)
MIN_IMAGE_COUNT = 3            # 썸네일 제외, 본문에 최소 삽입할 이미지 수
MAX_TEMPLATE_SECTIONS = 1      # 체크리스트/FAQ/부록 등 범용 템플릿 섹션 허용 개수

# 지금까지 계속 반복된 "뭉뚱그리기" 표현 — 발견 즉시 실패 처리
BANNED_VAGUE_PHRASES = [
    "글로벌 리딩 기업", "혁신 자이언트 기업", "선도적 기업들",
    "통신 장비 제조 기업들", "글로벌 산업 분석 기관", "주요 기업들",
    "관련 기업들", "업계 관계자", "전문가들에 따르면",
    "글로벌 시장 분석가들", "일부 기업", "특정 기업",
    "OO기업", "OO 기업", "A사", "B씨", "C사",
]

# 주제별로 "이 정도는 실제 이름이 나와야 정상" 인 화이트리스트
TOPIC_ENTITY_WHITELIST = {
    "반도체": ["삼성전자", "TSMC", "SK하이닉스", "ASML", "엔비디아", "인텔", "AMD", "마이크론"],
    "엔비디아": ["엔비디아", "NVIDIA", "젠슨 황", "블랙웰", "H100", "H200", "NVLink"],
    "노키아": ["노키아", "벨 연구소", "알카텔-루슨트", "FP5", "7750 SR", "1830 PSS", "엔비디아"],
    "챗gpt": ["OpenAI", "ChatGPT", "GPT-4o", "GPT-4", "샘 알트만"],
    "배터리": ["LG에너지솔루션", "삼성SDI", "SK온", "CATL", "파나소닉"],
    "2차전지": ["LG에너지솔루션", "삼성SDI", "SK온", "CATL", "파나소닉"],
}

# 과장/선동/스팸성 상업적 어휘 목록 — 발견 즉시 실패 처리
BANNED_PROMOTIONAL_PHRASES = [
    "절호의 기회", "무조건 사야", "100% 보장", "인생 역전", 
    "대박", "급등 직전", "무료 증정", "지금 당장 매수", 
    "천기누설", "폭등 예고", "손실 없는", "확실한 수익"
]

# 발행 전 자기검토 시 반드시 통과해야 하는 체크리스트
MASTER_SYSTEM_PROMPT = """
너는 애드센스 승인 기준을 통과하는 고품질 블로그 글만 작성하는 
전문 에디터다. 아래 규칙을 절대적으로 지켜라.

[구체적 명칭 필수 규칙]
- 제목에 특정 산업/기업 관련 키워드가 있으면, 반드시 실제 존재하는 
  회사명, 제품명, 서비스명을 최소 2개 이상 구체적으로 언급해야 한다.
- "글로벌 리딩 기업", "주요 기업들", "통신 장비 제조 기업들", "관련 기업들",
  "A사", "B씨"처럼 회사를 특정하지 않고 뭉뚱그리는 표현은 절대 금지한다.
  실제 회사명을 모르면 웹 검색으로 찾아내서 명확히 기술하라.

[분량 규칙]
- 실질 정보로 채운 본문이 최소 4,000자 이상이어야 한다.
- 분량이 부족하면 같은 문장을 반복하지 말고, 그 주제에 대해 
  다룰 수 있는 새로운 세부 항목(구체적 기능, 실제 사례, 
  단계별 방법, 비교 항목 등)을 추가로 발굴해서 채워라.
- "결국", "나아가", "이러한" 으로 시작하는 요약형 문단으로 
  분량을 채우는 것은 금지한다.

[사실 검증 및 수치 출처 규칙]
- 확인되지 않은 특정 분기/자료(예: "2026년 2분기 IR 공시 발표에 따르면")를 
  지어내어 인용하지 마라.
- 사실 기반 데이터를 언급할 때는 "~로 알려져 있다", "~하는 추세다", 
  "~로 집계된다" 등 객관적이고 담백한 안전 표현을 사용하라.

[YMYL 면책조항 및 어투 규칙]
- 금융, 주식, 투자, 세금, 건강 관련 포스팅의 경우 본문 하단에 
  "본 글은 투자 권유가 아닌 정보 제공용이며, 모든 투자 책임은 본인에게 있습니다" 
  등의 면책 문구를 반드시 수록하라.
- 과장/선동 어휘("절호의 기회", "무조건 사야", "대박" 등) 절대 금지.
"""

# 발행 전 자동 검증 8대 마스터 하드 게이트 --------------------------------------

def validate_char_count(body_text: str) -> Tuple[bool, str]:
    """1. 실질 정보 분량 계산 (공백 포함, HTML 태그 및 줄바꿈 제거)"""
    clean_text = re.sub(r'<[^>]+>', ' ', body_text or "")
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    count = len(clean_text)
    if count < MIN_CHAR_COUNT:
        return False, f"글자수 부족: {count:,}자 (최소 {MIN_CHAR_COUNT:,}자 필요)"
    if count > MAX_CHAR_COUNT:
        return False, f"글자수 과다(반복 의심): {count:,}자 (최대 {MAX_CHAR_COUNT:,}자 권장)"
    return True, f"글자수 통과: {count:,}자"


def validate_no_duplicate_sections(body_text: str, min_block_len: int = 200) -> Tuple[bool, str]:
    """2. 동일하거나 거의 동일한 문단이 반복되는지 검사 (문단 핑거프린트 100자 대조)"""
    clean_text = re.sub(r'<[^>]+>', ' ', body_text or "")
    paragraphs = [p.strip() for p in clean_text.split("\n\n") if len(p.strip()) > min_block_len]
    seen = set()
    for p in paragraphs:
        fingerprint = re.sub(r'\s+', '', p[:100])
        if fingerprint in seen:
            return False, f"중복 문단 발견: '{p[:40]}...'"
        seen.add(fingerprint)
    return True, "중복 문단 없음"


def validate_image_count(image_urls: list) -> Tuple[bool, str]:
    """3. 본문에 삽입될 고유 이미지 URL 개수 검증 (최소 3개)"""
    unique_urls = set(u for u in image_urls if u)
    if len(unique_urls) < MIN_IMAGE_COUNT:
        return False, f"이미지 부족/중복: 고유 이미지 {len(unique_urls)}개 (최소 {MIN_IMAGE_COUNT}개 필요)"
    return True, f"이미지 통과: 고유 {len(unique_urls)}개"


def validate_title_body_match(title: str, body_text: str) -> Tuple[bool, str]:
    """4. 제목에 숫자(예: 3가지)가 있으면 본문 소제목 개수와 대략 맞는지 체크"""
    clean_text = re.sub(r'<[^>]+>', ' ', body_text or "")
    match = re.search(r'(\d+)가지', title)
    if match:
        expected = int(match.group(1))
        h2_matches = re.findall(r'<h[23]>\s*\d+\.\s*', body_text or "")
        md_matches = re.findall(r'^\d+\.\s', clean_text, re.MULTILINE)
        md_h2_matches = re.findall(r'^##\s*\d+\.', body_text or "", re.MULTILINE)
        section_count = max(len(h2_matches), len(md_matches), len(md_h2_matches))
        if section_count > 0 and section_count != expected:
            return False, f"제목은 '{expected}가지'인데 본문 섹션은 {section_count}개"
    return True, "제목-본문 구조 일치"


def validate_specificity(title: str, body_text: str) -> Tuple[bool, str]:
    """
    5. Specificity 검증:
       - 뭉뚱그린 표현 발견 시 FAIL
       - 제목 주제에 맞는 실제 고유명사 최소 2개 이상 등장 검증
    """
    found_vague = [p for p in BANNED_VAGUE_PHRASES if p in body_text]
    if found_vague:
        return False, f"뭉뚱그린 표현 발견 (실제 회사/제품명으로 교체 필요): {found_vague}"

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
            return False, (
                f"'{title}' 주제인데 실제 회사/제품명이 {len(found_entities)}개만 등장함 "
                f"(최소 2개 필요). 발견된 것: {found_entities} / "
                f"참고 가능한 목록: {whitelist}"
            )
        return True, f"고유명사 통과: {found_entities}"
    else:
        proper_nouns = set(re.findall(r'\b[A-Z][a-zA-Z0-9]{2,}\b', body_text))
        if len(proper_nouns) < 3:
            return False, (
                f"화이트리스트에 없는 새 주제. 영문 고유명사(회사/제품명 추정)가 "
                f"{len(proper_nouns)}개만 발견됨 (최소 3개 필요): {proper_nouns}"
            )
        return True, f"신규 주제 - 추정 고유명사 통과: {proper_nouns}"


def validate_unsourced_stats(body_text: str) -> Tuple[bool, str]:
    """
    6. Unsourced Stats / Fake Citations 검증:
       'OO 20XX년 N분기 ~공시/발표/보고서에 따르면'처럼 허위로 시점/분기를 지목하는 날조 인용구 차단
    """
    clean_body = re.sub(r'<[^>]+>', ' ', body_text or "")
    clean_body = re.sub(r'\n+', '. ', clean_body)
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', clean_body) if len(s.strip()) > 15]

    fake_citation_pattern = re.compile(
        r'(?:202[4-6]년|[1-4]분기|[1-12]월)\s+.*?(?:공시|발표|보고서|IR|실적)\s*(?:에\s*따르면|에\s*의하면|에\s*의해|에\s*기술)'
    )

    fake_citations = []
    for s in sentences:
        if fake_citation_pattern.search(s):
            fake_citations.append(s[:70])

    if fake_citations:
        return False, f"날조된 가짜 출처(특정 시점/분기 지목) 감지 ({len(fake_citations)}건): {fake_citations[:3]}"

    return True, "허위 출처 날조 없음 (안전 표현 검증 통과)"


def validate_ymyl_disclaimer(title: str, body_text: str) -> Tuple[bool, str]:
    """
    7. YMYL Disclaimer 검증:
       주식, 투자, 금융, 부동산, 건강, 세금 관련 포스팅 시 면책 문구 포함 여부 검증
    """
    ymyl_keywords = ["주식", "투자", "수혜주", "재테크", "비트코인", "대출", "세금", "건강", "의료", "증권", "배터리", "부동산"]
    is_ymyl = any(kw in title for kw in ymyl_keywords) or any(kw in body_text[:500] for kw in ymyl_keywords)
    
    if is_ymyl:
        disclaimer_patterns = ["면책", "투자의 책임", "참고용", "권유가 아닙니다", "주의사항", "전문가와 상의", "책임은 본인"]
        has_disclaimer = any(p in body_text for p in disclaimer_patterns)
        if not has_disclaimer:
            return False, "YMYL(금융/주식/건강) 포스팅에 필수 면책조항 문구가 누락됨"
        return True, "YMYL 면책조항 표기 통과"
    
    return True, "비(非) YMYL 포스팅 (면책조항 예외)"


def validate_promotional_tone(body_text: str) -> Tuple[bool, str]:
    """
    8. Promotional Tone 검증:
       과장/선동/대박형 스팸성 마케팅 어휘 사용 금지 검증
    """
    found_promo = [phrase for phrase in BANNED_PROMOTIONAL_PHRASES if phrase in body_text]
    if found_promo:
        return False, f"과장/선동성 마케팅 어휘 발견 (객관적 담백 문체로 수정 필요): {found_promo}"
    return True, "과장/선동 어휘 없음 (담백한 문체 통과)"


def run_full_validation(title: str, body_text: str, image_urls: list) -> dict:
    """발행 전 최종 8대 마스터 하드 게이트 — 하나라도 실패하면 발행 중단 및 재생성"""
    checks = {
        "char_count": validate_char_count(body_text),
        "no_duplicate": validate_no_duplicate_sections(body_text),
        "image_count": validate_image_count(image_urls),
        "title_match": validate_title_body_match(title, body_text),
        "specificity": validate_specificity(title, body_text),
        "unsourced_stats": validate_unsourced_stats(body_text),
        "ymyl_disclaimer": validate_ymyl_disclaimer(title, body_text),    # 신규 7번째
        "promotional_tone": validate_promotional_tone(body_text),          # 신규 8번째
    }
    all_passed = all(result[0] for result in checks.values())
    return {"passed": all_passed, "details": checks}
