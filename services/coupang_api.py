# -*- coding: utf-8 -*-
"""
쿠팡 파트너스 API 연동 모듈 (Coupang API Service)
- HMAC-SHA256 암호화 인증 헤더 생성
- 쿠팡 상품 키워드 검색
- 딥링크 (Affiliate Link) 변환 API
"""

import hmac
import hashlib
import time
import requests
import json
from config import get_config, COUPANG_ACCESS_KEY, COUPANG_SECRET_KEY, COUPANG_SUB_ID

DOMAIN = "https://api-gateway.coupang.com"


def generate_hmac_signature(method: str, url_path: str, secret_key: str, access_key: str, query_string: str = "") -> str:
    """
    쿠팡 파트너스 API용 HMAC-SHA256 서명 인증 헤더를 생성합니다.
    """
    # GMT 타임스탬프 형식 (YYMMDDTHHMMSSZ)
    datetime_gmt = time.strftime('%y%m%dT%H%M%SZ', time.gmtime())
    
    message = datetime_gmt + method + url_path + query_string
    signature = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    auth_header = f"CEA algorithm=HmacSHA256, access-key={access_key}, signed-date={datetime_gmt}, signature={signature}"
    return auth_header


def search_coupang_products(keyword: str, limit: int = 5) -> dict:
    """
    키워드로 쿠팡 상품을 검색하여 상품 목록을 반환합니다.
    공식 규격 엔드포인트: /v2/providers/affiliate_open_api/apis/openapi/products/search
    """
    access_key = get_config(COUPANG_ACCESS_KEY)
    secret_key = get_config(COUPANG_SECRET_KEY)

    if not access_key or not secret_key:
        return {
            "success": False,
            "error": "쿠팡 파트너스 Access Key 및 Secret Key 설정이 필요합니다."
        }

    method = "GET"
    # 검증된 공식 엔드포인트 경로
    candidate_paths = [
        "/v2/providers/affiliate_open_api/apis/openapi/products/search",
        "/v2/providers/affiliate_open_api/apis/openapi/v1/products/search"
    ]
    query = f"keyword={requests.utils.quote(keyword)}&limit={limit}"

    last_error = ""

    for path in candidate_paths:
        auth_header = generate_hmac_signature(method, path, secret_key, access_key, query)
        headers = {
            "Authorization": auth_header,
            "Content-Type": "application/json;charset=UTF-8"
        }
        url = f"{DOMAIN}{path}?{query}"

        try:
            response = requests.get(url, headers=headers, timeout=10)
            data = response.json()

            if response.status_code == 200 and data.get("rCode") == "0":
                product_list = data.get("data", {}).get("productData", [])
                return {
                    "success": True,
                    "products": product_list,
                    "used_path": path
                }
            else:
                r_msg = data.get("rMessage", response.text)
                r_code = data.get("rCode", "")
                last_error = f"[{r_code}] {r_msg}"

                # PRECONDITION_FAILED 인 경우 다음 candidate_path 시도
                if "PRECONDITION_FAILED" in str(r_msg) or "PRECONDITION_FAILED" in str(r_code):
                    continue
                else:
                    break

        except Exception as e:
            last_error = str(e)
            continue

    return {
        "success": False,
        "error": f"쿠팡 API 호출 실패: {last_error}"
    }


def create_deeplink(coupang_urls: list[str]) -> dict:
    """
    일반 쿠팡 상품 URL을 파트너스 제휴 딥링크 URL로 변환합니다.
    """
    access_key = get_config(COUPANG_ACCESS_KEY)
    secret_key = get_config(COUPANG_SECRET_KEY)
    sub_id = get_config(COUPANG_SUB_ID, default="streamlit_app")

    if not access_key or not secret_key:
        return {
            "success": False,
            "error": "쿠팡 파트너스 API 키가 설정되지 않았습니다."
        }

    method = "POST"
    path = "/v2/providers/affiliate_open_api/apis/openapi/v1/deeplink"
    
    auth_header = generate_hmac_signature(method, path, secret_key, access_key, "")
    
    headers = {
        "Authorization": auth_header,
        "Content-Type": "application/json;charset=UTF-8"
    }

    payload = {
        "coupangUrls": coupang_urls,
        "subId": sub_id
    }

    url = f"{DOMAIN}{path}"
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        data = response.json()
        
        if response.status_code == 200 and data.get("rCode") == "0":
            deeplink_list = data.get("data", [])
            return {
                "success": True,
                "deeplinks": deeplink_list
            }
        else:
            r_msg = data.get("rMessage", response.text)
            return {"success": False, "error": f"딥링크 생성 오류: {r_msg}"}

    except Exception as e:
        return {"success": False, "error": f"딥링크 요청 예외: {str(e)}"}
