import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import re

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="이커머스 상세페이지 기획 AI", layout="wide")
st.title("🛍️ 이커머스 상세페이지 기획 및 마케팅 AI")

# --- 2. API 키 및 모델 설정 (Sidebar) ---
with st.sidebar:
    st.header("⚙️ 설정")
    api_key = st.text_input("Google Gemini API Key", type="password")
    
    # 🚨 핵심 수정 부분: 3.6이나 3.1이 아닌, API 서버가 인식하는 정확한 공식 모델명 사용!
    model_choice = st.selectbox(
        "AI 모델 선택", 
        ["gemini-3.6-flash", "gemini-3.1-pro"] 
    )
    st.info("💡 속도는 Flash, 복잡한 추론과 품질은 Pro를 권장합니다.")

# API 키가 입력되면 설정 적용
if api_key:
    genai.configure(api_key=api_key)

# --- 3. 스크래퍼 및 라우터 함수 (뼈대) ---
def scrape_amazon(url):
    # 아마존 스크래핑 로직 (기존 코드의 BeautifulSoup/정규식 로직을 여기에 통합)
    return {"title": "아마존 임시 상품명", "price": "$99.99", "features": ["특징1", "특징2"]}

def scrape_smartstore(url):
    # 스마트스토어 스크래핑 로직
    return {"title": "스마트스토어 임시 상품명", "price": "100,000원", "features": ["특징A", "특징B"]}

def route_and_scrape(url):
    """URL 도메인을 판독하여 적절한 스크래퍼를 호출하고 데이터를 규격화합니다."""
    if "amazon" in url:
        return scrape_amazon(url)
    elif "naver" in url:
        return scrape_smartstore(url)
    else:
        return {"error": "지원하지 않는 쇼핑몰입니다."}

# --- 4. 메인 UI 및 탭 구성 ---
target_url = st.text_input("분석할 상품의 URL을 입력하세요:")

if st.button("데이터 수집 및 분석 시작"):
    if not api_key:
        st.warning("⚠️ 왼쪽 사이드바에 API 키를 먼저 입력해주세요.")
    elif not target_url:
        st.warning("⚠️ URL을 입력해주세요.")
    else:
        with st.spinner("데이터를 수집하고 AI를 호출하는 중입니다..."):
            try:
                # 1. 데이터 수집
                product_data = route_and_scrape(target_url)
                
                # 2. AI 모델 로드 (선택된 모델 사용)
                model = genai.GenerativeModel(model_choice)
                
                # 3. 프롬프트 생성 및 AI 호출 테스트
                prompt = f"다음 상품 데이터를 바탕으로 마케팅 포인트를 3가지로 요약해줘: {product_data}"
                response = model.generate_content(prompt)
                
                st.success("✅ AI 분석 완료!")
                
                # 4. 5개 탭으로 결과 보여주기
                tab1, tab2, tab3, tab4, tab5 = st.tabs([
                    "PDP 리스팅", "A+ Content", "PPC 전략", "마케팅 시딩 가이드", "AI 원본 요약"
                ])
                
                with tab1:
                    st.subheader("PDP 리스팅 기획")
                    st.write("(여기에 PDP 기획 결과 출력)")
                with tab2:
                    st.subheader("A+ Content 기획")
                    st.write("(여기에 A+ Content 결과 출력)")
                with tab3:
                    st.subheader("PPC 전략")
                    st.write("(여기에 PPC 광고 전략 출력)")
                with tab4:
                    st.subheader("마케팅 시딩 가이드")
                    st.write("(여기에 시딩 가이드 출력)")
                with tab5:
                    st.subheader("AI 원본 요약 테스트")
                    st.write(response.text) # 정상적으로 텍스트가 나오면 404 에러 해결된 것!

            except Exception as e:
                st.error(f"❌ 에러가 발생했습니다: {e}")