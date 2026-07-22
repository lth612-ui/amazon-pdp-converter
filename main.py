import streamlit as st
import requests
from bs4 import BeautifulSoup
from PIL import Image
import io
from google import genai

# 웹페이지 기본 설정
st.set_page_config(page_title="ClickTive PDP Converter", page_icon="🛍️", layout="wide")

import os

# Streamlit Secrets 또는 환경변수에서 키를 불러오도록 변경 (깃허브 보안 통과용)
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))
client = genai.Client(api_key=GEMINI_API_KEY)

# 웹 크롤링 함수
def fetch_page_content(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            title = soup.find(id='productTitle')
            return title.get_text(strip=True) if title else ""
    except Exception:
        return ""
    return ""

# UI 타이틀
st.title("🛍️ 클릭티브 PDP Converter (PRO)")
st.caption("아마존 URL 분석 또는 국내 상세페이지 통이미지를 직접 업로드하여 아마존 최적화 SEO 텍스트를 생성합니다.")

st.divider()

# 탭 구성 (URL 입력 vs 이미지 업로드)
tab1, tab2 = st.tabs(["🔗 아마존 URL 분석", "🖼️ 통이미지/상세페이지 파일 업로드"])

# 프롬프트 템플릿
SYSTEM_PROMPT = """
당신은 세계 최고 수준의 아마존 SEO 및 마케팅 카피라이터입니다.
제공된 정보(URL, 텍스트, 또는 상세페이지 이미지)를 기반으로 아마존 셀러 센트럴에 바로 사용할 수 있는 최적화된 마케팅 문구를 작성하세요.

[수칙]
1. Product Title: 핵심 키워드 포함, 검색 노출 최적화 (200자 이내)
2. Bullet Points: 5개 항목, [대문자 헤드라인] + 설득력 있는 셀링 포인트
3. Backend Search Terms: 249바이트 제한 준수, 중복 단어 제외, 쉼표 없이 공백으로만 구분
4. 이미지 내 한국어 텍스트가 있다면 정확히 파악하여 자연스럽고 매력적인 영어 마케팅 문구로 번역/재창조하세요.

[출력 Format]
각 섹션을 명확히 구분하여 깔끔한 마크다운으로 작성해주세요.
"""

# ----- TAB 1: URL 분석 -----
with tab1:
    url_input = st.text_input("아마존 상품 상세페이지 URL을 입력하세요:", placeholder="https://www.amazon.com/dp/...")
    if st.button("URL 기반 SEO 생성 🚀", type="primary", key="btn_url"):
        if url_input:
            with st.spinner("웹페이지 분석 및 Gemini AI 생성 중..."):
                try:
                    page_text = fetch_page_content(url_input)
                    prompt = f"{SYSTEM_PROMPT}\n\n[입력 URL]: {url_input}\n[추출 텍스트]: {page_text}"
                    
                    response = client.models.generate_content(
                        model='gemini-3.6-flash',
                        contents=prompt,
                    )
                    st.session_state['result'] = response.text
                    st.success("분석 완료!")
                except Exception as e:
                    st.error(f"오류 발생: {e}")
        else:
            st.warning("URL을 입력해주세요!")

# ----- TAB 2: 이미지 업로드 분석 -----
with tab2:
    uploaded_files = st.file_uploader(
        "한국어 상세페이지 이미지(PNG, JPG, JPEG)를 업로드하세요 (다중 선택 가능):", 
        type=["png", "jpg", "jpeg"], 
        accept_multiple_files=True
    )
    
    if uploaded_files:
        # 이미지 미리보기
        cols = st.columns(min(len(uploaded_files), 4))
        for idx, file in enumerate(uploaded_files):
            img = Image.open(file)
            with cols[idx % 4]:
                st.image(img, caption=file.name, use_container_width=True)

    if st.button("이미지 OCR & SEO 생성 🚀", type="primary", key="btn_img"):
        if uploaded_files:
            with st.spinner("이미지 시각 분석 및 Gemini AI 처리 중..."):
                try:
                    contents_payload = [SYSTEM_PROMPT]
                    for file in uploaded_files:
                        img = Image.open(file)
                        contents_payload.append(img)
                    
                    response = client.models.generate_content(
                        model='gemini-2.0-flash',
                        contents=contents_payload,
                    )
                    st.session_state['result'] = response.text
                    st.success("이미지 분석 및 문구 생성 완료!")
                except Exception as e:
                    st.error(f"이미지 분석 중 오류 발생: {e}")
        else:
            st.warning("분석할 이미지 파일을 최소 1개 이상 업로드해주세요!")

# ----- 결과 출력 및 편의기능 UI -----
if 'result' in st.session_state:
    st.divider()
    
    col_head1, col_head2 = st.columns([3, 1])
    with col_head1:
        st.subheader("📝 AI가 생성한 SEO 최적화 결과")
    with col_head2:
        # 1. 전체 결과 TXT 다운로드
        st.download_button(
            label="💾 전체 결과 TXT 다운로드",
            data=st.session_state['result'],
            file_name="amazon_seo_result.txt",
            mime="text/plain",
            use_container_width=True
        )

    # 2. 결과 텍스트 영역 (우측 상단 클릭 한 번으로 원클릭 복사 가능)
    st.text_area(
        label="📌 아래 상자 우측 상단의 [📋 복사 아이콘]을 누르면 전체 문구가 바로 클립보드에 복사됩니다:",
        value=st.session_state['result'],
        height=350
    )

    # 3. 마크다운 예쁘게 보기 (기존 렌더링 방식)
    with st.expander("👁️ 서식 포함 예쁘게 보기 (Preview)", expanded=True):
        st.markdown(st.session_state['result'])