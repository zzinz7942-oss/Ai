"""
썸네일 자동 생성 및 텍스트 겹침 방지 오버레이 모듈 (Thumbnail Generator)
- Pillow(PIL) 기반 배경 이미지 가독성 100% 보장 렌더러
- 배경 이미지 밝기/복잡도(Luminance) 연산 후 어두운/밝은 텍스트 자동 전환
- 고정 좌표 반투명 박스(하단 또는 중앙 밴드) 오버레이로 텍스트-배경 겹침 완전 방지
"""

import os
import re
import math
from pathlib import Path
from typing import Tuple, Optional
from PIL import Image, ImageDraw, ImageFont, ImageStat

import config


def get_image_luminance(image: Image.Image, box: Tuple[int, int, int, int]) -> float:
    """
    이미지의 지정 영역(crop)의 평균 휘도(Luminance: 0.299R + 0.587G + 0.114B) 계산.
    0 (검정) ~ 255 (흰색)
    """
    crop = image.crop(box).convert("RGB")
    stat = ImageStat.Stat(crop)
    r_avg, g_avg, b_avg = stat.mean[:3]
    luminance = 0.299 * r_avg + 0.587 * g_avg + 0.114 * b_avg
    return luminance


def find_system_font(font_size: int = 36) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """한글 지원 시스템 폰트 탐색 (Windows / Linux / macOS)"""
    font_candidates = [
        "C:/Windows/Fonts/malgun.ttf",       # 맑은 고딕
        "C:/Windows/Fonts/malgunbd.ttf",     # 맑은 고딕 Bold
        "C:/Windows/Fonts/gulim.ttc",        # 굴림
        "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    ]
    for font_path in font_candidates:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, font_size)
            except Exception:
                pass
    # 폰트 파일이 없으면 기본 폰트
    return ImageFont.load_default()


def generate_thumbnail(
    bg_image_path: Path,
    title_text: str,
    output_path: Optional[Path] = None,
    target_size: Tuple[int, int] = (1200, 630),
) -> Path:
    """
    배경 이미지 위에 가독성이 보장된 텍스트 썸네일을 생성합니다.
    """
    if not output_path:
        output_path = config.IMAGE_SAVE_DIR / f"thumb_overlay_{bg_image_path.name}"

    # 1. 배경 이미지 로드 및 리사이즈/크롭
    try:
        base_img = Image.open(bg_image_path).convert("RGBA")
        base_img = base_img.resize(target_size, Image.Resampling.LANCZOS)
    except Exception as e:
        print(f"  ⚠️ 배경 이미지 로드 실패 ({e}). 단색 그래픽 배경 생성...")
        base_img = Image.new("RGBA", target_size, (15, 23, 42, 255)) # Dark navy

    width, height = target_size

    # 2. 텍스트 박스 고정 영역 설정 (하단 40% 영역)
    box_height = int(height * 0.38)
    box_y1 = height - box_height
    overlay_box = (0, box_y1, width, height)

    # 3. 해당 영역 휘도 측정
    luminance = get_image_luminance(base_img, overlay_box)

    # 4. 휘도에 따른 오버레이 박스 및 텍스트 색상 결정
    if luminance > 140:
        # 밝은 배경 -> 어두운 글자, 밝은 반투명 박스 (White glass)
        box_bg_color = (255, 255, 255, 210)   # 반투명 흰색
        text_color = (15, 23, 42, 255)         # 진한 네이비/검정
        accent_color = (225, 29, 72, 255)      # 신뢰감 있는 차분한 레드/로즈
    else:
        # 어두운 배경 -> 밝은 글자, 어두운 반투명 박스 (Dark glass)
        box_bg_color = (15, 23, 42, 210)      # 반투명 어두운 네이비
        text_color = (255, 255, 255, 255)      # 흰색
        accent_color = (56, 189, 248, 255)     # 맑은 스카이블루

    # 5. 오버레이 반투명 박스 그리기
    overlay = Image.new("RGBA", target_size, (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)

    # 하단 밴드 박스
    draw_overlay.rectangle(overlay_box, fill=box_bg_color)
    # 밴드 상단 경계선 포인트 라인
    draw_overlay.line([(0, box_y1), (width, box_y1)], fill=accent_color, width=4)

    # 이미지 결합
    composed = Image.alpha_composite(base_img, overlay)
    draw = ImageDraw.Draw(composed)

    # 6. 제목 텍스트 정제 및 줄바꿈 처리
    clean_title = re.sub(r'[^\w\s가-힣0-9.,!?%-]', '', title_text).strip()
    font_size = 42
    font = find_system_font(font_size)

    # 텍스트 2줄 나누기
    words = clean_title.split()
    line1, line2 = "", ""
    if len(words) <= 4:
        line1 = clean_title
    else:
        mid = len(words) // 2
        line1 = " ".join(words[:mid])
        line2 = " ".join(words[mid:])

    # 7. 텍스트 그리기 (중앙 정렬)
    y_start = box_y1 + 35
    if line1:
        draw.text((width // 2, y_start), line1, fill=text_color, font=font, anchor="mm")
    if line2:
        draw.text((width // 2, y_start + 52), line2, fill=accent_color if len(line2) > 5 else text_color, font=font, anchor="mm")

    # 8. 저장
    final_rgb = composed.convert("RGB")
    final_rgb.save(output_path, "JPEG", quality=92, optimize=True)
    print(f"  🎨 가독성 보장 썸네일 생성 완료: {output_path.name} (휘도: {luminance:.1f})")

    return output_path
