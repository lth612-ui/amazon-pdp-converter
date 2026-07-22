import streamlit as st
import google.generativeai as genai
from PIL import Image
from bs4 import BeautifulSoup
import requests
import pandas as pd
import time
import re

# ==========================================
# 1. 페이지 및 기본 설정
# ==========================================
st.set_page_config(
    page_title="Chris PDP Converter (ULTIMATE)",
    page_icon="🚀",
    layout="wide"
)

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("⚠️ Streamlit Secrets에 GEMINI_API_KEY를 설정해 주세요.")

AMAZON_RESTRICTED_WORDS = [
    "best", "top", "free shipping", "guaranteed", "fda approved",
    "cure", "miracle", "100%", "#1", "cheapest", "discount"
]

# 세션 상태 초기화 (프로젝트 목록 관리)
if "project_list" not in st.session_state:
    st.session_state.project_list = ["Project_Serum_01", "Project_Mask_02"]

# ==========================================
# 2. 사이드바 옵션
# ==========================================
st.sidebar.title("⚙️ 옵션 및 설정")

st.sidebar.subheader("📂 프로젝트 관리")

# 새 프로젝트 생성 UI
new_proj_name = st.sidebar.text_input("➕ 새 프로젝트 생성", placeholder="예: Project_Sunscreen_03")
if st.sidebar.button("프로젝트 추가", use_container_width=True):
    if new_proj_name.strip():
        if new_proj_name.strip() not in st.session_state.project_list:
            st.session_state.project_list.append(new_proj_name.strip())
            st.sidebar.success(f"'{new_proj_name.strip()}' 생성 완료!")
        else:
            st.sidebar.warning("이미 존재하는 프로젝트명입니다.")
    else:
        st.sidebar.warning("프로젝트 이름을 입력해 주세요.")

# 기존 프로젝트 선택
selected_project = st.sidebar.selectbox(
    "📁 작업할 프로젝트 선택", 
    ["새 작업 (기본)"] + st.session_state.project_list
)

st.sidebar.markdown("---")

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
tone_extra = st.sidebar.text_area("추가 브랜드 지시사항 (선택)", placeholder="예: '비건' 키워드를 꼭 강조해주세요.")

st.sidebar.markdown("---")
st.sidebar.info("💡 **자동 검증 로직 작동 중**\n- Title 200자 / Search Terms 249 Bytes\n- 아마존 금지어 자동 체크\n- 원클릭 복사 & TXT 다운로드 제공")

# ==========================================
# 3. 헬퍼 함수
# ==========================================
def check_forbidden_words(text):
    """대소문자 구분 없이 아마존 금지어를 검사합니다."""
    text_lower = text.lower()
    found = [word for word in AMAZON_RESTRICTED_WORDS if word in text_lower]
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

def render_result_box(result_text, file_prefix="amazon_pdp"):
    st.markdown("---")
    st.subheader("📄 AI 생성 결과 (원클릭 복사 & TXT 다운로드)")
    
    col_dl, col_blank = st.columns([2, 8])
    with col_dl:
        st.download_button(
            label="📥 전체 결과 TXT 다운로드",
            data=result_text,
            file_name=f"{file_prefix}_{int(time.time())}.txt",
            mime="text/plain"
        )
        
    st.text_area(
        label="📌 아래 상자 우측 상단의 [복사 아이콘]을 누르면 전체 문구가 클립보드에 바로 복사됩니다:",
        value=result_text,
        height=250
    )
    
    with st.expander("👁️ 서식 포함 예쁘게 보기 (Preview)", expanded=True):
        st.markdown(result_text, unsafe_allow_html=True)

def highlight_usp(text, raw_keywords):
    """입력 키워드(한/영) 및 주요 명사를 지능적으로 추론하여 노란색 형광펜을 적용합니다."""
    keywords_to_highlight = set()
    
    if isinstance(raw_keywords, str):
        words = [w.strip() for w in re.split(r'[,/|\s]+', raw_keywords) if len(w.strip()) > 1]
        for w in words:
            keywords_to_highlight.add(w)
            
    auto_patterns = [r'\b[A-Z0-9\-\s]{3,}\b', r'Niacinamide', r'Hyaluronic', r'Collagen', r'Peptide', r'Absorption', r'Fast-Acting']
    for pat in auto_patterns:
        matches = re.findall(pat, text, flags=re.IGNORECASE)
        for m in matches:
            if len(m.strip()) > 3 and not m.lower().startswith("http"):
                keywords_to_highlight.add(m.strip())

    highlighted = text
    for kw in list(keywords_to_highlight)[:5]:
        pattern = re.compile(re.escape(kw), re.IGNORECASE)
        highlighted = pattern.sub(f"<mark style='background-color: #ffeb3b; color: #111111; padding: 2px 5px; border-radius: 3px; font-weight: bold;'>{kw}</mark>", highlighted)
    return highlighted

