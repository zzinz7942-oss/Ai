"""
run_scrcpy_record.py
스마트폰 IP 주소 자동 감지 -> 무선 연결(adb connect) -> scrcpy PC 미러링 실행
- 찌그러짐 없는 스마트폰 정비율 유지 및 마우스 창 크기 자유 조절 최적화
- 마우스 테두리 잡고 드래그 이동/크기 조절 & 창 자유 팬닝 (--shortcut-mod=lalt)
- recorded_shorts 전용 폴더 자동 생성 및 녹화 파일 안전 통합 저장
- 무선 블랙 스크린 방지 최적화 옵션 (4M 비트레이트, opengl/software 렌더 드라이버, 50ms 디스플레이 버퍼)
- --record (또는 -r) 옵션 지정 시 숏폼 MP4 동영상 녹화 기능 활성화
"""

import os
import sys
import shutil
import zipfile
import argparse
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# adb_helper 모듈 임포트
import adb_helper


def find_or_download_scrcpy() -> str:
    """시스템 환경변수 및 주요 경로에서 scrcpy.exe 탐색 및 없을 시 자동 다운로드"""
    # 1. 시스템 PATH 체크
    scrcpy_in_path = shutil.which("scrcpy")
    if scrcpy_in_path:
        return scrcpy_in_path

    # 2. 로컬 및 주요 C 드라이브 설치 경로 탐색
    candidate_paths = [
        Path(__file__).parent / "scrcpy-win64" / "scrcpy.exe",
        Path(__file__).parent / "scrcpy-win64-v2.4" / "scrcpy.exe",
        Path("C:/scrcpy/scrcpy.exe"),
        Path("C:/Program Files/scrcpy/scrcpy.exe"),
    ]

    for path in candidate_paths:
        if path.exists():
            return str(path)

    # 3. scrcpy 자동 다운로드 (Genymobile 최신 Windows v2.4 릴리스)
    print("⚠️ 시스템에서 scrcpy를 찾을 수 없어 scrcpy-win64 패키지를 자동 다운로드합니다...")
    target_dir = Path(__file__).parent
    zip_path = target_dir / "scrcpy-win64.zip"
    url = "https://github.com/Genymobile/scrcpy/releases/download/v2.4/scrcpy-win64-v2.4.zip"

    try:
        print(f"📥 scrcpy 다운로드 중: {url}")
        urllib.request.urlretrieve(url, zip_path)
        print("📦 압축 해제 중...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(target_dir)

        if zip_path.exists():
            zip_path.unlink()

        downloaded_scrcpy = target_dir / "scrcpy-win64-v2.4" / "scrcpy.exe"
        if downloaded_scrcpy.exists():
            print(f"✅ scrcpy 자동 설치 완료: {downloaded_scrcpy}")
            return str(downloaded_scrcpy)

    except Exception as e:
        print(f"❌ scrcpy 자동 다운로드 실패: {e}")

    raise FileNotFoundError("scrcpy.exe 실행 파일을 찾을 수 없으며 자동 다운로드에 실패했습니다.")


def launch_scrcpy(
    specified_ip: str = None,
    port: int = 5555,
    is_record: bool = False,
    record_filename: str = None,
    render_driver: str = "opengl",
    bitrate: str = "4M",
    disable_audio: bool = True,
    show_touches: bool = True,
    stay_awake: bool = True,
    borderless: bool = False,
    crop: str = None
):
    """
    1. 스마트폰 IP 주소 자동 탐지 (또는 지정 IP)
    2. adb tcpip 5555 & adb connect 무선 연결
    3. scrcpy 미러링 실행 (비율 유지 + 자유로운 마우스 창 크기 조절/이동 최적화)
    """
    print("=" * 65)
    mode_title = "PC 미러링 & 숏폼 동영상 녹화 모드" if is_record else "PC 미러링 전용 모드"
    print(f"📱 [스마트폰 무선 자동 감지 - {mode_title}]")
    print("=" * 65)

    # 1. 무선 타겟 주소 자동 확보
    if specified_ip:
        target_addr = f"{specified_ip}:{port}" if ":" not in specified_ip else specified_ip
        adb_path = adb_helper.find_or_download_adb()
        subprocess.run([adb_path, "tcpip", str(port)], capture_output=True)
        subprocess.run([adb_path, "connect", target_addr], capture_output=True)
    else:
        # 스마트폰 IP 자동 감지 및 무선 커넥트 실행
        target_addr = adb_helper.auto_connect_wireless(port=port)

    if not target_addr:
        print("❌ 스마트폰 무선 연결 주소를 확보하지 못했습니다.")
        print("💡 팁: 스마트폰이 USB로 연결되어 있고 'USB 디버깅'이 활성화되어 있는지 확인해 주세요.")
        return False

    # 2. scrcpy 실행 파일 확보
    try:
        scrcpy_path = find_or_download_scrcpy()
    except Exception as e:
        print(f"❌ {e}")
        return False

    # 3. 화면 비율 보존 및 자유로운 마우스 창 크기 조절/이동 최적화 옵션 구성
    scrcpy_cmd = [
        scrcpy_path,
        "-s", target_addr,
        "--shortcut-mod", "lalt",             # Alt + 마우스 드래그 창 이동
        "--video-bit-rate", bitrate,         # 무선 대역폭 초과 방지
        "--max-fps", "60",                   # 프레임 60fps 안정화
        "--display-buffer", "50",            # 디스플레이 버퍼ing
        "--render-driver", render_driver,    # 렌더링 그래픽 드라이버 설정 (opengl/software)
        "--window-title", f"SmartPhone Mirroring ({target_addr})"
    ]

    # 무테두리 자유 창 모드 옵션
    if borderless:
        scrcpy_cmd.append("--window-borderless")

    # 화면 부분 크롭(Zoom/Pan) 옵션
    if crop:
        scrcpy_cmd.extend(["--crop", crop])

    # 마우스 클릭 터치 시각화
    if show_touches:
        scrcpy_cmd.append("--show-touches")

    # 미러링 중 화면 켜짐 유지
    if stay_awake:
        scrcpy_cmd.append("--stay-awake")

    if disable_audio:
        scrcpy_cmd.append("--no-audio")

    # 4. recorded_shorts 전용 저장 폴더 생성 및 통일 설정
    record_path = None
    if is_record:
        shorts_dir = Path(__file__).parent / "recorded_shorts"
        shorts_dir.mkdir(parents=True, exist_ok=True)

        if not record_filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            record_filename = f"shorts_record_{timestamp}.mp4"

        record_path = shorts_dir / record_filename
        scrcpy_cmd.extend([
            "--record", str(record_path),
            "--video-codec", "h264"
        ])
        print(f"🎥 [녹화 기능 활성화] 저장 위치: {record_path.absolute()}")

    print(f"\n🖥️ PC 화면 미러링 시작! (스마트폰 원본 정비율 보존 & 마우스 창 크기 조절)")
    print(f"📍 연결 기기 주소 : {target_addr}")
    print(f"📍 비트레이트 설정 : {bitrate}")
    print(f"📍 렌더 드라이버  : {render_driver}")
    print("\n🎮 [마우스 창 크기 및 화면 찌그러짐 방지 안내]")
    print("  • 마우스로 창 테두리를 잡고 조절하면 스마트폰 원본 비율이 100% 자동 유지됩니다.")
    print("  • Alt + X                  : 창 크기 조절 시 생긴 검은 여백 즉시 싹 제거")
    print("  • Alt + G                  : 1:1 선명 원본 피셀 사이즈로 창 크기 자동 맞춤")
    print("  • Alt + 마우스 드래그      : 창 위치 어디든 자유롭게 이동\n")

    print(f"🚀 실행 명령어: {' '.join(scrcpy_cmd)}")

    try:
        process = subprocess.Popen(scrcpy_cmd)
        print("📲 미러링 작동 중...")
        process.wait()

        if is_record and record_path:
            if record_path.exists() and record_path.stat().st_size > 0:
                print(f"\n🎉 숏폼 영상 녹화 완료!")
                print(f"   파일명: {record_path.name}")
                print(f"   저장폴더: {record_path.parent.absolute()}")
                print(f"   용량  : {record_path.stat().st_size / (1024*1024):.2f} MB")
            else:
                print("⚠️ 녹화 파일이 생성되지 않았거나 용량이 0입니다.")

        print("✅ 미러링이 정상적으로 종료되었습니다.")
        return True

    except Exception as e:
        print(f"❌ scrcpy 실행 중 오류 발생: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SmartPhone Wireless Mirroring & Shortform Recording Tool (Aspect Ratio Preserved)")
    parser.add_argument("--record", "-r", action="store_true", help="화면 녹화 기능 활성화 (--record 사용 시 MP4 저장)")
    parser.add_argument("--ip", type=str, default=None, help="스마트폰 IP 수동 지정 (기본값: 자동 탐지)")
    parser.add_argument("--output", "-o", type=str, default=None, help="녹화 파일명 지정 (예: my_video.mp4)")
    parser.add_argument("--render", type=str, default="opengl", choices=["opengl", "software", "d3d11"], help="렌더 드라이버 설정 (기본값: opengl)")
    parser.add_argument("--bitrate", "-b", type=str, default="4M", help="무선 비트레이트 설정 (기본값: 4M)")
    parser.add_argument("--borderless", action="store_true", help="무테두리 자유 창 모드")
    parser.add_argument("--crop", type=str, default=None, help="화면 부분 크롭 (예: 1080:1920:0:0)")
    parser.add_argument("--audio", action="store_true", help="오디오 전송 포함 (기본값: 무선 안정화를 위해 끔)")

    args = parser.parse_args()

    launch_scrcpy(
        specified_ip=args.ip,
        is_record=args.record,
        record_filename=args.output,
        render_driver=args.render,
        bitrate=args.bitrate,
        borderless=args.borderless,
        crop=args.crop,
        disable_audio=not args.audio
    )
