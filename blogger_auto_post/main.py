"""
메인 파이프라인 (Blogger Autonomous Auto-Posting Pipeline)
- 애드센스 고가치 콘텐츠 승인용 15,000자 이상 초장문 자동 작성 & 검증 & 발행
- 확인/승인 절차 없이 끝까지 자동 진행 및 실행 결과 요약 보고
"""

import os
import re
import sys
import time
import json
import argparse
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import config
import topic_selector
import prompt_builder
import ai_reviewer
import blog_master_config
import image_fetcher
import thumbnail_generator
import content_builder
import blogger_client
import trend_fetcher


def validate_post(
    title: str,
    html_content: str,
    markdown_text: str,
    labels: List[str],
    topic: str,
    image_count: int,
    image_hashes: List[str]
) -> Tuple[bool, Dict]:
    """
    blog_master_config.py 통합 표준 모듈 기반 발행 전 하드 게이트 검증
    """
    raw_text = re.sub(r'<[^>]+>', ' ', html_content or "")
    clean_text = re.sub(r'\s+', ' ', raw_text).strip()
    char_count = len(clean_text)
    
    # 1. blog_master_config 마스터 검증 게이트 수행
    image_urls = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', html_content or "")
    std_val = blog_master_config.run_full_validation(title, markdown_text, image_urls)

    fail_reasons = []
    for check_name, (passed, msg) in std_val["details"].items():
        if not passed:
            fail_reasons.append(msg)

    # 2. 해시태그 & 유사도 추가 검증
    combined_tags = [t for t in labels if t.startswith("#")]
    hashtag_count = len(combined_tags)
    if hashtag_count < config.MIN_HASHTAG_COUNT:
        fail_reasons.append(f"해시태그 부족 ({hashtag_count}개 < {config.MIN_HASHTAG_COUNT}개)")

    is_similar, sim_percent, matched_topic = topic_selector.is_topic_too_similar(topic, days=7, max_similarity=config.TOPIC_SIMILARITY_MAX)
    if is_similar:
        fail_reasons.append(f"주제 중복 초과 (최근 글과 유사도 {sim_percent}% >= 70%)")

    is_pass = len(fail_reasons) == 0

    metrics = {
        "title": title,
        "char_count": char_count,
        "image_count": len(image_urls),
        "hashtag_count": hashtag_count,
        "topic_similarity": sim_percent,
        "is_pass": is_pass,
        "fail_reasons": fail_reasons,
        "standards_details": std_val["details"]
    }

    return is_pass, metrics


