"""
sbs_vr_player.py
유튜브/카드보드 SBS(Side-by-Side) 좌우 분할 3D 및 VR 영상 실시간 변환 & 데스크톱 플레이어
- 모드 1: SBS 360도 VR 마우스 회전 모드 (좌안 영상 추출 후 360도 마우스 드래그 조작)
- 모드 2: 3D 적청(Red-Cyan Anaglyph) 모드 (적청 안경 착용 시 일반 모니터 입체 3D 감상)
- 모드 3: 단안(Monocular 2D) 모드 (좌안 16:9 싱글 2D 화면 변환)
- 모드 4: 원본 SBS 좌우 분할 비교 모드
"""

import os
import sys
import math
import argparse
from pathlib import Path
from tkinter import Tk, filedialog

import cv2
import numpy as np

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


def build_equirectangular_map(out_w: int, out_h: int, yaw_deg: float, pitch_deg: float, fov_deg: float, eq_w: int, eq_h: int):
    """360도 등방형 텍스처를 원근 투영 렌더링 맵으로 변환 연산"""
    yaw = math.radians(yaw_deg)
    pitch = math.radians(pitch_deg)
    fov = math.radians(fov_deg)

    f = 0.5 * out_w / math.tan(0.5 * fov)

    u = np.arange(out_w, dtype=np.float32) - (out_w / 2.0)
    v = np.arange(out_h, dtype=np.float32) - (out_h / 2.0)
    u_grid, v_grid = np.meshgrid(u, v)

    x_c = u_grid / f
    y_c = v_grid / f
    z_c = np.ones_like(x_c)

    norm = np.sqrt(x_c**2 + y_c**2 + z_c**2)
    x_c /= norm
    y_c /= norm
    z_c /= norm

    cos_p, sin_p = math.cos(pitch), math.sin(pitch)
    R_x = np.array([
        [1, 0, 0],
        [0, cos_p, -sin_p],
        [0, sin_p, cos_p]
    ], dtype=np.float32)

    cos_y, sin_y = math.cos(yaw), math.sin(yaw)
    R_y = np.array([
        [cos_y, 0, sin_y],
        [0, 1, 0],
        [-sin_y, 0, cos_y]
    ], dtype=np.float32)

    R = R_y @ R_x

    rays = np.stack([x_c, y_c, z_c], axis=-1)
    rotated_rays = rays @ R.T

    rx = rotated_rays[..., 0]
    ry = rotated_rays[..., 1]
    rz = rotated_rays[..., 2]

    longitude = np.arctan2(rx, rz)
    latitude = np.arcsin(np.clip(-ry, -1.0, 1.0))

    map_x = ((longitude + np.pi) / (2.0 * np.pi)) * eq_w
    map_y = ((np.pi / 2.0 - latitude) / np.pi) * eq_h

    return map_x.astype(np.float32), map_y.astype(np.float32)


