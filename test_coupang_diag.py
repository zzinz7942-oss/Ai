# -*- coding: utf-8 -*-
"""
쿠팡 파트너스 API 엔드포인트 및 인증 진단 스크립트
"""

import hmac
import hashlib
import time
import requests

DOMAIN = "https://api-gateway.coupang.com"

def generate_signature(method: str, path: str, secret_key: str, access_key: str, query: str = "") -> tuple[str, str]:
    datetime_gmt = time.strftime('%y%m%dT%H%M%SZ', time.gmtime())
    message = datetime_gmt + method + path + query
    signature = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    auth_header = f"CEA algorithm=HmacSHA256, access-key={access_key}, signed-date={datetime_gmt}, signature={signature}"
    return auth_header, datetime_gmt

def test_endpoints(access_key: str, secret_key: str, keyword: str = "노트북"):
    paths_to_test = [
        "/v2/providers/affiliate_open_api/apis/openapi/v2/products/search",
        "/v2/providers/affiliate_open_api/apis/openapi/products/search",
        "/v2/providers/affiliate_open_api/apis/openapi/v1/products/search",
        "/v2/providers/affiliate_open_api/apis/openapi/v1/deeplink"
    ]

    print(f"Testing Coupang API with AccessKey={access_key[:5]}***...")

    for path in paths_to_test:
        if "deeplink" in path:
            method = "POST"
            query = ""
            payload = {"coupangUrls": ["https://www.coupang.com/vp/products/123456"], "subId": "test"}
            auth_header, _ = generate_signature(method, path, secret_key, access_key, query)
            headers = {"Authorization": auth_header, "Content-Type": "application/json;charset=UTF-8"}
            url = f"{DOMAIN}{path}"
            res = requests.post(url, headers=headers, json=payload, timeout=5)
        else:
            method = "GET"
            query = f"keyword={requests.utils.quote(keyword)}&limit=1"
            auth_header, _ = generate_signature(method, path, secret_key, access_key, query)
            headers = {"Authorization": auth_header, "Content-Type": "application/json;charset=UTF-8"}
            url = f"{DOMAIN}{path}?{query}"
            res = requests.get(url, headers=headers, timeout=5)

        print(f"\nPath: {path}")
        print(f"Status Code: {res.status_code}")
        print(f"Response: {res.text}")

if __name__ == "__main__":
    import os
    ak = os.getenv("COUPANG_ACCESS_KEY", "test_access_key")
    sk = os.getenv("COUPANG_SECRET_KEY", "test_secret_key")
    test_endpoints(ak, sk)
