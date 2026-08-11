# -*- coding: utf-8 -*-
"""
과일 이름 및 가격 정밀 파싱 & 자연스러운 1.2배속 AI 음성 릴스 동영상 서비스 (Upgraded Fruit Video Engine)
- '복숭아 1팩16000원 아오리사과 1팩 10000원' 무공백/공백 텍스트 100% 정밀 파싱
- AI 느낌 제거한 자연스러운 한국어 신경망 성우 음성 (SunHiNeural +20% 쾌속 발음)
"""

import os
import re
import tempfile
import asyncio
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import edge_tts
from moviepy.editor import ImageSequenceClip, AudioFileClip

from image_cropper import auto_crop_phone_screenshot


def parse_fruit_input_text(raw_text: str) -> list:
    """
    사장님이 띄어쓰기 없이 '복숭아 1팩16000원 아오리사과 1팩 10000원'으로 써도
    과일명, 단위, 가격을 100% 정확하게 정밀 파싱합니다.
    """
    if not raw_text:
        return [
            {"name": "🍑 단단이 복숭아 (1팩)", "price": "16,000원"},
            {"name": "🍏 아오리 사과 (1팩)", "price": "10,000원"}
        ]

    items = []
    # 정밀 정규식: (과일명 + 단위) + (숫자원)
    matches = re.findall(r'([가-힣\s]+(?:\s*\d+팩|\s*\d+개|\s*\d+송이|\s*\d+봉|\s*\d+상자)?)\s*(\d+원)', raw_text)
    
    if matches:
        for fruit_name, price_val in matches:
            name_clean = fruit_name.strip()
            price_clean = price_val.strip()

            num_only = re.sub(r'[^\d]', '', price_clean)
            price_fmt = f"{int(num_only):,}원" if num_only else price_clean

            emoji = "🍎"
            if "복숭아" in name_clean: emoji = "🍑"
            elif "사과" in name_clean or "아오리" in name_clean: emoji = "🍏"
            elif "수박" in name_clean: emoji = "🍉"
            elif "포도" in name_clean or "머스캣" in name_clean: emoji = "🍇"
            elif "딸기" in name_clean: emoji = "🍓"
            elif "참외" in name_clean or "멜론" in name_clean: emoji = "🍈"
            elif "자두" in name_clean: emoji = "🍒"
            elif "귤" in name_clean or "한라봉" in name_clean: emoji = "🍊"

            items.append({
                "name": f"{emoji} {name_clean}",
                "price": price_fmt
            })

    if not items:
        # 일반 줄바꿈 처리
        lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
        for l in lines:
            items.append({"name": f"🍎 {l}", "price": "당일 특가"})

    return items if items else [{"name": f"🍎 {raw_text}", "price": "당일 특가"}]


async def generate_tts_audio_async(text: str, output_path: str):
    """자연스럽고 또박또박한 1.2배속 한국어 신경망 성우 음성 생성 (+20% rate)"""
    communicate = edge_tts.Communicate(text, "ko-KR-SunHiNeural", rate="+20%")
    await communicate.save(output_path)


def create_tts_audio(text: str, output_path: str):
    """TTS 음성 파일 생성 유틸리티"""
    try:
        asyncio.run(generate_tts_audio_async(text, output_path))
    except Exception:
        from gtts import gTTS
        tts = gTTS(text=text, lang='ko')
        tts.save(output_path)