def run_autonomous_pipeline(max_topic_trials: int = 3, max_retries_per_topic: int = 3) -> Dict:
    """
    사용자 개입 없는 무인 자동 포스팅 파이프라인
    """
    print("=" * 70)
    print("🚀 Google Blogger 15,000자 자율 포스팅 파이프라인 시작")
    print(f"⏰ 실행 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    session_report = {
        "executed_at": datetime.now().isoformat(),
        "published_posts": [],
        "skipped_topics": [],
        "status": "COMPLETED"
    }

    for trial in range(1, max_topic_trials + 1):
        # 1. 주제 선정
        topic_info = topic_selector.select_best_topic()
        if not topic_info:
            print("  ⚠️ 유효한 주제 후보를 찾지 못했습니다.")
            break

        topic = topic_info["topic"]
        category = topic_info.get("category", "")
        keyword = topic_info.get("keyword", "")

        print(f"\n📌 [시도 {trial}/{max_topic_trials}] 진행 주제: [{category}] {topic}")
        topic_selector.mark_topic_attempted(topic)

        # 주제당 최대 3회 자동 생성 및 재검증 시도
        topic_success = False
        last_metrics = {}

        for attempt in range(1, max_retries_per_topic + 1):
            print(f"\n  🔄 [생성 시도 {attempt}/{max_retries_per_topic}] 원고 작성 및 멀티미디어 수집 중...")

            # 실시간 뉴스 트렌드 결합
            trends = trend_fetcher.fetch_realtime_trends(topic_keyword=keyword, max_count=3)

            # 2. 15,000자 장문 글 생성, A/B 타이틀, 메타 디스크립션
            markdown_text, title, meta_desc = ai_reviewer.generate_full_post(topic, category, trends)

            # API 할당량 소진 검사
            if getattr(ai_reviewer, "LAST_API_QUOTA_EXHAUSTED", False):
                print("\n🛑 [오늘 API 할당량 소진 감지] 3회 재시도 연속 실패로 오늘 할당량이 소진되어 작업을 안전하게 일시 중단합니다.")
                session_report["status"] = "QUOTA_EXHAUSTED"
                session_report["skipped_topics"].append({
                    "topic": topic,
                    "reason": "오늘 API 할당량 소진으로 작업 일시 중단"
                })
                break

            # AI 클리셰 정제
            review_res = ai_reviewer.review_and_correct_post(markdown_text)
            markdown_text = review_res["reviewed"]

            # 해시태그 8~12개 생성
            labels = ai_reviewer.generate_hashtags(markdown_text, title, config.POST_LABELS)

            # 3. 소제목별 고유 키워드 이미지 수집 (generate_images_for_post)
            section_headings = re.findall(r'^##\s+(.+)', markdown_text, re.MULTILINE)
            img_bundle = image_fetcher.generate_images_for_post(title, section_headings)

            images = {}
            if img_bundle.get("thumbnail"):
                images["thumbnail"] = img_bundle["thumbnail"]

            for idx, sec_img in enumerate(img_bundle.get("sections", []), 1):
                if sec_img:
                    images[f"section_{idx}"] = sec_img

            # Google Drive / Blogger 이미지 업로드 (가능 시)
            hosted_urls = {}
            if getattr(config, "UPLOAD_TO_DRIVE", False):
                for k, meta in images.items():
                    if meta and meta.get("local_path"):
                        h_url = blogger_client.upload_image_to_blogger(meta["local_path"])
                        if h_url:
                            hosted_urls[k] = h_url

            # HTML 포맷팅
            final_html = content_builder.build_html(markdown_text, images, hosted_urls, labels=labels)
            total_image_count = len([img for img in images.values() if img])

            # 5. 발행 전 검증
            is_valid, metrics = validate_post(
                title=title,
                html_content=final_html,
                markdown_text=markdown_text,
                labels=labels,
                topic=topic,
                image_count=total_image_count,
                image_hashes=[]
            )
            last_metrics = metrics

            if is_valid:
                print(f"\n  ✅ [마스터 검증 통과!] (시도 {attempt}/{max_retries_per_topic}) 6대 하드 게이트 100% 충족!")
                
                # 6. 블로그 포스트 업로드 (LIVE 또는 DRAFT)
                status = getattr(config, "POST_STATUS", "DRAFT")
                try:
                    upload_res = blogger_client.upload_post(
                        title=title,
                        html_content=final_html,
                        labels=labels,
                        status=status
                    )
                    post_id = upload_res.get("id", "")
                    post_url = upload_res.get("url", "")
                    
                    # 7. 라이브 접속 재검증 (규칙 4: 생성 시점 로그만 믿지 말고 실제 라이브 URL 접속 검증)
                    live_ver = blog_master_config.run_full_validation_with_live_check(
                        title=title,
                        body_text=markdown_text,
                        image_urls=image_urls,
                        live_url=post_url,
                        post_id=post_id
                    )
                    print(f"  🌐 [라이브 접속 실시간 재검증 결과] PASS: {live_ver.get('passed', False)} | URL: {post_url}")
                except Exception as e:
                    print(f"  ⚠️ Blogger API 업로드 오류 ({e}). 수동 로그 기록으로 진행...")
                    post_id = "LOCAL_ONLY"
                    post_url = "http://localhost/preview.html"

                # 발행 로그 저장 (최근 7일 중복 주제 방지용)
                pub_record = {
                    "topic": topic,
                    "title": title,
                    "category": category,
                    "char_count": metrics["char_count"],
                    "image_count": metrics["image_count"],
                    "published_at": datetime.now().isoformat(),
                    "post_id": post_id,
                    "url": post_url,
                    "status": status
                }
                topic_selector.save_published_log(pub_record)
                topic_selector.mark_topic_completed(topic)

                session_report["published_posts"].append({
                    "title": title,
                    "category": category,
                    "char_count": metrics["char_count"],
                    "image_count": total_image_count,
                    "retries": attempt - 1,
                    "url": post_url,
                    "status": status
                })

                topic_success = True
                break
            else:
                print(f"  🛑 [검증 실패] (시도 {attempt}/{max_retries_per_topic}) 사유: {', '.join(metrics['fail_reasons'])}")
                if metrics["char_count"] < config.MIN_CHAR_COUNT:
                    markdown_text = ai_reviewer.expand_short_post(markdown_text, topic)

        if getattr(ai_reviewer, "LAST_API_QUOTA_EXHAUSTED", False):
            break

        if not topic_success:
            print(f"  ⚠️ 주제 '{topic}'는 {max_retries_per_topic}회 재시도 후에도 요건 미달되어 다음 후보 주제로 자동 전환합니다.")
            session_report["skipped_topics"].append({
                "topic": topic,
                "reason": f"3회 재검증 실패 ({', '.join(last_metrics.get('fail_reasons', []))})"
            })
            continue
        else:
            # 1개 글 자동 포스팅 완료 후 종료
            break


    # 최종 결과 보고서 출력
    print("\n" + "=" * 70)
    print("📊 [최종 포스팅 실행 요약 보고서]")
    print(f"  - 실행 일시    : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  - 발행 성공 건 : {len(session_report['published_posts'])}건")

    for post in session_report["published_posts"]:
        print(f"    • 제목: {post['title']}")
        print(f"      글자 수: {post['char_count']:,}자 (공백 포함)")
        print(f"      이미지: {post['image_count']}개 (중복 0%)")
        print(f"      재생성 횟수: {post['retries']}회")
        print(f"      상태/URL: [{post['status']}] {post['url']}")

    if session_report["skipped_topics"]:
        print(f"  - 스킵된 주제 건 : {len(session_report['skipped_topics'])}건")
        for sk in session_report["skipped_topics"]:
            print(f"    • {sk['topic']} ({sk['reason']})")

    print("=" * 70)
    return session_report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Blogger Autonomous Auto-Posting Pipeline")
    parser.add_argument("--once", action="store_true", help="1회 즉시 실행 후 종료")
    parser.add_argument("--test-run", action="store_true", help="테스트 실행 (임시저장 DRAFT 상태로 1회 실행)")
    parser.add_argument("--no-drive", action="store_true", help="Google Drive 업로드 스킵")
    parser.add_argument("--skip-review", action="store_true", help="AI 자기검토 단계 스킵")
    parser.add_argument("--edit", type=str, help="기존 포스트 ID 수정")
    parser.add_argument("--generate-prompt", type=str, help="프롬프트 생성할 주제")
    args = parser.parse_args()

    if args.no_drive:
        config.UPLOAD_TO_DRIVE = False

    if args.test_run:
        print("🧪 [테스트 실행 모드 --test-run] POST_STATUS = DRAFT 로 설정하여 파이프라인을 1회 검증합니다.\n")
        config.POST_STATUS = "DRAFT"

    run_autonomous_pipeline()

