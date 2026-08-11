"""
기존 발행 글 전수 점검 및 자동 보완/정제 모듈 (Audit & Repair Published Posts)
- Blogger API에 등록된 모든 기존 글 전수 수집 및 위험 요소 검수
- main.py와 동일한 6대 핵심 조건 검증(15,000자+, 이미지 5개+, 가독성 썸네일, 해시태그 8개+, AI 클리셰 제거) 및 최대 3회 재시도 적용
- 체크포인트 로그(repaired_checkpoint_log.json)를 통한 중복/누락 방지 및 이어받기 지원
- API 한도/에외 발생 시 기존 글 안전 보존 및 자동 중단 파이프라인
"""

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Set

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import config
import blogger_client
import content_builder
import ai_reviewer
import image_fetcher
import thumbnail_generator
import main

CHECKPOINT_LOG_PATH = config.LOGS_DIR / "repaired_checkpoint_log.json"

AI_CLICHES = [
    r"안녕하세요.*?\n",
    r"요즘.*?화제입니다\.",
    r"오늘은.*?알아보겠습니다\.",
    r"지금까지.*?알아보았습니다\.",
    r"도움이 되셨기를 바랍니다\.",
    r"도움이 되었기를 바랍니다\.",
    r"다음 포스팅에서 만나요\.",
    r"감사합니다\.",
    r"함께 알아보시죠\.",
    r"유익한 정보가 되셨길",
    r"에 대해 알아보겠습니다",
    r"살펴보겠습니다",
    r"다양한 이유가 존재합니다"
]



