"""
blog_content_standards.py 연동 및 단일 마크다운 검증 테스트
"""

import sys
import os

os.environ["PYTHONUNBUFFERED"] = "1"
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def pprint(*args, **kwargs):
    kwargs["flush"] = True
    print(*args, **kwargs)

import blog_content_standards
import main

pprint("=" * 70)
pprint("🧪 [blog_content_standards.py 단일 표준 하드 게이트 연동 테스트]")
pprint("=" * 70)

# 테스트 포스트 샘플
test_title = "노키아가 스마트폰 패배자에서 AI 수혜주로 부활한 3가지 핵심 이유"
sample_body = """
2026년 현재 노키아 AI 네트워크 인프라와 주가 급등 분야는 단순한 일시적 이슈를 넘어 전체 산업 생태계의 패러다임이 근본적으로 개편되는 전환점에 있습니다.

1. 스마트폰 사업 철수 이후 10년 통신 인프라 기업 체질 개선
2. AI 데이터센터 트래픽 폭증과 광네트워킹 장비 독점 수혜
3. 엔비디아 AI RAN 파트너십 결합 및 차세대 통신 인프라 구축

""" + ("노키아 벨연구소의 고성능 라우팅 실리콘과 800G 광스위치 장비는 글로벌 데이터센터 트래픽을 처리하는 핵심 인프라로 자리 잡았습니다. " * 75)

sample_images = [
    "https://images.unsplash.com/photo-1518770660439",
    "https://images.unsplash.com/photo-1451187580459",
    "https://images.unsplash.com/photo-1526374965328"
]

val_result = blog_content_standards.run_full_validation(test_title, sample_body, sample_images)

pprint(f"📌 전체 검증 통과 여부: {val_result['passed']}")
pprint("📊 세부 검증 항목:")
for name, (passed, msg) in val_result["details"].items():
    status_icon = "✅" if passed else "❌"
    pprint(f"   {status_icon} [{name}] {msg}")

# main.py validate_post 연동 검증
is_pass, metrics = main.validate_post(
    title=test_title,
    html_content="<p>" + sample_body + "</p>" + "".join([f'<img src="{u}">' for u in sample_images]),
    markdown_text=sample_body,
    labels=["#노키아", "#AI기술", "#통신망", "#테크", "#반도체", "#엔비디아", "#네트워크", "#블로그"],
    topic="노키아 AI 네트워크 부활",
    image_count=len(sample_images),
    image_hashes=[]
)

pprint(f"\n🚀 main.validate_post() 연동 결과: Pass={is_pass}")
if not is_pass:
    pprint(f"   - 결격 사유: {metrics['fail_reasons']}")

pprint("=" * 70)
