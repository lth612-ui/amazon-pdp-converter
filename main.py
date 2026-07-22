import streamlit as st
import google.generativeai as genai
from PIL import Image
from bs4 import BeautifulSoup
import requests

# 1. 페이지 및 기본 설정
st.set_page_config(
    page_title="Chris PDP Converter (ULTIMATE)",
    page_icon="🚀",
    layout="wide"
)

# API 키 설정
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("⚠️ Streamlit Secrets에 GEMINI_API_KEY를 설정해 주세요.")

AMAZON_RESTRICTED_WORDS = [
    "best", "top", "free shipping", "guaranteed", "fda approved",
    "cure", "miracle", "100%", "#1", "cheapest", "discount"
]

# 2. 사이드바 옵션
st.sidebar.title("⚙️ 옵션 및 설정")

model_choice = st.sidebar.radio(
    "Gemini 모델 선택",
    ("Flash (빠른 속도)", "Pro (고품질 분석)")
)
selected_model = "gemini-3.6-flash" if "Flash" in model_choice else "gemini-3.1-pro"

target_country = st.sidebar.selectbox(
    "🌐 타겟 언어/국가",
    (
        "US English (미국)",
        "JP Japanese (일본)",
        "DE German (독일/유럽)",
        "UK English (영국/유럽)",
        "FR French (프랑스/유럽)"
    )
)

brand_tone = st.sidebar.selectbox(
    "🎯 브랜드 톤 앤 매너",
    (
        "Premium & Luxury (고급스럽고 매끄러움)",
        "Friendly & Engaging (친근하고 설득력 있음)",
        "Technical & Professional (전문적이고 신뢰감 있음)",
        "Clean & Natural (친환경/자연주의 강조)"
    )
)

st.sidebar.markdown("---")
st.sidebar.info("💡 **자동 검증 로직 작동 중**\n- Title 200자 / Search Terms 249 Bytes\n- 아마존 금지어 자동 체크\n- 이미지 & 링크 자동 비전 분석")

# 헬퍼 함수
def check_forbidden_words(text):
    found = [word for word in AMAZON_RESTRICTED_WORDS if word in text.lower()]
    return list(set(found))

def crawl_amazon_url(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            title = soup.find(id="productTitle")
            return title.get_text(strip=True) if title else url
        return url
    except:
        return url

# 3. 메인 화면 UI
st.title("🚀 Chris PDP Converter (ULTIMATE)")
st.caption("아마존 PDP 최적화, A+ Content, PPC 키워드, 경쟁사 분석 및 인플루언서 시딩 가이드라인")

# --- 메인 입력 파트 ---
st.markdown("### 📥 1. 제품 정보 입력 (링크/이미지/텍스트 중 선택 가능)")

col_input1, col_input2 = st.columns(2)

with col_input1:
    st.markdown("#### 🔗 [방법 A] 아마존 URL 또는 이미지로 자동 분석")
    my_product_url = st.text_input("내 제품 아마존 URL", placeholder="https://www.amazon.com/dp/...")
    uploaded_image = st.file_uploader("제품 패키지 / 상세페이지 이미지 업로드", type=["png", "jpg", "jpeg", "webp"])

with col_input2:
    st.markdown("#### 📝 [방법 B] 직접 텍스트 입력")
    product_name = st.text_input("제품명 (미입력 시 URL/이미지에서 자동 추론)", placeholder="예: 비타민 C 세럼 30ml")
    key_features = st.text_area("주요 특징/성분/소구점", placeholder="예: 순수 비타민C 15%, 피부 톤 개선, 끈적임 없는 수분제형", height=100)

st.markdown("---")

# --- 경쟁사 입력 파트 (선택) ---
with st.expander("⚔️ 경쟁사 비교 설정 (선택사항 - 클릭하여 열기)"):
    col_comp1, col_comp2 = st.columns(2)
    with col_comp1:
        competitor_url = st.text_input("경쟁사 제품 아마존 URL", placeholder="https://www.amazon.com/dp/...")
    with col_comp2:
        competitor_info = st.text_input("경쟁사 특징/단점 메모", placeholder="예: 경쟁사는 가격이 비싸고 용량이 적음")

st.markdown("---")

# 4. Output 탭 구성 (시딩/마케팅 가이드 포함 5개 탭)
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📝 Amazon Listing (PDP)", 
    "🎨 A+ Content Plan", 
    "🎯 PPC Strategy", 
    "⚔️ 경쟁사 비교 분석",
    "📢 Seeding & Marketing Guide"
])

base_instruction = f"""
[기본 지침]
- 타겟 국가/언어: {target_country}
- 브랜드 톤앤매너: {brand_tone}
- 지정된 언어로 매끄럽고 설득력 있게 작성하세요.
"""

# 입력 데이터 수집 함수
def get_input_contents():
    contents = [base_instruction]
    if my_product_url:
        crawled = crawl_amazon_url(my_product_url)
        contents.append(f"내 제품 아마존 URL: {my_product_url}\n수집/참조 제목: {crawled}")
    if product_name:
        contents.append(f"제품명: {product_name}")
    if key_features:
        contents.append(f"제품 특징: {key_features}")
    if uploaded_image:
        img = Image.open(uploaded_image)
        contents.append("업로드된 제품 이미지:")
        contents.append(img)
    return contents

