"""
post_content.md의 고품질 원고를 직접 HTML로 변환하여 Blogger에 즉시 업로드하는 스크립트
"""

import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import config
import content_builder
import blogger_client

post_md_path = Path("post_content.md")
if not post_md_path.exists():
    print("❌ post_content.md 파일이 존재하지 않습니다.")
    sys.exit(1)

md_text = post_md_path.read_text(encoding="utf-8")

# 첫 번째 줄 (# 제목) 에서 제목 추출
lines = md_text.strip().split("\n")
title = "매달 아껴도 통장이 텅 빈다면? 연 100만 원 버리는 지출 누수 패턴 5가지와 차단법"
for line in lines:
    if line.startswith("# "):
        title = line.replace("# ", "").strip()
        break

print(f"📌 [업로드 준비] 제목: {title}")

# HTML 변환
labels = ["지출누수", "재테크", "구독다이어트", "페이인포", "카드포인트"]
html_content = content_builder.build_html(md_text, images={}, hosted_urls={}, labels=labels)

print(f"📊 HTML 변환 완료 (길이: {len(html_content):,}자)")

# Blogger 업로드 (DRAFT 또는 LIVE 설정)
try:
    result = blogger_client.upload_post(
        title=title,
        html_content=html_content,
        labels=labels,
        status=getattr(config, "POST_STATUS", "DRAFT")
    )
    print(f"🎉 성공적으로 업로드되었습니다! Post ID: {result.get('id')}")
    print(f"🔗 URL: {result.get('url')}")
except Exception as e:
    print(f"❌ 업로드 실패: {e}")
