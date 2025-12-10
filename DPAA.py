# -*- coding: utf-8 -*-
# 🎬 드라마 사전분석 아카이브 (Streamlit + 공개 Google Sheets CSV + Google Slides Embed)

# region [1. Imports & 기본 설정]
import re
from typing import List, Optional
from urllib.parse import urlparse, parse_qs, quote

import pandas as pd
import streamlit as st
from streamlit.components.v1 import iframe as st_iframe

# 페이지 설정
PAGE_TITLE = "드라마 사전분석 아카이브"
PAGE_ICON = "🎬"

st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# 상단 헤더 / 메뉴 / 푸터 / 사이드바 숨기기 & 전체 배경 톤 조정
HIDE_STREAMLIT_UI = """
<style>
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}
section[data-testid="stSidebar"] {display:none !important;}

/* 상단 여백 제거 */
.block-container {
    padding-top: 0rem !important;
    padding-bottom: 2rem !important;
    max-width: 95% !important;
}
[data-testid="stHeader"] {
    display: none;
}
</style>
"""
st.markdown(HIDE_STREAMLIT_UI, unsafe_allow_html=True)

# 시크릿에서 관리시트 URL 읽기
ARCHIVE_SHEET_URL = st.secrets.get("ARCHIVE_SHEET_URL", "")

# 뷰 모드 및 파라미터 처리
VIEW_MODE_LIST = "list"
VIEW_MODE_DETAIL = "detail"

params = st.query_params
CURRENT_VIEW_MODE = params.get("view", VIEW_MODE_LIST)
CURRENT_SELECTED_IP = params.get("ip", None)
# endregion


