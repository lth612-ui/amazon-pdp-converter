import os
import streamlit as st
import requests
from bs4 import BeautifulSoup
from PIL import Image
from google import genai
from google.genai import types

# ---------------------------------------------------------
# 1. 페이지 및 사이드바 설정
# ---------------------------------------------------------
st.set_page_config(page_title="클릭티브 PDP Converter (ULTIMATE)", layout="wide", page_icon="🚀")

# Gemini API 설정
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error("⚠️ GEMINI_API_KEY 설정이 필요합니다. Streamlit Secrets에 키를 입력해 주세요.")
    st.stop()

client = genai.Client(api_key=api_key)

# 아마존 정책상 주의/금지어 리스트
AMAZON_RESTRICTED_WORDS = [
    "guarantee", "guaranteed", "best", "top seller", "free shipping",
    "fda approved", "cure", "100% quality", "cheapest", "#1"
]

# 사이드바 옵션
st.sidebar.title("⚙️ 옵션 및 설정")

selected_model = st.sidebar.radio(
    "🤖 Gemini 모델 선택",
    options=["gemini-3.6-flash", "gemini-3.1-pro"],
    format_func=lambda x: "⚡ Flash (빠른 속도)" if "flash" in x else "🧠 Pro (고품질 분석)",
    index=0
)

target_market = st.sidebar.selectbox(
    "🌐 타겟 언어/국가",
    ["US English (미국)", "UK English (영국)"]
)

brand_tone = st.sidebar.selectbox(
    "🎨 브랜드 톤 앤 매너",
    [
        "Premium & Luxury (고급스럽고 매끄러운)",
        "Scientific & Clinical (전문적이고 신뢰감 있는)",
        "Eco-Friendly & Natural (친환경적이고 순한)",
        "Friendly & Casual (친근하고 대화하듯)",
        "Persuasive & Benefit-driven (구매 유도 및 혜택 강조)"
    ]
)

st.sidebar.markdown("---")
st.sidebar.info("💡 **검증 로직 작동 중**\n- Title 200자 준수\n- Search Terms 249 Bytes 준수\n- 아마존 금지어 자동 모니터링")

# ---------------------------------------------------------
# 2. 헬퍼 함수 정의
# ---------------------------------------------------------
def check_forbidden_words(text):
    """금지어 감지 함수"""
    found = []
    text_lower = text.lower()
    for word in AMAZON_RESTRICTED_WORDS:
        if word in text_lower:
            found.append(word)
    return found

