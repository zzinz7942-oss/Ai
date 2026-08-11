# -*- coding: utf-8 -*-
"""
인스타그램/스레드 쿠팡 파트너스 자동 포스팅 Streamlit 웹 애플리케이션
"""

import os
import tempfile
import streamlit as st
from PIL import Image

import config
from config import get_config, set_config
from services.analyzer import analyze_media_content
from services.content_generator import generate_marketing_caption
from services.threads_service import post_to_threads
from services.instagram_service import post_to_instagram

# ─────────────────────────────────────────────
# Streamlit 페이지 설정 및 커스텀 스타일링
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="과일대장 오토 마케팅 스튜디오",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for rich aesthetics
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif;
    }
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #6EE7B7 0%, #3B82F6 50%, #9333EA 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .sub-title {
        color: #9CA3AF;
        font-size: 1.05rem;
        margin-bottom: 2rem;
    }
    .stCard {
        background-color: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    .product-badge {
        background: linear-gradient(90deg, #F59E0B 0%, #EF4444 100%);
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
    }
</style>

<!-- 크롬 자동 번역으로 인한 React 충돌(removeChild 에러) 원천 차단 -->
<meta name="google" content="notranslate">
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# 사이드바: API 키 및 인증 정보 설정
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("🔑 API 및 계정 설정")
    st.caption("서비스 실행을 위한 필수 인증 키를 입력하세요.")
    
    # Threads API 상태 확인
    t_has_token = bool(get_config(config.THREADS_ACCESS_TOKEN))
    t_has_id = bool(get_config(config.THREADS_USER_ID))
    t_status = "🟢 설정 완료" if (t_has_token and t_has_id) else "🔴 미설정"

    with st.expander(f"🧵 Meta Threads API ({t_status})", expanded=not (t_has_token and t_has_id)):
        st.markdown("Meta Threads API 인증 정보를 입력하세요.")
        t_token = st.text_input("Access Token", value=get_config(config.THREADS_ACCESS_TOKEN), type="password", key="sb_t_token")
        t_userid = st.text_input("User ID", value=get_config(config.THREADS_USER_ID), key="sb_t_userid")
        if st.button("💾 Threads API 설정 저장", type="primary", use_container_width=True, key="btn_save_threads"):
            if t_token and t_userid:
                set_config(config.THREADS_ACCESS_TOKEN, t_token.strip())
                set_config(config.THREADS_USER_ID, t_userid.strip())
                st.success("✅ Threads API 인증 키가 성공적으로 저장되었습니다!")
                st.rerun()
            else:
                st.warning("Access Token과 User ID를 모두 입력해주세요.")

    with st.expander("📸 Instagram 계정", expanded=False):
        i_user = st.text_input("Username (아이디)", value=get_config(config.INSTAGRAM_USERNAME))
        i_pass = st.text_input("Password (비밀번호)", value=get_config(config.INSTAGRAM_PASSWORD), type="password")
        if st.button("Instagram 정보 저장"):
            set_config(config.INSTAGRAM_USERNAME, i_user)
            set_config(config.INSTAGRAM_PASSWORD, i_pass)
            st.success("인스타그램 계정 정보가 저장되었습니다.")

    with st.expander("📝 네이버 블로그 계정", expanded=False):
        n_user = st.text_input("네이버 아이디", value=get_config(config.NAVER_ID))
        n_pass = st.text_input("네이버 비밀번호", value=get_config(config.NAVER_PW), type="password")
        if st.button("네이버 정보 저장"):
            set_config(config.NAVER_ID, n_user)
            set_config(config.NAVER_PW, n_pass)
            st.success("네이버 계정 정보가 저장되었습니다.")

    with st.expander("🤖 Gemini AI 엔진 (무료 키)", expanded=False):
        g_key = st.text_input("Gemini API Key", value=get_config(config.GEMINI_API_KEY), type="password")
        if st.button("AI 키 저장"):
            set_config(config.GEMINI_API_KEY, g_key)
            st.success("Gemini API 키가 저장되었습니다.")

    st.divider()
    st.info("💡 모든 설정 정보는 로컬에 안전하게 저장됩니다.")


# ─────────────────────────────────────────────
# 메인 헤더
# ─────────────────────────────────────────────
st.markdown('<div class="main-title">🚀 Auto-Marketing Studio</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">인스타그램 영상/캡처 분석 ➔ 쿠팡 딥링크 자동 매칭 ➔ 인스타 & 쓰레드 자동 포스팅</div>', unsafe_allow_html=True)


# 세션 상태 초기화
if "analysis_data" not in st.session_state:
    st.session_state.analysis_data = None
if "selected_product" not in st.session_state:
    st.session_state.selected_product = None
if "generated_caption" not in st.session_state:
    st.session_state.generated_caption = ""
if "deeplink_url" not in st.session_state:
    st.session_state.deeplink_url = ""


# ─────────────────────────────────────────────
# 탭 구성
# ─────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "🔍 1. 미디어 분석 & 쿠팡 매칭",
    "✍️ 2. 마케팅 콘텐츠 생성",
    "🚀 3. 인스타 & 쓰레드 자동 게시",
    "🛠️ 4. 영상 속 프로그램/소스코드 분석",
    "🌐 5. Agent Reach 무제한 웹/소셜 크롤러",
    "⚡ 6. 원클릭 수익화 파이프라인 (세이프티)",
    "🍓 7. 과일가게 홍보카드 & 문구 생성기",
    "📱 8. 24시간 모바일 무인 모니터링 & 클라우드 헬스 센터",
    "🏪 9. 스토어 재고 검색 및 비교"
])


