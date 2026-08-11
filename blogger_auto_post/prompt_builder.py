"""
15,000자 초장문 & AI 티 안 나는 인간형 톤앤매너 프롬프트 빌더 (Prompt Builder)
- human_writing_guide.md 규칙 완전 적용
- AI 상투어구(도입/결론 인삿말) 100% 영구 금지
- 8개 섹션별 다각도 분석 관점(배경/패러다임 -> 기술원리 -> 밸류체인/기업동향 -> 2025/2026 정량손익 -> 3대 페르소나 시나리오 -> 3대 리스크 체크리스트 -> 전문가 팁/전망 -> FAQ) 지침 제공
"""

import config
from trend_fetcher import format_trends_for_prompt


import blog_content_standards

def build_system_prompt() -> str:
    """인간형 페르소나 및 blog_content_standards 톤앤매너 지침 생성"""
    return f"""{blog_content_standards.MASTER_SYSTEM_PROMPT}

너는 10년 차 수석 칼럼니스트이자 실전 전문가이다. 독자가 읽었을 때 사람이 직접 현장 경험과 최신 데이터를 바탕으로 써 내려간 글처럼 생동감 넘치게 서술해야 한다.

[AI 티 안 나는 인간형 톤앤매너 핵심 지침]
1. AI 상투어구 100% 영구 금지:
   - "안녕하세요", "요즘 ~가 화제입니다", "~에 대해 알아보겠습니다", "도움이 되었기를 바라며", "다음 포스팅에서 만나요", "감사합니다" 등의 상투적 도입/결론 문장은 절대 쓰지 마라.
2. 대화체와 생생한 톤:
   - 교과서적인 사전적 정의(~란 ~를 의미합니다) 대신 "쉽게 말해 내 통장에서 매달 빠져나가는 ~원 차이입니다"처럼 실전 대화 톤으로 설명하라.
3. 문장 리듬감과 구체적 데이터:
   - 짧은 단문과 깊이 있는 장문을 조화롭게 섞어 읽기 편하게 작성하라.
4. 분량 및 실질 정보:
   - 각 섹션당 공백 포함 1,000자 내외의 풍부한 실질 정보를 작성하되 전체 분량이 4,000자 ~ 8,000자 범위 내에 들도록 조율하라.
"""