def load_repaired_checkpoints() -> Dict[str, Dict]:
    """이미 보완이 완성되어 Blogger에 저장된 post_id 체크포인트 맵 로드"""
    if not CHECKPOINT_LOG_PATH.exists():
        return {}
    try:
        with open(CHECKPOINT_LOG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_repaired_checkpoint(post_id: str, title: str, char_count: int, image_count: int):
    """검증을 100% 통과하여 Blogger에 저장된 포스트 post_id 기록"""
    checkpoints = load_repaired_checkpoints()
    checkpoints[post_id] = {
        "title": title,
        "char_count": char_count,
        "image_count": image_count,
        "repaired_at": datetime.now().isoformat(),
        "status": "VERIFIED_AND_SAVED"
    }
    try:
        with open(CHECKPOINT_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(checkpoints, f, ensure_ascii=False, indent=2)
        print(f"  📝 [체크포인트 저장 완료] ID: {post_id} ('{title[:25]}...')")
    except Exception as e:
        print(f"  ⚠️ 체크포인트 저장 실패 ({e})")


def is_post_verified_and_passed(post_id: str) -> bool:
    """
    사용자의 절대 원칙:
    run_full_validation()을 이미 100% 통과(status == 'VERIFIED_AND_SAVED')한 포스트는 
    사용자가 명시적으로 '이 글 다시 수정해줘'라고 지목하지 않는 한 
    어떠한 자동 스캔/배치 스크립트에서도 절대 다시 건드리지 않고 100% 건너뛴다.
    """
    checkpoints = load_repaired_checkpoints()
    return post_id in checkpoints and checkpoints[post_id].get("status") == "VERIFIED_AND_SAVED"



def audit_single_post(post: Dict) -> Dict:
    """단일 게시물의 애드센스 위배 위험요인 종합 진단"""
    post_id = post.get("id", "")
    title = post.get("title", "")
    html_content = post.get("content", "")
    labels = post.get("labels", [])
    url = post.get("url", "")
    published_at = post.get("published", "")

    raw_text = re.sub(r'<[^>]+>', ' ', html_content)
    raw_text = re.sub(r'\s+', ' ', raw_text).strip()
    char_count = len(raw_text)

    img_urls = re.findall(r'<img\s+[^>]*src=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
    image_count = len(img_urls)
    has_duplicate_img = len(img_urls) != len(set(img_urls))

    hex_tags = []
    clean_tags = []
    for tag in labels:
        clean = str(tag).strip().lstrip('#')
        if content_builder.HEX_COLOR_RE.match(clean):
            hex_tags.append(clean)
        elif content_builder.is_valid_topic_hashtag(clean):
            clean_tags.append(clean)

    found_cliches = []
    for pat in AI_CLICHES:
        if re.search(pat, raw_text, re.IGNORECASE):
            found_cliches.append(pat.replace(r".*?", "...").replace(r"\.", "."))

    risk_issues = []
    risk_level = "SAFE"

    if char_count < 5000:
        risk_issues.append(f"초저품질 심각한 분량 부족 ({char_count:,}자 < 15,000자)")
        risk_level = "HIGH"
    elif char_count < config.MIN_CHAR_COUNT:
        risk_issues.append(f"분량 미달 ({char_count:,}자 < 15,000자)")
        if risk_level != "HIGH":
            risk_level = "MEDIUM"

    if image_count < config.MIN_IMAGE_COUNT:
        risk_issues.append(f"이미지 부족 ({image_count}개 < {config.MIN_IMAGE_COUNT}개)")
        if risk_level != "HIGH":
            risk_level = "MEDIUM"

    if has_duplicate_img:
        risk_issues.append("본문 내 이미지 URL 중복 수집")
        if risk_level != "HIGH":
            risk_level = "MEDIUM"

    if hex_tags:
        risk_issues.append(f"Hex 색상코드 태그 오삽입 ({', '.join(hex_tags)})")
        if risk_level != "HIGH":
            risk_level = "MEDIUM"

    if found_cliches:
        risk_issues.append(f"AI 상투어구 포함 ({len(found_cliches)}개)")
        if risk_level != "HIGH":
            risk_level = "MEDIUM"

    return {
        "post_id": post_id,
        "title": title,
        "url": url,
        "published_at": published_at,
        "char_count": char_count,
        "image_count": image_count,
        "hex_tags": hex_tags,
        "clean_tags": clean_tags,
        "found_cliches": found_cliches,
        "risk_level": risk_level,
        "risk_issues": risk_issues,
        "raw_html": html_content
    }


def audit_all_published_posts() -> List[Dict]:
    """기존에 발행된 모든 글 전수 점검 수행"""
    print("=" * 70)
    print("🔍 [기존 발행 글 전수 점검] Google Blogger 전체 포스트 전수 진단 시작...")
    print("=" * 70)

    posts = blogger_client.list_all_posts(fetch_bodies=True)
    if not posts:
        print("  📝 기존 발행 글이 없거나 읽어올 수 없습니다.")
        return []

    print(f"  총 {len(posts)}개 게시물 점검 중...\n")

    audit_results = []
    high_risk_count = 0
    medium_risk_count = 0
    safe_count = 0

    for idx, p in enumerate(posts, 1):
        result = audit_single_post(p)
        audit_results.append(result)

        lvl = result["risk_level"]
        title_str = result["title"][:32]

        if lvl == "HIGH":
            high_risk_count += 1
            icon = "🚨 [HIGH RISK]"
        elif lvl == "MEDIUM":
            medium_risk_count += 1
            icon = "⚠️ [MEDIUM RISK]"
        else:
            safe_count += 1
            icon = "✅ [SAFE]"

        print(f"  {idx}. {icon} {title_str}...")
        print(f"     분량: {result['char_count']:,}자 | 이미지: {result['image_count']}개")
        if result["risk_issues"]:
            print(f"     위험 요인: {', '.join(result['risk_issues'])}")

    report_file = config.LOGS_DIR / "published_audit_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(audit_results, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 70)
    print("📊 [전수 점검 결과 요약]")
    print(f"  - 전체 게시물 수 : {len(posts)}개")
    print(f"  - 🚨 HIGH 위험군  : {high_risk_count}개 (15,000자 대폭 미달 / 심각한 저품질)")
    print(f"  - ⚠️ MEDIUM 위험군 : {medium_risk_count}개 (부분 분량/태그/클리셰 보완 필요)")
    print(f"  - ✅ SAFE 안전군   : {safe_count}개")
    print(f"  - 진단 리포트 저장 : {report_file}")
    print("=" * 70)

    return audit_results


def repair_post(audit_item: Dict, max_retries: int = 3) -> Dict:
    """
    main.py와 동일한 6대 검증 + 최대 3회 자동 재시도 적용 (검증 100% 통과 전엔 Blogger 저장 절대 금지)
    """
    post_id = audit_item["post_id"]
    title = audit_item["title"]
    raw_html = audit_item["raw_html"]
    clean_tags = audit_item["clean_tags"]

    print(f"\n🛠️ [게시물 6대 검증 & 3회 재시도 보완 진행] '{title}' (ID: {post_id})...")

    raw_text = re.sub(r'<style.*?>.*?</style>', '', raw_html, flags=re.DOTALL)
    raw_text = re.sub(r'<[^>]+>', '\n', raw_text)
    raw_text = re.sub(r'\n+', '\n', raw_text).strip()

    for attempt in range(1, max_retries + 1):
        print(f"\n  🔄 [보완 시도 {attempt}/{max_retries}] 15,000자 장문 원고 생성 및 멀티미디어 수집 중...")

        # 1. 15,000자 8개 섹션 분할 원고 생성 (15,000자 100% 보장)
        repaired_md, new_title, meta_desc = ai_reviewer.generate_full_post(topic=title)

        review_res = ai_reviewer.review_and_correct_post(repaired_md)
        repaired_md = review_res["reviewed"]

        # 2. 순수 명사 키워드 해시태그 8~12개 생성
        new_labels = ai_reviewer.generate_hashtags(repaired_md, title, clean_tags)

        # 3. 소제목별 고유 키워드 이미지 수집 (최소 5~8개, 거울셀카/인물 필터링)
        keywords = content_builder.extract_keywords_for_images(repaired_md, topic_title=title)
        images = {}
        used_urls = set()
        recent_hashes = image_fetcher.get_all_recent_image_hashes()
        collected_hashes = []

        for kw in keywords:
            img_data = image_fetcher.get_image(
                query_ko=kw["ko"],
                query_en=kw["en"],
                used_urls=used_urls,
                recent_hashes=recent_hashes
            )
            if img_data:
                images[kw["key"]] = img_data
                if img_data.get("img_hash"):
                    collected_hashes.append(img_data["img_hash"])

        # 4. 가독성 보장 썸네일 합성 (PIL 반투명 박스 오버레이)
        if "thumbnail" in images and images["thumbnail"] and images["thumbnail"].get("local_path"):
            thumb_bg_path = images["thumbnail"]["local_path"]
            thumb_output_path = thumbnail_generator.generate_thumbnail(
                bg_image_path=thumb_bg_path,
                title_text=title
            )
            images["thumbnail"]["local_path"] = thumb_output_path

        # 5. HTML 렌더링
        final_html = content_builder.build_html(repaired_md, images, hosted_urls={}, labels=new_labels)
        total_img_count = len([img for img in images.values() if img])

        # 6. main.py 6대 조건 엄격 검증
        is_valid, metrics = main.validate_post(
            title=title,
            html_content=final_html,
            markdown_text=repaired_md,
            labels=new_labels,
            topic=title,
            image_count=total_img_count,
            image_hashes=collected_hashes
        )

        # [핵심 보장 1] 검증을 100% 통과했을 때만 Blogger API 업데이트 저장 실행
        if is_valid:
            print(f"  ✅ [6대 검증 통과!] (시도 {attempt}/{max_retries}) 분량: {metrics['char_count']:,}자 | 이미지: {total_img_count}개")
            try:
                updated = blogger_client.update_post(
                    post_id=post_id,
                    title=title,
                    html_content=final_html,
                    labels=new_labels,
                    status=config.POST_STATUS
                )
                image_fetcher.save_used_images_log(collected_hashes, post_title=title)

                # [핵심 보장 2] 완료된 post ID 체크포인트 로그 기록
                save_repaired_checkpoint(post_id, title, metrics['char_count'], total_img_count)

                print(f"  🎉 [Blogger 수정 반영 완료] '{title}' 포스트가 100% 검증을 통과하여 저장되었습니다.")
                return {"success": True, "post_id": post_id, "title": title, "metrics": metrics}
            except Exception as e:
                print(f"  ⚠️ 수정 업데이트 실패 ({e})")
                return {"success": False, "post_id": post_id, "title": title, "error": str(e)}
        else:
            print(f"  🛑 [검증 미달] (시도 {attempt}/{max_retries}) 사유: {', '.join(metrics['fail_reasons'])}")

    print(f"  ⚠️ 포스트 '{title}'는 {max_retries}회 보완 재시도 후에도 요건 미달되어 Blogger에 저장하지 않았습니다.")
    return {"success": False, "post_id": post_id, "title": title, "error": "3회 재검증 미달"}


def repair_all_high_risk_posts(limit: int = 0, shutdown_on_complete: bool = False) -> Dict:
    """
    위험도가 높은 기존 글 전체 또는 N건 자동 보완 실행
    - 체크포인트 기반으로 이미 보완된 글 자동 건너뜀
    - API 한도 / 오류 발생 시 예외 처리로 나머지 포스트 안전 유지 및 정지
    - shutdown_on_complete=True 설정 시 최종 요약 리포트 후 60초 대기 카운트다운 후 PC 자동 종료
    """
    audit_results = audit_all_published_posts()
    high_risks = [item for item in audit_results if item["risk_level"] in ["HIGH", "MEDIUM"]]

    checkpoints = load_repaired_checkpoints()

    # 체크포인트 대조: 이미 검증 통과해 저장된 글 제외
    pending_items = []
    for item in high_risks:
        p_id = item["post_id"]
        if p_id in checkpoints:
            print(f"  ⏭️ [체크포인트 건너뜀] 이미 보완 저장 완료됨: '{item['title'][:30]}' (ID: {p_id})")
        else:
            pending_items.append(item)

    if limit > 0:
        pending_items = pending_items[:limit]

    if not pending_items:
        print("\n  🎉 보완이 필요한 미완료 위험군 게시물이 없습니다.")
        if shutdown_on_complete:
            execute_pc_shutdown_countdown()
        return {"repaired_count": 0, "status": "ALL_COMPLETED"}

    print(f"\n🚀 총 {len(pending_items)}개 미완료 위험군 게시물 6대 검증 보완 수정을 시작합니다.")

    repaired_count = 0
    stop_reason = ""

    for item in pending_items:
        try:
            res = repair_post(item, max_retries=3)
            if res.get("success"):
                repaired_count += 1
            time.sleep(3) # API 제한 방지 지연
        except KeyboardInterrupt:
            print("\n👋 사용자에 의해 보완 작업이 안전하게 정지되었습니다.")
            stop_reason = "USER_INTERRUPT"
            break
        except Exception as e:
            # [핵심 보장 3] API 한도 또는 예외 시 나머지 포스트 건드리지 않고 안전 중단
            print(f"\n🛑 [API 한도/예외 발생] ({e})")
            print("  안전을 위해 현재 작업을 중단합니다. 이미 보완된 포스트는 체크포인트에 정상 보존되었습니다.")
            stop_reason = f"EXCEPT_STOP: {e}"
            break

    print(f"\n🎉 [실행 완료] 금회 보완 완료: {repaired_count}개 | 중단 사유: {stop_reason if stop_reason else '정상 완료'}")

    if shutdown_on_complete:
        execute_pc_shutdown_countdown()

    return {"repaired_count": repaired_count, "stop_reason": stop_reason}


def execute_pc_shutdown_countdown(seconds: int = 60):
    import subprocess
    print("\n" + "=" * 70)
    print(f"📢 [PC 자동 종료 안내] 작업 완료로 인해 {seconds}초 후 컴퓨터가 자동 종료됩니다.")
    print("   취소하려면 60초 이내에 Ctrl+C를 누르거나 명령창(cmd)에 'shutdown /a'를 입력하세요.")
    print("=" * 70)
    try:
        for s in range(seconds, 0, -10):
            print(f"  ⏳ [자동 종료 카운트다운] {s}초 후 PC가 종료됩니다...")
            time.sleep(10)
        print("  🔌 PC 종료 명령(shutdown /s /t 0)을 실행합니다.")
        subprocess.run(["shutdown", "/s", "/t", "0"])
    except KeyboardInterrupt:
        print("\n  🛑 사용자가 카운트다운을 취소했습니다. PC 종료를 취소합니다.")
        try:
            subprocess.run(["shutdown", "/a"])
        except Exception:
            pass


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Audit & Repair Published Blogger Posts")
    parser.add_argument("--repair-all", action="store_true", help="위험군 포스트 전수 보완 실행")
    parser.add_argument("--shutdown", action="store_true", help="작업 완료 시 PC 자동 종료 (60초 카운트다운)")
    args = parser.parse_args()

    if args.repair_all:
        repair_all_high_risk_posts(shutdown_on_complete=args.shutdown)
    else:
        audit_all_published_posts()

