"""
youtube_vr_player.py
유튜브 및 웹 브라우저에서 재생되는 좌우 분할(SBS) VR/3D 영상 화면 실시간 캡처 & 마우스 조작 플레이어
- 화면 상의 유튜브 SBS 영상 영역 실시간 캡처 (Pillow ImageGrab + OpenCV 연산)
- 모드 1: 360도 VR 마우스 회전 모드 (좌안 캡처 후 마우스 클릭&드래그로 360도 상하좌우 시점 회전)
- 모드 2: 3D 적청(Red-Cyan Anaglyph) 입체 모드 (적청 안경 착용 시 3D 입체)
- 모드 3: 단안(Monocular 2D) 일반 화면 변환 모드
- 모드 4: 실시간 캡처 영역 라이브 뷰 모드
- 'S' 키: 캡처 영역 수동 선택 및 재지정 (유튜브 비디오 창에 클릭 락온)
"""

import os
import sys
import math
import time
import argparse
from pathlib import Path

import cv2
import numpy as np
from PIL import ImageGrab

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


def build_equirectangular_map(out_w: int, out_h: int, yaw_deg: float, pitch_deg: float, fov_deg: float, eq_w: int, eq_h: int):
    """360도 등방형 텍스처를 원근 투영 렌더링 맵으로 연산"""
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