# region [2. 스타일 (CSS) 정의]
# ==============================================================================
# 2. 스타일 (CSS) 정의
# ==============================================================================
CUSTOM_CSS = """
<style>
/* 폰트 및 기본 컬러 */
html, body, [class*="css"]  {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, 'Helvetica Neue', 'Segoe UI', 'Apple SD Gothic Neo', 'Noto Sans KR', 'Malgun Gothic', sans-serif;
    color: #e0e0e0;
}
[data-testid="stAppViewContainer"] {
    background-color: #141414;
}

/* ---- [수정 1] 필터 입력창 스타일 개선 (Placeholder 밝게) ---- */
[data-testid="stTextInput"] input {
    background-color: #2b2b2b !important;
    color: #ffffff !important;
    border: 1px solid #444 !important;
}
/* 안내 문구(Placeholder) 색상 변경 */
[data-testid="stTextInput"] input::placeholder {
    color: #bbbbbb !important;
    opacity: 1 !important;
}
/* 멀티셀렉트 스타일 */
[data-baseweb="select"] > div {
    background-color: #2b2b2b !important;
    border-color: #444 !important;
    color: white !important;
}
[data-baseweb="select"] input::placeholder {
    color: #bbbbbb !important;
}
[data-baseweb="tag"] {
    background-color: #444 !important;
    color: #eee !important;
}
[data-baseweb="menu"] {
    background-color: #2b2b2b !important;
    border-color: #444 !important;
}

/* 타이틀 */
.main-title {
    font-size: 32px;
    font-weight: 800;
    letter-spacing: -0.02em;
    background: linear-gradient(135deg, #FF5F6D 0%, #FFC371 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-top: 2rem;
    margin-bottom: 0.2rem;
}
.subtitle {
    color: #888;
    font-size: 14px;
    margin-bottom: 1.5rem;
}
.detail-title {
    font-size: 36px;
    font-weight: 700;
    color: #ffffff;
    margin-bottom: 0.5rem;
}
.detail-meta {
    font-size: 14px;
    color: #b3b3b3;
    margin-bottom: 1rem;
}

/* 카드 UI */
.drama-card {
    border-radius: 0;
    padding: 0;
    margin-bottom: 24px;
    background: transparent;
    border: none;
    display: block;
    cursor: pointer;
    position: relative;
}
.drama-card-link {
    text-decoration: none;
    color: inherit;
    display: block;
}

/* 포스터 래퍼 */
.poster-wrapper {
    position: relative;
    width: 100%;
    padding-bottom: 150%; /* 2:3 */
    border-radius: 12px;
    overflow: hidden;
    background-color: #1f1f1f;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    transition: transform 0.25s ease;
    z-index: 1;
}
.drama-poster {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    object-position: center;
    display: block;
    z-index: 2;
}
.drama-card:hover .poster-wrapper {
    transform: translateY(-5px);
    box-shadow: 0 12px 24px rgba(0, 0, 0, 0.5);
    z-index: 10;
}

/* 오버레이 */
.drama-overlay {
    position: absolute;
    inset: 0;
    background: linear-gradient(
        to bottom,
        rgba(0,0,0,0) 0%,
        rgba(0,0,0,0.6) 40%,
        rgba(0,0,0,0.95) 90%
    );
    opacity: 0;
    transition: opacity 0.2s ease;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    padding: 20px 16px;
    z-index: 3;
}
.drama-card:hover .drama-overlay {
    opacity: 1;
}
.overlay-title {
    font-size: 17px;
    font-weight: 700;
    color: #fff;
    margin-bottom: 6px;
    text-shadow: 0 1px 2px rgba(0,0,0,0.8);
    line-height: 1.2;
}
.overlay-meta {
    font-size: 12px;
    color: #d1d1d1;
    margin-bottom: 12px;
    line-height: 1.3;
}
.overlay-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    max-height: 80px;
    overflow: hidden;
}
.tag-badge {
    display: inline-block;
    padding: 3px 8px;
    border-radius: 4px;
    background: rgba(255, 255, 255, 0.15);
    border: 1px solid rgba(255, 255, 255, 0.25);
    font-size: 10px;
    color: #fff;
    backdrop-filter: blur(4px);
    white-space: nowrap;
}

/* 상세페이지 임베드 */
.embed-container {
    margin-top: 20px;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 20px 50px rgba(0,0,0,0.6);
    background: #000;
    border: 1px solid #333;
}
.back-button {
    display: inline-flex;
    align-items: center;
    padding: 8px 16px;
    margin-bottom: 10px;
    background-color: #333;
    border-radius: 6px;
    color: #fff !important;
    text-decoration: none !important;
    font-size: 13px;
}
.back-button:hover { background-color: #444; }
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
# endregion


# region [3. 데이터 로딩]
def build_csv_url_from_sheet_url(sheet_url: str) -> Optional[str]:
    if not isinstance(sheet_url, str) or sheet_url.strip() == "":
        return None
    m = re.search(r"/spreadsheets/d/([^/]+)/", sheet_url)
    if not m:
        return None
    sheet_id = m.group(1)
    parsed = urlparse(sheet_url)
    qs = parse_qs(parsed.query)
    gid = qs.get("gid", ["0"])[0]
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

@st.cache_data(ttl=300, show_spinner=False)
def load_archive_df() -> pd.DataFrame:
    csv_url = build_csv_url_from_sheet_url(ARCHIVE_SHEET_URL)
    if not csv_url:
        return normalize_archive_df(pd.DataFrame([{
            "IP명": "데이터 연동 필요", "해시태그": "#예시"
        }]))
    try:
        df_raw = pd.read_csv(csv_url)
        return normalize_archive_df(df_raw)
    except Exception:
        return pd.DataFrame()

def normalize_archive_df(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        "IP명": "ip_name", "IP": "ip_name",
        "프레젠테이션주소": "pres_url", "프레젠테이션 주소": "pres_url",
        "프레젠테이션 URL": "pres_url", "프레젠테이션": "pres_url",
        "장표범위": "slide_range", "노출 장표": "slide_range",
        "해시태그": "hashtags",
        "포스터이미지URL": "poster_url", "포스터 이미지 URL": "poster_url",
        "작성월": "written_month", "방영일": "air_date", "주연배우": "main_cast",
    }
    for k, v in rename_map.items():
        if k in df.columns and v not in df.columns:
            df = df.rename(columns={k: v})
            
    required_cols = ["ip_name", "pres_url", "slide_range", "hashtags", "poster_url", "written_month", "air_date", "main_cast"]
    for col in required_cols:
        if col not in df.columns:
            df[col] = ""
            
    for c in required_cols:
        df[c] = df[c].astype(str).str.strip()
        
    df["hashtags_list"] = df["hashtags"].apply(parse_hashtags)
    return df[df["ip_name"] != ""].reset_index(drop=True)

def parse_hashtags(tag_str: str) -> List[str]:
    if not tag_str: return []
    return ["#" + t.strip() for t in tag_str.split("#") if t.strip()]

def collect_all_hashtags(df: pd.DataFrame) -> List[str]:
    tags = set()
    for row_tags in df["hashtags_list"]:
        tags.update(row_tags)
    return sorted(tags)
# endregion


# region [4. 뷰 렌더링]

# 4-1. 헤더 & 필터
def render_header_filter(df: pd.DataFrame):
    st.markdown(f'<div class="main-title">{PAGE_TITLE}</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">IP별 분석 리포트 아카이브</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    with col1:
        keyword = st.text_input("검색", placeholder="작품명 또는 키워드 입력...", label_visibility="collapsed")
    with col2:
        all_tags = collect_all_hashtags(df)
        selected_tags = st.multiselect("태그", options=all_tags, placeholder="해시태그 선택", label_visibility="collapsed")
    
    st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
    return keyword, selected_tags

def filter_archive(df, keyword, selected_tags):
    temp = df.copy()
    if keyword:
        k = keyword.lower()
        temp = temp[temp["ip_name"].str.lower().str.contains(k) | temp["hashtags"].str.lower().str.contains(k)]
    if selected_tags:
        s = set(selected_tags)
        temp = temp[temp["hashtags_list"].apply(lambda x: s.issubset(set(x)))]
    return temp

# 4-2. 리스트 뷰
def render_list_view(df: pd.DataFrame):
    keyword, selected_tags = render_header_filter(df)
    filtered = filter_archive(df, keyword, selected_tags)
    
    if filtered.empty:
        st.info("조건에 맞는 작품이 없습니다.")
        return

    per_row = 5
    rows = [filtered.iloc[i:i+per_row] for i in range(0, len(filtered), per_row)]

    for row_data in rows:
        cols = st.columns(per_row)
        for idx, (_, row) in enumerate(row_data.iterrows()):
            with cols[idx]:
                ip_name = row["ip_name"]
                poster_url = row["poster_url"] if row["poster_url"].startswith("http") else "https://via.placeholder.com/300x450/111/555?text=No+Img"
                
                meta = []
                if row["main_cast"] != "nan" and row["main_cast"]: meta.append(row["main_cast"])
                if row["air_date"] != "nan" and row["air_date"]: meta.append(row["air_date"])
                meta_html = "<br>".join(meta)
                
                tags_html = "".join([f'<span class="tag-badge">{t}</span>' for t in row["hashtags_list"]])
                link = f"?view={VIEW_MODE_DETAIL}&ip={quote(ip_name)}"
                
                # [수정 2] 포스터 이미지 태그에 referrerpolicy="no-referrer" 추가하여 로딩 문제 해결
                st.markdown(f"""
                <a href="{link}" class="drama-card-link" target="_self">
                    <div class="drama-card">
                        <div class="poster-wrapper">
                            <img class="drama-poster" src="{poster_url}" alt="{ip_name}" referrerpolicy="no-referrer">
                            <div class="drama-overlay">
                                <div class="overlay-title">{ip_name}</div>
                                <div class="overlay-meta">{meta_html}</div>
                                <div class="overlay-tags">{tags_html}</div>
                            </div>
                        </div>
                    </div>
                </a>
                """, unsafe_allow_html=True)

# 4-3. 상세 뷰
def build_embed_url(pres_url: str):
    if not pres_url or "docs.google.com" not in pres_url: return None
    m = re.search(r"/d/([^/]+)/", pres_url)
    if not m: return None
    # [수정 3] rm=minimal 제거 -> 하단 컨트롤 바(화살표) 생성되어 뒤로가기 가능
    return f"https://docs.google.com/presentation/d/{m.group(1)}/embed?start=false&loop=false&delayms=3000"

def render_detail_view(df: pd.DataFrame, selected_ip: str):
    st.markdown(f'<a href="?view={VIEW_MODE_LIST}" class="back-button" target="_self">← 목록으로</a>', unsafe_allow_html=True)
    
    row = df[df["ip_name"] == selected_ip]
    if row.empty:
        st.error("잘못된 접근입니다.")
        return
    row = row.iloc[0]
    
    tags_html = " ".join([f'<span class="tag-badge" style="font-size:12px; padding:5px 10px;">{t}</span>' for t in row["hashtags_list"]])
    meta_txt = f"{row['written_month']} 작성" 
    if row['air_date'] != "nan": meta_txt += f" | {row['air_date']} 방영"
    if row['main_cast'] != "nan": meta_txt += f" | 주연: {row['main_cast']}"
    
    st.markdown(f"""
        <div style="padding: 10px 0;">
            <div class="detail-title">{row['ip_name']}</div>
            <div class="detail-meta">{meta_txt}</div>
            <div style="margin-top:10px;">{tags_html}</div>
        </div>
    """, unsafe_allow_html=True)
    
    embed_url = build_embed_url(row["pres_url"])
    if embed_url:
        st.markdown('<div class="embed-container">', unsafe_allow_html=True)
        st_iframe(embed_url, height=720, scrolling=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.warning("프레젠테이션 주소가 없습니다.")

# endregion


# region [5. 실행]
def main():
    df = load_archive_df()
    if CURRENT_VIEW_MODE == VIEW_MODE_DETAIL and CURRENT_SELECTED_IP:
        render_detail_view(df, CURRENT_SELECTED_IP)
    else:
        render_list_view(df)

if __name__ == "__main__":
    main()
# endregion