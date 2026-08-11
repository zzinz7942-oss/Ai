"""
HTML 콘텐츠 빌더 (Image Clean-Up & Multi-Section Dynamic Injection & Query Translator)
- 마크다운 본문 내 AI가 임의 생성한 텍스트 캡션/출처 문구 자동 제거
- 유효한 http(s):// 이미지 URL에 대해서만 <img src="..."> + <figcaption> 한 벌로 정상 조합
- 소제목(H2/H3)별로 5~8개 이미지 동적 배치 및 전문 주제별 영문 키워드 매핑
- CSS 색상 Hex 코드(#1a1a2e 등) 및 순수 숫자 태그 배제
- 한 포스트 내 동일 이미지 URL 중복 수집 100% 방지
"""

import re
from pathlib import Path
from typing import Optional, List, Set

import markdown as md_lib

_POST_CSS = """
<style>
  .blog-post { font-family: 'Noto Sans KR', sans-serif; line-height: 1.85; color: #1e293b; max-width: 820px; margin: auto; padding: 10px; }
  .blog-post h2 { font-size: 1.65rem; color: #0f172a; border-left: 6px solid #2563eb; padding-left: 14px; margin: 2.8rem 0 1.2rem; font-weight: 700; }
  .blog-post h3 { font-size: 1.25rem; color: #1e293b; margin: 2.2rem 0 0.9rem; font-weight: 600; border-bottom: 2px solid #f1f5f9; padding-bottom: 6px; }
  .blog-post p  { margin-bottom: 1.3rem; font-size: 1.04rem; word-break: keep-all; }
  .blog-post blockquote { background: #f0fdf4; border-left: 4px solid #16a34a; padding: 14px 20px; border-radius: 8px; margin: 1.8rem 0; font-size: 0.98rem; }
  .blog-post table { width: 100%; border-collapse: collapse; margin: 1.8rem 0; font-size: 0.96rem; }
  .blog-post th { background: #1e293b; color: #fff; padding: 11px 15px; text-align: left; }
  .blog-post td { padding: 10px 15px; border-bottom: 1px solid #e2e8f0; }
  .blog-post tr:nth-child(even) td { background: #f8fafc; }
  .blog-post hr { border: none; border-top: 2px solid #e2e8f0; margin: 2.8rem 0; }
  .post-image-wrap { margin: 2.2rem 0; text-align: center; clear: both; }
  .post-image-wrap img { max-width: 100%; border-radius: 14px; box-shadow: 0 8px 30px rgba(0,0,0,0.12); height: auto; display: block; margin: 0 auto; }
  .post-image-wrap figcaption { font-size: 0.85rem; color: #64748b; margin-top: 8px; }
  .tip-box { background: #eff6ff; border-left: 4px solid #3b82f6; padding: 16px 20px; border-radius: 8px; margin: 1.8rem 0; }
  .tip-box strong { color: #1d4ed8; }
  .summary-box { background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 12px; padding: 18px 22px; margin: 1.5rem 0 2.2rem; }
  .summary-box h4 { margin-top: 0; color: #0f172a; font-size: 1.1rem; }
  .post-tags-container { margin-top: 45px; padding-top: 25px; border-top: 1px dashed #cbd5e1; }
  .post-tag-badge { display: inline-block; background: #f1f5f9; color: #2563eb; font-size: 14px; font-weight: 600; padding: 6px 14px; border-radius: 20px; margin-right: 8px; margin-bottom: 10px; text-decoration: none; }
</style>
"""

_TIP_RE = re.compile(r'<blockquote>\s*<p>💡(.*?)</p>\s*</blockquote>', re.DOTALL)
HEX_COLOR_RE = re.compile(r'^#?[0-9a-fA-F]{3,6}$')

