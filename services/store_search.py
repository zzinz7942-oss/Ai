# -*- coding: utf-8 -*-
"""
다이소/GS25/올리브영 실제 크롤링 + OmniRoute 통합 블로그 생성
"""

import os
import time
import requests
from bs4 import BeautifulSoup
from services.omniroute_service import generate_ai_text_with_fallback

HEADERS_COMMON = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/json",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS_COMMON)


def _safe_request(url, params=None, headers=None, timeout=15):
    try:
        h = {**HEADERS_COMMON, **(headers or {})}
        resp = SESSION.get(url, params=params, headers=h, timeout=timeout)
        resp.raise_for_status()
        return resp
    except Exception as e:
        print(f"  ⚠ 요청 실패 [{url}]: {e}")
        return None

def search_oliveyoung(keyword: str, max_items: int = 10) -> list:
    print(f"[올리브영] '{keyword}' 검색 중...")
    url = "https://www.oliveyoung.co.kr/store/search/getSearchMain.do"
    params = {"query": keyword}
    resp = _safe_request(url, params=params)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    items = []
    product_list = soup.select("ul.cate_prd_list li") or soup.select("div.prd_info")

    for li in product_list[:max_items]:
        try:
            name_tag = li.select_one("p.tx_name") or li.select_one("a.prd_name") or li.select_one("[class*='name']")
            price_tag = li.select_one("span.tx_cur span.tx_num") or li.select_one("span.price") or li.select_one("[class*='price']")
            brand_tag = li.select_one("span.tx_brand") or li.select_one("[class*='brand']")
            link_tag = li.select_one("a[href]")

            name = name_tag.get_text(strip=True) if name_tag else ""
            price = price_tag.get_text(strip=True) if price_tag else ""
            brand = brand_tag.get_text(strip=True) if brand_tag else ""
            link = link_tag["href"] if link_tag else ""

            if name:
                if link and not link.startswith("http"):
                    link = "https://www.oliveyoung.co.kr" + link
                items.append({"store": "올리브영", "name": name, "price": price, "brand": brand, "url": link})
        except Exception:
            continue
    return items

def search_daiso(keyword: str, max_items: int = 10) -> list:
    print(f"[다이소] '{keyword}' 검색 중...")
    url = "https://www.daisomall.co.kr/api/search/goods"
    params = {"keyword": keyword, "page": 1, "size": max_items}
    headers = {**HEADERS_COMMON, "Referer": "https://www.daisomall.co.kr/", "Accept": "application/json"}
    resp = _safe_request(url, params=params, headers=headers)

    if not resp or resp.status_code != 200:
        return _search_daiso_html(keyword, max_items)

    items = []
    try:
        data = resp.json()
        goods_list = data.get("data", {}).get("goods", []) or data.get("result", {}).get("items", []) or data.get("items", []) or []
        for g in goods_list[:max_items]:
            name = g.get("goodsNm") or g.get("name") or g.get("title", "")
            price = g.get("salePrice") or g.get("price") or ""
            code = g.get("goodsNo") or g.get("goodsCd") or ""
            items.append({"store": "다이소", "name": name, "price": f"{price}원" if price else "", "brand": "", "url": f"https://www.daisomall.co.kr/goods/{code}" if code else ""})
    except Exception:
        return _search_daiso_html(keyword, max_items)
    return items

def _search_daiso_html(keyword: str, max_items: int = 10) -> list:
    url = f"https://www.daisomall.co.kr/search?keyword={keyword}"
    resp = _safe_request(url)
    if not resp:
        return []
    soup = BeautifulSoup(resp.text, "html.parser")
    items = []
    cards = soup.select("div.goods-list li") or soup.select("ul.product-list li") or soup.select("[class*='product'] [class*='item']")
    for card in cards[:max_items]:
        try:
            name_tag = card.select_one("[class*='name']") or card.select_one("a")
            price_tag = card.select_one("[class*='price']") or card.select_one("span.num")
            name = name_tag.get_text(strip=True) if name_tag else ""
            price = price_tag.get_text(strip=True) if price_tag else ""
            if name:
                items.append({"store": "다이소", "name": name, "price": price, "brand": "", "url": ""})
        except Exception:
            continue
    return items

