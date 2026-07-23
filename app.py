import streamlit as st
import google.generativeai as genai
from PIL import Image
from bs4 import BeautifulSoup
import requests
import pandas as pd
import time
import re
import html
import hashlib
from urllib.parse import urlparse

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
    st.stop()

AMAZON_RESTRICTED_WORDS = [
    "best", "top", "free shipping", "guaranteed", "fda approved",
    "cure", "miracle", "100%", "#1", "cheapest", "discount"
]

MODEL_CHOICES = ("Flash (빠른 속도)", "Pro (고품질 분석)")
COUNTRY_CHOICES = (
    "US English (미국)",
    "JP Japanese (일본)",
    "DE German (독일/유럽)",
    "UK English (영국/유럽)",
    "FR French (프랑스/유럽)"
)
TONE_CHOICES = (
    "Premium & Luxury (고급스럽고 매끄러움)",
    "Friendly & Engaging (친근하고 설득력 있음)",
    "Technical & Professional (전문적이고 신뢰감 있음)",
    "Clean & Natural (친환경/자연주의 강조)"
)

MAX_BULK_ROWS = 50

# ==========================================
# [중요] 세션 상태 및 프로젝트 저장소 초기화
# ==========================================
if "project_list" not in st.session_state:
    st.session_state.project_list = ["Project_Serum_01", "Project_Mask_02"]

if "project_data" not in st.session_state:
    st.session_state.project_data = {}

if "current_project" not in st.session_state:
    st.session_state.current_project = "새 작업 (기본)"

def init_project_store(proj_name):
    if proj_name not in st.session_state.project_data:
        st.session_state.project_data[proj_name] = {
            "my_product_url": "",
            "product_name": "",
            "key_features": "",
            "competitor_url": "",
            "competitor_info": "",
            "results": {}, 
            "target_country": COUNTRY_CHOICES[0],
            "brand_tone": TONE_CHOICES[0],
            "tone_extra": "",
            "model_choice": MODEL_CHOICES[0],
        }

init_project_store("새 작업 (기본)")
for p in st.session_state.project_list:
    init_project_store(p)

# ==========================================
# 2. 사이드바 - 프로젝트 관리
# ==========================================
st.sidebar.title("⚙️ 옵션 및 설정")
st.sidebar.subheader("📂 프로젝트 관리")

new_proj_name = st.sidebar.text_input("➕ 새 프로젝트 생성", placeholder="예: Project_Sunscreen_03")
if st.sidebar.button("프로젝트 추가", use_container_width=True):
    name_clean = new_proj_name.strip()
    if name_clean:
        if name_clean not in st.session_state.project_list:
            st.session_state.project_list.append(name_clean)
            init_project_store(name_clean)
            st.session_state.current_project = name_clean
            st.sidebar.success(f"'{name_clean}' 생성 및 이동 완료!")
            st.rerun()
        else:
            st.sidebar.warning("이미 존재하는 프로젝트명입니다.")
    else:
        st.sidebar.warning("프로젝트 이름을 입력해 주세요.")

selected_project = st.sidebar.selectbox(
    "📁 작업할 프로젝트 선택",
    ["새 작업 (기본)"] + st.session_state.project_list,
    index=(["새 작업 (기본)"] + st.session_state.project_list).index(st.session_state.current_project)
    if st.session_state.current_project in (["새 작업 (기본)"] + st.session_state.project_list) else 0
)

if selected_project != st.session_state.current_project:
    st.session_state.current_project = selected_project
    st.rerun()

current_p_data = st.session_state.project_data[st.session_state.current_project]

st.sidebar.markdown("---")

model_choice = st.sidebar.radio(
    "Gemini 모델 선택",
    MODEL_CHOICES,
    index=MODEL_CHOICES.index(current_p_data.get("model_choice", MODEL_CHOICES[0])),
    key=f"model_choice_{st.session_state.current_project}"
)
current_p_data["model_choice"] = model_choice
selected_model = "gemini-3.6-flash" if "Flash" in model_choice else "gemini-3.1-pro"

