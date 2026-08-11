"""
player_360.py
360도 / VR 전용 데스크톱 비디오 플레이어 (Equirectangular to Perspective 360 Rendering)
- recorded_shorts 폴더 안의 360도 MP4 영상 자동 감지 및 선택 지원
- 마우스 클릭 & 드래그로 상하좌우 360도 자유 시점 회전 (Pitch/Yaw)
- 마우스 휠로 줌인/줌아웃 (FOV 시야각 조절)
- 스페이스바(일시정지/재생), R(시점 리셋), 화살표키(탐색/시점 조절), H(도움말 온오프)
"""

import os
import sys
import math
import glob
import time
import argparse
from pathlib import Path

import cv2
import numpy as np
from pathlib import Path
from tkinter import Tk, filedialog

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


def build_equirectangular_map(out_w: int, out_h: int, yaw_deg: float, pitch_deg: float, fov_deg: float, eq_w: int, eq_h: int):
    """
    360도 등방형(Equirectangular) 동영상을 사용자의 현재 Yaw, Pitch, FOV 시점에 맞춰
    원근 투영(Rectilinear Perspective) 렌더링 맵 생성 (NumPy 초고속 연산)
    """
    yaw = math.radians(yaw_deg)
    pitch = math.radians(pitch_deg)
    fov = math.radians(fov_deg)

    # 초점 거리 (Focal Length)
    f = 0.5 * out_w / math.tan(0.5 * fov)

    # 출력 화면 2D 그리드 (u, v)
    u = np.arange(out_w, dtype=np.float32) - (out_w / 2.0)
    v = np.arange(out_h, dtype=np.float32) - (out_h / 2.0)
    u_grid, v_grid = np.meshgrid(u, v)

    # 3D 광선 벡터 (x: 우측, y: 아래, z: 정면)
    x_c = u_grid / f
    y_c = v_grid / f
    z_c = np.ones_like(x_c)

    # 단위 벡터 정규화
    norm = np.sqrt(x_c**2 + y_c**2 + z_c**2)
    x_c /= norm
    y_c /= norm
    z_c /= norm

    # X축 회전 행렬 (Pitch - 피치 상하)
    cos_p, sin_p = math.cos(pitch), math.sin(pitch)
    R_x = np.array([
        [1, 0, 0],
        [0, cos_p, -sin_p],
        [0, sin_p, cos_p]
    ], dtype=np.float32)

    # Y축 회전 행렬 (Yaw - 요 좌우)
    cos_y, sin_y = math.cos(yaw), math.sin(yaw)
    R_y = np.array([
        [cos_y, 0, sin_y],
        [0, 1, 0],
        [-sin_y, 0, cos_y]
    ], dtype=np.float32)

    # 합성 회전 행렬
    R = R_y @ R_x

    # 광선 벡터 회전
    rays = np.stack([x_c, y_c, z_c], axis=-1)
    rotated_rays = rays @ R.T

    rx = rotated_rays[..., 0]
    ry = rotated_rays[..., 1]
    rz = rotated_rays[..., 2]

    # 구면 좌표계(Longitude, Latitude) 변환
    longitude = np.arctan2(rx, rz)
    latitude = np.arcsin(np.clip(-ry, -1.0, 1.0))

    # Equirectangular 2D 텍스처 좌표 매핑
    map_x = ((longitude + np.pi) / (2.0 * np.pi)) * eq_w
    map_y = ((np.pi / 2.0 - latitude) / np.pi) * eq_h

    return map_x.astype(np.float32), map_y.astype(np.float32)