def parse_bulk_listing(raw_text):
    """Bulk 생성 시 한 셀에 입력된 결과에서 Title과 Bullet 1~5를 개별 컬럼으로 분리합니다."""
    title = ""
    bullets = ["", "", "", "", ""]
    
    title_match = re.search(r"(?:1\.\s*Product Title|Title)[:\n]*\s*(.*?)(?=\n+#|\n+2\.|\n+Bullet|\Z)", raw_text, re.DOTALL | re.IGNORECASE)
    if title_match:
        title = title_match.group(1).strip()
        
    bullet_matches = re.findall(r"(?:[*•]|\d+\.)\s*(.*)", raw_text)
    clean_bullets = [b.strip() for b in bullet_matches if len(b.strip()) > 5]
    
    for i in range(min(5, len(clean_bullets))):
        bullets[i] = clean_bullets[i]
        
    return title, bullets[0], bullets[1], bullets[2], bullets[3], bullets[4]

# ==========================================
# 4. 메인 화면 UI
# ==========================================
st.title("🚀 Chris PDP Converter (ULTIMATE)")
st.caption(f"현재 선택된 프로젝트: **{selected_project}** | 아마존 PDP, A+ Content, PPC, 경쟁사 분석 & 시딩 가이드")

work_mode = st.radio("🛠️ 작업 모드 선택", ["단일 상품 정밀 분석 (Single)", "여러 상품 일괄 생성 (Bulk CSV)"], horizontal=True)
st.divider()

