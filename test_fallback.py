import sys
sys.path.insert(0, '.')
from services.omniroute_service import generate_ai_text_with_fallback

print("=== Fallback Chain Test ===")
result = generate_ai_text_with_fallback(
    prompt="쿠팡 주방용품 상품을 SNS에 홍보하는 한국어 마케팅 문구 한 문장만 써줘.",
    system_instruction="SNS 마케팅 전문가입니다."
)

if result.get("success"):
    print(f"SUCCESS: {result.get('provider')}")
    print(f"RESPONSE: {result.get('text')}")
else:
    print(f"FAIL: {result.get('error')}")