class VR360Player:
    def __init__(self, video_path: str, out_w: int = 1280, out_h: int = 720):
        self.video_path = video_path
        self.out_w = out_w
        self.out_h = out_h

        # 시점 조작 변수 (Yaw, Pitch, FOV)
        self.yaw = 0.0
        self.pitch = 0.0
        self.fov = 90.0

        # 마우스 인터랙션 상태
        self.is_dragging = False
        self.last_mouse_x = 0
        self.last_mouse_y = 0

        # 재생 상태 변수
        self.is_paused = False
        self.show_hud = True
        self.map_need_update = True
        self.map_x = None
        self.map_y = None

        # 비디오 캐치
        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            raise ValueError(f"비디오 파일을 열 수 없습니다: {self.video_path}")

        self.eq_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.eq_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0

        self.window_name = "360 VR Video Player (Drag Mouse to Rotate View)"

    def mouse_callback(self, event, x, y, flags, param):
        """마우스 클릭, 드래그, 휠 줌 이벤트를 처리하는 콜백 함수"""
        if event == cv2.EVENT_LBUTTONDOWN:
            self.is_dragging = True
            self.last_mouse_x = x
            self.last_mouse_y = y

        elif event == cv2.EVENT_MOUSEMOVE:
            if self.is_dragging:
                dx = x - self.last_mouse_x
                dy = y - self.last_mouse_y

                # 감도 조절 및 피치/요 값 업데이트
                sensitivity = 0.25 * (self.fov / 90.0)
                self.yaw += dx * sensitivity
                self.pitch += dy * sensitivity

                # 피치 상하 범위 제한 (-85도 ~ +85도)
                self.pitch = max(-85.0, min(85.0, self.pitch))

                # 요 값 범위 정규화 (-180도 ~ +180도)
                if self.yaw > 180.0:
                    self.yaw -= 360.0
                elif self.yaw < -180.0:
                    self.yaw += 360.0

                self.last_mouse_x = x
                self.last_mouse_y = y
                self.map_need_update = True

        elif event == cv2.EVENT_LBUTTONUP:
            self.is_dragging = False

        elif event == cv2.EVENT_MOUSEWHEEL:
            # 휠 줌인 / 줌아웃 (FOV 30도 ~ 120도 조절)
            if flags > 0:
                self.fov = max(30.0, self.fov - 4.0)
            else:
                self.fov = min(120.0, self.fov + 4.0)
            self.map_need_update = True

    def draw_hud_overlay(self, frame):
        """화면 상단 및 하단 조작 가이드 & 상태 오버레이 렌더링"""
        if not self.show_hud:
            return frame

        overlay = frame.copy()
        current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
        curr_sec = int(current_frame / self.fps) if self.fps > 0 else 0
        total_sec = int(self.total_frames / self.fps) if self.fps > 0 else 0

        # 상단 오버레이 바
        cv2.rectangle(overlay, (0, 0), (self.out_w, 45), (15, 23, 42), -1)
        cv2.rectangle(overlay, (0, self.out_h - 45), (self.out_w, self.out_h), (15, 23, 42), -1)
        
        # 반투명 블렌딩
        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

        # 상단 텍스트 정보
        fn_title = Path(self.video_path).name
        status_str = "PAUSED" if self.is_paused else "PLAYING"
        top_info = f"360 VR [{status_str}] | File: {fn_title} | Yaw: {int(self.yaw)}deg | Pitch: {int(self.pitch)}deg | FOV: {int(self.fov)}deg"
        cv2.putText(frame, top_info, (15, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)

        # 하단 가이드 텍스트
        bottom_info = f"[{curr_sec//60:02d}:{curr_sec%60:02d} / {total_sec//60:02d}:{total_sec%60:02d}]  | [Mouse Drag] Look Around | [Wheel] Zoom | [Space] Pause | [R] Reset View | [Q] Exit"
        cv2.putText(frame, bottom_info, (15, self.out_h - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 230, 118), 1, cv2.LINE_AA)

        # 타임라인 진척도 바
        if self.total_frames > 0:
            progress = current_frame / self.total_frames
            bar_w = int(self.out_w * progress)
            cv2.line(frame, (0, self.out_h - 2), (bar_w, self.out_h - 2), (0, 230, 118), 4)

        return frame

    def run(self):
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, self.out_w, self.out_h)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)

        print("\n" + "=" * 65)
        print("🎮 [360도 VR 데스크톱 플레이어 조작 안내]")
        print("  • 마우스 좌클릭 + 드래그   : 360도 상하좌우 시점 자유 이동 (Look Around)")
        print("  • 마우스 휠 스크롤        : 줌인 / 줌아웃 (FOV 30도 ~ 120도)")
        print("  • 스페이스바 (Space)       : 일시정지 / 재생")
        print("  • R 키                     : 정면 시점 원복 (Reset View)")
        print("  • H 키                     : 정보 OSD 가이드 온/오프")
        print("  • 좌/우 방향키 (← / →)    : 5초 뒤로 / 앞으로 이동")
        print("  • Q 또는 ESC 키            : 플레이어 종료")
        print("=" * 65 + "\n")

        last_frame = None

        while True:
            # 렌더링 매핑 테이블 업데이트 (시점 변경 시)
            if self.map_need_update or self.map_x is None:
                self.map_x, self.map_y = build_equirectangular_map(
                    self.out_w, self.out_h, self.yaw, self.pitch, self.fov, self.eq_w, self.eq_h
                )
                self.map_need_update = False

            # 프레임 읽기 (일시정지가 아니면 다음 프레임 가져오기)
            if not self.is_paused or last_frame is None:
                ret, frame = self.cap.read()
                if not ret:
                    # 비디오 끝에 도달하면 처음으로 루프 재생
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = self.cap.read()
                    if not ret:
                        break
                last_frame = frame

            # Equirectangular -> 360 원근 투영 변환 (Remap 연산)
            rendered_frame = cv2.remap(last_frame, self.map_x, self.map_y, cv2.INTER_LINEAR)

            # HUD 오버레이 표시
            display_frame = self.draw_hud_overlay(rendered_frame)

            # 화면 출력
            cv2.imshow(self.window_name, display_frame)

            # 키보드 입력 처리
            delay = int(1000 / self.fps) if not self.is_paused else 30
            key = cv2.waitKey(delay) & 0xFF

            if key in [ord('q'), ord('Q'), 27]:  # Q 또는 ESC
                break
            elif key == ord(' '):  # 스페이스바
                self.is_paused = not self.is_paused
            elif key in [ord('r'), ord('R')]:  # R (시점 리셋)
                self.yaw, self.pitch, self.fov = 0.0, 0.0, 90.0
                self.map_need_update = True
            elif key in [ord('h'), ord('H')]:  # H (HUD 토글)
                self.show_hud = not self.show_hud
            elif key == 81 or key == 2:  # 좌 화살표 (5초 뒤로)
                curr = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, curr - 5 * self.fps))
            elif key == 83 or key == 3:  # 우 화살표 (5초 앞으로)
                curr = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, min(self.total_frames - 1, curr + 5 * self.fps))

        self.cap.release()
        cv2.destroyAllWindows()


