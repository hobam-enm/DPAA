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

# 상단 여백 제거 및 헤더 숨김
HIDE_UI = """
<style>
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}
section[data-testid="stSidebar"] {display:none !important;}

.block-container {
    padding-top: 0rem !important;
    padding-bottom: 3rem !important;
    max-width: 95% !important;
}
[data-testid="stHeader"] { display: none; }
</style>

<meta name="referrer" content="no-referrer">
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
# [2] CSS 스타일 (Nuclear Option: 이미지 강제 확대)
# ==============================================================================
CUSTOM_CSS = """
<style>
/* ---- 전체 폰트 및 배경 ---- */
html, body, [class*="css"]  {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Noto Sans KR", sans-serif;
    color: #e0e0e0;
}
[data-testid="stAppViewContainer"] {
    background-color: #141414;
}

/* ---- 메인 타이틀 ---- */
.main-title {
    font-size: 34px;
    font-weight: 800;
    background: linear-gradient(90deg, #ff4b4b, #ff9f43);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-top: 30px;
    margin-bottom: 8px;
}
.subtitle {
    color: #999;
    font-size: 15px;
    margin-bottom: 25px;
    line-height: 1.5;
}

/* ---- 필터 UI ---- */
[data-testid="stTextInput"] input {
    background-color: #2b2b2b !important;
    color: #fff !important;
    border: 1px solid #444 !important;
    border-radius: 8px;
}
[data-testid="stTextInput"] input::placeholder { color: #bbb !important; }
[data-baseweb="select"] > div {
    background-color: #2b2b2b !important;
    border-color: #444 !important;
    color: #fff !important;
    border-radius: 8px;
}
[data-baseweb="tag"] {
    background-color: #555 !important;
    color: #fff !important;
}

/* ---- [핵심 수정] 카드 & 포스터 (강제 적용 !important) ---- */
.drama-card {
    display: block !important;
    margin-bottom: 24px;
    text-decoration: none;
    color: inherit;
    position: relative;
    cursor: pointer;
    background: transparent;
    border: none;
}

/* 래퍼: 2:3 비율 영역 확보 */
.poster-wrapper {
    position: relative !important;
    width: 100% !important;
    height: 0 !important;
    padding-bottom: 150% !important; /* 2:3 비율 */
    border-radius: 12px;
    overflow: hidden;
    background-color: #1a1a1a;
    box-shadow: 0 6px 15px rgba(0,0,0,0.4);
    transition: transform 0.25s cubic-bezier(0.25, 0.46, 0.45, 0.94);
    z-index: 1;
}

/* 이미지: 무조건 꽉 채우기 (Streamlit 기본 스타일 무시) */
.drama-poster {
    position: absolute !important;
    top: 0 !important;
    left: 0 !important;
    width: 100% !important;
    height: 100% !important;
    min-width: 100% !important;  /* 혹시 모를 축소 방지 */
    min-height: 100% !important; /* 혹시 모를 축소 방지 */
    object-fit: cover !important; /* 비율 유지하며 꽉 채움 */
    object-position: center !important;
    margin: 0 !important;
    padding: 0 !important;
    border: none !important;
    display: block !important;
}

/* 호버 효과 */
.drama-card:hover .poster-wrapper {
    transform: translateY(-6px);
    box-shadow: 0 15px 35px rgba(0,0,0,0.6);
    z-index: 10;
}
.drama-card:hover .drama-poster {
    transform: scale(1.05); /* 살짝 줌인 */
    transition: transform 0.3s ease;
}

/* ---- 오버레이 ---- */
.drama-overlay {
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background: linear-gradient(
        to bottom,
        rgba(0,0,0,0) 0%,
        rgba(0,0,0,0.2) 40%,
        rgba(0,0,0,0.95) 100%
    );
    opacity: 0;
    transition: opacity 0.3s ease;
    z-index: 2;
    padding: 16px;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
}
.drama-card:hover .drama-overlay { opacity: 1; }

.overlay-title {
    font-size: 18px;
    font-weight: 700;
    color: #fff;
    margin-bottom: 6px;
    text-shadow: 0 2px 4px rgba(0,0,0,0.8);
    line-height: 1.2;
}
.overlay-meta {
    font-size: 12px;
    color: #ddd;
    margin-bottom: 10px;
    line-height: 1.4;
    text-shadow: 0 1px 2px rgba(0,0,0,0.8);
}
.overlay-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
}
.tag-badge {
    display: inline-block;
    padding: 3px 8px;
    border-radius: 4px;
    background: rgba(255, 255, 255, 0.2);
    border: 1px solid rgba(255, 255, 255, 0.3);
    font-size: 11px;
    color: #fff;
    backdrop-filter: blur(4px);
    white-space: nowrap;
}

/* ---- 상세 페이지 ---- */
.detail-title {
    font-size: 36px;
    font-weight: 700;
    color: #fff;
    margin-bottom: 10px;
}
.detail-meta {
    font-size: 14px;
    color: #bbb;
    margin-bottom: 20px;
}
.embed-frame {
    width: 100%;
    border-radius: 12px;
    overflow: hidden;
    background: #000;
    border: 1px solid #333;
    box-shadow: 0 20px 60px rgba(0,0,0,0.7);
}
.btn-back {
    display: inline-block;
    padding: 8px 16px;
    margin-bottom: 15px;
    background: #333;
    border-radius: 6px;
    color: #fff !important;
    text-decoration: none;
    font-size: 13px;
    transition: background 0.2s;
}
.btn-back:hover { background: #444; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ==============================================================================
# [3] 데이터 로딩
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
        return pd.DataFrame([{
            "ip": "데이터 연동 필요", "tags_list": ["#예시"], "img": "", "url": "", "cast": "", "date": "", "air": ""
        }])
        
    try:
        df = pd.read_csv(csv)
        # 컬럼 매핑 (관리시트 헤더 -> 코드 변수명)
        col_map = {
            "IP명": "ip", "IP": "ip", 
            "프레젠테이션주소": "url", "프레젠테이션 주소": "url",
            "장표범위": "range", "노출 장표": "range", 
            "해시태그(#제목 #장르 #주연배우 #분석주제 #분석IP)": "tags",
            "포스터이미지URL": "img", "포스터 이미지 URL": "img",
            "작성월": "date", "방영일": "air", "주연배우": "cast"
        }
        df = df.rename(columns={k:v for k,v in col_map.items() if k in df.columns})
        
        # 필수 컬럼 보정
        req = ["ip", "url", "range", "tags", "img", "date", "air", "cast"]
        for c in req:
            if c not in df.columns: df[c] = ""
            df[c] = df[c].astype(str).str.strip().replace("nan", "")
            
        df["tags_list"] = df["tags"].apply(lambda x: ["#"+t.strip() for t in x.split("#") if t.strip()])
        return df[df["ip"] != ""]
    except: return pd.DataFrame()


# ==============================================================================
# [4] 화면 렌더링
# ==============================================================================

# 4-1. 공통 헤더
def render_header(df):
    st.markdown(f'<div class="main-title">{PAGE_TITLE}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">드라마 마케팅 사전분석 리포트를 한 곳에 모은 아카이브입니다.<br>'
        'IP별 디지털 마케팅 기획 방향성과 인사이트를 빠르게 찾아보세요.</div>',
        unsafe_allow_html=True,
    )
    
    col1, col2 = st.columns([1, 1])
    with col1:
        kw = st.text_input("검색", placeholder="IP명 또는 키워드 입력...", label_visibility="collapsed")
    with col2:
        all_tags = sorted(list(set([t for sub in df["tags_list"] for t in sub])))
        tags = st.multiselect("태그", all_tags, placeholder="해시태그 필터", label_visibility="collapsed")
    
    st.write("") 
    return kw, tags

# 4-2. 리스트 페이지
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

    cols_per_row = 5
    rows = [filtered.iloc[i:i+cols_per_row] for i in range(0, len(filtered), cols_per_row)]
    
    for row_data in rows:
        cols = st.columns(cols_per_row)
        for idx, (_, row) in enumerate(row_data.iterrows()):
            with cols[idx]:
                img_src = row['img'] if row['img'].startswith("http") else "https://via.placeholder.com/300x450/333/999?text=No+Img"
                
                meta_infos = []
                if row['cast']: meta_infos.append(f"{row['cast']}")
                if row['air']: meta_infos.append(f"{row['air']}")
                meta_html = "<br>".join(meta_infos)
                
                tags_html = "".join([f'<span class="tag-badge">{t}</span>' for t in row['tags_list']])
                link = f"?view={VIEW_MODE_DETAIL}&ip={quote(row['ip'])}"
                
                # [이미지 강제 확장 적용]
                st.markdown(f"""
                <a href="{link}" class="drama-card" target="_self">
                    <div class="poster-wrapper">
                        <img class="drama-poster" src="{img_src}" alt="{row['ip']}">
                        <div class="drama-overlay">
                            <div class="overlay-title">{row['ip']}</div>
                            <div class="overlay-meta">{meta_html}</div>
                            <div class="overlay-tags">{tags_html}</div>
                        </div>
                    </div>
                </a>
                """, unsafe_allow_html=True)

# 4-3. 상세 페이지
def render_detail(df, ip):
    st.markdown(f'<a href="?view={VIEW_MODE_LIST}" class="btn-back" target="_self">← 목록으로 돌아가기</a>', unsafe_allow_html=True)
    
    row = df[df["ip"] == ip]
    if row.empty:
        st.error("잘못된 접근입니다.")
        return
    row = row.iloc[0]
    
    tags_html = " ".join([f'<span class="tag-badge" style="padding:5px 10px; font-size:12px;">{t}</span>' for t in row['tags_list']])
    
    meta_infos = []
    if row['date']: meta_infos.append(f"작성: {row['date']}")
    if row['air']: meta_infos.append(f"방영: {row['air']}")
    if row['cast']: meta_infos.append(f"주연: {row['cast']}")
    meta_str = " &nbsp;|&nbsp; ".join(meta_infos)

    st.markdown(f"""
        <div style="margin: 10px 0 25px 0;">
            <div class="detail-title">{row['ip']}</div>
            <div class="detail-meta">{meta_str}</div>
            <div>{tags_html}</div>
        </div>
    """, unsafe_allow_html=True)
    
    target_url = row['url']
    is_pdf = False
    if target_url:
        target_url = target_url.strip()
        if target_url.lower().endswith(".pdf") or "/file/d/" in target_url:
            is_pdf = True
            
    st.markdown('<div class="embed-frame">', unsafe_allow_html=True)
    
    if is_pdf:
        pdf_url = target_url.replace("/view", "/preview")
        st_iframe(pdf_url, height=800, scrolling=True)
    elif "docs.google.com/presentation" in target_url:
        m = re.search(r"/d/([^/]+)/", target_url)
        if m:
            embed_url = f"https://docs.google.com/presentation/d/{m.group(1)}/embed?start=false&loop=false&delayms=60000"
            st_iframe(embed_url, height=800, scrolling=True)
        else:
            st.warning("프레젠테이션 링크 형식이 올바르지 않습니다.")
    else:
        st.warning("🔗 등록된 문서가 없거나 지원하지 않는 링크입니다.")
        
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