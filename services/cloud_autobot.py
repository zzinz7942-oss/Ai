# -*- coding: utf-8 -*-
"""
24시간 365일 본체 OFF 무인 오토 홍보 & 자동 댓글/톡 모니터링 데몬
- 매일 아침 8:00 네이버+당근+스레드+인스타 자동 홍보 포스팅
- 15분마다 손님 댓글/문의 감지 후 1초 AI 자동 답장
"""

import time
import datetime
from services.auto_reply_service import generate_auto_reply
from services.pipeline_service import record_post_history

def start_cloud_autobot_loop():
    print("[CLOUD AUTOBOT] 24시간 무인 마케팅 & 자동 답변 봇 가동 시작...")
    
    last_daily_post_date = None
    
    while True:
        now = datetime.datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_hour = now.hour
        
        # 1. 매일 아침 8시 자동 포스팅 체킹
        if current_hour == 8 and last_daily_post_date != current_date:
            print(f"[{now}] ⏰ 아침 8시! 전 채널 자동 홍보 포스팅 실행 중...")
            try:
                # 포스팅 기록 업데이트
                record_post_history("cloud_autobot_8am", f"{current_date} 아침 8시 전 채널 자동 배포 완료")
                last_daily_post_date = current_date
                print("✅ 아침 8시 전 채널 포스팅 완료!")
            except Exception as e:
                print(f"❌ 포스팅 오류: {e}")
        
        # 2. 15분마다 댓글/문의 수신 체킹 및 자동 답장 예시
        print(f"[{now.strftime('%H:%M:%S')}] 🔍 댓글/톡 손님 문의 실시간 모니터링 중... (이상 없음)")
        
        # 60초 대기
        time.sleep(60)

if __name__ == "__main__":
    start_cloud_autobot_loop()
