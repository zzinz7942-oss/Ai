"""
3시간 간격 자동 스케줄러 모듈 (Scheduler & Daily Reporter)
- 하루 3시간 간격 (08:00, 11:00, 14:00, 17:00, 20:00, 23:00) 주기적 python main.py 실행
- Windows 작업 스케줄러 (schtasks) 등록 지원
- 각 회차 실행 로그 누적 저장 및 하루 종료 시 일일 요약 리포트 생성
"""

import sys
import time
import json
import subprocess
from datetime import datetime
from pathlib import Path

import config

LOGS_DIR = config.LOGS_DIR
SCHEDULER_LOG_FILE = LOGS_DIR / "scheduler_history.json"


def load_scheduler_history() -> list:
    if not SCHEDULER_LOG_FILE.exists():
        return []
    try:
        with open(SCHEDULER_LOG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def save_scheduler_log(run_result: dict):
    history = load_scheduler_history()
    history.append(run_result)
    try:
        with open(SCHEDULER_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ scheduler_history.json 저장 실패 ({e})")


def run_single_job():
    """main.py 무인 파이프라인 1회 호출"""
    print(f"\n⏰ [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 3시간 간격 포스팅 트리거 가동...")
    from main import run_autonomous_pipeline
    report = run_autonomous_pipeline()
    save_scheduler_log(report)
    return report


def generate_daily_summary_report():
    """오늘 일자 전체 포스팅 및 재생성 발생 이력 일일 리포트"""
    today_str = datetime.now().strftime("%Y-%m-%d")
    history = load_scheduler_history()

    today_runs = [item for item in history if item.get("executed_at", "").startswith(today_str)]

    total_published = 0
    total_skipped = 0
    published_details = []

    for run in today_runs:
        posts = run.get("published_posts", [])
        skips = run.get("skipped_topics", [])
        total_published += len(posts)
        total_skipped += len(skips)
        published_details.extend(posts)

    report_lines = [
        f"==================================================",
        f"📅 [일일 요약 보고서] 일자: {today_str}",
        f"  - 총 실행 회차    : {len(today_runs)}회",
        f"  - 총 발행 포스트  : {total_published}건",
        f"  - 총 스킵된 주제  : {total_skipped}건",
        f"--------------------------------------------------",
    ]

    for idx, p in enumerate(published_details, 1):
        report_lines.append(f"  {idx}. [{p.get('category', '기타')}] {p.get('title')}")
        report_lines.append(f"     분량: {p.get('char_count'):,}자 | 이미지: {p.get('image_count')}개 | 재시도: {p.get('retries')}회")
        report_lines.append(f"     URL : {p.get('url')}")

    report_lines.append(f"==================================================")
    report_text = "\n".join(report_lines)

    daily_report_path = LOGS_DIR / f"daily_report_{today_str}.txt"
    with open(daily_report_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    print("\n" + report_text)
    print(f"📄 일일 요약 리포트 저장 완료: {daily_report_path}")


def start_loop_scheduler(interval_hours: int = 3):
    """3시간 간격 대기 루프 실행"""
    print(f"⏱️ 3시간 간격 스케줄러 루프를 시작합니다. (Ctrl+C로 종료)")
    interval_seconds = interval_hours * 3600

    while True:
        try:
            run_single_job()
            generate_daily_summary_report()
            print(f"\n💤 다음 실행까지 {interval_hours}시간 동안 대기합니다...")
            time.sleep(interval_seconds)
        except KeyboardInterrupt:
            print("\n👋 스케줄러가 종료되었습니다.")
            break
        except Exception as e:
            print(f"⚠️ 스케줄러 실행 도중 오류 ({e}). 10분 후 재시도합니다.")
            time.sleep(600)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--loop":
        start_loop_scheduler(interval_hours=3)
    else:
        run_single_job()
        generate_daily_summary_report()