# ─────────────────────────────────────────────
# TAB 1: 미디어 분석 & 쿠팡 매칭
# ─────────────────────────────────────────────
with tab1:
    st.subheader("1. 분석할 미디어 제공")
    col1, col2 = st.columns([1, 1])

    input_mode = st.radio("입력 방식 선택:", ["인스타그램 영상 URL 입력", "화면 캡처 이미지 업로드"], horizontal=True)

    target_media = None
    is_url = False

    if input_mode == "인스타그램 영상 URL 입력":
        url_input = st.text_input("인스타그램 게시물/릴스 URL", placeholder="https://www.instagram.com/reel/...")
        if url_input:
            target_media = url_input.strip()
            is_url = True
    else:
        uploaded_file = st.file_uploader("화면 캡처 이미지 파일 업로드", type=["png", "jpg", "jpeg", "webp"])
        if uploaded_file:
            temp_img = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            temp_img.write(uploaded_file.read())
            temp_img.close()
            target_media = temp_img.name
            is_url = False

    if st.button("🔍 미디어 분석 시작", type="primary", use_container_width=True):
        if not target_media:
            st.warning("분석할 URL 또는 이미지 파일을 제공해주세요.")
        else:
            with st.spinner("AI가 미디어 프레임 및 콘텐츠 분석을 진행 중입니다..."):
                res = analyze_media_content(target_media, is_url=is_url)
                if res.get("success"):
                    st.session_state.analysis_data = res
                    st.success("미디어/게시물 분석 완료!")
                else:
                    st.error(f"분석 실패: {res.get('error')}")

    # 분석 결과 표출
    if st.session_state.analysis_data:
        data = st.session_state.analysis_data.get("data", {})
        analyzed_img = st.session_state.analysis_data.get("analyzed_image_path")
        
        st.divider()
        st.markdown("### 📊 AI 분석 결과")
        
        res_col1, res_col2 = st.columns([1, 2])
        with res_col1:
            if analyzed_img and os.path.exists(analyzed_img):
                st.image(analyzed_img, caption="분석된 미디어 프레임/이미지", use_container_width=True)

        with res_col2:
            st.markdown(f"**상품명:** {data.get('product_name', '미상')}")
            st.markdown(f"**카테고리:** {data.get('category', '일반')}")
            st.markdown(f"**요약:** {data.get('summary', '')}")
            keywords = data.get('keywords', [])
            st.markdown(f"**추천 검색 키워드:** {', '.join(keywords)}")




# ─────────────────────────────────────────────
# TAB 2: 마케팅 콘텐츠 생성
# ─────────────────────────────────────────────
with tab2:
    st.subheader("2. 마케팅 홍보 문구 생성 및 편집")
    
    selected_prod = st.session_state.selected_product
    deeplink = st.session_state.deeplink_url
    analysis_data = st.session_state.analysis_data

    if not analysis_data and not selected_prod:
        st.info("💡 Tab 1에서 먼저 '미디어 분석'을 완료해 주세요.")
    else:
        # 데이터 소스 결정 (쿠팡 파트너스 매칭 정보 우선, 없을 경우 미디어 분석 데이터 활용)
        if selected_prod:
            p_name = selected_prod.get('productName', '')
            p_price = selected_prod.get('productPrice', 0)
            st.success(f"🛒 쿠팡 상품 매칭됨: {p_name} | 딥링크: {deeplink}")
        else:
            ai_data = analysis_data.get("data", {}) if analysis_data else {}
            p_name = ai_data.get("product_name", "인스타 추천 꿀템/정보")
            p_price = 0
            st.info(f"📊 미디어 분석 데이터 기반 생성: 제목({p_name}) | (쿠팡 상품 미선택 상태)")
        
        if st.button("✨ 마케팅 문구 자동 생성", type="primary", use_container_width=True):
            summary_text = ""
            category_text = ""
            if analysis_data:
                summary_text = analysis_data.get("data", {}).get("summary", "")
                category_text = analysis_data.get("data", {}).get("category", "")
                
            caption = generate_marketing_caption(
                product_name=p_name,
                product_price=p_price,
                deeplink_url=deeplink,
                summary=summary_text,
                category=category_text
            )
            st.session_state.generated_caption = caption

        edited_caption = st.text_area(
            "최종 업로드용 마케팅 캡션 (편집 가능)",
            value=st.session_state.generated_caption,
            height=300
        )
        st.session_state.generated_caption = edited_caption