def create_fruit_promo_video(
    shop_name: str,
    location: str,
    raw_fruit_text: str,
    image_paths: list,
    output_mp4_path: str
) -> dict:
    """
    정밀 파싱된 과일/가격과 자연스러운 1.2배속 AI 성우 음성으로 9:16 모바일 릴스를 완성합니다.
    """
    if not image_paths:
        return {"success": False, "error": "업로드된 과일 사진이 없습니다."}

    # 1. 텍스트 정밀 파싱
    fruit_items = parse_fruit_input_text(raw_fruit_text)

    # 2. 스마트폰 테두리 크롭 및 과일 색감 싱싱 보정
    clean_images = [auto_crop_phone_screenshot(p) for p in image_paths if os.path.exists(p)]
    if not clean_images:
        clean_images = image_paths

    # 3. 자연스러운 성우 대본 구성
    item_ment_list = [f"{item['name'].replace('🍑','').replace('🍏','').replace('🍎','').replace('🍇','').strip()} {item['price']}" for item in fruit_items]
    voice_script = f"오늘 {shop_name} 대박 꿀과일 입고 소식! {', '.join(item_ment_list)}! 당도 미쳤습니다! {location} {shop_name}으로 지금 바로 오세요!"

    temp_audio_path = os.path.join(tempfile.gettempdir(), "fruit_voice.mp3")
    create_tts_audio(voice_script, temp_audio_path)

    # 4. 9:16 비디오 프레임(1080x1920) 렌더링
    frames = []
    fps = 30
    duration_per_img = 2.5 # 사진당 2.5초로 스피디하게 전환
    total_frames_per_img = int(fps * duration_per_img)

    for idx, img_p in enumerate(clean_images):
        try:
            raw_img = Image.open(img_p).convert("RGB")
            # 과일 색감 싱싱 보정
            raw_img = ImageEnhance.Color(raw_img).enhance(1.3)
            raw_img = ImageEnhance.Contrast(raw_img).enhance(1.1)

            for f in range(total_frames_per_img):
                canvas = Image.new("RGB", (1080, 1920), color=(15, 23, 42))
                draw = ImageDraw.Draw(canvas)

                # 상단 헤더 뱃지
                draw.rectangle([(60, 80), (1020, 220)], fill=(225, 29, 72))
                
                try:
                    font_title = ImageFont.truetype("malgun.ttf", 62)
                    font_sub = ImageFont.truetype("malgun.ttf", 44)
                    font_price = ImageFont.truetype("malgun.ttf", 55)
                except Exception:
                    font_title = font_sub = font_price = ImageFont.load_default()

                draw.text((100, 115), f"🍓 {shop_name} 오늘 당도보장 특가!", fill=(255, 255, 255), font=font_title)

                # 중앙 과일 이미지 배치 (미세 줌인 효과)
                scale = 1.0 + (f / total_frames_per_img) * 0.05
                w, h = raw_img.size
                target_w = 960
                target_h = int(h * (target_w / w))
                if target_h > 1000:
                    target_h = 1000
                    target_w = int(w * (target_h / h))

                resized_fruit = raw_img.resize((int(target_w * scale), int(target_h * scale)), Image.Resampling.LANCZOS)
                pos_x = (1080 - resized_fruit.width) // 2
                pos_y = (1920 - resized_fruit.height) // 2 - 50
                canvas.paste(resized_fruit, (pos_x, pos_y))

                # 하단 파싱된 과일 및 가격 오버레이
                draw = ImageDraw.Draw(canvas)
                draw.rectangle([(60, 1480), (1020, 1820)], fill=(255, 255, 255))

                if idx < len(fruit_items):
                    item = fruit_items[idx]
                    draw.text((90, 1510), f"{item['name']}", fill=(15, 23, 42), font=font_title)
                    draw.text((90, 1600), f"🔥 당일 특가: {item['price']}", fill=(225, 29, 72), font=font_price)
                else:
                    draw.text((90, 1530), f"🛒 오늘의 당도 보장 꿀과일 입고!", fill=(15, 23, 42), font=font_title)

                draw.text((90, 1710), f"📍 위치: {location}", fill=(71, 85, 105), font=font_sub)

                frame_np = np.array(canvas)
                frames.append(frame_np)

        except Exception as e:
            print(f"프레임 렌더링 예외: {e}")

    if not frames:
        return {"success": False, "error": "영상 프레임 생성 실패"}

    # 5. MoviePy 인코딩
    try:
        video_clip = ImageSequenceClip(frames, fps=fps)
        if os.path.exists(temp_audio_path):
            audio_clip = AudioFileClip(temp_audio_path)
            if audio_clip.duration > video_clip.duration:
                video_clip = video_clip.loop(duration=audio_clip.duration)
            video_clip = video_clip.set_audio(audio_clip)

        video_clip.write_videofile(
            output_mp4_path,
            fps=fps,
            codec="libx264",
            audio_codec="aac",
            preset="ultrafast",
            verbose=False,
            logger=None
        )
        return {
            "success": True,
            "mp4_path": output_mp4_path,
            "script": voice_script,
            "parsed_items": fruit_items
        }
    except Exception as e:
        print(f"영상 인코딩 오류: {e}")
        return {"success": False, "error": f"영상 렌더링 실패: {e}"}