target_country = st.sidebar.selectbox(
    "🌐 타겟 언어/국가",
    COUNTRY_CHOICES,
    index=COUNTRY_CHOICES.index(current_p_data.get("target_country", COUNTRY_CHOICES[0])),
    key=f"target_country_{st.session_state.current_project}"
)
current_p_data["target_country"] = target_country

brand_tone = st.sidebar.selectbox(
    "🎯 브랜드 톤 앤 매너",
    TONE_CHOICES,
    index=TONE_CHOICES.index(current_p_data.get("brand_tone", TONE_CHOICES[0])),
    key=f"brand_tone_{st.session_state.current_project}"
)
current_p_data["brand_tone"] = brand_tone

tone_extra = st.sidebar.text_area(
    "추가 브랜드 지시사항 (선택)",
    value=current_p_data.get("tone_extra", ""),
    placeholder="예: '비건' 키워드를 꼭 강조해주세요.",
    key=f"tone_extra_{st.session_state.current_project}"
)
current_p_data["tone_extra"] = tone_extra


# ==========================================
# 3. 데이터 수집(스크래퍼) 및 헬퍼 함수
# ==========================================

def is_valid_url(url):
    """http 또는 https로 시작하는 유효한 웹 주소인지 검증"""
    try:
        parsed = urlparse(url.strip())
        return parsed.scheme in {"http", "https"} and bool(parsed.hostname)
    except ValueError:
        return False

