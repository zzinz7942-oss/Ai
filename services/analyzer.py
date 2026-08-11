# -*- coding: utf-8 -*-
"""
미디어 분석 모듈 (Analyzer Service)
- 인스타그램 영상 URL 분석 (yt-dlp / 프레임 추출)
- 화면 캡처 이미지 분석 (Gemini API Vision / OpenAI Vision)
- 상품 키워드, 제품 특징, 프로그램/설치파일/소스코드 정보 추출
"""

import os
import tempfile
from PIL import Image
import cv2
import requests
import json
from config import get_config, GEMINI_API_KEY, OPENAI_API_KEY


def download_instagram_media(url: str, output_dir: str) -> dict:
    """
    yt-dlp를 사용하여 인스타그램 비디오/이미지를 다운로드하고 메타데이터를 추출합니다.
    """
    try:
        import yt_dlp
    except ImportError:
        return {"success": False, "error": "yt-dlp 패키지가 설치되지 않았습니다."}

    ydl_opts = {
        'outtmpl': os.path.join(output_dir, '%(id)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'writethumbnail': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_path = None
            thumbnail_path = None
            
            # 다운로드된 파일 찾기
            ext = info.get('ext', 'mp4')
            file_id = info.get('id', 'video')
            expected_video = os.path.join(output_dir, f"{file_id}.{ext}")
            
            if os.path.exists(expected_video):
                video_path = expected_video
            
            # 썸네일 확인
            for f in os.listdir(output_dir):
                if f.startswith(file_id) and f.endswith(('.jpg', '.png', '.webp')):
                    thumbnail_path = os.path.join(output_dir, f)
                    break

            return {
                "success": True,
                "title": info.get('title', ''),
                "description": info.get('description', ''),
                "uploader": info.get('uploader', ''),
                "video_path": video_path,
                "thumbnail_path": thumbnail_path,
            }
    except Exception as e:
        return {"success": False, "error": f"다운로드 실패: {str(e)}"}


def extract_frames_from_video(video_path: str, max_frames: int = 5) -> list[str]:
    """
    영상 파일에서 정해진 수만큼의 프레임을 이미지로 추출하여 임시 경로 리스트로 반환합니다.
    """
    if not video_path or not os.path.exists(video_path):
        return []

    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames <= 0:
        cap.release()
        return []

    step = max(1, total_frames // max_frames)
    frame_paths = []
    
    count = 0
    saved = 0
    temp_dir = os.path.dirname(video_path)

    while cap.isOpened() and saved < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        if count % step == 0:
            frame_filename = os.path.join(temp_dir, f"frame_{saved}.jpg")
            cv2.imwrite(frame_filename, frame)
            frame_paths.append(frame_filename)
            saved += 1
        count += 1

    cap.release()
    return frame_paths


def analyze_image_with_gemini(image_path: str, user_prompt: str = "") -> dict:
    """
    Google Gemini 1.5/2.0 API를 사용하여 이미지를 분석하고 상품 키워드 및 정보를 추출합니다.
    """
    api_key = get_config(GEMINI_API_KEY)
    if not api_key:
        return {"success": False, "error": "Gemini API 키가 설정되지 않았습니다."}

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')

        img = Image.open(image_path)
        
        prompt = (
            "다음 이미지를 분석하여 상품 정보 및 비디오 콘텐츠 정보를 JSON 형식으로 추출해줘.\n"
            "추출해야 할 내용:\n"
            "1. product_name: 이미지/영상에 등장하는 주요 상품명 (한국어)\n"
            "2. category: 상품 카테고리 (예: 주방용품, 전자기기, 패션 등)\n"
            "3. keywords: 쿠팡에서 해당 상품을 검색할 때 사용할 핵심 검색 키워드 3개 (리스트)\n"
            "4. summary: 상품의 주요 특징 및 소구점 요약 (2-3문장)\n"
            "5. detected_software: 영상/이미지 내에 포착된 프로그램명, 설치 파일, 소스코드 또는 도구명 (있을 경우 작성, 없으면 빈 리스트)\n\n"
            "반드시 유효한 JSON 형식으로만 응답해줘."
        )
        if user_prompt:
            prompt += f"\n추가 지시사항: {user_prompt}"

        response = model.generate_content([prompt, img])
        text = response.text.strip()
        
        # JSON 마크다운 청소
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        data = json.loads(text)
        return {"success": True, "data": data, "raw": response.text}

    except Exception as e:
        return {"success": False, "error": f"Gemini 분석 실패: {str(e)}"}


def parse_coupang_url(url: str, output_dir: str) -> dict:
    """
    쿠팡 링크(link.coupang.com 또는 coupang.com/vp/products/...)를 파싱하고
    쿠팡 API 또는 AI 비전을 통해 상품명, 키워드, 요약 정보를 추출합니다.
    """
    import re
    from config import get_config, GEMINI_API_KEY
    from services.coupang_api import search_coupang_products, create_deeplink

    # 1. 딥링크 URL 변환/추적
    final_url = url
    product_id = ""
    try:
        res = requests.head(url, allow_redirects=True, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }, timeout=10)
        final_url = res.url
    except Exception:
        pass

    # URL에서 상품 ID 추출 시도
    m = re.search(r'products/(\d+)', final_url)
    if m:
        product_id = m.group(1)

    # 2. 쿠팡 딥링크 생성 시도
    deeplink_res = create_deeplink([url])
    short_deeplink = url
    if deeplink_res.get("success") and deeplink_res.get("deeplinks"):
        short_deeplink = deeplink_res["deeplinks"][0].get("shortUrl", url)

    # 3. Gemini AI를 활용해 URL 기반 상품 정보 분석
    api_key = get_config(GEMINI_API_KEY)
    product_name = f"쿠팡 추천 상품 (ID: {product_id})" if product_id else "쿠팡 인기 추천 상품"
    keywords = ["쿠팡추천템", "인기상품", "가성비템"]
    summary = "쿠팡 파트너스 연동 추천 상품입니다."
    category = "주방용품/생활용품"

    if api_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            prompt = (
                f"다음 쿠팡 상품 URL ({final_url}) 및 상품 ID ({product_id}) 정보를 분석하여,\n"
                "가장 유력한 상품 카테고리와 마케팅 정보, 추천 키워드를 추론해 JSON으로 반환해줘.\n"
                "응답 예시: {\"product_name\": \"...\", \"category\": \"...\", \"keywords\": [\"...\", \"...\"], \"summary\": \"...\", \"detected_software\": []}"
            )
            ai_res = model.generate_content(prompt)
            text = ai_res.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            parsed_data = json.loads(text.strip())
            product_name = parsed_data.get("product_name", product_name)
            category = parsed_data.get("category", category)
            keywords = parsed_data.get("keywords", keywords)
            summary = parsed_data.get("summary", summary)
        except Exception as e:
            print(f"쿠팡 AI 분석 참고 예외: {e}")

    # 대표 안내 이미지 (Catbox 기본 썸네일)
    dummy_image = os.path.join(output_dir, "coupang_thumb.png")
    try:
        img = Image.new('RGB', (540, 540), color=(15, 23, 42))
        img.save(dummy_image)
    except Exception:
        dummy_image = None

    return {
        "success": True,
        "is_coupang": True,
        "deeplink_url": short_deeplink,
        "analyzed_image_path": dummy_image,
        "data": {
            "product_name": product_name,
            "category": category,
            "keywords": keywords,
            "summary": summary,
            "detected_software": []
        }
    }


def analyze_media_content(url_or_image_path: str, is_url: bool = True) -> dict:
    """
    통합 분석 함수: URL (인스타그램 및 쿠팡 URL 지원) 또는 파일 경로를 받아 미디어 수집 및 AI 분석 수행
    """
    temp_dir = tempfile.mkdtemp()
    target_image = None
    media_info = {}

    if is_url:
        # 쿠팡 URL 판별 (coupang.com 또는 link.coupang.com)
        if "coupang.com" in url_or_image_path.lower():
            return parse_coupang_url(url_or_image_path, temp_dir)

        # 인스타그램 URL 처리
        dl_res = download_instagram_media(url_or_image_path, temp_dir)
        if not dl_res.get("success"):
            return dl_res
        
        media_info = dl_res
        if dl_res.get("thumbnail_path"):
            target_image = dl_res["thumbnail_path"]
        elif dl_res.get("video_path"):
            frames = extract_frames_from_video(dl_res["video_path"], max_frames=1)
            if frames:
                target_image = frames[0]
    else:
        target_image = url_or_image_path

    if not target_image or not os.path.exists(target_image):
        return {"success": False, "error": "분석할 이미지를 생성하거나 찾을 수 없습니다."}

    # AI 비전 분석
    analysis_res = analyze_image_with_gemini(target_image)
    if analysis_res.get("success"):
        analysis_res["media_info"] = media_info
        analysis_res["analyzed_image_path"] = target_image

    return analysis_res