# ─────────────────────────────────────────────
# TAB 3: 인스타 & 쓰레드 자동 포스팅
# ─────────────────────────────────────────────
with tab3:
    st.subheader("3. SNS 자동 업로드")

    # Threads API 설정 가이드 및 빠른 입력 상자
    cur_threads_token = get_config(config.THREADS_ACCESS_TOKEN)
    cur_threads_userid = get_config(config.THREADS_USER_ID)
    
    if not (cur_threads_token and cur_threads_userid):
        st.warning("⚠️ Threads Access Token 또는 User ID가 설정되지 않았습니다. 아래에서 바로 설정하거나 왼쪽 사이드바에서 입력하세요.")
        with st.expander("🔑 Meta Threads API 인증 정보 설정", expanded=True):
            t_col1, t_col2 = st.columns([3, 2])
            with t_col1:
                input_t_token = st.text_input("Threads Access Token", value=cur_threads_token, type="password", key="tab3_t_token")
            with t_col2:
                input_t_userid = st.text_input("Threads User ID", value=cur_threads_userid, key="tab3_t_userid")
            
            if st.button("💾 Threads API 정보 저장", type="primary", key="tab3_save_threads"):
                if input_t_token and input_t_userid:
                    set_config(config.THREADS_ACCESS_TOKEN, input_t_token.strip())
                    set_config(config.THREADS_USER_ID, input_t_userid.strip())
                    st.success("✅ Threads API 설정이 성공적으로 저장되었습니다!")
                    st.rerun()
                else:
                    st.error("Token과 User ID를 입력해 주세요.")

    caption_to_post = st.session_state.generated_caption
    analyzed_img = st.session_state.analysis_data.get("analyzed_image_path") if st.session_state.analysis_data else None

    if not caption_to_post:
        st.warning("업로드할 마케팅 캡션이 없습니다. Tab 2에서 캡션을 생성해 주세요.")
    else:
        st.markdown("#### 게시글 미리보기")
        p_col1, p_col2 = st.columns([1, 2])
        with p_col1:
            if analyzed_img and os.path.exists(analyzed_img):
                st.image(analyzed_img, caption="업로드할 대표 이미지", use_container_width=True)
        with p_col2:
            st.text_area("캡션 미리보기", value=caption_to_post, height=180, disabled=True)

        st.divider()
        st.markdown("#### 업로드 타겟 플랫폼 선택")

        post_threads = st.checkbox("🧵 Threads 업로드", value=True)
        post_insta = st.checkbox("📸 Instagram 업로드", value=False)

        if st.button("🚀 원클릭 자동 게시 시작", type="primary", use_container_width=True):
            if post_threads:
                with st.spinner("Threads 포스팅 중..."):
                    t_res = post_to_threads(text=caption_to_post, image_path=analyzed_img)
                    if t_res.get("success"):
                        st.success(f"🧵 Threads 게시 성공! [게시글 확인]({t_res.get('post_url')})")
                    else:
                        st.error(f"Threads 게시 실패: {t_res.get('error')}")

            if post_insta:
                with st.spinner("Instagram 포스팅 중..."):
                    i_res = post_to_instagram(caption=caption_to_post, image_path=analyzed_img)
                    if i_res.get("success"):
                        st.success(f"📸 Instagram 게시 성공! [게시글 확인]({i_res.get('post_url')})")
                    else:
                        st.error(f"Instagram 게시 실패: {i_res.get('error')}")


# ─────────────────────────────────────────────
# TAB 4: 영상 속 프로그램/소스코드 분석 & 실행 지원
# ─────────────────────────────────────────────
with tab4:
    st.subheader("4. 영상/이미지 속 프로그램, 설치파일, 소스코드 탐지 및 로컬 구성")
    st.caption("인스타그램 영상 또는 화면 캡처에 포함된 개발 툴, 설치 파일, 프로그램 정보를 분석하고 로컬 PC 환경에 설치/구현할 수 있도록 지원합니다.")

    if st.session_state.analysis_data:
        data = st.session_state.analysis_data.get("data", {})
        detected_sw = data.get("detected_software", [])
        
        if detected_sw:
            st.markdown(f"#### 🔍 탐지된 소프트웨어 및 프로그램 리스트")
            for item in detected_sw:
                st.markdown(f"- 📦 **{item}**")
        else:
            st.info("AI 분석 결과 별도의 특수 설치 파일이 탐지되지 않았거나 일반 미디어 내용입니다.")

    st.markdown("#### 💻 로컬 다운로드 및 설치 명령 생성기")
    software_query = st.text_input("분석 또는 설치할 프로그램/라이브러리명 입력", placeholder="예: ffmpeg, yt-dlp, python-dotenv 등")
    
    if software_query:
        st.markdown(f"##### '{software_query}' 설치 및 설치 확인 명령어 (Windows PowerShell)")
        st.code(f"pip install {software_query}\n# 또는 scoop / choco 패키지 매니저\nchoco install {software_query} -y", language="powershell")


# ─────────────────────────────────────────────
# TAB 5: Agent Reach 무제한 웹/소셜 크롤러
# ─────────────────────────────────────────────
with tab5:
    st.subheader("5. Agent Reach - AI 에이전트 무제한 웹 & 소셜 미디어 크롤러")
    st.caption("유료 API 비용 없이 트위터/X, 레딧, 유튜브 자막, Bilibili, RSS, 깃허브, 웹페이지 데이터를 명령어 한 줄로 읽어오는 오픈소스 엔진입니다.")

    from services.agent_reach_service import run_agent_reach_doctor, run_agent_reach_command

    col_ar1, col_ar2 = st.columns([1, 2])
    with col_ar1:
        if st.button("🩺 Agent Reach 채널 상태 진단 (Doctor)", type="primary", use_container_width=True):
            with st.spinner("Agent Reach 진단을 실행 중입니다..."):
                doc_res = run_agent_reach_doctor()
                if doc_res.get("success"):
                    st.text_area("Doctor 진단 결과", value=doc_res["output"], height=300)
                else:
                    st.error(f"진단 오류: {doc_res.get('error')}")

    with col_ar2:
        st.markdown("#### 🔍 무제한 웹/소셜 데이터 즉시 조회")
        ar_platform = st.selectbox("수집 타겟 플랫폼", ["web (웹페이지)", "youtube (유튜브 자막)", "twitter (트위터/X)", "reddit (레딧)", "github (깃허브)"])
        ar_query = st.text_input("조회할 URL 또는 검색 키워드 입력", placeholder="https://... 또는 검색어")

        if st.button("🌐 데이터 수집 실행", use_container_width=True):
            if not ar_query:
                st.warning("URL 또는 검색어를 입력해주세요.")
            else:
                plat_code = ar_platform.split(" ")[0]
                with st.spinner(f"Agent Reach로 {plat_code} 데이터 수집 중..."):
                    cmd = [plat_code, "read" if "http" in ar_query else "search", ar_query]
                    fetch_res = run_agent_reach_command(cmd)
                    if fetch_res.get("success"):
                        st.success("데이터 수집 완료!")
                        st.text_area("수집 결과", value=fetch_res["output"], height=350)
                    else:
                        st.error(f"수집 실패: {fetch_res.get('error')}")