class SBSVRPlayer:
    def __init__(self, video_path: str, out_w: int = 1280, out_h: int = 720):
        self.video_path = video_path
        self.out_w = out_w
        self.out_h = out_h

        # 재생 모드: 1=360도 VR 마우스, 2=적청 3D 입체, 3=단안 2D, 4=원본 SBS
        self.mode = 1
        self.mode_names = {
            1: "360도 VR 마우스 드래그 모드",
            2: "3D 적청(Red-Cyan Anaglyph) 입체 모드",
            3: "단안(Monocular) 2D 일반 화면 모드",
            4: "원본 SBS(Side-by-Side) 좌우 분할 모드"
        }

        # 360도 시점 변수
        self.yaw = 0.0
        self.pitch = 0.0
        self.fov = 90.0

        # 마우스 드래그 상태
        self.is_dragging = False
        self.last_mouse_x = 0
        self.last_mouse_y = 0

        # 재생 제어 변수
        self.is_paused = False
        self.show_hud = True
        self.map_need_update = True
        self.map_x = None
        self.map_y = None

        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            raise ValueError(f"비디오 파일을 열 수 없습니다: {self.video_path}")

        self.raw_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.raw_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0

        self.window_name = "SBS VR & 3D Video Player (Press 1/2/3/4 to Change Mode)"

    def mouse_callback(self, event, x, y, flags, param):
        """360도 VR 모드일 때 마우스 클릭/드래그 시점 회전 조작"""
        if self.mode != 1:
            return

        if event == cv2.EVENT_LBUTTONDOWN:
            self.is_dragging = True
            self.last_mouse_x = x
            self.last_mouse_y = y

        elif event == cv2.EVENT_MOUSEMOVE:
            if self.is_dragging:
                dx = x - self.last_mouse_x
                dy = y - self.last_mouse_y

                sensitivity = 0.25 * (self.fov / 90.0)
                self.yaw += dx * sensitivity
                self.pitch += dy * sensitivity

                self.pitch = max(-85.0, min(85.0, self.pitch))

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
            if flags > 0:
                self.fov = max(30.0, self.fov - 4.0)
            else:
                self.fov = min(120.0, self.fov + 4.0)
            self.map_need_update = True

    def process_sbs_frame(self, raw_frame):
        """SBS 프레임을 선택된 모드(360도/3D적청/2D단안/SBS)로 변환"""
        h, w = raw_frame.shape[:2]
        half_w = w // 2

        # 좌안, 우안 이미지 분리
        left_eye = raw_frame[:, :half_w]
        right_eye = raw_frame[:, half_w:]

        # 모드 1: 360도 VR 마우스 드래그 모드
        if self.mode == 1:
            eq_frame = cv2.resize(left_eye, (1920, 960))
            eq_h, eq_w = eq_frame.shape[:2]

            if self.map_need_update or self.map_x is None:
                self.map_x, self.map_y = build_equirectangular_map(
                    self.out_w, self.out_h, self.yaw, self.pitch, self.fov, eq_w, eq_h
                )
                self.map_need_update = False

            return cv2.remap(eq_frame, self.map_x, self.map_y, cv2.INTER_LINEAR)

        # 모드 2: 3D 적청(Red-Cyan Anaglyph) 모드
        elif self.mode == 2:
            l_resized = cv2.resize(left_eye, (self.out_w, self.out_h))
            r_resized = cv2.resize(right_eye, (self.out_w, self.out_h))

            anaglyph = np.zeros_like(l_resized)
            anaglyph[:, :, 0] = r_resized[:, :, 0]  # Blue (Right)
            anaglyph[:, :, 1] = r_resized[:, :, 1]  # Green (Right)
            anaglyph[:, :, 2] = l_resized[:, :, 2]  # Red (Left)
            return anaglyph

        # 모드 3: 단안(Monocular 2D) 화면 모드
        elif self.mode == 3:
            return cv2.resize(left_eye, (self.out_w, self.out_h))

        # 모드 4: 원본 SBS 좌우 분할 화면 모드
        else:
            return cv2.resize(raw_frame, (self.out_w, self.out_h))

    def draw_hud(self, frame):
        if not self.show_hud:
            return frame

        overlay = frame.copy()
        current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
        curr_sec = int(current_frame / self.fps) if self.fps > 0 else 0
        total_sec = int(self.total_frames / self.fps) if self.fps > 0 else 0

        cv2.rectangle(overlay, (0, 0), (self.out_w, 45), (15, 23, 42), -1)
        cv2.rectangle(overlay, (0, self.out_h - 45), (self.out_w, self.out_h), (15, 23, 42), -1)
        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

        fn_title = Path(self.video_path).name
        status_str = "PAUSED" if self.is_paused else "PLAYING"
        mode_str = self.mode_names.get(self.mode, "")
        
        top_info = f"SBS VR [{status_str}] | Mode: {self.mode}. {mode_str} | File: {fn_title}"
        if self.mode == 1:
            top_info += f" | Yaw:{int(self.yaw)} Pitch:{int(self.pitch)} FOV:{int(self.fov)}"

        cv2.putText(frame, top_info, (15, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1, cv2.LINE_AA)

        bottom_info = f"[{curr_sec//60:02d}:{curr_sec%60:02d} / {total_sec//60:02d}:{total_sec%60:02d}]  | [1] 360VR  [2] 3D적청  [3] 2D단안  [4] 원본SBS  | [Space] 일시정지  [Q] 종료"
        cv2.putText(frame, bottom_info, (15, self.out_h - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 230, 118), 1, cv2.LINE_AA)

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
        print("🎮 [SBS 3D/VR 플레이어 모드 변경 단축키]")
        print("  • [1] 키: 360도 VR 마우스 드래그 회전 모드 (Mouse Look-Around)")
        print("  • [2] 키: 3D 적청(Red-Cyan Anaglyph) 입체 모드 (안경 착용 시 입체)")
        print("  • [3] 키: 단안(Monocular 2D) 일반 화면 변환 모드")
        print("  • [4] 키: 원본 SBS(Side-by-Side) 좌우 분할 모드")
        print("  • 스페이스바: 일시정지 / 재생 | R키: 시점 리셋 | Q/ESC: 종료")
        print("=" * 65 + "\n")

        last_raw_frame = None

        while True:
            if not self.is_paused or last_raw_frame is None:
                ret, raw_frame = self.cap.read()
                if not ret:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, raw_frame = self.cap.read()
                    if not ret:
                        break
                last_raw_frame = raw_frame

            processed_frame = self.process_sbs_frame(last_raw_frame)
            display_frame = self.draw_hud(processed_frame)

            cv2.imshow(self.window_name, display_frame)

            delay = int(1000 / self.fps) if not self.is_paused else 30
            key = cv2.waitKey(delay) & 0xFF

            if key in [ord('q'), ord('Q'), 27]:
                break
            elif key == ord(' '):
                self.is_paused = not self.is_paused
            elif key == ord('1'):
                self.mode = 1
                self.map_need_update = True
                print("🔄 모드 변경: 360도 VR 마우스 드래그 모드")
            elif key == ord('2'):
                self.mode = 2
                print("🔄 모드 변경: 3D 적청(Red-Cyan) 입체 모드")
            elif key == ord('3'):
                self.mode = 3
                print("🔄 모드 변경: 단안(Monocular 2D) 일반 모드")
            elif key == ord('4'):
                self.mode = 4
                print("🔄 모드 변경: 원본 SBS 좌우 분할 모드")
            elif key in [ord('r'), ord('R')]:
                self.yaw, self.pitch, self.fov = 0.0, 0.0, 90.0
                self.map_need_update = True
            elif key in [ord('h'), ord('H')]:
                self.show_hud = not self.show_hud
            elif key == 81 or key == 2:  # ← 5초 뒤로
                curr = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, curr - 5 * self.fps))
            elif key == 83 or key == 3:  # → 5초 앞으로
                curr = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, min(self.total_frames - 1, curr + 5 * self.fps))

        self.cap.release()
        cv2.destroyAllWindows()


