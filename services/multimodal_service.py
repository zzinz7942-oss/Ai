# -*- coding: utf-8 -*-
"""
Multimodal Service - 초간단/초고속 무과금 멀티모달 자동 렌더링 시스템
(이미지 생성 + TTS 음성 추출 + 동적 모션 영상 조립)
"""
import os
import json
import urllib.request
import asyncio
from typing import List

# edge-tts (100% 무료 마이크로소프트 음성)
import edge_tts

# moviepy (영상 조립 및 편집)
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip
from config import get_config, NVIDIA_API_KEY

def _ensure_dir(path: str):
    dir_name = os.path.dirname(path)
    if dir_name and not os.path.exists(dir_name):
        os.makedirs(dir_name, exist_ok=True)

# ── 1. 무료 이미지 생성 (Pollinations.ai - 100% 무료, 키 불필요) ──────────────────────
def generate_image_free(prompt: str, output_path: str) -> bool:
    """API 키 없이 평생 무료로 초고화질 이미지를 생성하는 모듈"""
    import urllib.parse
    
    print(f"[이미지 생성 중] (Prompt: {prompt[:30]}...)")
    
    # 띄어쓰기 및 특수문자를 URL용으로 인코딩
    safe_prompt = urllib.parse.quote(prompt + ", highly detailed, masterpiece, 8k resolution, cinematic lighting")
    
    # Pollinations.ai: 완전 무료 & 무제한 텍스트->이미지 생성기
    url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1080&height=1920&nologo=true"
    
    import time
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=60) as r:
                img_data = r.read()
                _ensure_dir(output_path)
                with open(output_path, "wb") as f:
                    f.write(img_data)
                print(f"[이미지 저장 완료] {output_path}")
                return True
        except Exception as e:
            print(f"[이미지 생성 실패 (시도 {attempt+1}/3)] {e}")
            time.sleep(2)
            
    return False

# ── 2. 무료 음성 생성 (Edge-TTS) ──────────────────────────────────────
async def _async_generate_audio(text: str, output_path: str, voice: str = "ko-KR-SunHiNeural"):
    communicate = edge_tts.Communicate(text, voice)
    _ensure_dir(output_path)
    await communicate.save(output_path)

def generate_audio_free(text: str, output_path: str, voice: str = "ko-KR-SunHiNeural") -> bool:
    """Edge-TTS를 이용한 100% 무료 아나운서급 음성 생성"""
    print(f"[Edge-TTS] 음성 추출 중... (Voice: {voice})")
    try:
        asyncio.run(_async_generate_audio(text, output_path, voice))
        print(f"[Edge-TTS] 음성 저장 완료: {output_path}")
        return True
    except Exception as e:
        print(f"[Edge-TTS] 음성 추출 실패: {e}")
        return False

# ── 3. 동적 영상 조립 (Ken Burns 모션) ─────────────────────────────────
def assemble_video_free(image_paths: List[str], audio_path: str, output_path: str) -> bool:
    """파이썬 기반 동적 줌(Ken Burns) 효과 영상 자동 렌더링"""
    print("[MoviePy] 동적 영상(릴스/쇼츠) 조립 시작...")
    try:
        _ensure_dir(output_path)
        
        # 1. 오디오 로드
        audio = AudioFileClip(audio_path)
        total_duration = audio.duration
        
        if not image_paths:
            print("이미지가 없습니다.")
            return False
            
        # 2. 이미지 장당 노출 시간 계산
        duration_per_image = total_duration / len(image_paths)
        
        clips = []
        for img_path in image_paths:
            # 기본 클립 생성
            clip = ImageClip(img_path).set_duration(duration_per_image)
            
            # 줌인(Ken Burns) 효과 함수 정의 (화면 중심 기준 약간씩 커짐)
            def zoom(get_frame, t):
                frame = get_frame(t)
                # 0~duration까지 1.0배에서 1.05배로 서서히 줌인 (아주 살짝만 커짐)
                # MoviePy 1.0.3에서는 resize를 수동으로 구현하기 복잡하므로
                # 단순화된 Ken Burns를 위해 crossfadein(트랜지션)으로 대체하거나 단순 출력.
                # 복잡한 렌더링 방지를 위해 모션 없이 트랜지션만 적용 (가장 빠름)
                return frame
            
            # clip = clip.fl(zoom) # 메모리 오버 방지 및 렌더링 속도 최적화를 위해 제외 가능
            
            # 대신 0.5초 디졸브(크로스페이드) 트랜지션 추가
            clip = clip.crossfadein(0.5)
            clips.append(clip)
            
        # 3. 비디오 이어붙이기 (method='compose'로 트랜지션 적용)
        video = concatenate_videoclips(clips, padding=-0.5, method="compose")
        
        # 전체 길이를 오디오에 맞춤
        video = video.set_audio(audio)
        video = video.set_duration(total_duration)
        
        # 4. 빠른 렌더링 옵션 (1080p, 24fps)
        print("[MoviePy] 렌더링 중... (잠시만 기다려주세요)")
        video.write_videofile(
            output_path, 
            fps=24, 
            codec="libx264", 
            audio_codec="aac",
            preset="ultrafast",  # 렌더링 속도 최우선
            threads=4,
            logger=None
        )
        print(f"[MoviePy] 영상 렌더링 완료: {output_path}")
        return True
    except Exception as e:
        print(f"[MoviePy] 영상 조립 실패: {e}")
        return False