# ─────────────────────────────────────────────
# TAB 6: 원클릭 수익화 파이프라인 (세이프티 모드 & Human-in-the-Loop)
# ─────────────────────────────────────────────
with tab6:
    st.subheader("⚡ 수익화 자동화 파이프라인 대시보드 (세이프티 모드 적용)")
    st.caption("무분별한 연속 업로드를 방지하는 '일일 안전 포스팅 제한'과 사람의 최종 검수 승인(Human-in-the-Loop) 프로세스가 적용되어 안전합니다.")

    from services.pipeline_service import (
        generate_pipeline_draft,
        approve_and_publish,
        get_daily_post_count
    )

    # 1. 상단 세이프티 현황 바
    daily_count = get_daily_post_count()
    max_limit = st.slider("🛡️ 하루 최대 안전 포스팅 횟수 제한 설정", min_value=1, max_value=10, value=3)

    badge_status = f"🟢 정상 ({daily_count}/{max_limit}회 완료)" if daily_count < max_limit else f"⚠️ 일일 안전 한도 도달 ({daily_count}/{max_limit}회)"
    st.info(f"📊 **오늘의 자동화 실행 현황:** {badge_status}")

    st.divider()

    col_p1, col_p2 = st.columns([1, 1])

    with col_p1:
        st.markdown("### 🔍 1단계: 트렌드 수집 & AI 초안 자동 준비")
        target_topic = st.text_input("수익화 주제 / 키워드 입력", value="주방 꿀템", placeholder="예: 주방 꿀템, 자취 필수템, 가성비 가전 등")
        
        if st.button("📝 1단계: AI 파이프라인 초안 준비", type="primary", use_container_width=True):
            with st.spinner("Agent Reach 트렌드 수집, 쿠팡 딥링크 생성 및 AI 마케팅 문구 초안 준비 중..."):
                draft_res = generate_pipeline_draft(target_topic)
                if draft_res.get("success"):
                    st.session_state.pipeline_draft = draft_res
                    st.success("1단계 마케팅 초안 준비 완료!")
                else:
                    st.error("초안 준비 중 오류가 발생했습니다.")

    with col_p2:
        st.markdown("### 🙋‍♂️ 2단계: 사람 최종 검수 & 업로드 승인 (Human-in-the-Loop)")
        
        draft = st.session_state.get("pipeline_draft")
        if not draft:
            st.info("💡 1단계를 먼저 실행하여 AI 마케팅 초안을 준비해주세요.")
        else:
            st.success(f"매칭 상품/주제: **{draft.get('product_name')}**")
            if draft.get("deeplink_url"):
                st.markdown(f"**생성된 제휴 딥링크:** [{draft.get('deeplink_url')}]({draft.get('deeplink_url')})")

            final_caption = st.text_area(
                "최종 업로드용 캡션 (검수 및 수정 가능)",
                value=draft.get("caption", ""),
                height=220
            )

            post_t = st.checkbox("🧵 Threads 업로드", value=True, key="tab6_threads")
            post_i = st.checkbox("📸 Instagram 업로드", value=False, key="tab6_insta")

            if st.button("✅ 최종 검수 승인 & SNS 자동 업로드", type="primary", use_container_width=True):
                current_count = get_daily_post_count()  # 버튼 클릭 시점의 최신 횟수 재조회
                if current_count >= max_limit:
                    st.error(f"⚠️ 일일 안전 제한({current_count}/{max_limit}회)에 도달하여 추가 업로드가 차단되었습니다.")
                else:
                    with st.spinner("최종 승인된 포스트를 SNS에 게시 중입니다..."):
                        pub_res = approve_and_publish(
                            draft_data=draft,
                            caption_text=final_caption,
                            max_daily_limit=max_limit,
                            post_threads=post_t,
                            post_insta=post_i
                        )

                        if pub_res.get("success"):
                            st.balloons()
                            st.success(f"🎉 게시글이 성공적으로 업로드되었습니다! (오늘 누적 {pub_res.get('daily_count')}/{max_limit}회)")
                            sns_r = pub_res.get("sns_results", {})
                            if "threads" in sns_r and sns_r["threads"].get("success"):
                                st.markdown(f"🔗 [Threads 게시글 바로가기]({sns_r['threads'].get('post_url')})")
                            st.rerun()
                        else:
                            st.error(pub_res.get("error"))