def select_sbs_video() -> str:
    """recorded_shorts 폴더 감지 또는 사용자 선택"""
    shorts_dir = Path(__file__).parent / "recorded_shorts"
    shorts_dir.mkdir(parents=True, exist_ok=True)

    mp4_files = list(shorts_dir.glob("*.mp4"))
    if mp4_files:
        mp4_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        latest = mp4_files[0]
        print(f"🎬 recorded_shorts 최신 SBS/VR 영상 자동 감지: {latest.name}")
        return str(latest.absolute())

    root = Tk()
    root.withdraw()
    selected = filedialog.askopenfilename(
        title="SBS 3D / VR 비디오 파일 선택",
        filetypes=[("Video Files", "*.mp4 *.mov *.avi *.mkv"), ("All Files", "*.*")]
    )
    root.destroy()
    return selected


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SBS 3D & VR Real-Time Converter & Player")
    parser.add_argument("--video", "-v", type=str, default=None, help="재생할 SBS 3D/VR MP4 파일 경로")
    parser.add_argument("--width", type=int, default=1280, help="창 가로 크기")
    parser.add_argument("--height", type=int, default=720, help="창 세로 크기")

    args = parser.parse_args()

    v_path = args.video
    if not v_path:
        v_path = select_sbs_video()

    if v_path and os.path.exists(v_path):
        player = SBSVRPlayer(v_path, out_w=args.width, out_h=args.height)
        player.run()
    else:
        print("❌ 재생할 비디오 파일을 찾을 수 없어 프로그램을 종료합니다.")
