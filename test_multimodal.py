import sys
import os
sys.path.insert(0, '.')
from services.multimodal_service import generate_image_free, generate_audio_free, assemble_video_free

print("=== 멀티모달 자비스 테스트 ===")
# 1. 텍스트 설정
script = "안녕하세요, 지금 보시는 이 100% 무료 자동화 영상은, 복잡한 렌더링 셋팅 없이 단 10초만에 완성된 릴스입니다."
audio_path = "test_output/audio.mp3"
img1_path = "test_output/img1.jpg"
img2_path = "test_output/img2.jpg"
video_path = "test_output/final_shorts.mp4"

# 2. 오디오 생성
print("\n[1] 오디오 생성 시작")
if generate_audio_free(script, audio_path):
    print("-> 오디오 생성 성공")

# 3. 이미지 생성
print("\n[2] 이미지 생성 시작")
if generate_image_free("A futuristic robot working on a laptop, neon cyberpunk city, cinematic lighting", img1_path):
    print("-> 이미지 1 생성 성공")
if generate_image_free("A high-tech server room with glowing blue lights, photorealistic, 8k", img2_path):
    print("-> 이미지 2 생성 성공")

# 4. 비디오 렌더링
print("\n[3] 영상 자동 조립 시작")
if assemble_video_free([img1_path, img2_path], audio_path, video_path):
    print(f"-> 최종 영상 완성: {video_path}")