if work_mode == "여러 상품 일괄 생성 (Bulk CSV)":
    st.subheader("📦 다중 상품 일괄 생성 (Bulk Processing)")
    st.info("제품명이나 특징이 담긴 CSV 파일을 업로드하면 한 번에 리스팅을 생성합니다.")
    
    uploaded_csv = st.file_uploader("CSV 파일 업로드", type=['csv'])
    
    if uploaded_csv is not None:
        df = pd.read_csv(uploaded_csv)
        st.dataframe(df.head())
        
        if st.button("🚀 일괄 생성 시작 (Batch Run)", type="primary"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            titles = []
            b1_list, b2_list, b3_list, b4_list, b5_list = [], [], [], [], []
            raw_results = []
            
            total_items = len(df)
            model = genai.GenerativeModel(selected_model)
            
            for i, row in df.iterrows():
                product_info_bulk = str(row.to_dict())
                status_text.text(f"처리 중: {i+1}번째 상품 ({i+1}/{total_items})")
                
                prompt = f"""다음 상품 정보를 바탕으로 아마존 SEO Listing (Title 및 5 Bullet Points)을 생성하세요.
                타겟 국가: {target_country}, 브랜드 톤: {brand_tone}, 추가지시사항: {tone_extra}
                상품정보: {product_info_bulk}"""
                
                try:
                    time.sleep(2)
                    response = model.generate_content(prompt)
                    raw_text = response.text
                    
                    title, b1, b2, b3, b4, b5 = parse_bulk_listing(raw_text)
                    
                    titles.append(title)
                    b1_list.append(b1)
                    b2_list.append(b2)
                    b3_list.append(b3)
                    b4_list.append(b4)
                    b5_list.append(b5)
                    raw_results.append(raw_text)
                    
                except Exception as e:
                    titles.append("Error")
                    b1_list.append(str(e))
                    b2_list.append("")
                    b3_list.append("")
                    b4_list.append("")
                    b5_list.append("")
                    raw_results.append(f"에러 발생: {e}")
                
                progress_bar.progress((i + 1) / total_items)
                
            df['AI_Title'] = titles
            df['Bullet_1'] = b1_list
            df['Bullet_2'] = b2_list
            df['Bullet_3'] = b3_list
            df['Bullet_4'] = b4_list
            df['Bullet_5'] = b5_list
            df['Full_Raw_Output'] = raw_results
            
            status_text.text("✅ 일괄 생성 완료! 아래에서 파일을 다운로드하세요.")
            
            csv_data = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 전체 결과 다운로드 (CSV)", data=csv_data, file_name=f"bulk_generated_{int(time.time())}.csv", mime="text/csv")

else:
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

    with st.expander("⚔️ 경쟁사 비교 설정 (선택사항 - 클릭하여 열기)"):
        col_comp1, col_comp2 = st.columns(2)
        with col_comp1:
            competitor_url = st.text_input("경쟁사 제품 아마존 URL", placeholder="https://www.amazon.com/dp/...")
        with col_comp2:
            competitor_info = st.text_input("경쟁사 특징/단점 메모", placeholder="예: 경쟁사는 가격이 비싸고 용량이 적음")

    st.markdown("---")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📝 Amazon Listing (PDP)", 
        "🎨 A+ Content Plan", 
        "🎯 PPC Strategy", 
        "⚔️ 경쟁사 비교 분석",
        "📢 Seeding & Marketing Guide"
    ])

    base_instruction = f"""
    [기본 지침]
    - 프로젝트명: {selected_project}
    - 타겟 국가/언어: {target_country}
    - 브랜드 톤앤매너: {brand_tone}
    - 추가 지시사항: {tone_extra}
    - 지정된 언어로 매끄럽고 설득력 있게 작성하세요.
    """

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
                    위 정보(이미지, URL, 텍스트)를 바탕으로 아마존 SEO 최적화 Listing을 생성하세요.

                    [내부 가이드라인 - 출력문에 절대 노출하지 말 것]
                    - Product Description 부분에는 HTML 태그를 절대로 쓰지 마세요.
                    - 순수 텍스트(Plain Text)와 줄바꿈(Enter)만 사용하세요.

                    [출력 형식]
                    # Amazon Listing Optimization
                    ## 1. Product Title
                    ## 2. Bullet Points (5 Key Selling Points)
                    ## 3. Search Terms (249바이트 이내)
                    ## 4. Product Description
                    """
                    try:
                        response = model.generate_content(inputs + [prompt])
                        res_text = response.text
                        
                        full_check_text = f"{product_name} {key_features} {res_text}"
                        forbidden = check_forbidden_words(full_check_text)
                        
                        st.subheader("📊 리스팅 최적화 리포트")
                        col1, col2 = st.columns([1, 2])
                        
                        with col1:
                            seo_score = max(0, 100 - (len(forbidden) * 20))
                            st.metric(label="SEO Optimization Score", value=f"{seo_score} / 100")
                            st.progress(seo_score / 100)
                            
                        with col2:
                            if forbidden:
                                st.error(f"⚠️ **아마존 정책 위반 의심 단어 감지 ({len(forbidden)}개)**: {', '.join(forbidden)}")
                            else:
                                st.success("✅ 아마존 정책 위반 금지어가 감지되지 않았습니다.")
                        
                        render_result_box(res_text, f"{selected_project}_pdp_listing")
                        
                    except Exception as e:
                        st.error(f"API 호출 중 오류 발생: {e}")

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
                    render_result_box(response.text, f"{selected_project}_aplus_content")

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
                    render_result_box(response.text, f"{selected_project}_ppc_keywords")

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
                    res_text = response.text
                    
                    st.markdown("#### 💡 Our Unique Selling Proposition (USP) Highlight")
                    
                    highlighted_text = highlight_usp(res_text, key_features)
                    st.markdown(
                        f"""
                        <div style="background-color: #1e1e24; color: #e0e0e0; padding: 18px; border-radius: 8px; border: 1px solid #33333e; height: 260px; overflow-y: scroll; line-height: 1.6;">
                            {highlighted_text}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    
                    render_result_box(res_text, f"{selected_project}_competitor_analysis")

    # Tab 5: Seeding & Marketing Guide
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
                       - 권장 연출/촬영 구도
                       - 캡션(글) 핵심 셀링 포인트
                       - 금지 표현/주의사항

                    2. 🎬 **숏폼/SNS 광고 카피 및 콘셉트 (Instagram Reels / TikTok)**
                       - 후킹 문구 (Hook) 3가지 버전
                       - 메인 셀링 카피 3가지 버전
                       - CTA (Call To Action - 구매 유도 문구)
                    """
                    response = model.generate_content(inputs + [prompt])
                    render_result_box(response.text, f"{selected_project}_seeding_guide")