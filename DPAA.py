# -*- coding: utf-8 -*-
# 🎬 드라마 사전분석 아카이브 (Streamlit + 공개 Google Sheets CSV + Google Slides Embed)

import re
from typing import List, Optional
from urllib.parse import urlparse, parse_qs, quote

import pandas as pd
import streamlit as st
from streamlit.components.v1 import iframe as st_iframe

# ==============================================================================
# [1] 기본 설정
# ==============================================================================
PAGE_TITLE = "드라마 사전분석 아카이브"
PAGE_ICON = "🎬"

st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# 상단 헤더 / 메뉴 / 푸터 / 사이드바 숨기기 + 상단 여백 제거 (요청사항 반영)
HIDE_UI = """
<style>
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}
section[data-testid="stSidebar"] {display:none !important;}

/* 상단 여백 제거 */
.block-container {
    padding-top: 0rem !important;
    padding-bottom: 3rem !important;
    max-width: 95% !important;
}
[data-testid="stHeader"] { display: none; }
</style>
"""
st.markdown(HIDE_UI, unsafe_allow_html=True)

# 시크릿 URL & 파라미터
ARCHIVE_SHEET_URL = st.secrets.get("ARCHIVE_SHEET_URL", "")
VIEW_MODE_LIST = "list"
VIEW_MODE_DETAIL = "detail"

params = st.query_params
CURRENT_VIEW_MODE = params.get("view", VIEW_MODE_LIST)
CURRENT_SELECTED_IP = params.get("ip", None)