class YouTubeVRCapturePlayer:
    def __init__(self, out_w: int = 1280, out_h: int = 720):
        self.out_w = out_w
        self.out_h = out_h

        # 캡처 영극 (None일 경우 기본 화면 중앙 절반 캡처)
        screen_img = ImageGrab.grab()
        self.screen_w, self.screen_h = screen_img.size

        # 기본 캡처 영역 (화면 중앙 16:9 비율 영역)
        cx, cy = self.screen_w // 2, self.screen_h // 2
        cw, ch = int(self.screen_w * 0.7), int(self.screen_h * 0.7)
        self.bbox = (max(0, cx - cw // 2), max(0, cy - ch // 2), min(self.screen_w, cx + cw // 2), min(self.screen_h, cy + ch // 2))

        # 재생 모드: 1=360도 VR 마우스, 2=적청 3D, 3=단안 2D, 4=캡처 라아브
        self.mode = 1
        self.mode_names = {
            1: "360도 VR 마우스 회전 모드 (유튜브 SBS 360° 락온)",
            2: "3D 적청(Red-Cyan Anaglyph) 입체 모드",
            3: "단안(Monocular) 2D 일반 화면 모드",
            4: "유튜브 SBS 캡처 영역 라이브 모드"
        }

        # 360도 시점 변수
        self.yaw = 0.0
        self.pitch = 0.0
        self.fov = 90.0

        # 마우스 드래그 상태
        self.is_dragging = False
        self.last_mouse_x = 0
        self.last_mouse_y = 0

        self.is_paused = False
        self.show_hud = True
        self.map_need_update = True
        self.map_x = None
        self.map_y = None

        self.window_name = "YouTube Real-Time VR Player (Press 1/2/3/4 to Change Mode)"

    def mouse_callback(self, event, x, y, flags, param):
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

    def capture_screen_frame(self):
        """Pillow ImageGrab 기반 실시간 브라우저 캡처"""
        img = ImageGrab.grab(bbox=self.bbox)
        frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        return frame

    def process_captured_sbs(self, raw_frame):
        """캡처된 유튜브 SBS 영상 실시간 360도/3D 변환 연산"""
        h, w = raw_frame.shape[:2]
        half_w = w // 2

        if half_w < 10 or h < 10:
            return np.zeros((self.out_h, self.out_w, 3), dtype=np.uint8)

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

        # 모드 2: 3D 적청(Red-Cyan Anaglyph) 입체 모드
        elif self.mode == 2:
            l_resized = cv2.resize(left_eye, (self.out_w, self.out_h))
            r_resized = cv2.resize(right_eye, (self.out_w, self.out_h))

            anaglyph = np.zeros_like(l_resized)
            anaglyph[:, :, 0] = r_resized[:, :, 0]  # Blue (Right)
            anaglyph[:, :, 1] = r_resized[:, :, 1]  # Green (Right)
            anaglyph[:, :, 2] = l_resized[:, :, 2]  # Red (Left)
            return anaglyph

        # 모드 3: 단안(Monocular 2D) 일반 화면 모드
        elif self.mode == 3:
            return cv2.resize(left_eye, (self.out_w, self.out_h))

        # 모드 4: 원본 라이브 캡처 프레임 모드
        else:
            return cv2.resize(raw_frame, (self.out_w, self.out_h))

    def select_capture_region_interactive(self):
        """전체 화면 캡처 후 마우스로 유튜브 영상 영역 직접 드래그 지정"""
        print("📌 캡처할 유튜브 비디오 창 영역을 마우스 드래그로 선택해 주세요...")
        full_img = ImageGrab.grab()
        full_bgr = cv2.cvtColor(np.array(full_img), cv2.COLOR_RGB2BGR)

        roi = cv2.selectROI("Select YouTube Video Region (Press SPACE or ENTER when done)", full_bgr, showCrosshair=True)
        cv2.destroyWindow("Select YouTube Video Region (Press SPACE or ENTER when done)")

        x, y, w, h = roi
        if w > 50 and h > 50:
            self.bbox = (x, y, x + w, y + h)
            print(f"✅ 캡처 영역 설정 완료: {self.bbox}")
        else:
            print("⚠️ 선택이 취소되거나 영역이 너무 작아 기존 캡처 영역을 유지합니다.")

    def draw_hud(self, frame):
        if not self.show_hud:
            return frame

        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (self.out_w, 45), (15, 23, 42), -1)
        cv2.rectangle(overlay, (0, self.out_h - 45), (self.out_w, self.out_h), (15, 23, 42), -1)
        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

        status_str = "PAUSED" if self.is_paused else "LIVE CAPTURE"
        mode_str = self.mode_names.get(self.mode, "")

        top_info = f"YouTube VR [{status_str}] | Mode: {self.mode}. {mode_str}"
        if self.mode == 1:
            top_info += f" | Yaw:{int(self.yaw)} Pitch:{int(self.pitch)} FOV:{int(self.fov)}"

        cv2.putText(frame, top_info, (15, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1, cv2.LINE_AA)

        bottom_info = f"[1] 360VR  [2] 3D적청  [3] 2D단안  [4] 라이브  |  [S] 캡처영역 재선택  |  [Space] 일시정지  [Q] 종료"
        cv2.putText(frame, bottom_info, (15, self.out_h - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 230, 118), 1, cv2.LINE_AA)

        return frame

    def run(self):
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, self.out_w, self.out_h)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)

        print("\n" + "=" * 65)
        print("🔴 [유튜브 VR 실시간 라이브 캡처 플레이어 사용 방법]")
        print("  1. 브라우저(유튜브 등)에서 SBS 좌우 분할 VR/3D 영상을 재생합니다.")
        print("  2. 'S' 키를 누르면 화면 캡처 창이 열립니다.")
        print("  3. 유튜브 비디오 영역을 마우스 드래그로 사각형 선택 후 엔터를 칩니다.")
        print("  4. 모드 선택:")
        print("     - [1] 키: 360도 VR 마우스 회전 모드 (클릭 & 드래그로 시점 조작)")
        print("     - [2] 키: 3D 적청(Red-Cyan Anaglyph) 입체 모드")
        print("     - [3] 키: 단안(Monocular 2D) 일반 모니터 화면 전환 모드")
        print("     - [4] 키: 원본 라이브 캡처 비교 모드")
        print("  • 스페이스바: 일시정지 / 재생 | R키: 시점 리셋 | Q/ESC: 종료")
        print("=" * 65 + "\n")

        last_raw_frame = None

        while True:
            if not self.is_paused or last_raw_frame is None:
                raw_frame = self.capture_screen_frame()
                last_raw_frame = raw_frame

            processed_frame = self.process_captured_sbs(last_raw_frame)
            display_frame = self.draw_hud(processed_frame)

            cv2.imshow(self.window_name, display_frame)

            key = cv2.waitKey(30) & 0xFF

            if key in [ord('q'), ord('Q'), 27]:
                break
            elif key == ord(' '):
                self.is_paused = not self.is_paused
            elif key in [ord('s'), ord('S')]:
                self.select_capture_region_interactive()
            elif key == ord('1'):
                self.mode = 1
                self.map_need_update = True
                print("🔄 모드 변경: 360도 VR 마우스 드래그 회전 모드")
            elif key == ord('2'):
                self.mode = 2
                print("🔄 모드 변경: 3D 적청(Red-Cyan Anaglyph) 입체 모드")
            elif key == ord('3'):
                self.mode = 3
                print("🔄 모드 변경: 단안(Monocular 2D) 화면 모드")
            elif key == ord('4'):
                self.mode = 4
                print("🔄 모드 변경: 캡처 영역 라이브 모드")
            elif key in [ord('r'), ord('R')]:
                self.yaw, self.pitch, self.fov = 0.0, 0.0, 90.0
                self.map_need_update = True
            elif key in [ord('h'), ord('H')]:
                self.show_hud = not self.show_hud

        cv2.destroyAllWindows()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YouTube Real-Time SBS VR Capture Player")
    parser.add_argument("--width", type=int, default=1280, help="창 가로 크기")
    parser.add_argument("--height", type=int, default=720, help="창 세로 크기")

    args = parser.parse_args()

    player = YouTubeVRCapturePlayer(out_w=args.width, out_h=args.height)
    player.run()
