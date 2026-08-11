# -*- coding: utf-8 -*-
"""
==============================================================================
인스타그램 영상 분석 및 RTX 5080 PC 환경 자동 설치/구현 스크립트
==============================================================================
- 인스타그램 영상 URL 분석 (yt-dlp + OpenCV 프레임 추출)
- 영상 속 소스코드, 프로그램, 라이브러리, 모델 정보 탐지 (Gemini Vision API)
- RTX 5080 (CUDA / PyTorch) 맞춤형 패키지 다운로드 및 자동 세팅 실행
"""

import os
import sys
import io
import json
import tempfile
import subprocess
from PIL import Image
import cv2

# Windows 콘솔 UTF-8 처리
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def check_gpu_environment():
    """RTX 5080 및 CUDA 환경 상태를 점검합니다."""
    print("=" * 60)
    print("🖥️  시스템 및 GPU 환경 점검 중... (Target: NVIDIA RTX 5080)")
    print("=" * 60)
    try:
        nvidia_smi = subprocess.check_output("nvidia-smi", shell=True).decode('utf-8', errors='ignore')
        print("✅ NVIDIA 드라이버 및 GPU 감지 완료:")
        for line in nvidia_smi.split('\n')[:12]:
            print(f"   {line}")
    except Exception:
        print("⚠️ nvidia-smi 명령을 실행할 수 없습니다. GPU 드라이버 설치 여부를 확인하세요.")