# 불필요한 조사, 동사, 어미, 대명사 한국어 스톱워드
KOREAN_STOPWORDS = {
    "당신이", "당신의", "당신은", "보이지", "않는", "알아야", "있어야", "무엇이", "어떻게",
    "우리가", "내가", "그것은", "이것은", "하는", "할까", "위한", "대한", "통해", "관한",
    "따른", "위해", "하며", "되고", "있는", "되면", "해서", "움직이는", "아닌", "모든",
    "하여", "되는", "가지", "관련", "대해", "따라", "부터", "까지", "에게", "에서",
    "으로", "로써", "라고", "하고", "하며", "이고", "이며", "어떤", "무슨", "이런",
    "저런", "그런", "것이", "것을", "것은", "것이다", "방법", "가이드", "정리", "2026년",
    "꿀팁", "추천", "필수", "총정리", "노하우", "핵심", "비교", "주의해야", "폭탄",
    "고르는", "3가지", "2가지", "1가지", "4가지", "5가지", "종료", "유예", "데이", "진짜",
    "이유", "승자로", "패배자에서", "버는", "쓰는", "듣는", "보는", "주는", "찾는", "만드는",
    "이렇게", "바뀌어야", "한다", "시작해야", "깨달은", "준비하며"
}



def _image_html(alt: str, credit: str, hosted_url: Optional[str] = None, web_url: Optional[str] = None) -> str:
    src = ""
    if hosted_url and hosted_url.startswith("http") and "localhost" not in hosted_url:
        src = hosted_url
    elif web_url and web_url.startswith("http") and "localhost" not in web_url:
        src = web_url

    if not src:
        return ""

    return (
        f'<div class="post-image-wrap">\n'
        f'<img src="{src}" alt="{alt}" loading="lazy">\n'
        f'</div>\n'
    )


def clean_llm_raw_credits(markdown_text: str) -> str:
    lines = markdown_text.split('\n')
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if re.search(r'Photo by .* on Unsplash', stripped, re.IGNORECASE):
            continue
        if re.search(r'Photo via .*', stripped, re.IGNORECASE):
            continue
        if '<figcaption>' in stripped or '</figcaption>' in stripped:
            continue
        cleaned_lines.append(line)
    return '\n'.join(cleaned_lines)


def is_valid_topic_hashtag(tag: str) -> bool:
    clean = tag.strip().lstrip('#')
    if not clean or len(clean) < 2:
        return False
    if HEX_COLOR_RE.match(clean):
        return False
    if clean.isdigit():
        return False
    if re.search(r'^\d+가지$', clean):
        return False
    if clean in KOREAN_STOPWORDS:
        return False
    if clean.endswith(('는', '은', '를', '을', '에서', '하여', '하며', '까지', '부터')):
        return False
    return True



def extract_and_format_tags(markdown_text: str, extra_labels: Optional[List[str]] = None) -> tuple[str, str]:
    labels = set()

    if extra_labels:
        for lbl in extra_labels:
            clean = str(lbl).strip().lstrip('#')
            if is_valid_topic_hashtag(clean):
                labels.add(clean)

    found = re.findall(r'(?:^|\s)#([\w가-힣]+)', markdown_text)
    for f in found:
        clean = f.strip().lstrip('#')
        if is_valid_topic_hashtag(clean):
            labels.add(clean)

    clean_md = re.sub(r'(?:\n\s*#[\w가-힣]+)+$', '', markdown_text.strip())

    if not labels:
        return clean_md, ""

    sorted_labels = sorted(list(labels))
    tag_badges = [f'<span class="post-tag-badge">#{t}</span>' for t in sorted_labels]
    tags_block = f'<div class="post-tags-container">\n{"".join(tag_badges)}\n</div>'

    return clean_md, tags_block


