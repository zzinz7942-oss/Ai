"""
단건 포스트 보완 테스트 및 3대 버그 검증 스크립트 (Test Single Post Repair)
"""

import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import audit_published_posts


def run_single_test():
    print("=" * 70)
    print("🧪 [단건 포스트 보완 및 3대 버그 수정 검증 테스트]")
    print("=" * 70)

    audit_results = audit_published_posts.audit_all_published_posts()
    high_risks = [item for item in audit_results if item["risk_level"] in ["HIGH", "MEDIUM"]]

    if not high_risks:
        print("  🎉 보완 대상 포스트가 없습니다.")
        return

    # 첫 번째(반도체 관련) 포스트 단건 선정
    target_post = high_risks[0]
    print(f"\n🎯 [테스트 대상 단건 포스트]: '{target_post['title']}' (ID: {target_post['post_id']})")
    print(f"  - 기존 글자 수: {target_post['char_count']:,}자")

    # 보완 수정 실행 (6대 검증 + 3회 재시도 적용)
    res = audit_published_posts.repair_post(target_post, max_retries=3)

    print("\n" + "=" * 70)
    print("📊 [단건 테스트 결과 요약]")
    if res.get("success"):
        m = res.get("metrics", {})
        print(f"  - 상태        : ✅ 100% 6대 검증 통과 완료")
        print(f"  - 최종 글자 수: {m.get('char_count', 0):,}자 (공백 포함)")
        print(f"  - 이미지 개수 : {m.get('image_count', 0)}개 (중복 0%, 거울셀카 필터링)")
        print(f"  - 해시태그 수 : {m.get('hashtag_count', 0)}개 (조사/동사 정제 완료)")
    else:
        print(f"  - 상태        : 🛑 실패 ({res.get('error')})")
    print("=" * 70)


if __name__ == "__main__":
    run_single_test()