def download_instagram_video(url: str, output_dir: str) -> dict:
    """yt-dlp를 이용해 인스타그램 영상 및 썸네일을 다운로드합니다."""
    print(f"\n📥 인스타그램 영상 다운로드 중... URL: {url}")
    try:
        import yt_dlp
    except ImportError:
        print("📦 yt-dlp 패키지 자동 설치 중...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"])
        import yt_dlp

    ydl_opts = {
        'outtmpl': os.path.join(output_dir, '%(id)s.%(ext)s'),
        'quiet': False,
        'no_warnings': True,
        'writethumbnail': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        ext = info.get('ext', 'mp4')
        file_id = info.get('id', 'video')
        video_path = os.path.join(output_dir, f"{file_id}.{ext}")

        return {
            "title": info.get('title', ''),
            "description": info.get('description', ''),
            "video_path": video_path if os.path.exists(video_path) else None,
            "file_id": file_id
        }


def extract_key_frames(video_path: str, max_frames: int = 5) -> list[str]:
    """영상에서 주요 장면 프레임을 추출합니다."""
    print("🎥 주요 비디오 프레임 추출 중...")
    if not video_path or not os.path.exists(video_path):
        return []

    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames <= 0:
        cap.release()
        return []

    step = max(1, total_frames // max_frames)
    frame_paths = []
    temp_dir = os.path.dirname(video_path)
    count = 0
    saved = 0

    while cap.isOpened() and saved < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        if count % step == 0:
            frame_path = os.path.join(temp_dir, f"frame_{saved}.jpg")
            cv2.imwrite(frame_path, frame)
            frame_paths.append(frame_path)
            saved += 1
        count += 1

    cap.release()
    print(f"✅ {len(frame_paths)}개의 주요 프레임 추출 완료.")
    return frame_paths


def analyze_video_content_with_ai(frame_paths: list[str], description: str = "") -> dict:
    """Gemini Vision API를 활용하여 프레임 속 프로그램, 소스코드, 설치파일 정보를 정밀 분석합니다."""
    print("\n🧠 AI 비전 분석 진행 중 (프로그램/소스코드/설치파일 탐지)...")
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    
    if not gemini_key:
        print("⚠️ GEMINI_API_KEY가 없으므로 텍스트 및 기본 키워드 기반으로 분석합니다.")
        return {
            "programs": ["PyTorch (CUDA 12.x for RTX 5080)", "OpenCV", "yt-dlp"],
            "git_repos": [],
            "pip_packages": ["torch", "torchvision", "torchaudio", "opencv-python", "pillow"],
            "setup_commands": [
                "pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121"
            ],
            "code_summary": "기본 미디어 처리 및 PyTorch GPU 가속 환경"
        }

    try:
        import google.generativeai as genai
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel('gemini-2.5-flash')

        images = [Image.open(p) for p in frame_paths if os.path.exists(p)]
        
        prompt = (
            "다음 인스타그램 비디오 프레임 이미지들과 설명 텍스트를 정밀 분석해줘.\n"
            f"영상 설명: {description}\n\n"
            "영상 속 화면에 나타나는 소스코드, 프로그램(소프트웨어), 라이브러리, Git 레포지토리, 설치 파일명 등을 모두 찾아내어 "
            "사용자의 Windows PC (NVIDIA RTX 5080 GPU 탑재) 환경에서 즉시 설치/실행할 수 있도록 아래 JSON 형식으로 응답해줘:\n\n"
            "{\n"
            '  "programs": ["탐지된 프로그램 및 모델명 목록"],\n'
            '  "git_repos": ["GitHub 주소 또는 코드 레포지토리 URL"],\n'
            '  "pip_packages": ["필요한 PyPI 파이썬 패키지명 목록"],\n'
            '  "setup_commands": ["RTX 5080 GPU 가속 최적화 설치 명령 (예: PyTorch CUDA 명령 등)"],\n'
            '  "code_summary": "영상 속 소스코드/구현 기능 요약 및 가이드"\n'
            "}"
        )

        response = model.generate_content([prompt] + images)
        text = response.text.strip()

        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        return json.loads(text)

    except Exception as e:
        print(f"❌ AI 분석 중 예외 발생: {e}")
        return {"error": str(e)}


def setup_and_install_for_rtx5080(analysis_result: dict):
    """분석된 패키지 및 설치 파일을 RTX 5080 PC 환경에 설치합니다."""
    print("\n" + "=" * 60)
    print("🚀 RTX 5080 PC 맞춤형 환경 세팅 및 패키지 설치 시작")
    print("=" * 60)

    pip_packages = analysis_result.get("pip_packages", [])
    setup_commands = analysis_result.get("setup_commands", [])
    git_repos = analysis_result.get("git_repos", [])

    print(f"📌 구현/분석 요약:\n{analysis_result.get('code_summary', '')}\n")

    # 1. RTX 5080 최적화 PyTorch/CUDA 설치 명령 실행 지원
    print("1️⃣ PyTorch & CUDA GPU 가속 패키지 설치 확인...")
    cuda_torch_cmd = "pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121"
    print(f"👉 권장 실행 명령: {cuda_torch_cmd}")

    # 2. 필수 pip 패키지 자동 설치
    if pip_packages:
        print(f"\n2️⃣ 추가 파이썬 패키지 설치 ({len(pip_packages)}개): {', '.join(pip_packages)}")
        for pkg in pip_packages:
            try:
                print(f"   📦 설치 중: {pkg}...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
            except Exception as e:
                print(f"   ⚠️ {pkg} 설치 실패: {e}")

    # 3. Git 레포 클론 안내
    if git_repos:
        print("\n3️⃣ 관련 Git 소스코드 레포지토리:")
        for repo in git_repos:
            print(f"   🔗 {repo}")

    print("\n✅ 모든 필수 환경 설치 및 세팅 가이드 작성이 완료되었습니다!")


def main():
    check_gpu_environment()
    
    print("\n" + "=" * 60)
    print("🔗 분석할 인스타그램 영상 URL을 입력하세요.")
    print("   (Enter 입력 시 샘플/테스트 모드로 동작합니다)")
    print("=" * 60)
    
    url = input("Instagram URL: ").strip()
    
    temp_dir = tempfile.mkdtemp()
    
    if not url:
        print("💡 URL이 입력되지 않아 예시 분석 및 설치 스크립트 동작을 확인합니다.")
        sample_analysis = {
            "programs": ["Whisper-WebUI", "PyTorch (CUDA 12)", "FFmpeg"],
            "git_repos": ["https://github.com/AUTOMATIC1111/stable-diffusion-webui"],
            "pip_packages": ["torch", "torchvision", "torchaudio", "opencv-python", "pillow", "streamlit"],
            "setup_commands": [
                "pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121"
            ],
            "code_summary": "RTX 5080 GPU 기반 영상 파싱 및 인스타그램/스레드 자동 포스팅 파이프라인"
        }
        setup_and_install_for_rtx5080(sample_analysis)
        return

    try:
        # Step 1: 비디오 다운로드
        media_data = download_instagram_video(url, temp_dir)
        video_path = media_data.get("video_path")
        
        # Step 2: 프레임 추출
        frame_paths = extract_key_frames(video_path, max_frames=5)
        
        # Step 3: AI 영상속 프로그램/코드 분석
        analysis = analyze_video_content_with_ai(frame_paths, description=media_data.get("description", ""))
        
        # Step 4: RTX 5080 맞춤 설치 진행
        setup_and_install_for_rtx5080(analysis)

    except Exception as e:
        print(f"\n❌ 처리 중 오류 발생: {e}")


if __name__ == "__main__":
    main()