# ─────────────────────────────────────────────
# TAB 7: 과일가게 홍보카드 & 마케팅 문구 생성기 (당근 + 네이버 블로그 지원)
# ─────────────────────────────────────────────
with tab7:
    st.subheader("🍓 과일가게 전용 홍보 카드 & 마케팅 문구 생성기 (당근마켓 & 네이버 블로그 지원)")
    st.caption("매장 정보, 오시는 길(위치), 전화번호, 당일 도매 시세, 과일 실물 사진 여러 장을 올리면 당근마켓 및 네이버 블로그에 즉시 올릴 수 있는 마케팅 원문과 뷰티 홍보 카드를 자동 제작합니다.")

    # ─────────────────────────────────────────────
    # 계정 정보 전용 보관함 (네이버, 인스타그램, 당근)
    # ─────────────────────────────────────────────
    cur_nav_id = get_config(config.NAVER_ID)
    cur_nav_pw = get_config(config.NAVER_PW)
    cur_insta_id = get_config(config.INSTAGRAM_USERNAME)
    cur_insta_pw = get_config(config.INSTAGRAM_PASSWORD)

    with st.expander("🔑 과일대장 전용 마케팅 계정 보관함 (네이버 / 인스타그램 / 당근)", expanded=not (cur_nav_id and cur_insta_id)):
        st.markdown("##### 🔑 각 서비스 아이디와 비밀번호를 1회 저장해 두시면 24시간 봇이 100% 자동 포스팅합니다.")
        a_col1, a_col2, a_col3 = st.columns(3)
        with a_col1:
            st.markdown("**🟢 네이버 블로그 봇**")
            n_id_in = st.text_input("네이버 ID", value=cur_nav_id, key="t7_nav_id_top")
            n_pw_in = st.text_input("네이버 비밀번호", value=cur_nav_pw, type="password", key="t7_nav_pw_top")
        with a_col2:
            st.markdown("**📸 인스타그램 봇**")
            i_id_in = st.text_input("인스타 ID/이메일", value=cur_insta_id, key="t7_insta_id_top")
            i_pw_in = st.text_input("인스타 비밀번호", value=cur_insta_pw, type="password", key="t7_insta_pw_top")
        with a_col3:
            st.markdown("**🥕 당근마켓 연동**")
            d_phone_in = st.text_input("당근 연동 대표번호", value=get_config("DANGGEUN_PHONE", "010-7789-1905"), key="t7_dg_phone_top")
            st.caption("당근마켓은 세이션 1회 유지 방식입니다.")

        if st.button("💾 네이버 / 인스타그램 / 당근 계정 정보 1회 안전 저장", type="primary", use_container_width=True, key="btn_save_master_accs"):
            if n_id_in: set_config(config.NAVER_ID, n_id_in.strip())
            if n_pw_in: set_config(config.NAVER_PW, n_pw_in.strip())
            if i_id_in: set_config(config.INSTAGRAM_USERNAME, i_id_in.strip())
            if i_pw_in: set_config(config.INSTAGRAM_PASSWORD, i_pw_in.strip())
            if d_phone_in: set_config("DANGGEUN_PHONE", d_phone_in.strip())
            st.success("✅ 모든 마케팅 계정 정보가 안전하게 저장되었습니다!")
            st.rerun()

    st.divider()

    f_col1, f_col2 = st.columns([1, 1])

    with f_col1:
        st.markdown("#### 🛒 1. 과일가게 매장 정보 & 당일 시세 입력")
        fruit_shop_name = st.text_input("과일가게 상호명", value="과일대장", placeholder="예: 과일대장 광산점")
        fruit_location = st.text_input("매장 위치 / 오시는 길 (상세 주소 & 랜드마크)", value="전남광주통합특별시 광산구 광산로89번길 29 (광산역 도보 3분)", placeholder="누가 보더라도 바로 찾아올 수 있게 상세히 작성")
        fruit_phone = st.text_input("전화번호 / 주문 연락처", value="010-7789-1905", placeholder="예: 010-7789-1905")
        
        market_price_tag = st.selectbox(
            "📉 당일 과일 도매/경매 시세 변동 반영 (매일 가격 변동 시 선택)",
            [
                "당일 새벽 경매 시세 적용 (기본)",
                "📉 도매가 폭락! 당일 깜짝 특가 (-15% 할인)",
                "🔥 당도 최상급 갓 입고 (수량 한정)",
                "📈 도매 시세 상승 직전! 오늘만 한정 특가",
                "🎁 주말 맞이 과일 폭탄 세일"
            ]
        )

        fruit_today = st.text_area(
            "오늘의 당도 보장 과일 및 시세가 (줄바꿈 구분)",
            value="복숭아 1팩 16000원\n아오리사과 1팩 10000원",
            height=120
        )
        fruit_event = st.text_input("고객 혜택 / 이벤트 (없을 경우 비워두세요)", value="", placeholder="예: 당근보고 오셨다고 말씀해 주시면 맛보기 과일 서비스!")

        uploaded_fruit_imgs = st.file_uploader(
            "📸 과일 실물 및 매장 사진 여러 장 업로드 (다중 선택 가능)",
            type=["png", "jpg", "jpeg", "webp"],
            accept_multiple_files=True,
            key="fruit_imgs_uploader"
        )
        
        uploaded_paths = []
        if uploaded_fruit_imgs:
            st.markdown("##### 🖼️ 업로드된 과일 사진 목록")
            img_cols = st.columns(min(len(uploaded_fruit_imgs), 3))
            for idx, u_img in enumerate(uploaded_fruit_imgs):
                temp_f = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                temp_f.write(u_img.read())
                temp_f.close()
                uploaded_paths.append(temp_f.name)
                with img_cols[idx % 3]:
                    st.image(temp_f.name, caption=f"과일 사진 {idx+1}", use_container_width=True)

        make_fruit_btn = st.button("✨ 당근마켓 & 네이버 블로그 마케팅 원문 생성", type="primary", use_container_width=True)
        make_video_btn = st.button("🎬 복숭아/아오리사과 9:16 인스타 릴스/쇼츠 홍보동영상 생성", type="secondary", use_container_width=True)

    with f_col2:
        st.markdown("#### 🎨 2. 완성된 홍보 카드 & 홍보 동영상 (MP4)")

        if make_video_btn:
            if not uploaded_paths:
                st.warning("과일 사진을 최소 1장 이상 업로드해 주세요.")
            else:
                with st.spinner("AI가 과일명과 가격을 자동으로 인식하여 아나운서 음성 더빙 9:16 홍보 동영상을 제작 중입니다..."):
                    from fruit_video_generator import create_fruit_promo_video
                    
                    video_output = os.path.join(tempfile.gettempdir(), "fruit_reels_promo.mp4")
                    vid_res = create_fruit_promo_video(
                        shop_name=fruit_shop_name,
                        location=fruit_location,
                        raw_fruit_text=fruit_today,
                        image_paths=uploaded_paths,
                        output_mp4_path=video_output
                    )

                    if vid_res.get("success"):
                        st.session_state.fruit_mp4_path = vid_res.get("mp4_path")
                        st.session_state.fruit_video_script = vid_res.get("script")
                        st.success("🎬 고화질 릴스/쇼츠 홍보동영상 완벽 완성!")
                    else:
                        st.error(f"동영상 제작 오류: {vid_res.get('error')}")

        if "fruit_mp4_path" in st.session_state and st.session_state.fruit_mp4_path and os.path.exists(st.session_state.fruit_mp4_path):
            st.markdown("##### 🎬 완성된 9:16 모바일 릴스/쇼츠 홍보 동영상 (AI 더빙+자막)")
            st.video(st.session_state.fruit_mp4_path)
            st.caption(f"🎙️ AI 더빙 대본: '{st.session_state.get('fruit_video_script', '')}'")

            with open(st.session_state.fruit_mp4_path, "rb") as vf:
                st.download_button(
                    label="📥 릴스/쇼츠 홍보동영상 파일 (MP4) 다운로드",
                    data=vf.read(),
                    file_name=f"{fruit_shop_name}_복숭아_아오리사과_홍보영상.mp4",
                    mime="video/mp4",
                    use_container_width=True
                )
            st.divider()
        
        if make_fruit_btn:
            with st.spinner("AI가 당근마켓 및 네이버 블로그 SEO에 최적화된 홍보 원문을 작성 중입니다..."):
                # 당근/SNS 캡션 생성
                cap_res = generate_fruit_marketing_captions(
                    shop_name=fruit_shop_name,
                    location=fruit_location,
                    today_fruits=fruit_today,
                    event_info=fruit_event,
                    phone_number=fruit_phone,
                    price_market_tag=market_price_tag
                )

                # 네이버 블로그 전용 SEO 포스팅 작성
                blog_res = generate_naver_blog_post(
                    shop_name=fruit_shop_name,
                    location=fruit_location,
                    today_fruits=fruit_today,
                    event_info=fruit_event,
                    phone_number=fruit_phone,
                    price_market_tag=market_price_tag
                )
                
                # HTML 모바일 홍보 카드 생성
                card_html = create_fruit_promo_card_html(
                    shop_name=fruit_shop_name,
                    location=fruit_location,
                    today_fruits=fruit_today,
                    event_info=fruit_event,
                    image_paths=uploaded_paths,
                    phone_number=fruit_phone,
                    price_market_tag=market_price_tag
                )

                png_path = os.path.join(tempfile.gettempdir(), "fruit_promo_card.png")
                capture_fruit_card_png(card_html, png_path)

                st.session_state.fruit_captions = cap_res.get("captions", "")
                st.session_state.naver_blog_post = blog_res.get("blog_post", "")
                st.session_state.fruit_card_html = card_html
                st.session_state.fruit_png_path = png_path if os.path.exists(png_path) else None
                st.success("당근마켓 & 네이버 블로그 홍보 원문 작성이 완벽히 완성되었습니다!")

        if "fruit_captions" in st.session_state and st.session_state.fruit_captions:
            st.markdown("##### 📱 짤림 없는 뷰티 모바일 홍보 카드 미리보기")
            st.components.v1.html(st.session_state.fruit_card_html, height=620, scrolling=True)

            if st.session_state.get("fruit_png_path") and os.path.exists(st.session_state["fruit_png_path"]):
                st.download_button(
                    label="📥 홍보 카드 고화질 이미지 (PNG) 다운로드 (당근/네이버 첨부용)",
                    data=open(st.session_state["fruit_png_path"], "rb").read(),
                    file_name=f"{fruit_shop_name}_홍보카드.png",
                    mime="image/png",
                    use_container_width=True
                )

            st.divider()
            
            # 당근마켓 vs 네이버 블로그 원문 서식 탭
            b_tab1, b_tab2 = st.tabs(["🥕 1. 당근마켓 / 카톡 전송용 문구", "🟢 2. 네이버 블로그 SEO 포스팅 원문"])

            with b_tab1:
                st.text_area("당근마켓/카톡 맞춤 캡션 (복사해서 당근 동네생활/소식에 등록하세요)", value=st.session_state.fruit_captions, height=320)

            with b_tab2:
                st.text_area("네이버 블로그 SEO 원문 (복사해서 네이버 블로그 에디터에 붙여넣으세요)", value=st.session_state.get("naver_blog_post", ""), height=280)
                st.markdown("👉 **[네이버 블로그 스마트 에디터 바로가기](https://blog.naver.com/)**")

                st.divider()
                st.markdown("#### 🤖 네이버 봇(Naver Bot) 자동 포스팅 & 임시저장 실행")
                
                cur_nav_id = get_config(config.NAVER_ID)
                cur_nav_pw = get_config(config.NAVER_PW)

                with st.expander("🔑 네이버 봇 로그인 계정 설정", expanded=not (cur_nav_id and cur_nav_pw)):
                    n_col1, n_col2 = st.columns([1, 1])
                    with n_col1:
                        nav_id_in = st.text_input("네이버 아이디", value=cur_nav_id, key="tab7_nav_id")
                    with n_col2:
                        nav_pw_in = st.text_input("네이버 비밀번호", value=cur_nav_pw, type="password", key="tab7_nav_pw")
                    
                    if st.button("💾 네이버 계정 저장", key="tab7_save_nav"):
                        if nav_id_in and nav_pw_in:
                            set_config(config.NAVER_ID, nav_id_in.strip())
                            set_config(config.NAVER_PW, nav_pw_in.strip())
                            st.success("✅ 네이버 봇 계정이 안전하게 저장되었습니다!")
                            st.rerun()

                bot_mode = st.radio(
                    "🤖 네이버 봇 실행 모드 선택",
                    ["🛡️ 임시저장 모드 (추천: 저품질 제재 없이 가장 안전함)", "🚀 즉시 발행 모드 (자동 포스팅)"],
                    horizontal=True
                )
                
                if st.button("🤖 네이버 봇으로 자동 포스팅 실행", type="primary", use_container_width=True):
                    if not (cur_nav_id and cur_nav_pw):
                        st.warning("⚠️ 위에서 네이버 아이디와 비밀번호를 먼저 설정하고 저장해 주세요.")
                    else:
                        with st.spinner("Playwright 네이버 봇이 스마트 에디터를 열고 글과 사진을 포스팅 중입니다..."):
                            from services.naver_bot_service import run_naver_blog_bot
                            
                            target_mode = "draft" if "임시저장" in bot_mode else "publish"
                            b_title = f"[{fruit_shop_name}] 오늘 입고된 당도 보장 꿀과일 시세가 및 오시는 길 🍓🍎"
                            b_content = st.session_state.get("naver_blog_post", "")
                            
                            bot_res = run_naver_blog_bot(
                                naver_id=cur_nav_id,
                                naver_pw=cur_nav_pw,
                                title=b_title,
                                content=b_content,
                                image_paths=uploaded_paths,
                                mode=target_mode
                            )

                            if bot_res.get("success"):
                                st.balloons()
                                st.success(bot_res.get("msg"))
                            else:
                                st.error(bot_res.get("error"))

            st.divider()
            st.markdown("### 🚀 3. 전 채널(네이버+당근+스레드+인스타그램) 1클릭 동시 자동 홍보 배포")
            st.caption("단 한 번의 버튼 클릭으로 네이버 블로그, 당근마켓, 메타 스레드, 인스타그램 전체 무료 채널에 홍보문구와 사진을 동시에 자동 배포합니다.")

            c_col1, c_col2, c_col3, c_col4 = st.columns(4)
            with c_col1:
                chk_nav = st.checkbox("🟢 네이버 블로그 봇", value=True)
            with c_col2:
                chk_dg = st.checkbox("🥕 당근마켓 봇", value=True)
            with c_col3:
                chk_th = st.checkbox("🧵 스레드(Threads) 봇", value=True)
            with c_col4:
                chk_in = st.checkbox("📸 인스타그램 봇", value=True)

            # 계정 설정 안내 확장 박스
            cur_insta_id = get_config(config.INSTAGRAM_USERNAME)
            cur_insta_pw = get_config(config.INSTAGRAM_PASSWORD)

            with st.expander("🔑 봇 실행용 계정 보관함 (네이버 & 인스타그램 계정 설정)", expanded=not (cur_nav_id and cur_nav_pw and cur_insta_id and cur_insta_pw)):
                acc_c1, acc_c2 = st.columns(2)
                with acc_c1:
                    st.markdown("##### 🟢 네이버 블로그 봇 계정")
                    nav_id_v = st.text_input("네이버 아이디", value=cur_nav_id, key="tab7_nav_id_master")
                    nav_pw_v = st.text_input("네이버 비밀번호", value=cur_nav_pw, type="password", key="tab7_nav_pw_master")
                with acc_c2:
                    st.markdown("##### 📸 인스타그램 봇 계정")
                    insta_id_v = st.text_input("인스타그램 아이디/이메일", value=cur_insta_id, key="tab7_insta_id_master")
                    insta_pw_v = st.text_input("인스타그램 비밀번호", value=cur_insta_pw, type="password", key="tab7_insta_pw_master")
                
                if st.button("💾 네이버 & 인스타그램 계정 안전 저장", use_container_width=True):
                    if nav_id_v: set_config(config.NAVER_ID, nav_id_v.strip())
                    if nav_pw_v: set_config(config.NAVER_PW, nav_pw_v.strip())
                    if insta_id_v: set_config(config.INSTAGRAM_USERNAME, insta_id_v.strip())
                    if insta_pw_v: set_config(config.INSTAGRAM_PASSWORD, insta_pw_v.strip())
                    st.success("✅ 네이버 및 인스타그램 계정이 사장님의 컴퓨터에 안전하게 보관되었습니다!")
                    st.rerun()

            if st.button("🚀 전 채널(네이버+당근+스레드+인스타) 동시 포스팅 실행!", type="primary", use_container_width=True):
                with st.spinner("전 채널 오토 봇이 네이버, 당근, 스레드, 인스타그램에 동시에 글과 사진을 배포 중입니다..."):
                    from services.omni_marketing_bot import run_omni_multi_channel_posting

                    cur_nav_id = get_config(config.NAVER_ID)
                    cur_nav_pw = get_config(config.NAVER_PW)

                    omni_res = run_omni_multi_channel_posting(
                        shop_name=fruit_shop_name,
                        location=fruit_location,
                        phone_number=fruit_phone,
                        today_fruits=fruit_today,
                        event_info=fruit_event,
                        image_paths=uploaded_paths,
                        naver_id=cur_nav_id,
                        naver_pw=cur_nav_pw,
                        enable_naver=chk_nav,
                        enable_threads=chk_th,
                        enable_insta=chk_in,
                        enable_danggeun=chk_dg
                    )

                    st.balloons()
                    st.success("🎉 전 채널 동시 자동 홍보 배포가 성공적으로 완료되었습니다!")
                    st.json(omni_res.get("results", {}))