# ----- 사이트별 전담 스크래퍼 -----
def scrape_amazon(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    res = requests.get(url, headers=headers, timeout=10)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")
    title_tag = soup.select_one("#productTitle")
    bullet_tags = soup.select("#feature-bullets li span")

    title = title_tag.get_text(" ", strip=True) if title_tag else ""
    bullets = [b.get_text(" ", strip=True) for b in bullet_tags if b.get_text(strip=True)]

    if not title and not bullets:
         return {"success": False, "error": "봇 차단 의심 (Amazon)"}
    
    return {"success": True, "platform": "Amazon", "title": title, "bullets": bullets, "price": ""}

def scrape_naver_smartstore(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers, timeout=10)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")
    
    title_meta = soup.find("meta", property="og:title")
    title = title_meta["content"] if title_meta else "제목을 찾을 수 없음"
    
    price = ""
    script_data = re.search(r'"price":(\d+)', res.text)
    if script_data:
         price = script_data.group(1)
         
    return {"success": True, "platform": "Naver SmartStore", "title": title, "bullets": [], "price": price}

def scrape_cafe24(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers, timeout=10)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")
    
    title_meta = soup.find("meta", property="og:title")
    title = title_meta["content"] if title_meta else "제목을 찾을 수 없음"
    
    price_meta = soup.find("meta", property="product:price:amount")
    price = price_meta["content"] if price_meta else ""
    
    return {"success": True, "platform": "Independent Mall", "title": title, "bullets": [], "price": price}

def get_product_data(url):
    """URL 도메인을 판독하여 알맞은 스크래퍼를 실행하는 라우터"""
    domain = urlparse(url).netloc
    try:
        if "amazon." in domain or "amzn.to" in domain:
            return scrape_amazon(url)
        elif "smartstore.naver.com" in domain:
            return scrape_naver_smartstore(url)
        else:
            return scrape_cafe24(url)
    except requests.RequestException as e:
        return {"success": False, "error": f"접속 실패 ({str(e)})"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ----- 텍스트 처리 헬퍼 함수 -----
def check_forbidden_words(text):
    found = []
    text_lower = text.lower()
    for word in AMAZON_RESTRICTED_WORDS:
        word_lower = word.lower()
        escaped = re.escape(word_lower)
        if re.fullmatch(r"[a-z0-9]+", word_lower):
            pattern = rf"\b{escaped}\b"
        else:
            pattern = escaped
        if re.search(pattern, text_lower):
            found.append(word)
    return sorted(set(found))

def render_result_box(result_text, file_prefix="amazon_pdp"):
    st.markdown("---")
    st.subheader("📄 AI 생성 결과 (원클릭 복사 & TXT 다운로드)")
    col_dl, col_blank = st.columns([2, 8])
    with col_dl:
        st.download_button(
            label="📥 전체 결과 TXT 다운로드",
            data=result_text,
            file_name=f"{file_prefix}_{int(time.time())}.txt",
            mime="text/plain",
            key=f"download_{file_prefix}"
        )
    result_hash = hashlib.md5(result_text.encode("utf-8")).hexdigest()[:8]
    st.text_area(
        label="📌 아래 상자 우측 상단의 [복사 아이콘]을 누르면 전체 문구가 클립보드에 바로 복사됩니다:",
        value=result_text,
        height=250,
        key=f"result_text_{file_prefix}_{result_hash}"
    )
    with st.expander("👁️ 서식 포함 예쁘게 보기 (Preview)", expanded=True):
        st.markdown(result_text)

def extract_numbered_section(text, section_num, next_section_num):
    pattern = rf"(?:^|\n)\s*(?:#{{1,4}}\s*)?\**{section_num}\.\s.*?(?=\n\s*(?:#{{1,4}}\s*)?\**{next_section_num}\.\s|\Z)"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(0).strip()
    return text

def strip_section_header(section_text):
    lines = section_text.split("\n", 1)
    return lines[1].strip() if len(lines) > 1 else ""

def utf8_byte_length(text):
    return len(text.encode("utf-8"))

def highlight_usp(text, raw_keywords):
    escaped_text = html.escape(text)
    keywords_to_highlight = set()
    if isinstance(raw_keywords, str) and raw_keywords.strip():
        words = [w.strip() for w in re.split(r'[,/|\s]+', raw_keywords) if len(w.strip()) > 1]
        for w in words:
            keywords_to_highlight.add(w)

    highlighted = escaped_text
    for kw in list(keywords_to_highlight)[:8]:
        pattern = re.compile(re.escape(html.escape(kw)), re.IGNORECASE)
        highlighted = pattern.sub(
            f"<mark style='background-color: #ffeb3b; color: #111111; padding: 2px 5px; "
            f"border-radius: 3px; font-weight: bold;'>{html.escape(kw)}</mark>",
            highlighted
        )
    return highlighted.replace("\n", "<br>")

def parse_bulk_listing(raw_text):
    title = ""
    bullets = [""] * 5
    title_match = re.search(r"##\s*1\.\s*Product Title\s*\n+(.+)", raw_text, re.IGNORECASE)
    if title_match:
        title = title_match.group(1).strip()

    bullet_section = re.search(r"##\s*2\.\s*Bullet Points\s*(.*?)(?=\n##|\Z)", raw_text, re.DOTALL | re.IGNORECASE)
    if bullet_section:
        found = re.findall(r"^\s*[*•-]\s+(.+)$", bullet_section.group(1), re.MULTILINE)
        for i, bullet in enumerate(found[:5]):
            bullets[i] = bullet.strip()
    return title, bullets[0], bullets[1], bullets[2], bullets[3], bullets[4]

def generate_ai_content(model_name, contents, error_label="AI 생성"):
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(contents)
        if not getattr(response, "text", None):
            raise ValueError("AI 응답이 비어 있습니다. 잠시 후 다시 시도해 주세요.")
        return response.text
    except Exception as e:
        st.error(f"❌ {error_label} 중 오류가 발생했습니다: {e}")
        return None

# ==========================================
# 4. 메인 화면 UI
# ==========================================
st.title("🚀 Chris PDP Converter (ULTIMATE - Multi Mall)")
st.caption(f"현재 선택된 프로젝트: **{st.session_state.current_project}** | 아마존/네이버/자사몰 수집 지원")

work_mode = st.radio("🛠️ 작업 모드 선택", ["단일 상품 정밀 분석 (Single)", "여러 상품 일괄 생성 (Bulk CSV)"], horizontal=True)
st.divider()

base_instruction = f"""
[기본 지침]
- 프로젝트명: {st.session_state.current_project}
- 타겟 국가/언어: {target_country}
- 브랜드 톤앤매너: {brand_tone}
- 추가 지시사항: {tone_extra}
- 지정된 언어로 매끄럽고 설득력 있게 작성하세요.

[사실성 및 안전 지침 - 반드시 준수]
- 사용자가 제공하지 않은 성분, 함량, 인증, 임상시험 결과를 임의로 만들어내지 마세요.
- "dermatologist-tested", "hypoallergenic", "FDA approved", "clinically proven",
  "vegan", "organic" 등의 표현은 입력 정보에 명시적으로 언급된 경우에만 사용하세요.
- 제품 효과를 치료, 완치, 또는 100% 보장하는 표현으로 작성하지 마세요.
- 입력 정보로 확인할 수 없는 사실은 추측해서 채우지 말고 생략하세요.
"""

if work_mode == "여러 상품 일괄 생성 (Bulk CSV)":
    # --- Bulk Processing 영역 (동일 유지) ---
    st.subheader("📦 다중 상품 일괄 생성 (Bulk Processing)")
    st.info("제품명이나 특징이 담긴 CSV 파일을 업로드하면 한 번에 리스팅을 생성합니다.")
    uploaded_csv = st.file_uploader("CSV 파일 업로드", type=['csv'])

    if uploaded_csv is not None:
        try:
            df = pd.read_csv(uploaded_csv)
        except Exception as e:
            st.error(f"CSV 파일을 읽는 중 오류가 발생했습니다: {e}")
            df = None

        if df is not None:
            df = df.dropna(how="all").reset_index(drop=True)
            if df.empty:
                st.warning("CSV에 처리할 상품 정보가 없습니다.")
            elif len(df) > MAX_BULK_ROWS:
                st.warning(f"최대 {MAX_BULK_ROWS}개 상품까지 처리할 수 있습니다.")
            else:
                st.dataframe(df.head())
                if st.button("🚀 일괄 생성 시작 (Batch Run)", type="primary"):
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    titles, b1_list, b2_list, b3_list, b4_list, b5_list, raw_results = [], [], [], [], [], [], []
                    total_items = len(df)

                    for i, row in df.iterrows():
                        product_info_bulk = str(row.to_dict())
                        status_text.text(f"처리 중: {i+1}번째 상품 ({i+1}/{total_items})")

                        prompt = f"""{base_instruction}
                        다음 상품 정보를 바탕으로 아마존 SEO Listing을 생성하세요.
                        상품정보: {product_info_bulk}

                        [출력 형식 - 아래 마크다운 형식을 지켜서 작성]
                        ## 1. Product Title
                        (제목 한 줄)

                        ## 2. Bullet Points
                        * (첫 번째)
                        * (두 번째)
                        * (세 번째)
                        * (네 번째)
                        * (다섯 번째)
                        """
                        time.sleep(2)
                        raw_text = generate_ai_content(selected_model, prompt, f"{i+1}번째 상품")
                        if raw_text:
                            title, b1, b2, b3, b4, b5 = parse_bulk_listing(raw_text)
                            bullets_parsed = [b1, b2, b3, b4, b5]
                            if not title or sum(bool(b) for b in bullets_parsed) < 5:
                                titles.append(title if title else "Parse Error")
                                b1_list.append(b1 if b1 else "⚠️ 출력 형식 파싱 실패")
                                b2_list.append(b2); b3_list.append(b3); b4_list.append(b4); b5_list.append(b5)
                            else:
                                titles.append(title); b1_list.append(b1); b2_list.append(b2); b3_list.append(b3); b4_list.append(b4); b5_list.append(b5)
                            raw_results.append(raw_text)
                        else:
                            titles.append("Error"); b1_list.append("생성 실패"); b2_list.append(""); b3_list.append(""); b4_list.append(""); b5_list.append("")
                            raw_results.append("에러 발생")
                        progress_bar.progress((i + 1) / total_items)

                    df['AI_Title'] = titles; df['Bullet_1'] = b1_list; df['Bullet_2'] = b2_list; df['Bullet_3'] = b3_list; df['Bullet_4'] = b4_list; df['Bullet_5'] = b5_list; df['Full_Raw_Output'] = raw_results
                    status_text.text("✅ 일괄 생성 완료! 아래에서 파일을 다운로드하세요.")
                    csv_data = df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button("📥 전체 결과 다운로드 (CSV)", data=csv_data, file_name=f"bulk_generated_{int(time.time())}.csv", mime="text/csv")

else:
    # --- Single Product 영역 ---
    st.markdown("### 📥 1. 제품 정보 입력 (링크/이미지/텍스트 중 선택 가능)")

    col_input1, col_input2 = st.columns(2)
    with col_input1:
        st.markdown("#### 🔗 [방법 A] URL로 자동 분석 (아마존/네이버/자사몰)")
        my_product_url = st.text_input(
            "내 제품 쇼핑몰 URL",
            value=current_p_data["my_product_url"],
            placeholder="https://...",
            key=f"url_{st.session_state.current_project}"
        )
        current_p_data["my_product_url"] = my_product_url
        uploaded_image = st.file_uploader("제품 패키지 / 상세페이지 이미지 업로드", type=["png", "jpg", "jpeg", "webp"])

    with col_input2:
        st.markdown("#### 📝 [방법 B] 직접 텍스트 입력")
        product_name = st.text_input(
            "제품명 (미입력 시 URL/이미지에서 자동 추론)",
            value=current_p_data["product_name"],
            key=f"name_{st.session_state.current_project}"
        )
        current_p_data["product_name"] = product_name
        key_features = st.text_area(
            "주요 특징/성분/소구점",
            value=current_p_data["key_features"],
            height=100,
            key=f"feat_{st.session_state.current_project}"
        )
        current_p_data["key_features"] = key_features

    with st.expander("⚔️ 경쟁사 비교 설정 (선택사항 - 클릭하여 열기)"):
        col_comp1, col_comp2 = st.columns(2)
        with col_comp1:
            competitor_url = st.text_input(
                "경쟁사 제품 URL (아마존/네이버/자사몰)",
                value=current_p_data["competitor_url"],
                key=f"comp_url_{st.session_state.current_project}"
            )
            current_p_data["competitor_url"] = competitor_url
        with col_comp2:
            competitor_info = st.text_input(
                "경쟁사 특징/단점 메모",
                value=current_p_data["competitor_info"],
                key=f"comp_info_{st.session_state.current_project}"
            )
            current_p_data["competitor_info"] = competitor_info

    st.markdown("---")
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📝 Amazon Listing (PDP)", "🎨 A+ Content Plan", "🎯 PPC Strategy", 
        "⚔️ 경쟁사 비교 분석", "📢 Seeding & Marketing Guide"
    ])

    def get_input_contents():
        contents = [base_instruction]
        if my_product_url:
            if not is_valid_url(my_product_url):
                st.warning("⚠️ 유효한 URL 형식이 아닙니다.")
                contents.append(f"내 제품 URL(참고용): {my_product_url}")
            else:
                crawl_result = get_product_data(my_product_url)
                if crawl_result.get("success"):
                    platform = crawl_result.get("platform", "Unknown")
                    title = crawl_result.get("title", "(제목 수집 실패)")
                    price = crawl_result.get("price", "")
                    bullets = crawl_result.get("bullets", [])
                    
                    info = f"내 제품 URL ({platform}): {my_product_url}\n수집된 제목: {title}"
                    if price:
                        info += f"\n수집된 가격: {price}"
                    if bullets:
                        bullet_text = "\n".join(f"- {b}" for b in bullets[:10])
                        info += f"\n수집된 특징(Bullet Points):\n{bullet_text}"
                    contents.append(info)
                else:
                    st.warning(f"⚠️ 페이지 수집에 실패했습니다: {crawl_result.get('error')}. 입력하신 URL만 참고합니다.")
                    contents.append(f"내 제품 URL(수집 실패): {my_product_url}")
                    
        if product_name: contents.append(f"제품명: {product_name}")
        if key_features: contents.append(f"제품 특징: {key_features}")
        if uploaded_image:
            contents.append("업로드된 제품 이미지:")
            contents.append(Image.open(uploaded_image))
        return contents

    with tab1:
        if st.button("🚀 PDP 리스팅 생성하기", type="primary"):
            inputs = get_input_contents()
            if len(inputs) <= 1:
                st.warning("URL, 이미지, 또는 제품명 중 최소 하나는 입력해 주세요!")
            else:
                with st.spinner("이미지/링크/텍스트 분석 후 리스팅 작성 중..."):
                    prompt = """
                    위 정보(이미지, URL, 텍스트)를 바탕으로 아마존 SEO 최적화 Listing을 생성하세요.
                    [출력 형식]
                    # Amazon Listing Optimization
                    ## 1. Product Title
                    ## 2. Bullet Points (5 Key Selling Points)
                    ## 3. Search Terms (249바이트 이내)
                    ## 4. Product Description
                    """
                    res_text = generate_ai_content(selected_model, inputs + [prompt], "PDP 리스팅 생성")
                    if res_text: current_p_data["results"]["tab1"] = res_text

        if "tab1" in current_p_data["results"]:
            res_text = current_p_data["results"]["tab1"]
            full_check_text = f"{product_name} {key_features} {res_text}"
            forbidden = check_forbidden_words(full_check_text)

            st.subheader("📊 리스팅 컴플라이언스 리포트")
            col1, col2 = st.columns([1, 2])
            with col1:
                compliance_score = max(0, 100 - (len(forbidden) * 20))
                st.metric("Amazon Copy Compliance Score", f"{compliance_score} / 100")
                st.progress(compliance_score / 100)
            with col2:
                if forbidden: st.error(f"⚠️ **정책 위반 의심 단어 감지 ({len(forbidden)}개)**: {', '.join(forbidden)}")
                else: st.success("✅ 위반 금지어가 감지되지 않았습니다.")

            title_section = strip_section_header(extract_numbered_section(res_text, 1, 2))
            search_terms_section = strip_section_header(extract_numbered_section(res_text, 3, 4))
            col3, col4 = st.columns(2)
            with col3:
                title_len = len(title_section.strip())
                st.metric("Product Title 글자 수", f"{title_len}자")
            with col4:
                st_bytes = utf8_byte_length(search_terms_section.strip())
                st.metric("Search Terms 바이트 수", f"{st_bytes} / 249 bytes")

            render_result_box(res_text, f"{st.session_state.current_project}_pdp_listing")

    with tab2:
        if st.button("🎨 A+ Content 기획안 생성"):
            inputs = get_input_contents()
            if len(inputs) > 1:
                with st.spinner("A+ 비주얼 스토리보드 기획 중..."):
                    prompt = """위 정보를 기반으로 아마존 A+ Content (EBC) 5개 모듈 스토리보드를 작성하세요:
                    - 모듈 1: Hero Banner / 모듈 2: Key Benefits / 모듈 3: Deep Dive / 모듈 4: How to Use / 모듈 5: Brand Story"""
                    result = generate_ai_content(selected_model, inputs + [prompt], "A+ Content 생성")
                    if result: current_p_data["results"]["tab2"] = result
        if "tab2" in current_p_data["results"]: render_result_box(current_p_data["results"]["tab2"], f"{st.session_state.current_project}_aplus_content")

    with tab3:
        if st.button("🎯 PPC 키워드 전략 추출"):
            inputs = get_input_contents()
            if len(inputs) > 1:
                with st.spinner("검색 키워드 분석 중..."):
                    prompt = "위 제품 정보를 분석하여 아마존 PPC 광고 키워드를 뽑아주세요 (Exact 10, Broad 10, Long-tail 10, Negative 5)"
                    result = generate_ai_content(selected_model, inputs + [prompt], "PPC 키워드 생성")
                    if result: current_p_data["results"]["tab3"] = result
        if "tab3" in current_p_data["results"]: render_result_box(current_p_data["results"]["tab3"], f"{st.session_state.current_project}_ppc_keywords")

    with tab4:
        if st.button("⚔️ 1:1 경쟁사 비교 분석 실행"):
            inputs = get_input_contents()
            if len(inputs) <= 1:
                st.warning("내 제품 정보를 먼저 입력해 주세요!")
            elif not competitor_url and not competitor_info:
                st.warning("경쟁사 URL 또는 메모를 입력해 주세요!")
            else:
                with st.spinner("경쟁사 비교 분석 중..."):
                    comp_lines = []
                    if competitor_info: comp_lines.append(f"메모: {competitor_info}")
                    if competitor_url:
                        if not is_valid_url(competitor_url):
                            st.warning("⚠️ 경쟁사 URL 형식이 올바르지 않아 메모만 참고합니다.")
                        else:
                            comp_lines.append(f"URL: {competitor_url}")
                            comp_crawl = get_product_data(competitor_url)
                            if comp_crawl.get("success"):
                                if comp_crawl.get("title"): comp_lines.append(f"수집된 경쟁사 제목: {comp_crawl['title']}")
                                if comp_crawl.get("price"): comp_lines.append(f"수집된 경쟁사 가격: {comp_crawl['price']}")
                                if comp_crawl.get("bullets"):
                                    bullet_text = "\n".join(f"- {b}" for b in comp_crawl["bullets"][:10])
                                    comp_lines.append(f"수집된 특징(Bullet Points):\n{bullet_text}")
                            else:
                                st.warning("⚠️ 경쟁사 페이지 수집에 실패했습니다. 입력하신 메모만 참고합니다.")

                    comp_text = "\n[경쟁사 정보]\n" + "\n".join(comp_lines)
                    prompt = f"""내 제품 정보와 다음 경쟁사 정보를 비교 분석해 주세요: {comp_text}
                    [출력 내용 - 번호 순서 유지]
                    1. 내 제품의 독점적 우위 (USP) / 2. 핵심 마케팅 메시지 / 3. 강조할 비주얼 요소 / 4. 1:1 비교 요약표
                    """
                    result = generate_ai_content(selected_model, inputs + [prompt], "경쟁사 비교 분석")
                    if result: current_p_data["results"]["tab4"] = result
                    
        if "tab4" in current_p_data["results"]:
            res_text = current_p_data["results"]["tab4"]
            st.markdown("#### 💡 Our Unique Selling Proposition (USP) Highlight")
            usp_text = extract_numbered_section(res_text, 1, 2)
            highlighted_usp = highlight_usp(usp_text, key_features)
            st.markdown(f'<div style="background-color: #1e1e24; color: #ffffff; padding: 18px; border-radius: 8px; border: 1px solid #33333e; margin-bottom: 20px; line-height: 1.6;">{highlighted_usp}</div>', unsafe_allow_html=True)
            render_result_box(res_text, f"{st.session_state.current_project}_competitor_analysis")

    with tab5:
        st.subheader("📢 인플루언서 시딩 & SNS 마케팅 가이드라인")
        if st.button("📢 시딩 & 마케팅 가이드 생성"):
            inputs = get_input_contents()
            if len(inputs) > 1:
                with st.spinner("마케팅 카피 및 시딩 가이드라인 제작 중..."):
                    prompt = "위 제품 정보를 바탕으로 마케팅팀과 인플루언서가 사용할 시딩 가이드(Seeding Brief)와 숏폼(Reels/TikTok) 광고 카피를 작성하세요."
                    result = generate_ai_content(selected_model, inputs + [prompt], "시딩 & 마케팅 가이드 생성")
                    if result: current_p_data["results"]["tab5"] = result
        if "tab5" in current_p_data["results"]: render_result_box(current_p_data["results"]["tab5"], f"{st.session_state.current_project}_seeding_guide")