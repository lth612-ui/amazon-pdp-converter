import streamlit as st
import google.generativeai as genai
from PIL import Image
from bs4 import BeautifulSoup
import requests
import pandas as pd
import time
import re
import html
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

ALLOWED_AMAZON_DOMAINS = {
    "amazon.com", "www.amazon.com",
    "amazon.co.uk", "www.amazon.co.uk",
    "amazon.de", "www.amazon.de",
    "amazon.co.jp", "www.amazon.co.jp",
    "amazon.fr", "www.amazon.fr",
}

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
    """프로젝트별 데이터 저장 공간 초기화 함수"""
    if proj_name not in st.session_state.project_data:
        st.session_state.project_data[proj_name] = {
            "my_product_url": "",
            "product_name": "",
            "key_features": "",
            "competitor_url": "",
            "competitor_info": "",
            "results": {},  # 각 탭별 생성 결과 저장 (tab1, tab2, tab3, tab4, tab5)
            # [추가] 프로젝트별로 국가/톤/모델 설정도 함께 저장 (전에는 사이드바 설정이 전역 공유였음)
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

# [수정] current_p_data를 다른 사이드바 옵션(모델/국가/톤)보다 먼저 확보해서
# 아래 위젯들이 "프로젝트별 저장된 값"을 기본값으로 사용할 수 있게 한다.
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

st.sidebar.markdown("---")
st.sidebar.info(
    "💡 **프로젝트 세션 자동 저장 작동 중**\n"
    "- 프로젝트를 변경해도 입력 내용, 국가/톤 설정, AI 생성 결과가 보존됩니다.\n"
    "- (단, 업로드한 이미지는 프로젝트별로 저장되지 않습니다.)"
)

# ==========================================
# 3. 헬퍼 함수
# ==========================================
def check_forbidden_words(text):
    text_lower = text.lower()
    found = [word for word in AMAZON_RESTRICTED_WORDS if word in text_lower]
    return list(set(found))

def is_valid_amazon_url(url):
    """아마존 도메인 형식인지 최소한으로 검증한다."""
    try:
        parsed = urlparse(url.strip())
        return parsed.scheme in {"http", "https"} and parsed.hostname in ALLOWED_AMAZON_DOMAINS
    except ValueError:
        return False

def crawl_amazon_url(url):
    """
    아마존 상품 페이지에서 제목과 Bullet Point를 수집한다.
    [수정] 성공/실패를 명확히 구분해서 반환한다 (이전에는 실패해도 URL을 그대로 반환해
    호출부에서 성공 여부를 알 수 없었음).
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        title_tag = soup.select_one("#productTitle")
        bullet_tags = soup.select("#feature-bullets li span")
        return {
            "success": True,
            "title": title_tag.get_text(" ", strip=True) if title_tag else "",
            "bullets": [b.get_text(" ", strip=True) for b in bullet_tags if b.get_text(strip=True)]
        }
    except requests.RequestException as e:
        return {"success": False, "error": str(e)}

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
            key=f"download_{file_prefix}"  # [수정] 탭 간 위젯 key 충돌 방지
        )

    st.text_area(
        label="📌 아래 상자 우측 상단의 [복사 아이콘]을 누르면 전체 문구가 클립보드에 바로 복사됩니다:",
        value=result_text,
        height=250,
        key=f"result_text_{file_prefix}"  # [수정] 탭 간 위젯 key 충돌 방지
    )

    with st.expander("👁️ 서식 포함 예쁘게 보기 (Preview)", expanded=True):
        # [수정] AI 결과는 마크다운 문법만 사용하므로 unsafe_allow_html이 필요 없음.
        # 혹시 모델이 임의 HTML 태그를 출력해도 그대로 렌더링되지 않도록 기본 마크다운만 사용.
        st.markdown(result_text)

def extract_numbered_section(text, section_num, next_section_num):
    """
    언어(한/영)에 상관없이 'N. ...' 형태의 넘버링 섹션 헤더를 기준으로
    section_num 부터 next_section_num 직전까지의 텍스트를 추출한다.
    """
    pattern = rf"(?:^|\n)\s*(?:#{{1,4}}\s*)?\**{section_num}\.\s.*?(?=\n\s*(?:#{{1,4}}\s*)?\**{next_section_num}\.\s|\Z)"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(0).strip()
    return text

def strip_section_header(section_text):
    """섹션 텍스트에서 첫 줄(헤더)을 제거하고 본문만 반환한다."""
    lines = section_text.split("\n", 1)
    return lines[1].strip() if len(lines) > 1 else ""

def utf8_byte_length(text):
    return len(text.encode("utf-8"))

def highlight_usp(text, raw_keywords):
    """
    사용자가 입력한 key_features 에서만 키워드를 추출해 하이라이트한다.
    [수정] 원문을 먼저 html.escape() 처리한 뒤 하이라이트 태그를 삽입해,
    모델 출력에 우연히 <, > 같은 문자가 있어도 HTML이 깨지지 않도록 한다.
    """
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

    highlighted = highlighted.replace("\n", "<br>")
    return highlighted

def parse_bulk_listing(raw_text):
    """
    [수정] 이전 버전은 원문 전체에서 '숫자.'나 '*' 로 시작하는 모든 줄을 Bullet로 잡아서
    "1. Product Title" 같은 헤더 줄까지 Bullet_1에 들어가는 문제가 있었다.
    이번에는 '## 2. Bullet Points' 섹션을 먼저 잘라낸 뒤, 그 안에서만 Bullet(* 로 시작하는 줄)을 찾는다.
    """
    title = ""
    bullets = [""] * 5

    title_match = re.search(
        r"##\s*1\.\s*Product Title\s*\n+(.+)",
        raw_text, re.IGNORECASE
    )
    if title_match:
        title = title_match.group(1).strip()

    bullet_section = re.search(
        r"##\s*2\.\s*Bullet Points\s*(.*?)(?=\n##|\Z)",
        raw_text, re.DOTALL | re.IGNORECASE
    )
    if bullet_section:
        found = re.findall(
            r"^\s*[*•-]\s+(.+)$",
            bullet_section.group(1),
            re.MULTILINE
        )
        for i, bullet in enumerate(found[:5]):
            bullets[i] = bullet.strip()

    return title, bullets[0], bullets[1], bullets[2], bullets[3], bullets[4]

def generate_ai_content(model_name, contents, error_label="AI 생성"):
    """
    [추가] 모든 Gemini 호출을 감싸는 공통 함수.
    이전에는 tab1(PDP)만 try/except가 있었고 나머지 탭은 예외 발생 시 앱이
    긴 스택트레이스 오류 화면을 그대로 보여주는 문제가 있었다.
    """
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
st.title("🚀 Chris PDP Converter (ULTIMATE)")
st.caption(f"현재 선택된 프로젝트: **{st.session_state.current_project}** | 아마존 PDP, A+ Content, PPC, 경쟁사 분석 & 시딩 가이드")

work_mode = st.radio("🛠️ 작업 모드 선택", ["단일 상품 정밀 분석 (Single)", "여러 상품 일괄 생성 (Bulk CSV)"], horizontal=True)
st.divider()

# [기본 지침 + 사실성/안전 지침]
# [수정] AI가 사용자가 제공하지 않은 인증(dermatologist-tested 등)이나 임상 결과, 성분 함량을
# 임의로 만들어내는 문제를 막기 위한 지침을 추가했다.
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
            # [수정] 빈 CSV, 과도한 행 수, 완전 빈 행을 미리 검증한다.
            df = df.dropna(how="all").reset_index(drop=True)

            if df.empty:
                st.warning("CSV에 처리할 상품 정보가 없습니다. 파일 내용을 확인해 주세요.")
            elif len(df) > MAX_BULK_ROWS:
                st.warning(f"한 번에 최대 {MAX_BULK_ROWS}개 상품까지 처리할 수 있습니다. 파일을 나눠서 업로드해 주세요. (현재 {len(df)}개)")
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

                        # [수정] parse_bulk_listing()이 기대하는 출력 포맷을 명시적으로 강제한다.
                        prompt = f"""{base_instruction}

                        다음 상품 정보를 바탕으로 아마존 SEO Listing을 생성하세요.
                        상품정보: {product_info_bulk}

                        [출력 형식 - 반드시 아래 마크다운 형식을 그대로 지켜서 작성하세요]
                        ## 1. Product Title
                        (제목 한 줄)

                        ## 2. Bullet Points
                        * (첫 번째 셀링 포인트)
                        * (두 번째 셀링 포인트)
                        * (세 번째 셀링 포인트)
                        * (네 번째 셀링 포인트)
                        * (다섯 번째 셀링 포인트)
                        """

                        time.sleep(2)
                        raw_text = generate_ai_content(selected_model, prompt, f"{i+1}번째 상품 생성")

                        if raw_text:
                            title, b1, b2, b3, b4, b5 = parse_bulk_listing(raw_text)
                            titles.append(title)
                            b1_list.append(b1)
                            b2_list.append(b2)
                            b3_list.append(b3)
                            b4_list.append(b4)
                            b5_list.append(b5)
                            raw_results.append(raw_text)
                        else:
                            titles.append("Error")
                            b1_list.append("생성 실패 - 아래 Full_Raw_Output 참고")
                            b2_list.append("")
                            b3_list.append("")
                            b4_list.append("")
                            b5_list.append("")
                            raw_results.append("에러 발생: AI 응답을 받지 못했습니다.")

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
                    st.download_button("📥 전체 결과 다운로드 (CSV)", data=csv_data,
                                        file_name=f"bulk_generated_{int(time.time())}.csv", mime="text/csv")

else:
    st.markdown("### 📥 1. 제품 정보 입력 (링크/이미지/텍스트 중 선택 가능)")

    col_input1, col_input2 = st.columns(2)

    with col_input1:
        st.markdown("#### 🔗 [방법 A] 아마존 URL로 자동 분석 (제목/Bullet 수집)")
        my_product_url = st.text_input(
            "내 제품 아마존 URL",
            value=current_p_data["my_product_url"],
            placeholder="https://www.amazon.com/dp/...",
            key=f"url_{st.session_state.current_project}"
        )
        current_p_data["my_product_url"] = my_product_url

        uploaded_image = st.file_uploader("제품 패키지 / 상세페이지 이미지 업로드", type=["png", "jpg", "jpeg", "webp"])

    with col_input2:
        st.markdown("#### 📝 [방법 B] 직접 텍스트 입력")
        product_name = st.text_input(
            "제품명 (미입력 시 URL/이미지에서 자동 추론)",
            value=current_p_data["product_name"],
            placeholder="예: 비타민 C 세럼 30ml",
            key=f"name_{st.session_state.current_project}"
        )
        current_p_data["product_name"] = product_name

        key_features = st.text_area(
            "주요 특징/성분/소구점",
            value=current_p_data["key_features"],
            placeholder="예: 순수 비타민C 15%, 피부 톤 개선, 끈적임 없는 수분제형",
            height=100,
            key=f"feat_{st.session_state.current_project}"
        )
        current_p_data["key_features"] = key_features

    with st.expander("⚔️ 경쟁사 비교 설정 (선택사항 - 클릭하여 열기)"):
        col_comp1, col_comp2 = st.columns(2)
        with col_comp1:
            competitor_url = st.text_input(
                "경쟁사 제품 아마존 URL",
                value=current_p_data["competitor_url"],
                placeholder="https://www.amazon.com/dp/...",
                key=f"comp_url_{st.session_state.current_project}"
            )
            current_p_data["competitor_url"] = competitor_url
        with col_comp2:
            competitor_info = st.text_input(
                "경쟁사 특징/단점 메모",
                value=current_p_data["competitor_info"],
                placeholder="예: 경쟁사는 가격이 비싸고 용량이 적음",
                key=f"comp_info_{st.session_state.current_project}"
            )
            current_p_data["competitor_info"] = competitor_info

    st.markdown("---")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📝 Amazon Listing (PDP)",
        "🎨 A+ Content Plan",
        "🎯 PPC Strategy",
        "⚔️ 경쟁사 비교 분석",
        "📢 Seeding & Marketing Guide"
    ])

    def get_input_contents():
        """
        [수정] 아마존 URL 자동 분석의 성공/실패를 명확히 구분해서 사용자에게 알리고,
        URL이 아마존 도메인 형식이 아니면 경고한다. 성공 시 제목뿐 아니라
        Bullet Point(feature-bullets)까지 함께 수집해 AI 입력으로 활용한다.
        """
        contents = [base_instruction]
        if my_product_url:
            if not is_valid_amazon_url(my_product_url):
                st.warning("⚠️ 유효한 Amazon URL 형식이 아닙니다. URL을 다시 확인하거나 이미지/텍스트를 함께 입력해 주세요.")
                contents.append(f"내 제품 아마존 URL(형식 미검증, 참고용): {my_product_url}")
            else:
                crawl_result = crawl_amazon_url(my_product_url)
                if crawl_result.get("success"):
                    title = crawl_result.get("title") or "(제목 수집 실패)"
                    bullets = crawl_result.get("bullets") or []
                    info = f"내 제품 아마존 URL: {my_product_url}\n수집된 제목: {title}"
                    if bullets:
                        bullet_text = "\n".join(f"- {b}" for b in bullets[:10])
                        info += f"\n수집된 특징(Bullet Points):\n{bullet_text}"
                    contents.append(info)
                else:
                    st.warning("⚠️ Amazon 페이지 수집에 실패했습니다 (봇 차단 또는 접근 제한 가능). 이미지나 텍스트를 함께 입력해 주세요.")
                    contents.append(f"내 제품 아마존 URL(수집 실패, URL만 참고): {my_product_url}")
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
                    res_text = generate_ai_content(selected_model, inputs + [prompt], "PDP 리스팅 생성")
                    if res_text:
                        current_p_data["results"]["tab1"] = res_text

        if "tab1" in current_p_data["results"]:
            res_text = current_p_data["results"]["tab1"]
            full_check_text = f"{product_name} {key_features} {res_text}"
            forbidden = check_forbidden_words(full_check_text)

            # [수정] 실제 검사 항목(금지어)에 맞춰 명칭을 "Amazon Copy Compliance Score"로 변경.
            # 추가로 Search Terms 249바이트 제한과 타이틀 길이를 프롬프트 요청에만 의존하지 않고
            # 코드로 직접 측정해서 보여준다.
            st.subheader("📊 리스팅 컴플라이언스 리포트")
            col1, col2 = st.columns([1, 2])
            with col1:
                compliance_score = max(0, 100 - (len(forbidden) * 20))
                st.metric(label="Amazon Copy Compliance Score", value=f"{compliance_score} / 100")
                st.progress(compliance_score / 100)
            with col2:
                if forbidden:
                    st.error(f"⚠️ **아마존 정책 위반 의심 단어 감지 ({len(forbidden)}개)**: {', '.join(forbidden)}")
                else:
                    st.success("✅ 아마존 정책 위반 금지어가 감지되지 않았습니다.")

            title_section = strip_section_header(extract_numbered_section(res_text, 1, 2))
            search_terms_section = strip_section_header(extract_numbered_section(res_text, 3, 4))

            col3, col4 = st.columns(2)
            with col3:
                title_len = len(title_section.strip())
                st.metric("Product Title 글자 수", f"{title_len}자")
                if title_len > 200:
                    st.caption("⚠️ 아마존 권장 타이틀 길이(약 200자)를 초과했습니다.")
            with col4:
                st_bytes = utf8_byte_length(search_terms_section.strip())
                st.metric("Search Terms 바이트 수", f"{st_bytes} / 249 bytes")
                if st_bytes > 249:
                    st.caption("⚠️ 249바이트를 초과했습니다. 아마존이 초과분을 잘라서 인덱싱하지 않을 수 있습니다.")

            render_result_box(res_text, f"{st.session_state.current_project}_pdp_listing")

    # Tab 2: A+ Content
    with tab2:
        if st.button("🎨 A+ Content 기획안 생성"):
            inputs = get_input_contents()
            if len(inputs) <= 1:
                st.warning("제품 정보를 입력하거나 이미지를 업로드해 주세요!")
            else:
                with st.spinner("A+ 비주얼 스토리보드 기획 중..."):
                    prompt = """
                    위 정보를 기반으로 아마존 A+ Content (EBC) 5개 모듈 스토리보드를 작성하세요:
                    - 모듈 1: Hero Banner (브랜드 카피 및 이미지 레이아웃 제안)
                    - 모듈 2: Key Benefits (3대 핵심 효능 파트)
                    - 모듈 3: Deep Dive / Technology (성분/기술력 비주얼 제안)
                    - 모듈 4: How to Use (사용 단계 및 꿀팁)
                    - 모듈 5: Brand Story & Cross-selling
                    """
                    result = generate_ai_content(selected_model, inputs + [prompt], "A+ Content 생성")
                    if result:
                        current_p_data["results"]["tab2"] = result

        if "tab2" in current_p_data["results"]:
            render_result_box(current_p_data["results"]["tab2"], f"{st.session_state.current_project}_aplus_content")

    # Tab 3: PPC Strategy
    with tab3:
        if st.button("🎯 PPC 키워드 전략 추출"):
            inputs = get_input_contents()
            if len(inputs) <= 1:
                st.warning("제품 정보를 입력해 주세요!")
            else:
                with st.spinner("검색 키워드 분석 중..."):
                    prompt = """
                    위 제품 정보를 분석하여 아마존 PPC 광고 키워드를 뽑아주세요:
                    1. Exact Match Keywords (전환율 높은 메인 키워드 10개)
                    2. Broad/Phrase Keywords (확장형 키워드 10개)
                    3. Long-tail Keywords (세부 타겟 키워드 10개)
                    4. Negative Keywords (광고비 절감을 위한 제외 키워드 5개)
                    """
                    result = generate_ai_content(selected_model, inputs + [prompt], "PPC 키워드 생성")
                    if result:
                        current_p_data["results"]["tab3"] = result

        if "tab3" in current_p_data["results"]:
            render_result_box(current_p_data["results"]["tab3"], f"{st.session_state.current_project}_ppc_keywords")

    # Tab 4: Competitor Comparison
    with tab4:
        if st.button("⚔️ 1:1 경쟁사 비교 분석 실행"):
            inputs = get_input_contents()
            if len(inputs) <= 1:
                st.warning("내 제품 정보(URL/이미지/제품명 등)를 먼저 입력해 주세요!")
            elif not competitor_url and not competitor_info:
                st.warning("상단의 경쟁사 비교 설정에 경쟁사 URL 또는 정보를 입력해 주세요!")
            else:
                with st.spinner("내 제품과 경쟁사 비교 분석 중..."):
                    comp_lines = [f"URL: {competitor_url}" if competitor_url else "", f"메모: {competitor_info}" if competitor_info else ""]

                    if competitor_url:
                        if not is_valid_amazon_url(competitor_url):
                            st.warning("⚠️ 경쟁사 URL이 유효한 Amazon URL 형식이 아닙니다. 메모만 참고합니다.")
                        else:
                            comp_crawl = crawl_amazon_url(competitor_url)
                            if comp_crawl.get("success") and comp_crawl.get("title"):
                                comp_lines.append(f"수집된 경쟁사 제목: {comp_crawl['title']}")
                            else:
                                st.warning("⚠️ 경쟁사 페이지 수집에 실패했습니다. 입력하신 메모만 근거로 분석합니다.")

                    comp_text = "\n[경쟁사 정보]\n" + "\n".join(line for line in comp_lines if line)

                    prompt = f"""
                    내 제품 정보와 다음 경쟁사 정보를 비교 분석해 주세요: {comp_text}

                    [출력 내용 - 아래 번호 순서를 반드시 지켜서 작성]
                    1. 내 제품의 독점적 우위 (USP)
                    2. 경쟁사 고객 스틸을 위한 핵심 마케팅 메시지
                    3. PDP에서 강조해야 할 비주얼 요소
                    4. 1:1 비교 요약표 (성분/기능, 가성비, 타겟층, 소구점)
                    """
                    result = generate_ai_content(selected_model, inputs + [prompt], "경쟁사 비교 분석")
                    if result:
                        current_p_data["results"]["tab4"] = result

        if "tab4" in current_p_data["results"]:
            res_text = current_p_data["results"]["tab4"]
            st.markdown("#### 💡 Our Unique Selling Proposition (USP) Highlight")

            usp_text = extract_numbered_section(res_text, 1, 2)
            highlighted_usp = highlight_usp(usp_text, key_features)

            st.markdown(
                f"""
                <div style="background-color: #1e1e24; color: #ffffff; padding: 18px; border-radius: 8px; border: 1px solid #33333e; margin-bottom: 20px; line-height: 1.6;">
                    {highlighted_usp}
                </div>
                """,
                unsafe_allow_html=True
            )
            render_result_box(res_text, f"{st.session_state.current_project}_competitor_analysis")

    # Tab 5: Seeding & Marketing Guide
    with tab5:
        st.subheader("📢 인플루언서 시딩 & SNS 마케팅 가이드라인")
        if st.button("📢 시딩 & 마케팅 가이드 생성"):
            inputs = get_input_contents()
            if len(inputs) <= 1:
                st.warning("제품 정보를 입력하거나 이미지를 업로드해 주세요!")
            else:
                with st.spinner("마케팅 카피 및 시딩 가이드라인 제작 중..."):
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
                    result = generate_ai_content(selected_model, inputs + [prompt], "시딩 & 마케팅 가이드 생성")
                    if result:
                        current_p_data["results"]["tab5"] = result

        if "tab5" in current_p_data["results"]:
            render_result_box(current_p_data["results"]["tab5"], f"{st.session_state.current_project}_seeding_guide")