def search_gs25(keyword: str, max_items: int = 10) -> list:
    print(f"[GS25] '{keyword}' 검색 중...")
    url = "https://gs25.gsretail.com/gscvs/ko/products/youus-freshfoodDetail-search"
    params = {"searchWord": keyword, "pageNum": 1, "pageSize": max_items}
    headers = {**HEADERS_COMMON, "Referer": "https://gs25.gsretail.com/", "Accept": "application/json, text/html", "X-Requested-With": "XMLHttpRequest"}
    resp = _safe_request(url, params=params, headers=headers)
    items = []
    if resp:
        try:
            data = resp.json()
            results = data.get("results", []) or data.get("data", {}).get("list", []) or data.get("SubPageListData", []) or []
            for g in results[:max_items]:
                name = g.get("goodsNm") or g.get("name") or ""
                price = g.get("price") or g.get("salePrice") or ""
                items.append({"store": "GS25", "name": name, "price": f"{price}원" if price else "", "brand": "", "url": ""})
            if items:
                return items
        except Exception:
            pass
    return _search_gs25_html(keyword, max_items)

def _search_gs25_html(keyword: str, max_items: int = 10) -> list:
    urls_to_try = [
        "https://gs25.gsretail.com/gscvs/ko/products/event-goods",
        "https://gs25.gsretail.com/gscvs/ko/products/youus-pricing",
    ]
    items = []
    for page_url in urls_to_try:
        resp = _safe_request(page_url)
        if not resp:
            continue
        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select("div.prod_list li") or soup.select("ul.product_list li") or soup.select("[class*='product'] [class*='item']")
        for card in cards[:max_items]:
            try:
                name_tag = card.select_one("p.tit") or card.select_one("[class*='name']")
                price_tag = card.select_one("span.cost") or card.select_one("[class*='price']")
                name = name_tag.get_text(strip=True) if name_tag else ""
                price = price_tag.get_text(strip=True) if price_tag else ""
                if name and keyword.lower() in name.lower():
                    items.append({"store": "GS25", "name": name, "price": price, "brand": "", "url": page_url})
            except Exception:
                continue
        if items:
            break
        time.sleep(0.5)
    return items

def search_all(keyword: str) -> dict:
    results = {
        "keyword": keyword,
        "올리브영": search_oliveyoung(keyword),
        "다이소": search_daiso(keyword),
        "GS25": search_gs25(keyword),
    }
    return results

def generate_blog_report_omniroute(keyword: str) -> dict:
    raw = search_all(keyword)
    scraped_text = f"[검색 키워드: {keyword}]\n\n"
    
    for store_name in ["다이소", "GS25", "올리브영"]:
        items = raw.get(store_name, [])
        scraped_text += f"## {store_name} 검색 결과 ({len(items)}건)\n"
        if not items:
            scraped_text += "  (검색 결과 없음 — 사이트 차단 또는 해당 상품 미취급)\n\n"
            continue
        for i, item in enumerate(items, 1):
            scraped_text += f"  {i}. {item['name']} | 가격: {item['price'] or '미표시'} | 브랜드: {item['brand'] or '-'}\n"
        scraped_text += "\n"

    system_prompt = (
        "너는 한국 소비자 블로그 전문 작가야. "
        "아래 '실제 크롤링 데이터'만을 근거로 글을 써. "
        "데이터에 없는 상품이나 가격을 지어내지 마. "
        "데이터가 비어있는 매장은 '검색 결과를 가져오지 못했다'고 솔직히 써. "
        "AI스러운 과한 이모지, ~해요체 반복, 가짜 통계 금지. "
        "자연스러운 구어체, 실사용 관점으로 작성."
    )

    user_prompt = f"""아래는 다이소, GS25, 올리브영에서 '{keyword}'를 실제로 크롤링한 결과야.
이 데이터만 사용해서 블로그 비교 리포트를 작성해줘.

━━━ 크롤링 데이터 시작 ━━━
{scraped_text}
━━━ 크롤링 데이터 끝 ━━━

작성 조건:
- 제목: '{keyword}' 어디서 사야 할까? 다이소 vs GS25 vs 올리브영 실제 비교
- 자연스러운 도입부 (왜 비교하게 됐는지)
- 매장별 섹션: 실제 검색된 상품명, 가격, 특징 정리
- 결론: 가성비/품질/접근성 기준 추천
- 분량: 1500자 이상
- 마크다운 형식"""

    res = generate_ai_text_with_fallback(user_prompt, system_instruction=system_prompt)
    
    if not res.get("success"):
        return {"success": False, "provider": "None", "report": scraped_text, "error": "AI 호출 실패"}
        
    return {"success": True, "provider": res.get("provider", "Unknown"), "report": res.get("text", "")}