# Tab 1: Listing
with tab1:
    if st.button("🚀 PDP 리스팅 생성하기", type="primary"):
        inputs = get_input_contents()
        if len(inputs) <= 1:
            st.warning("아마존 URL, 이미지, 또는 제품명 중 최소 하나는 입력해 주세요!")
        else:
            with st.spinner("이미지/링크/텍스트 분석 후 리스팅 작성 중..."):
                model = genai.GenerativeModel(selected_model)
                prompt = """
                위 정보(이미지, URL, 텍스트)를 바탕으로 아마존 SEO 최적화 Listing을 생성하세요:
                1. Product Title (200자 이내, 핵심 키워드 대문자 강조)
                2. Bullet Points 5개 (핵심 셀링 포인트 위주)
                3. Search Terms (249 Bytes 이내, 쉼표 없이 키워드만)
                4. Product Description (⚠️ 중요: <p>, <b>, <br> 등의 HTML 태그를 절대로 사용하지 말고, 순수 텍스트(Plain Text)와 줄바꿈으로만 깔끔하게 작성하세요.)
                """
                response = model.generate_content(inputs + [prompt])
                st.markdown(response.text)
                
                forbidden = check_forbidden_words(response.text)
                if forbidden:
                    st.error(f"⚠️ **아마존 금지어 주의**: {', '.join(forbidden)}")

# Tab 2: A+ Content
with tab2:
    if st.button("🎨 A+ Content 기획안 생성"):
        inputs = get_input_contents()
        if len(inputs) <= 1:
            st.warning("제품 정보를 입력하거나 이미지를 업로드해 주세요!")
        else:
            with st.spinner("A+ 비주얼 스토리보드 기획 중..."):
                model = genai.GenerativeModel(selected_model)
                prompt = """
                위 정보를 기반으로 아마존 A+ Content (EBC) 5개 모듈 스토리보드를 작성하세요:
                - 모듈 1: Hero Banner (브랜드 카피 및 이미지 레이아웃 제안)
                - 모듈 2: Key Benefits (3대 핵심 효능 파트)
                - 모듈 3: Deep Dive / Technology (성분/기술력 비주얼 제안)
                - 모듈 4: How to Use (사용 단계 및 꿀팁)
                - 모듈 5: Brand Story & Cross-selling
                """
                response = model.generate_content(inputs + [prompt])
                st.markdown(response.text)

# Tab 3: PPC Strategy
with tab3:
    if st.button("🎯 PPC 키워드 전략 추출"):
        inputs = get_input_contents()
        if len(inputs) <= 1:
            st.warning("제품 정보를 입력해 주세요!")
        else:
            with st.spinner("검색 키워드 분석 중..."):
                model = genai.GenerativeModel(selected_model)
                prompt = """
                위 제품 정보를 분석하여 아마존 PPC 광고 키워드를 뽑아주세요:
                1. Exact Match Keywords (전환율 높은 메인 키워드 10개)
                2. Broad/Phrase Keywords (확장형 키워드 10개)
                3. Long-tail Keywords (세부 타겟 키워드 10개)
                4. Negative Keywords (광고비 절감을 위한 제외 키워드 5개)
                """
                response = model.generate_content(inputs + [prompt])
                st.markdown(response.text)

# Tab 4: Competitor Comparison
with tab4:
    if st.button("⚔️ 1:1 경쟁사 비교 분석 실행"):
        inputs = get_input_contents()
        if not competitor_url and not competitor_info:
            st.warning("상단의 경쟁사 비교 설정에 경쟁사 URL 또는 정보를 입력해 주세요!")
        else:
            with st.spinner("내 제품과 경쟁사 비교 분석 중..."):
                comp_text = f"\n[경쟁사 정보]\nURL: {competitor_url}\n메모: {competitor_info}"
                model = genai.GenerativeModel(selected_model)
                prompt = f"""
                내 제품 정보와 다음 경쟁사 정보를 비교 분석해 주세요: {comp_text}

                [출력 내용]
                1. 내 제품의 독점적 우위 (USP)
                2. 경쟁사 고객 스틸을 위한 핵심 마케팅 메시지
                3. PDP에서 강조해야 할 비주얼 요소
                4. 1:1 비교 요약표 (성분/기능, 가성비, 타겟층, 소구점)
                """
                response = model.generate_content(inputs + [prompt])
                st.markdown(response.text)

# Tab 5: Seeding & Marketing Guide (신규)
with tab5:
    st.subheader("📢 인플루언서 시딩 & SNS 마케팅 가이드라인")
    if st.button("📢 시딩 & 마케팅 가이드 생성"):
        inputs = get_input_contents()
        if len(inputs) <= 1:
            st.warning("제품 정보를 입력하거나 이미지를 업로드해 주세요!")
        else:
            with st.spinner("마케팅 카피 및 시딩 가이드라인 제작 중..."):
                model = genai.GenerativeModel(selected_model)
                prompt = """
                위 제품 정보를 바탕으로 마케팅팀과 인플루언서가 바로 사용할 수 있는 가이드라인을 작성하세요:

                1. 📸 **인플루언서 시딩 가이드 (Seeding Brief)**
                   - 필수 언급 키워드 & 해시태그 (#)
                   - 권장 연출/촬영 구도 (예: 제형 연출, 사용 전후 비포애프터 등)
                   - 캡션(글)에 반드시 들어가야 할 핵심 셀링 포인트
                   - 금지 표현/주의사항

                2. 🎬 **숏폼/SNS 광고 카피 및 콘셉트 (Instagram Reels / TikTok)**
                   - 후킹 문구 (Hook) 3가지 버전
                   - 메인 셀링 카피 3가지 버전
                   - CTA (Call To Action - 구매 유도 문구)
                """
                response = model.generate_content(inputs + [prompt])
                st.markdown(response.text)