# ==============================================================================
# [2] 스타일 (CSS) 정의 - 원본 느낌 유지하되 전문가스럽게 리터칭
# ==============================================================================
CUSTOM_CSS = """
<style>
/* ---- 전체 폰트 및 배경 ---- */
html, body, [class*="css"]  {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Noto Sans KR", sans-serif;
    color: #e0e0e0;
}
[data-testid="stAppViewContainer"] {
    background-color: #141414; /* 다크 모드 배경 유지 */
}

/* ---- [원복] 메인 타이틀 (오렌지 그라데이션) ---- */
.main-title {
    font-size: 34px;
    font-weight: 800;
    /* 원본의 그라데이션 컬러 복구 */
    background: linear-gradient(90deg, #ff4b4b, #ff9f43);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-top: 30px;
    margin-bottom: 10px;
}

/* ---- [원복] 서브타이틀 (한글 문구) ---- */
.subtitle {
    color: #999;
    font-size: 15px;
    margin-bottom: 25px;
    line-height: 1.5;
}

/* ---- 필터 UI (다크모드 유지) ---- */
[data-testid="stTextInput"] input {
    background-color: #2b2b2b !important;
    color: #fff !important;
    border: 1px solid #444 !important;
}
[data-testid="stTextInput"] input::placeholder {
    color: #aaa !important; /* 글씨 잘 보이게 */
}
[data-baseweb="select"] > div {
    background-color: #2b2b2b !important;
    border-color: #444 !important;
    color: #fff !important;
}
[data-baseweb="tag"] {
    background-color: #444 !important;
    color: #eee !important;
}

/* ---- 상세 페이지 헤더 ---- */
.detail-title {
    font-size: 36px;
    font-weight: 700;
    color: #ffffff;
    margin-bottom: 10px;
}
.detail-meta {
    font-size: 14px;
    color: #b3b3b3;
    margin-bottom: 15px;
}

/* ---- 카드 & 포스터 (이미지 로딩 문제 해결) ---- */
.drama-card {
    border-radius: 0;
    padding: 0;
    margin-bottom: 24px;
    background: transparent;
    border: none;
    display: block;
    cursor: pointer;
}
.drama-card-link {
    text-decoration: none;
    color: inherit;
    display: block;
}

/* [수정] 원본 코드로 회귀하되 꽉 차게만 수정 */
.poster-wrapper {
    position: relative;
    width: 100%;
    /* aspect-ratio 사용 (가장 안전한 방법) */
    aspect-ratio: 2 / 3;
    border-radius: 12px;
    overflow: hidden;
    background-color: #222; 
    box-shadow: 0 10px 24px rgba(0, 0, 0, 0.3);
}

/* [수정] 이미지는 무조건 꽉 차게 */
.drama-poster {
    width: 100%;
    height: 100%;
    object-fit: cover; /* 상하 여백 없이 꽉 채우기 */
    object-position: center;
    display: block;
}

/* 호버 효과 */
.drama-card:hover .poster-wrapper {
    transform: translateY(-5px);
    box-shadow: 0 16px 32px rgba(0, 0, 0, 0.5);
    transition: all 0.2s ease-out;
}

/* 오버레이 */
.drama-overlay {
    position: absolute;
    inset: 0;
    background: linear-gradient(
        180deg,
        rgba(0,0,0,0) 0%,
        rgba(0,0,0,0.6) 40%,
        rgba(0,0,0,0.95) 100%
    );
    opacity: 0;
    transition: opacity 0.2s ease-out;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    padding: 15px;
}
.drama-card:hover .drama-overlay {
    opacity: 1;
}

.overlay-title {
    font-size: 16px;
    font-weight: 700;
    color: #fff;
    margin-bottom: 6px;
}
.overlay-meta {
    font-size: 12px;
    color: #ddd;
    margin-bottom: 10px;
    line-height: 1.3;
}

/* [원복] 해시태그 영역 제한 해제 */
.overlay-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    /* max-height 제거 -> 태그 많으면 위로 쌓임 */
}

.tag-badge {
    display: inline-block;
    padding: 3px 7px;
    border-radius: 4px;
    background: rgba(255, 255, 255, 0.15);
    border: 1px solid rgba(255, 255, 255, 0.3);
    font-size: 11px;
    color: #fff;
    white-space: nowrap;
}

/* 버튼 */
.back-button {
    display: inline-block;
    padding: 8px 16px;
    margin-bottom: 15px;
    background-color: #333;
    border-radius: 6px;
    color: #fff !important;
    text-decoration: none !important;
    font-size: 13px;
}
.back-button:hover { background-color: #444; }

/* 임베드 프레임 */
.embed-container {
    margin-top: 20px;
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid #333;
    background: #000;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ==============================================================================
# [3] 데이터 처리
# ==============================================================================
def build_csv_url(sheet_url: str) -> Optional[str]:
    if not sheet_url or "docs.google.com" not in sheet_url: return None
    try:
        m = re.search(r"/spreadsheets/d/([^/]+)/", sheet_url)
        gid = parse_qs(urlparse(sheet_url).query).get("gid", ["0"])[0]
        return f"https://docs.google.com/spreadsheets/d/{m.group(1)}/export?format=csv&gid={gid}"
    except: return None

@st.cache_data(ttl=300, show_spinner=False)
def load_data():
    csv = build_csv_url(ARCHIVE_SHEET_URL)
    if not csv: 
        # 더미 데이터
        return pd.DataFrame([{
            "ip": "데이터 연동 필요", "tags_list": ["#예시"], "img": "", "url": ""
        }])
        
    try:
        df = pd.read_csv(csv)
        col_map = {
            "IP명": "ip", "IP": "ip", 
            "프레젠테이션주소": "url", "프레젠테이션 주소": "url",
            "장표범위": "range", "노출 장표": "range", 
            "해시태그": "tags",
            "포스터이미지URL": "img", "포스터 이미지 URL": "img",
            "작성월": "date", "방영일": "air", "주연배우": "cast"
        }
        df = df.rename(columns={k:v for k,v in col_map.items() if k in df.columns})
        
        req = ["ip", "url", "range", "tags", "img", "date", "air", "cast"]
        for c in req:
            if c not in df.columns: df[c] = ""
            df[c] = df[c].astype(str).str.strip().replace("nan", "")
            
        df["tags_list"] = df["tags"].apply(lambda x: ["#"+t.strip() for t in x.split("#") if t.strip()])
        return df[df["ip"] != ""]
    except: return pd.DataFrame()


# ==============================================================================
# [4] 뷰 렌더링
# ==============================================================================

# 4-1. 헤더 (원복됨)
def render_header(df):
    st.markdown(f'<div class="main-title">{PAGE_TITLE}</div>', unsafe_allow_html=True)
    # [원복] 원래 있던 한글 문구
    st.markdown(
        '<div class="subtitle">드라마 마케팅 사전분석 리포트를 한 곳에 모은 아카이브입니다. '
        'IP별 기획 방향성과 인사이트를 빠르게 찾아보세요.</div>',
        unsafe_allow_html=True,
    )
    
    col1, col2 = st.columns([1, 1])
    with col1:
        kw = st.text_input("검색", placeholder="IP명 또는 해시태그...", label_visibility="collapsed")
    with col2:
        all_tags = sorted(list(set([t for sub in df["tags_list"] for t in sub])))
        tags = st.multiselect("태그", all_tags, placeholder="해시태그 필터", label_visibility="collapsed")
    
    st.write("") 
    return kw, tags

# 4-2. 리스트 뷰
def render_list(df):
    kw, tags = render_header(df)
    
    mask = pd.Series(True, index=df.index)
    if kw:
        k = kw.lower()
        mask &= df["ip"].str.lower().str.contains(k) | df["tags"].str.lower().str.contains(k)
    if tags:
        mask &= df["tags_list"].apply(lambda x: set(tags).issubset(set(x)))
    
    filtered = df[mask]
    
    if filtered.empty:
        st.info("조건에 맞는 드라마가 없습니다.")
        return

    # 5열 그리드
    cols_per_row = 5
    rows = [filtered.iloc[i:i+cols_per_row] for i in range(0, len(filtered), cols_per_row)]
    
    for row_data in rows:
        cols = st.columns(cols_per_row)
        for idx, (_, row) in enumerate(row_data.iterrows()):
            with cols[idx]:
                # 이미지 없으면 Placeholder
                img_src = row['img'] if row['img'].startswith("http") else "https://via.placeholder.com/300x450/333/999?text=No+Img"
                
                meta = []
                if row['cast']: meta.append(f"주연: {row['cast']}")
                if row['date']: meta.append(f"{row['date']}")
                meta_html = "<br>".join(meta)
                
                tags_html = "".join([f'<span class="tag-badge">{t}</span>' for t in row['tags_list']])
                link = f"?view={VIEW_MODE_DETAIL}&ip={quote(row['ip'])}"
                
                # [중요] 포스터 이미지를 원본 방식(img 태그)으로 확실하게 복구
                st.markdown(f"""
                <a href="{link}" class="drama-card-link" target="_self">
                    <div class="drama-card">
                        <div class="poster-wrapper">
                            <img class="drama-poster" src="{img_src}" alt="{row['ip']}">
                            <div class="drama-overlay">
                                <div class="overlay-title">{row['ip']}</div>
                                <div class="overlay-meta">{meta_html}</div>
                                <div class="overlay-tags">{tags_html}</div>
                            </div>
                        </div>
                    </div>
                </a>
                """, unsafe_allow_html=True)

# 4-3. 상세 뷰
def render_detail(df, ip):
    st.markdown(f'<a href="?view={VIEW_MODE_LIST}" class="back-button" target="_self">← 드라마 리스트로 돌아가기</a>', unsafe_allow_html=True)
    
    row = df[df["ip"] == ip]
    if row.empty:
        st.error("데이터를 찾을 수 없습니다.")
        return
    row = row.iloc[0]
    
    tags_html = " ".join([f'<span class="tag-badge" style="font-size:12px; padding:5px 10px;">{t}</span>' for t in row['tags_list']])
    
    meta_txt = []
    if row['date']: meta_txt.append(f"작성: {row['date']}")
    if row['air']: meta_txt.append(f"방영: {row['air']}")
    if row['cast']: meta_txt.append(f"주연: {row['cast']}")
    meta_str = "  |  ".join(meta_txt)

    # [수정] 뱃지 제거, 깔끔한 타이틀
    st.markdown(f"""
        <div style="margin: 10px 0 20px 0;">
            <div class="detail-title">{row['ip']}</div>
            <div class="detail-meta">{meta_str}</div>
            <div>{tags_html}</div>
        </div>
    """, unsafe_allow_html=True)
    
    # [우회 방법] PDF 파일인지 확인하여 분기 처리
    target_url = row['url']
    is_pdf = target_url.lower().endswith(".pdf") or "/file/d/" in target_url
    
    st.markdown('<div class="embed-container">', unsafe_allow_html=True)
    
    if is_pdf:
        # PDF인 경우 (Google Drive Preview 사용) -> 핵심 페이지만 자른 PDF를 올렸을 때 유용
        # /view를 /preview로 바꾸면 깔끔하게 나옴
        pdf_preview_url = target_url.replace("/view", "/preview")
        st_iframe(pdf_preview_url, height=750, scrolling=True)
    elif "docs.google.com/presentation" in target_url:
        # 일반 슬라이드인 경우
        m = re.search(r"/d/([^/]+)/", target_url)
        if m:
            # start=false: 자동재생 끔
            embed_url = f"https://docs.google.com/presentation/d/{m.group(1)}/embed?start=false&loop=false&delayms=60000"
            st_iframe(embed_url, height=750, scrolling=True)
        else:
            st.warning("URL 형식이 올바르지 않습니다.")
    else:
        st.warning("프레젠테이션 주소가 없거나 지원하지 않는 형식입니다.")
        
    st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================================
# [5] 메인 실행
# ==============================================================================
def main():
    df = load_data()
    if CURRENT_VIEW_MODE == VIEW_MODE_DETAIL and CURRENT_SELECTED_IP:
        render_detail(df, CURRENT_SELECTED_IP)
    else:
        render_list(df)

if __name__ == "__main__":
    main()