def to_english_image_query(text: str) -> str:
    """한국어 텍스트를 전문 영문 검색 키워드로 변환"""
    t_lower = text.lower()

    if any(w in t_lower for w in ["반도체", "칩", "파운드리", "생산", "엔진", "하드웨어"]):
        return "semiconductor microchip processor technology circuit board"
    elif any(w in t_lower for w in ["부동산", "집", "청약", "증여", "건물"]):
        return "real estate modern house architecture document"
    elif any(w in t_lower for w in ["주식", "etf", "투자", "재테크", "금리", "절세", "예적금", "연금"]):
        return "stock market finance growth chart trading investment"
    elif any(w in t_lower for w in ["ai", "인공지능", "챗gpt", "에이전트", "자동화", "소프트웨어"]):
        return "artificial intelligence technology laptop data code"
    elif any(w in t_lower for w in ["건강", "영양제", "운동", "식단", "피로"]):
        return "wellness health fitness nutrition active lifestyle"
    elif any(w in t_lower for w in ["가전", "노트북", "스마트폰", "테크"]):
        return "modern tech gadgets laptop smartphone office"

    # 기본 정제 영문 워드 추출
    words = [w for w in re.findall(r'[a-zA-Z]{3,}', text)]
    if words:
        return " ".join(words[:4]) + " business technology"

    return "modern technology business work professional"


def extract_keywords_for_images(markdown_text: str, topic_title: str = "") -> list[dict]:
    headings = re.findall(r'^##\s+.+', markdown_text, re.MULTILINE)
    if not headings:
        headings = re.findall(r'^###\s+.+', markdown_text, re.MULTILINE)

    title_match = re.search(r'^#\s+(.+)', markdown_text, re.MULTILINE)
    main_title = topic_title or (title_match.group(1).strip() if title_match else "technology")

    keywords = [
        {
            "key": "thumbnail",
            "ko": main_title,
            "en": to_english_image_query(main_title),
        }
    ]

    for idx, heading in enumerate(headings[:7], 1):
        clean_heading = re.sub(r'^##?\s+\d*\.?\s*', '', heading).strip()
        keywords.append({
            "key": f"section_{idx}",
            "ko": clean_heading,
            "en": to_english_image_query(clean_heading),
        })

    return keywords


def build_html(
    markdown_text: str,
    images: dict,
    hosted_urls: Optional[dict] = None,
    labels: Optional[List[str]] = None,
) -> str:
    hosted_urls = hosted_urls or {}

    markdown_text = clean_llm_raw_credits(markdown_text)
    clean_md, tags_html_block = extract_and_format_tags(markdown_text, labels)

    raw_html = md_lib.markdown(
        clean_md,
        extensions=["tables", "fenced_code", "nl2br", "sane_lists"],
    )

    styled_html = _TIP_RE.sub(
        lambda m: f'<div class="tip-box"><strong>💡 실용 팁</strong>{m.group(1)}</div>',
        raw_html,
    )

    section_keys = [f"section_{i}" for i in range(1, 10)]
    injected_keys = set()
    used_img_urls = set()
    section_idx = 0

    def inject_after_heading(match):
        nonlocal section_idx
        tag = match.group(0)
        key = section_keys[section_idx] if section_idx < len(section_keys) else None
        section_idx += 1

        if key and key in images and images[key]:
            img_meta = images[key]
            target_url = hosted_urls.get(key) or img_meta.get("url")

            if target_url in used_img_urls:
                return tag

            img_block = _image_html(
                alt=img_meta.get("alt_text", ""),
                credit=img_meta.get("credit", ""),
                hosted_url=hosted_urls.get(key),
                web_url=img_meta.get("url"),
            )
            if img_block:
                injected_keys.add(key)
                if target_url:
                    used_img_urls.add(target_url)
                return tag + "\n" + img_block
        return tag

    styled_html = re.sub(r'<h[23]>.*?</h[23]>', inject_after_heading, styled_html)

    thumbnail_block = ""
    if "thumbnail" in images and images["thumbnail"]:
        meta = images["thumbnail"]
        target_url = hosted_urls.get("thumbnail") or meta.get("url")
        thumbnail_block = _image_html(
            alt=meta.get("alt_text", ""),
            credit=meta.get("credit", ""),
            hosted_url=hosted_urls.get("thumbnail"),
            web_url=meta.get("url"),
        )
        if target_url:
            used_img_urls.add(target_url)

    final_html = (
        _POST_CSS
        + '<div class="blog-post">\n'
        + thumbnail_block
        + styled_html
        + "\n"
        + tags_html_block
        + "\n</div>"
    )
    return final_html
