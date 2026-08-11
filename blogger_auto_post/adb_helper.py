"""
adb_helper.py
시스템 내 ADB 경로 자동 탐색, 구글 공식 platform-tools 자동 다운로드,
USB 연결된 스마트폰의 Wi-Fi IP 주소 자동 탐지 및 무선 연결(adb connect) 자동화 모듈
"""

import os
import re
import sys
import shutil
import zipfile
import subprocess
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


def find_or_download_adb() -> str:
    """시스템 환경변수, Android SDK 표준 경로, 프로젝트 폴더 탐색 및 필요 시 자동 다운로드"""
    # 1. 시스템 PATH 환경변수 체크
    adb_in_path = shutil.which("adb")
    if adb_in_path:
        return adb_in_path

    # 2. 시스템 표준 설치 경로 및 사용자 AppData 탐색
    user_home = Path.home()
    local_app_data = os.getenv("LOCALAPPDATA", str(user_home / "AppData" / "Local"))
    android_home = os.getenv("ANDROID_HOME") or os.getenv("ANDROID_SDK_ROOT")

    candidate_paths = [
        # 프로젝트 로컬 폴더
        Path(__file__).parent / "platform-tools" / "adb.exe",
        Path(__file__).parent / "bin" / "adb.exe",
        # Android Studio 표준 경로
        Path(local_app_data) / "Android" / "Sdk" / "platform-tools" / "adb.exe",
        # 주요 C 드라이브 설치 경로 및 에뮬레이터 경로
        Path("C:/platform-tools/adb.exe"),
        Path("C:/Android/platform-tools/adb.exe"),
        Path("C:/Program Files/Android/platform-tools/adb.exe"),
        Path("C:/Program Files (x86)/Android/android-sdk/platform-tools/adb.exe"),
        Path("C:/Program Files/Nox/bin/nox_adb.exe"),
    ]

    if android_home:
        candidate_paths.insert(0, Path(android_home) / "platform-tools" / "adb.exe")

    for path in candidate_paths:
        if path.exists():
            return str(path)

    # 3. 경로 검색 실패 시 구글 공식 platform-tools 자동 다운로드 (Fallback)
    print("⚠️ 시스템에서 adb.exe를 찾을 수 없어 구글 공식 platform-tools를 자동 다운로드합니다...")
    target_dir = Path(__file__).parent / "platform-tools"
    zip_path = Path(__file__).parent / "platform-tools-windows.zip"
    url = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"

    try:
        print(f"📥 구글 공식 서버에서 다운로드 중: {url}")
        urllib.request.urlretrieve(url, zip_path)
        print("📦 압축 해제 중...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(Path(__file__).parent)

        if zip_path.exists():
            zip_path.unlink()

        downloaded_adb = target_dir / "adb.exe"
        if downloaded_adb.exists():
            print(f"✅ ADB 자동 설치 완료: {downloaded_adb}")
            return str(downloaded_adb)
    except Exception as e:
        print(f"❌ ADB 자동 다운로드 중 오류 발생: {e}")

    raise FileNotFoundError("adb.exe를 찾을 수 없으며 자동 다운로드에 실패했습니다.")


def auto_detect_device_ip(adb_path: str) -> str:
    """연결된 스마트폰의 Wi-Fi IP 주소를 ADB shell 명령어로 자동 탐지"""
    print("🔍 [스마트폰 네트워크 IP 주소 자동 탐지 중...]")
    
    # 1. wlan0 인터페이스 IP 조회 시도
    cmds = [
        [adb_path, "shell", "ip", "-f", "inet", "addr", "show", "wlan0"],
        [adb_path, "shell", "ip", "route"],
        [adb_path, "shell", "getprop", "dhcp.wlan0.ipaddress"],
        [adb_path, "shell", "ifconfig", "wlan0"]
    ]

    for cmd in cmds:
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
            output = res.stdout.strip()
            
            # inet 192.168.X.X 패턴 매칭
            ip_matches = re.findall(r'(?:inet\s+|src\s+|addr:|\b)(192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+)', output)
            if ip_matches:
                detected_ip = ip_matches[0]
                print(f"✅ 스마트폰 Wi-Fi IP 자동 감지 성공: {detected_ip}")
                return detected_ip
        except Exception:
            continue

    return ""


def run_adb_tcpip(port: int = 5555) -> bool:
    """ADB 경로를 확보한 후 adb tcpip <port> 명령어를 실행"""
    print("=" * 60)
    print("📱 [ADB 경로 자동 검색 및 adb tcpip 실행 중...]")
    print("=" * 60)

    try:
        adb_path = find_or_download_adb()
        print(f"📍 최종 감지된 ADB 실행 파일: {adb_path}")

        cmd = [adb_path, "tcpip", str(port)]
        print(f"🚀 실행 명령어: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        if result.returncode == 0:
            print(f"✅ 성공: adb tcpip {port} 포트 설정이 완료되었습니다.")
            if result.stdout.strip():
                print(f"   출력: {result.stdout.strip()}")
            print("=" * 60)
            return True
        else:
            print(f"⚠️ ADB 명령어 실행 실패 (반환 코드 {result.returncode})")
            err_msg = result.stderr.strip() or result.stdout.strip()
            print(f"   오류 메시지: {err_msg}")
            print("=" * 60)
            return False

    except Exception as e:
        print(f"❌ 예외 발생: {e}")
        print("=" * 60)
        return False


def auto_connect_wireless(port: int = 5555) -> str:
    """
    USB로 연결된 스마트폰의 IP를 자동 탐지하고 adb tcpip -> adb connect 처리하는 종합 자동화 함수
    성공 시 "192.168.X.X:5555" 주소 반환
    """
    adb_path = find_or_download_adb()

    # 이미 무선으로 연결되어 있는지 확인
    devices_res = subprocess.run([adb_path, "devices"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    devices_output = devices_res.stdout

    # 이미 IP:5555 형식으로 연결된 경우
    existing_ip_match = re.search(r'((?:192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+):5555)\s+device', devices_output)
    if existing_ip_match:
        already_addr = existing_ip_match.group(1)
        print(f"✅ 기존에 이미 무선 연결되어 있는 스마트폰 감지: {already_addr}")
        return already_addr

    # IP 자동 탐지
    ip_addr = auto_detect_device_ip(adb_path)
    if not ip_addr:
        print("⚠️ 스마트폰 IP 주소를 자동으로 가져오지 못했습니다.")
        return ""

    # adb tcpip 5555 포트 설정
    tcpip_res = subprocess.run([adb_path, "tcpip", str(port)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(f"📡 5555 포트 무선 모드 활성화: {tcpip_res.stdout.strip()}")

    # adb connect <IP>:5555 실행
    target_addr = f"{ip_addr}:{port}"
    print(f"🔌 무선 커넥트 실행 중: adb connect {target_addr}")
    conn_res = subprocess.run([adb_path, "connect", target_addr], capture_output=True, text=True, encoding="utf-8", errors="replace")
    
    conn_output = conn_res.stdout.strip()
    print(f"   출력: {conn_output}")

    if "connected" in conn_output.lower() or "already connected" in conn_output.lower():
        print(f"🎉 스마트폰 무선 연결 완료: {target_addr}")
        return target_addr
    else:
        print("❌ 무선 연결에 실패했습니다. PC와 스마트폰이 동일한 Wi-Fi에 연결되어 있는지 확인해 주세요.")
        return ""


if __name__ == "__main__":
    auto_connect_wireless(5555)