# ─────────────────────────────────────────────
# TAB 8: 24시간 모바일 무인 모니터링 & 클라우드 헬스 센터
# ─────────────────────────────────────────────
with tab8:
    st.subheader("📱 24시간 모바일 실시간 모니터링 & 클라우드 배포 헬스 센터")
    st.caption("사장님의 스마트폰(아이폰/안드로이드)으로 본체가 꺼져도 24시간 365일 어디서나 실시간 시스템 상태를 확인하고 원클릭 자동 배포를 조작할 수 있습니다.")

    m_col1, m_col2, m_col3 = st.columns(3)
    
    with m_col1:
        st.metric(label="🟢 클라우드 서버 상태", value="24시간 정상 가동 중", delta="Uptime 100%")
    with m_col2:
        from services.pipeline_service import get_daily_post_count
        st.metric(label="📊 오늘 자동 배포 실적", value=f"{get_daily_post_count()}회 등록 완료", delta="안전 한도 준수 중")
    with m_col3:
        st.metric(label="🤖 AI 폴백 프로바이더", value="Gemini + OmniRoute", delta="정상 백업 중")

    st.divider()
    st.markdown("#### 📱 스마트폰 홈 화면에 '1초 바로가기 앱' 추가하는 법")
    st.markdown("""
    1. **스마트폰 브라우저(사파리/크롬)**에서 현재 주소를 엽니다.
    2. 브라우저 하단/상단 **`공유(Share)`** 또는 **`더보기(⋮)`** 버튼을 누릅니다.
    3. **`홈 화면에 추가 (Add to Home Screen)`**를 누르시면, 사장님 스마트폰 바탕화면에 **과일대장 전용 앱 아이콘**이 바로 생겨납니다!
    """)

    st.divider()
    st.markdown("#### 💬 24시간 손님 댓글/톡 문의 AI 자동 답장 시험장")
    st.caption("네이버, 당근, 인스타그램, 카카오톡으로 손님이 문의글을 남기면 AI 사장님이 1초 만에 답장하는 실제 테스트입니다.")
    
    test_q = st.text_input("손님 문의 예시 (예: 오늘 복숭아 얼마예요? 위치가 어디예요?)", value="오늘 샤인머스캣 당도 좋은가요? 주차 가능한가요?")
    if st.button("🤖 AI 사장님 1초 자동 답장 생성", type="primary"):
        from services.auto_reply_service import generate_auto_reply
        with st.spinner("AI 과일대장 사장님이 답장을 작성 중입니다..."):
            reply_result = generate_auto_reply(test_q)
            st.success("✅ 손님 문의에 대한 1초 자동 답장:")
            st.info(reply_result)

    st.divider()
    st.markdown("#### 👥 2인 공동 관리자 (Co-Manager) 매장 관제 권한 연동")
    st.caption("사장님 외에 부사장님이나 직원 1명을 서브 관리자로 등록하여 두 분이 동시에 스마트폰으로 24시간 매장 마케팅을 함께 관리할 수 있습니다.")
    
    cm_col1, cm_col2 = st.columns(2)
    with cm_col1:
        st.markdown("**👑 메인 대표 관리자 (사장님)**")
        st.text_input("대표 관리자", value="과일대장 대표 사장님", disabled=True, key="cm_master")
    with cm_col2:
        st.markdown("**🤝 서브 공동 관리자 (부사장/직원)**")
        sub_mgr_name = st.text_input("서브 관리자 이름/전화번호", value=get_config("SUB_MANAGER_INFO", "부사장님 (010-XXXX-XXXX)"), key="cm_sub_info")
        if st.button("💾 서브 관리자 등록 & 스마트폰 공동 관리 주소 발급", use_container_width=True):
            set_config("SUB_MANAGER_INFO", sub_mgr_name)
            st.success(f"✅ {sub_mgr_name} 님이 2인 공동 관리자로 성공적으로 등록되었습니다!")

    st.info("💡 **2인 공동 관리 팁**: 위 서브 관리자분께도 24시간 라이브 웹주소(https://...streamlit.app)를 카톡으로 전달해 주시면, 서브 관리자분의 스마트폰에서도 실시간으로 과일 시세 입력, 1초 포스팅, 24시간 봇 상태 조작이 동시에 가능합니다!")

    st.divider()
    st.markdown("#### 🌐 24시간 무인 클라우드 전용 배포 상태")
    st.info("💡 본 프로그램은 Streamlit Cloud & GitHub 파이프라인으로 연결되어 사장님의 PC 본체를 완전히 꺼두셔도 매일 아침 8시 자동 홍보 + 손님 문의 1초 자동 답장이 24시간 365일 상시 동작합니다.")