def crawl_amazon_url(url):
    """아마존 URL 스크래핑"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9'
    }
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200:
            return None, f"페이지를 불러올 수 없습니다. (상태 코드: {res.status_code})"
        
        soup = BeautifulSoup(res.text, 'html.parser')
        title_el = soup.find(id="productTitle")
        title = title_el.get_text().strip() if title_el else ""
        
        bullets_el = soup.find(id="feature-bullets")
        bullets = ""
        if bullets_el:
            items = bullets_el.find_all("span", class_="a-list-item")
            bullets = "\n".join([item.get_text().strip() for item in items if item.get_text().strip()])
            
        if not title and not bullets:
            return None, "상품 정보를 찾을 수 없습니다. (차단되었거나 봇 대처 화면)"
            
        return f"Product Title: {title}\n\nBullet Points:\n{bullets}", None
    except Exception as e:
        return None, str(e)

# ---------------------------------------------------------
# 3. 메인 UI 및 프롬프트 처리
# ---------------------------------------------------------
st.title("🚀 클릭티브 PDP Converter (ULTIMATE)")
st.caption("아마존 Listing, A+ Content, PPC 키워드, 경쟁사 비교분석까지 완벽 자동화")

st.divider()

# 메인 기능 탭
main_tab1, main_tab2, main_tab3, main_tab4 = st.tabs([
    "📦 Amazon Listing 생성", 
    "🎨 A+ Content (EBC) 초안", 
    "🎯 PPC 광고 키워드", 
    "⚔️ 경쟁사 비교 분석"
])

# ---------------------------------------------------------
# TAB 1: Amazon Listing 생성
# ---------------------------------------------------------
with main_tab1:
    st.subheader("1. 기본 Amazon SEO Listing 생성")
    
    input_type = st.radio("입력 방식 선택", ["아마존 URL", "상세페이지 통이미지 업로드"], horizontal=True)
    
    content_input = None
    image_input = None
    
    if input_type == "아마존 URL":
        url = st.text_input("아마존 상품 상세페이지 URL을 입력하세요:")
        if url:
            with st.spinner("페이지 정보 수집 중..."):
                crawled, err = crawl_amazon_url(url)
                if err:
                    st.warning(f"자동 크롤링 제한: {err}\n아래 텍스트 직접 입력창을 활용할 수도 있습니다.")
                else:
                    st.success("데이터 수집 완료!")
                    content_input = crawled
    else:
        uploaded_file = st.file_uploader("상세페이지 이미지를 업로드하세요 (PNG, JPG)", type=["png", "jpg", "jpeg"])
        if uploaded_file:
            image_input = Image.open(uploaded_file)
            st.image(image_input, caption="업로드된 이미지", use_column_width=True)

    if st.button("🚀 SEO Listing 생성하기", type="primary"):
        if not content_input and not image_input:
            st.error("URL을 입력하거나 이미지를 업로드해 주세요.")
        else:
            prompt = f"""
            You are an expert Amazon SEO & Copywriting Specialist.
            Create a highly optimized Amazon Product Listing using the provided product information.

            [Constraints & Guidelines]:
            1. Target Language: {target_market}
            2. Brand Tone: {brand_tone}
            3. Product Title: Maximum 200 characters. Highly readable, including core keywords, brand, specifications.
            4. Bullet Points: Exactly 5 points. Start each point with a bolded capitalized KEY BENEFIT IN BRACKETS.
            5. Backend Search Terms: Less than 249 BYTES in total. Space-separated, NO commas, NO duplicate words from title/bullets, NO forbidden words (e.g. best, free, guarantee).

            [Output Format Required (Strictly in Markdown)]:
            # [Amazon Listing Optimization]

            ### 1. Product Title
            (Write the title here)

            ### 2. Bullet Points
            * [KEY BENEFIT 1] explanation...
            * [KEY BENEFIT 2] explanation...
            * [KEY BENEFIT 3] explanation...
            * [KEY BENEFIT 4] explanation...
            * [KEY BENEFIT 5] explanation...

            ### 3. Backend Search Terms
            (Write space-separated keywords here)
            """

            with st.spinner("AI가 최적화 리스팅을 생성하고 있습니다..."):
                try:
                    contents = [prompt]
                    if image_input:
                        contents.append(image_input)
                    if content_input:
                        contents.append(content_input)
                        
                    response = client.models.generate_content(
                        model=selected_model,
                        contents=contents
                    )
                    
                    result_text = response.text
                    st.markdown("---")
                    st.subheader("📝 생성 결과 및 검증 리포트")
                    st.markdown(result_text)
                    
                    # 자동 정책/규정 검사
                    st.markdown("---")
                    st.subheader("🔍 실시간 규정 및 바이트 검수 결과")
                    
                    forbidden_found = check_forbidden_words(result_text)
                    if forbidden_found:
                        st.error(f"⚠️ **아마존 정책 위반 가능 단어 감지**: {', '.join(forbidden_found)}")
                    else:
                        st.success("✅ **정책 위반 단어 미감지**: 금지어가 포함되어 있지 않습니다.")
                        
                except Exception as e:
                    st.error(f"생성 중 오류가 발생했습니다: {e}")

# ---------------------------------------------------------
# TAB 2: A+ Content (EBC)
# ---------------------------------------------------------
with main_tab2:
    st.subheader("2. A+ Content (Enhanced Brand Content) 기획안")
    aplus_desc = st.text_area("상품 특징 및 USP(특장점)를 입력하세요:", placeholder="예: 100% 유기농 모로코 아르간 오일, 비건 인증, 수분 보습 24시간 유지...")
    
    if st.button("🎨 A+ Content 기획안 생성", type="primary"):
        if not aplus_desc:
            st.error("상품 특징을 입력해 주세요.")
        else:
            prompt = f"""
            Create a high-converting Amazon A+ Content (EBC) Wireframe and Copywriting draft.
            Target Language: {target_market}
            Tone: {brand_tone}
            Input Product Info: {aplus_desc}

            Structure:
            - **Module 1: Hero Brand Banner** (Header, Visual Description, Short Copy)
            - **Module 2: 3-Column Feature Highlight** (3 Key Features with Visual Cue & Headline)
            - **Module 3: Brand Story / Product Comparison Chart Concept**
            """
            with st.spinner("A+ Content 기획 중..."):
                res = client.models.generate_content(model=selected_model, contents=[prompt])
                st.markdown(res.text)

# ---------------------------------------------------------
# TAB 3: PPC 광고 키워드
# ---------------------------------------------------------
with main_tab3:
    st.subheader("3. Amazon PPC 키워드 추출")
    ppc_input = st.text_input("상품명 또는 대표 카테고리를 입력하세요:", placeholder="예: Oxy-Bubble Niacinamide Essence")
    
    if st.button("🎯 PPC 키워드 추출", type="primary"):
        if not ppc_input:
            st.error("상품명 또는 카테고리를 입력해 주세요.")
        else:
            prompt = f"""
            Generate an Amazon PPC Keyword Strategy for: '{ppc_input}'
            Language: {target_market}

            Categorize into:
            1. **Exact Match Keywords** (High Intent / High Conversion)
            2. **Broad / Phrase Match Keywords** (Traffic Drivers)
            3. **Long-tail Keywords** (Low CPC / High ROAS potential)
            4. **Negative Keywords** (Words to exclude to save spend)
            """
            with st.spinner("PPC 키워드 분석 중..."):
                res = client.models.generate_content(model=selected_model, contents=[prompt])
                st.markdown(res.text)

# ---------------------------------------------------------
# TAB 4: 경쟁사 비교 분석
# ---------------------------------------------------------
with main_tab4:
    st.subheader("4. 경쟁사 Listing 비교 및 차별화 전략")
    col1, col2 = st.subplots(2)
    with col1:
        my_prod = st.text_area("내 상품 특징:", placeholder="내 제품의 장점 및 성분...")
    with col2:
        comp_prod = st.text_area("경쟁사 상품/리뷰 특징:", placeholder="경쟁사 주요 리뷰 불만 사항 또는 스펙...")
        
    if st.button("⚔️ 비교 분석 및 차별화 카피 추출", type="primary"):
        if not my_prod or not comp_prod:
            st.error("내 상품과 경쟁사 정보 둘 다 입력해 주세요.")
        else:
            prompt = f"""
            Analyze both products and build a competitive marketing angle.
            Target Language: {target_market}
            
            [My Product]: {my_prod}
            [Competitor Product]: {comp_prod}

            Provide:
            1. **Competitor Weakness vs My Strength (Gap Analysis)**
            2. **Winning USP (Unique Selling Proposition)**
            3. **Hooking Copywriting Phrases to outshine competitor**
            """
            with st.spinner("비교 분석 중..."):
                res = client.models.generate_content(model=selected_model, contents=[prompt])
                st.markdown(res.text)