def build_section_prompt(topic: str, sec_idx: int, sec_name: str, category: str = "") -> str:
    """8개 섹션별 서로 다른 고유 분석 관점(Angle)과 전용 포맷 프롬프트 생성"""
    system_prompt = build_system_prompt()

    angles = {
        1: """[섹션 1 분석 관점: 2026년 이슈 배경 & 패러다임 변화]
- 이 주제가 2026년 현재 왜 세계적/사회적으로 가장 뜨거운 이슈인지 패러다임 변화 관점에서 분석하라.
- 일반 대중이 가지고 있는 대표적 오해 2가지를 꼬집고, 독자들의 호기심을 유발하라.
- 작성 포맷: 도입 3줄 핵심 요약 + 2026년 최근 이슈 배경 서술 (공백 포함 2,000자 이상)""",

        2: """[섹션 2 분석 관점: 메인 기술/제도적 작동 메커니즘]
- 이 주제의 핵심 동작 원리, 기술적 메커니즘 또는 제도적 구조(예: 반도체의 경우 팹/파운드리/HBM 공정 수율, 금융의 경우 금리/채권 이자 구조)를 일반인이 100% 이해하게 단계별로 설명하라.
- 작성 포맷: 3단계 동작 원리 도식화 문장 + 핵심 원리 심층 설명 (공백 포함 2,000자 이상)""",

        3: """[섹션 3 분석 관점: 글로벌 밸류체인 & 주요 기업/정부 정책 동향]
- 2026년 글로벌 거목 기업들(TSMC, 삼성전자, 엔비디아, 구글, MS 등) 및 정부 기관의 전략적 대응과 밸류체인 지형도를 분석하라.
- 작성 포맷: 마크다운 밸류체인 기업/정책 비교 분석 표 + 최신 시장 동향 (공백 포함 2,000자 이상)""",

        4: """[섹션 4 분석 관점: 2025 vs 2026 정량 손익 비교 & 수치 데이터]
- 독자 입장에서의 손익, 자본금, 비용 절감액, 시간 단축 지수를 2025년 대비 2026년 수치 데이터로 철저히 계산하라.
- 작성 포맷: 2025 vs 2026 정량 손익 비교 표 (원화, %, 기간 수치 3개 이상) + 상세 계산 근거 (공백 포함 2,000자 이상)""",

        5: """[섹션 5 분석 관점: 페르소나별 3가지 실전 시나리오 사례]
- 초보자(A), 중급 실무자(B), 전문 기획자/투자자(C) 3가지 페르소나별 실제 적용 세부 가이드와 정량적 성과 사례를 서술하라.
- 작성 포맷: 3가지 페르소나 시나리오 분석 + 실전 수수료/비용 산출 (공백 포함 2,000자 이상)""",

        6: """[섹션 6 분석 관점: 치명적 3대 리스크 & 손실 방지 체크리스트]
- 일반인이 가장 흔히 저지르는 3가지 치명적 과오/손실 리스크와 이를 예방하기 위한 안전 대책을 제시하라.
- 작성 포맷: 리스크 방지 체크리스트 표 + 실전 예방법 (공백 포함 2,000자 이상)""",

        7: """[섹션 7 분석 관점: 전문가 특급 노하우 & 2026~2027 향후 전망]
- 10년 차 전문가만 알고 있는 실전 꿀팁 3가지와 2026년 하반기~2027년 향후 기술/시장 트렌드 향방을 예측하라.
- 작성 포맷: 전문가 특급 팁 3가지 + 미래 트렌드 로드맵 (공백 포함 2,000자 이상)""",

        8: """[섹션 8 분석 관점: 자주 묻는 질문 (FAQ 5종) & 최종 실행 가이드]
- 독자들이 가장 많이 검색하는 핵심 궁금증 Q1~Q5 5가지에 대한 각 400자 이상의 깊이 있는 해답과 독자의 즉각적인 행동 실행을 유도하라.
- 작성 포맷: Q1~Q5 상세 Q&A + 실행 결언 (공백 포함 2,000자 이상)"""
    }

    angle_instruction = angles.get(sec_idx, angles[1])

    user_prompt = f"""
[포스팅 주제]: '{topic}' (카테고리: {category or 'IT/재테크'})
[현재 생성할 소제목]: '{sec_name}'

{angle_instruction}

위 지침과 분석 관점에 맞춰 상투적인 인삿말 없이 바로 내용에 들어가도록 공백 포함 2,000자 이상의 풍부한 마크다운 원고를 생성해줘.
"""

    return f"{system_prompt}\n\n{user_prompt}"


def build_blog_prompt(topic: str, category: str = "", trends: list = None) -> str:
    """15,000자 이상 자연스러운 인간형 톤 원고 프롬프트"""
    system_prompt = build_system_prompt()
    trend_context = format_trends_for_prompt(trends or [])

    user_prompt = f"""
[포스팅 주제 정보]
- 카테고리: {category or '전문 정보'}
- 메인 주제: {topic}
- 실시간 관련 트렌드 맥락: {trend_context}

위 주제에 대해 독자가 사람이 직접 연구하여 작성했다고 느낄 수 있도록, 15,000자 이상의 완성도 높은 마크다운 글을 작성해줘.
"""
    return f"{system_prompt}\n\n{user_prompt}"


def apply_tone_and_trend_to_markdown(markdown_text: str, trends: list = None) -> str:
    if not config.ENABLE_TREND_REFLECT or not trends:
        return markdown_text

    top_trend = trends[0]["title"] if trends else ""
    if not top_trend or "🔥 **실시간 관련 이슈" in markdown_text:
        return markdown_text

    banner = (
        f"\n> 🔥 **실시간 관련 이슈**: {top_trend}\n"
    )

    lines = markdown_text.splitlines()
    inserted = False
    new_lines = []

    for line in lines:
        new_lines.append(line)
        if not inserted and (line.startswith("## ") or line.strip() == "---"):
            new_lines.append(banner)
            inserted = True

    if not inserted:
        return markdown_text + "\n" + banner

    return "\n".join(new_lines)