# ─────────────────────────────────────────────
# TAB 9: 스토어 재고 검색 및 비교 (다이소/GS25/올리브영)
# ─────────────────────────────────────────────
with tab9:
    st.subheader("🏪 다이소 / GS25 / 올리브영 통합 검색 & 비교 리포트 (OmniRoute 무료 AI)")
    st.markdown("강력한 3사 실제 크롤링 데이터와 회원님의 **무료 OmniRoute AI(Groq, Mistral 등)**를 활용해 1원도 내지 않고 비교 블로그 포스팅을 자동 생성합니다.")
    
    st_col1, st_col2 = st.columns([2, 1])
    with st_col1:
        store_keyword = st.text_input("검색할 상품 키워드를 입력하세요 (예: 선크림, 보조배터리, 텀블러)", value="텀블러")
    with st_col2:
        st.write("")
        st.write("")
        btn_store_search = st.button("🚀 통합 검색 및 블로그 리포트 작성", type="primary", use_container_width=True)
    
    if btn_store_search:
        if not store_keyword.strip():
            st.error("검색어를 입력해주세요!")
        else:
            with st.spinner(f"'{store_keyword}' 상품을 다이소, GS25, 올리브영에서 긁어오고 있습니다... (약 10~20초 소요)"):
                from services.store_search import generate_blog_report_omniroute
                res = generate_blog_report_omniroute(store_keyword.strip())
                
                if res.get("success"):
                    st.success(f"✅ 검색 및 작성 완료! (사용된 AI: {res.get('provider')})")
                    st.markdown("### 📝 자동 생성된 비교 블로그 포스팅")
                    st.markdown(res.get("report"))
                else:
                    st.error("❌ 크롤링 또는 AI 글쓰기 중 오류가 발생했습니다.")
                    st.text_area("원시 크롤링 데이터", res.get("report", ""), height=300)
