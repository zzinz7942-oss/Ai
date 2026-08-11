# -*- coding: utf-8 -*-
"""
최종 수익화 파이프라인 서비스 (Safety Mode & Human-in-the-Loop)
1. 일일 안전 포스팅 횟수 제한 (Safety Rate Limit)
2. 초안 생성 단계 (Trend + Coupang + AI Copy Draft)
3. 최종 승인 업로드 단계 (Human Approval Upload)
"""

import os
import json
import tempfile
import time
from datetime import datetime
from PIL import Image

from services.agent_reach_service import run_agent_reach_command
from services.coupang_api import search_coupang_products, create_deeplink
from services.content_generator import generate_marketing_caption
from services.threads_service import post_to_threads
from services.instagram_service import post_to_instagram

DAILY_LOG_FILE = "pipeline_daily_log.json"


def get_daily_post_count() -> int:
    """오늘 날짜의 업로드 횟수를 반환합니다."""
    today = datetime.now().strftime("%Y-%m-%d")
    if os.path.exists(DAILY_LOG_FILE):
        try:
            with open(DAILY_LOG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get(today, 0)
        except Exception:
            return 0
    return 0


def increment_daily_post_count():
    """오늘 날짜의 업로드 횟수를 1 증가시킵니다."""
    today = datetime.now().strftime("%Y-%m-%d")
    data = {}
    if os.path.exists(DAILY_LOG_FILE):
        try:
            with open(DAILY_LOG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    
    data[today] = data.get(today, 0) + 1

    with open(DAILY_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def generate_pipeline_draft(topic_keyword: str) -> dict:
    """
    1단계: 트렌드 수집 + 쿠팡 상품 매칭 + AI 마케팅 캡션 초안 자동 준비
    """
    logs = []
    def log(msg: str):
        logs.append(f"[{time.strftime('%H:%M:%S')}] {msg}")

    log(f"🔍 1단계 초안 준비 시작 (주제: '{topic_keyword}')")

    # Step 1: Agent Reach 트렌드 데이터 수집
    log("1️⃣ Agent Reach로 소셜/웹 트렌드 데이터 수집 중...")
    ar_res = run_agent_reach_command(["web", "search", topic_keyword])
    trend_summary = ""
    if ar_res.get("success"):
        trend_summary = ar_res["output"][:300]
        log("✅ 트렌드 수집 완료")
    else:
        log("ℹ️ 기본 키워드 모드로 전환")

    # Step 2: 쿠팡 상품 매칭
    log("2️⃣ 쿠팡 파트너스 API 상품 검색 및 딥링크 생성...")
    coupang_res = search_coupang_products(topic_keyword, limit=3)
    
    selected_prod = None
    deeplink_url = ""
    p_name = topic_keyword
    p_price = 0

    if coupang_res.get("success") and coupang_res.get("products"):
        selected_prod = coupang_res["products"][0]
        p_name = selected_prod.get("productName", topic_keyword)
        p_price = selected_prod.get("productPrice", 0)
        orig_url = selected_prod.get("productUrl", "")
        log(f"✅ 매칭된 상품: '{p_name}' ({p_price:,}원)")

        dl_res = create_deeplink([orig_url])
        if dl_res.get("success") and dl_res.get("deeplinks"):
            deeplink_url = dl_res["deeplinks"][0].get("shortUrl", orig_url)
            log(f"✅ 제휴 딥링크 생성 완료: {deeplink_url}")
        else:
            deeplink_url = orig_url
    else:
        log("ℹ️ 일반 트렌드 캡션 모드로 작성")

    # Step 3: AI 마케팅 캡션 생성
    log("3️⃣ AI 엔진으로 SNS 마케팅 캡션 초안 생성 완료")
    caption = generate_marketing_caption(
        product_name=p_name,
        product_price=p_price,
        deeplink_url=deeplink_url,
        summary=trend_summary if trend_summary else f"SNS 핫트렌드 {topic_keyword}",
        category="트렌드/추천"
    )

    # 대표 이미지 생성
    temp_dir = tempfile.mkdtemp()
    thumb_path = os.path.join(temp_dir, "draft_promo.png")
    try:
        img = Image.new('RGB', (540, 540), color=(15, 23, 42))
        img.save(thumb_path)
    except Exception:
        thumb_path = None

    return {
        "success": True,
        "product_name": p_name,
        "product_price": p_price,
        "deeplink_url": deeplink_url,
        "caption": caption,
        "thumb_path": thumb_path,
        "logs": logs
    }


def approve_and_publish(draft_data: dict, caption_text: str, max_daily_limit: int = 3, post_threads: bool = True, post_insta: bool = False) -> dict:
    """
    2단계 (Human-in-the-Loop): 최종 사람 승인 후 일일 안전 포스팅 제한 체크 및 SNS 업로드
    """
    current_count = get_daily_post_count()
    if current_count >= max_daily_limit:
        return {
            "success": False,
            "error": f"⚠️ 일일 안전 포스팅 제한({current_count}/{max_daily_limit}회)에 도달하였습니다. 내일 다시 시도하거나 세이프티 제한을 변경해 주세요."
        }

    results = {}
    thumb_path = draft_data.get("thumb_path")

    if post_threads:
        t_res = post_to_threads(text=caption_text, image_path=thumb_path)
        results["threads"] = t_res

    if post_insta:
        i_res = post_to_instagram(caption=caption_text, image_path=thumb_path)
        results["instagram"] = i_res

    # 성공 시 일일 횟수 증가
    increment_daily_post_count()

    return {
        "success": True,
        "daily_count": get_daily_post_count(),
        "sns_results": results
    }