def select_video_file() -> str:
    """recorded_shorts 폴더 감지 또는 사용자 파일 선택 창"""
    shorts_dir = Path(__file__).parent / "recorded_shorts"
    shorts_dir.mkdir(parents=True, exist_ok=True)

    mp4_files = list(shorts_dir.glob("*.mp4"))
    if mp4_files:
        mp4_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        latest = mp4_files[0]
        print(f"🎬 recorded_shorts 폴더 내 최신 360도 영상 자동 감지: {latest.name}")
        return str(latest.absolute())

    # recorded_shorts 폴더에 영상이 없으면 파일 선택창 오픈
    print("💡 recorded_shorts 폴더 내 영상이 없어 파일 선택 창을 엽니다...")
    root = Tk()
    root.withdraw()
    selected = filedialog.askopenfilename(
        title="360도/VR 비디오 파일 선택",
        filetypes=[("Video Files", "*.mp4 *.mov *.avi *.mkv"), ("All Files", "*.*")]
    )
    root.destroy()

    return selected


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="360 VR Desktop Video Player")
    parser.add_argument("--video", "-v", type=str, default=None, help="재생할 360도 MP4 파일 경로")
    parser.add_argument("--width", type=int, default=1280, help="창 가로 크기")
    parser.add_argument("--height", type=int, default=720, help="창 세로 크기")

    args = parser.parse_args()

    v_path = args.video
    if not v_path:
        v_path = select_video_file()

    if v_path and os.path.exists(v_path):
        player = VR360Player(v_path, out_w=args.width, out_h=args.height)
        player.run()
    else:
        print("❌ 재생할 비디오 파일을 찾을 수 없어 프로그램을 종료합니다.")
