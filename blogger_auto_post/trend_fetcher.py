"""
실시간 트렌드 수집 및 주제 관련성 파싱 모듈
- Google News RSS를 포스트의 실제 주제(topic_keyword)에 맞게 수집
- 포스트 주제와 관련이 없는 트렌드는 자동 필터링하여 오삽입 방지
"""

import xml.etree.ElementTree as ET
import requests
import re
from typing import List, Dict
import config


def fetch_realtime_trends(topic_keyword: str = "IT", max_count: int = 5) -> List[Dict]:
    """
    포스트 주제(topic_keyword)에 꼭 맞는 트렌드 뉴스를 수집합니다.
    """
    if not getattr(config, "ENABLE_TREND_REFLECT", True):
        return []

    print(f"\n🔥 실시간 트렌드 수집 중 (주제 키워드: '{topic_keyword}')...")
    trends = []

    try:
        url = f"https://news.google.com/rss/search?q={requests.utils.quote(topic_keyword)}+%ED%8A%B8%EB%A0%8C%EB%93%9C&hl=ko&gl=KR&ceid=KR:ko"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            for item in root.findall("./channel/item")[:max_count]:
                title = item.findtext("title", "")
                link = item.findtext("link", "")
                pubDate = item.findtext("pubDate", "")
                
                topic_words = [w for w in re.findall(r'[\w가-힣]{2,}', topic_keyword) if len(w) >= 2]
                is_relevant = any(w in title for w in topic_words) if topic_words else True
                
                if title and is_relevant:
                    trends.append({
                        "title": title,
                        "link": link,
                        "pubDate": pubDate,
                        "source": "Google News Trends",
                        "is_relevant": True
                    })
    except Exception as e:
        print(f"  ⚠️ 뉴스 트렌드 RSS 수집 중 알림 ({e})")

    print(f"  ✅ 주제 관련 실시간 트렌드 {len(trends)}개 수집 완료")
    return trends


def format_trends_for_prompt(trends: List[Dict]) -> str:
    """수집된 트렌드 정보를 프롬프트용 텍스트 블록으로 정리합니다."""
    if not trends:
        return "최신 트렌드 정보 없음 (기본 지식 기반 작성)"

    lines = ["실시간 관련 트렌드 및 최신 이슈:"]
    for t in trends[:5]:
        lines.append(f"- {t['title']} ({t['source']})")
    return "\n".join(lines)


def check_trend_relevance(markdown_text: str, topic_title: str) -> bool:
    """
    본문에 트렌드 인용구가 삽입되어 있다면, 해당 인용구가 주제(topic_title)와 관련성이 있는지 검사합니다.
    """
    if "🔥 **최신 트렌드" not in markdown_text:
        return True

    match = re.search(r'>\s*🔥\s*\*\*최신 트렌드[^*]*\*\*:\s*([^\n]+)', markdown_text)
    if not match:
        return True

    trend_text = match.group(1).strip()
    topic_keywords = [w for w in re.findall(r'[\w가-힣]{2,}', topic_title) if w not in ["방법", "가이드", "정리", "2026년", "꿀팁", "추천", "필수"]]
    
    if not topic_keywords:
        return True

    is_relevant = any(kw in trend_text for kw in topic_keywords)
    return is_relevant
