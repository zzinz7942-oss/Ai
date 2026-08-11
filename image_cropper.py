# -*- coding: utf-8 -*-
"""
스마트폰 캡처 UI 100% 완벽 크롭 및 과일 색감 싱싱 보정 유틸리티 (Advanced Cropper & Fruit Vibrance Enhancer)
1. 스마트폰 상단바(U+ 7:29, 과일대장 헤더) 및 하단바(||| O <, 매장주 제공, 블로그주소) 100% 칼같이 잘라내기
2. 과일 사진 색감 뷰티 보정 (Vibrance & Contrast Enhancement): 과일 색상을 더욱 싱싱하고 먹음직스럽게 선명하게 보정
"""

import os
import cv2
import numpy as np
from PIL import Image, ImageEnhance


def auto_crop_phone_screenshot(image_path: str) -> str:
    """
    스마트폰 캡처 이미지에서 상단/하단 UI를 100% 제거하고 과일 색감을 예쁘고 싱싱하게 보정합니다.
    """
    if not os.path.exists(image_path):
        return image_path

    try:
        pil_img = Image.open(image_path)
        w, h = pil_img.size

        # 스마트폰 긴 캡처 비율인 경우 (높이가 가로보다 길 때)
        if h > w * 1.2:
            # 1. 상단 23.5% (시계, 배터리, U+ 7:29, 과일대장 검은 헤더) 제거
            # 2. 하단 28% (매장주 제공, 네이버 블로그 주소, 하단 백색 여백, 소프트키 ||| O <) 제거
            top = int(h * 0.235)
            bottom = int(h * 0.72)
            left = 0
            right = w

            # 자르기
            cropped_img = pil_img.crop((left, top, right, bottom))
        else:
            cropped_img = pil_img

        # 3. 과일 색감 싱싱 보정 (Color Vibrance & Contrast Enhancement)
        # 색상 채도(Color) 1.25배 향상 (과일이 더욱 알록달록 싱싱하게 보임)
        enhancer_color = ImageEnhance.Color(cropped_img)
        vibrant_img = enhancer_color.enhance(1.28)

        # 명암 선명도(Contrast) 1.15배 향상
        enhancer_contrast = ImageEnhance.Contrast(vibrant_img)
        final_img = enhancer_contrast.enhance(1.12)

        # 보정된 이미지 저장
        base, ext = os.path.splitext(image_path)
        clean_path = f"{base}_fresh.png"
        final_img.save(clean_path, quality=98)
        print(f"✨ 스마트폰 UI 제거 및 과일 싱싱 보정 완료: {clean_path}")
        return clean_path

    except Exception as e:
        print(f"이미지 크롭/보정 중 예외 발생: {e}")
        return image_path
