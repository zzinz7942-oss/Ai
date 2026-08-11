"""
설정 파일 - API 키, 사용자 톤/스타일 및 환경 변수 관리
.env 파일에서 값을 읽어옵니다.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트의 .env 파일 로드
load_dotenv(Path(__file__).parent / ".env")

# ─── Unsplash API ─────────────────────────────────────────────
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "")
UNSPLASH_API_BASE   = "https://api.unsplash.com"

# ─── OpenAI (DALL-E) - 선택 사항 ───────────────────────────────
OPENAI_API_KEY      = os.getenv("OPENAI_API_KEY", "")
DALLE_MODEL         = "dall-e-3"          # dall-e-2 or dall-e-3
DALLE_IMAGE_SIZE    = "1792x1024"         # 가로형 (썸네일 최적)

# ─── Google Blogger API ────────────────────────────────────────
BLOGGER_BLOG_ID     = os.getenv("BLOGGER_BLOG_ID", "")   # 블로그 수치 ID
GOOGLE_API_KEY      = os.getenv("GOOGLE_API_KEY", "")
GOOGLE_CLIENT_SECRETS_FILE = str(
    Path(__file__).parent / "client_secrets.json"
)
# OAuth 토큰을 저장할 경로 (최초 1회 인증 후 재사용)
GOOGLE_TOKEN_FILE   = str(Path(__file__).parent / "token.json")
BLOGGER_SCOPES      = ["https://www.googleapis.com/auth/blogger"]

# ─── 이미지 저장 경로 ──────────────────────────────────────────
IMAGE_SAVE_DIR      = Path(__file__).parent / "downloaded_images"
IMAGE_SAVE_DIR.mkdir(exist_ok=True)

# ─── 이미지 전략 선택 ──────────────────────────────────────────
# "unsplash" : Unsplash 무료 이미지 API (기본값, 무료)
# "dalle"    : DALL-E AI 이미지 생성 (OpenAI API 키 필요, 유료)
IMAGE_STRATEGY = os.getenv("IMAGE_STRATEGY", "unsplash")

# ─── 포스트 기본 설정 ──────────────────────────────────────────
POST_LABELS         = ["IT", "기술", "반도체", "트렌드"]   # 블로그 태그
POST_STATUS         = os.getenv("POST_STATUS", "DRAFT")   # "LIVE" 이면 즉시 발행, "DRAFT" 이면 임시저장

# ─── ✍️ 고유 어조 및 스타일 (작성자 고유 페르소나 설정) ─────────
WRITER_TONE = os.getenv(
    "WRITER_TONE",
    "전문적이면서도 독자가 쉽게 이해할 수 있는 친근하고 가독성 높은 어조 (~합니다/해드립니다 체)"
)
WRITER_STYLE = os.getenv(
    "WRITER_STYLE",
    "개요-원리-현황-실용팁 구조화, 핵심 인포그래픽/표 활용, 수치 데이터 기반 객관성 확보"
)
WRITER_PERSONA = os.getenv(
    "WRITER_PERSONA",
    "10년 차 테크 큐레이터이자 기술 칼럼니스트"
)

# ─── 🔥 실시간 트렌드 반영 설정 ──────────────────────────────
ENABLE_TREND_REFLECT = os.getenv("ENABLE_TREND_REFLECT", "true").lower() == "true"

# ─── 📏 검증 및 수치 하한선 설정 ─────────────────────────────
MIN_CHAR_COUNT      = int(os.getenv("MIN_CHAR_COUNT", "15000"))   # 공백 포함 15,000자 이상 강제
MIN_IMAGE_COUNT     = int(os.getenv("MIN_IMAGE_COUNT", "5"))       # 최소 이미지 5개 (썸네일 + 본문 4개)
MIN_HASHTAG_COUNT   = int(os.getenv("MIN_HASHTAG_COUNT", "8"))     # 최소 해시태그 8개
TOPIC_SIMILARITY_MAX= 70.0                                         # 최근 발행글과 주제 유사도 70% 미만

# ─── 📁 로그 및 역사 기록 경로 ────────────────────────────────
LOGS_DIR            = Path(__file__).parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)
PUBLISHED_LOG_PATH  = LOGS_DIR / "published_log.json"
USED_IMAGES_PATH    = LOGS_DIR / "used_images.json"

# ─── 💰 고CPC & 대표 카테고리 정의 ───────────────────────────
TARGET_CATEGORIES = [
    {"name": "재테크/금융", "keywords": ["주식", "ETF", "금리", "절세", "연금", "부동산", "소액투자", "청약"]},
    {"name": "IT/가전", "keywords": ["스마트폰", "노트북", "AI기술", "가전추천", "반도체", "보안", "전기차"]},
    {"name": "건강/의학", "keywords": ["영양제", "건강검진", "운동", "식단", "면역력", "만성피로", "혈당관리"]},
    {"name": "생활정보", "keywords": ["정부지원금", "환급금", "절약", "공통요금", "연말정산", "지원정책"]},
    {"name": "시사/경제", "keywords": ["물가", "환율", "고용", "소비트렌드", "금리인하", "경제전망"]}
]

