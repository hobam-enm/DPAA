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
# [2] CSS 스타일 (전문가 모드)
# ==============================================================================
CUSTOM_CSS = """
<style>
/* ---- 전체 테마 ---- */
html, body, [class*="css"]  {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif;
    color: #e0e0e0;
}
[data-testid="stAppViewContainer"] {
    background-color: #121212; /* 더 깊은 블랙 */
}

/* ---- 필터바 UI ---- */
[data-testid="stTextInput"] input {
    background-color: #252525 !important;
    color: #fff !important;
    border: 1px solid #3a3a3a !important;
    border-radius: 8px;
}
[data-testid="stTextInput"] input::placeholder {
    color: #888 !important; /* 잘 보이게 수정 */
}
[data-baseweb="select"] > div {
    background-color: #252525 !important;
    border-color: #3a3a3a !important;
    border-radius: 8px;
    color: #fff !important;
}

/* ---- 타이틀 영역 ---- */
.main-title {
    font-size: 34px;
    font-weight: 800;
    background: linear-gradient(90deg, #fff 0%, #aaa 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-top: 30px;
    margin-bottom: 5px;
}
.subtitle {
    color: #666;
    font-size: 14px;
    margin-bottom: 25px;
}

/* ---- 상세페이지 헤더 ---- */
.detail-header {
    margin-top: 20px;
    margin-bottom: 20px;
    border-bottom: 1px solid #333;
    padding-bottom: 20px;
}
.detail-title {
    font-size: 38px;
    font-weight: 700;
    color: #fff;
    margin-bottom: 10px;
}
.detail-meta-row {
    display: flex;
    align-items: center;
    gap: 15px;
    color: #aaa;
    font-size: 14px;
}
.range-badge {
    display: inline-block;
    background: rgba(255, 75, 75, 0.2);
    border: 1px solid #ff4b4b;
    color: #ff4b4b;
    padding: 6px 12px;
    border-radius: 6px;
    font-weight: 700;
    font-size: 14px;
    margin-bottom: 15px;
}

/* ---- 카드 & 포스터 (이미지 로딩 최우선) ---- */
.drama-card {
    display: block;
    cursor: pointer;
    margin-bottom: 24px;
    text-decoration: none;
    color: inherit;
}
.poster-wrapper {
    position: relative;
    width: 100%;
    padding-bottom: 150%; /* 2:3 비율 */
    border-radius: 12px;
    overflow: hidden;
    background-color: #1e1e1e; /* 로딩 전 배경 */
    box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    transition: transform 0.2s;
}
.drama-card:hover .poster-wrapper {
    transform: translateY(-5px);
    box-shadow: 0 15px 30px rgba(0,0,0,0.7);
}

/* [중요] 이미지는 CSS 복잡도 제거하여 무조건 노출 */
.drama-poster {
    position: absolute;
    top: 0; 
    left: 0;
    width: 100%; 
    height: 100%;
    object-fit: cover;
    z-index: 1; 
}

/* 오버레이 (정보창) */
.drama-overlay {
    position: absolute;
    inset: 0;
    background: linear-gradient(to top, rgba(0,0,0,0.95) 0%, rgba(0,0,0,0.6) 50%, rgba(0,0,0,0) 100%);
    opacity: 0;
    transition: opacity 0.2s;
    z-index: 2;
    padding: 20px;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
}
.drama-card:hover .drama-overlay { opacity: 1; }

.overlay-title { font-size: 18px; font-weight: 700; color: #fff; margin-bottom: 6px; }
.overlay-meta { font-size: 12px; color: #ccc; margin-bottom: 12px; line-height: 1.4; }
.tag-badge {
    display: inline-block;
    padding: 4px 8px;
    margin: 0 4px 4px 0;
    background: rgba(255,255,255,0.15);
    border: 1px solid rgba(255,255,255,0.2);
    border-radius: 4px;
    font-size: 11px;
    color: #eee;
    backdrop-filter: blur(2px);
}

/* 임베드 컨테이너 */
.embed-frame {
    width: 100%;
    border-radius: 12px;
    overflow: hidden;
    background: #000;
    border: 1px solid #333;
    box-shadow: 0 20px 60px rgba(0,0,0,0.8);
}

/* 버튼 */
.btn-back {
    display: inline-block;
    padding: 8px 16px;
    background: #333;
    border-radius: 6px;
    color: #fff !important;
    text-decoration: none;
    font-size: 13px;
    margin-bottom: 10px;
    transition: background 0.2s;
}
.btn-back:hover { background: #444; }
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
    if not csv: return pd.DataFrame()
    try:
        df = pd.read_csv(csv)
        
        # 컬럼 매핑
        col_map = {
            "IP명": "ip", "IP": "ip", "프레젠테이션주소": "url", "프레젠테이션 주소": "url",
            "장표범위": "range", "노출 장표": "range", "해시태그": "tags",
            "포스터이미지URL": "img", "포스터 이미지 URL": "img",
            "작성월": "date", "방영일": "air", "주연배우": "cast"
        }
        df = df.rename(columns={k:v for k,v in col_map.items() if k in df.columns})
        
        # 필수컬럼 보정
        req = ["ip", "url", "range", "tags", "img", "date", "air", "cast"]
        for c in req:
            if c not in df.columns: df[c] = ""
            df[c] = df[c].astype(str).str.strip().replace("nan", "")
            
        df["tags_list"] = df["tags"].apply(lambda x: ["#"+t.strip() for t in x.split("#") if t.strip()])
        return df[df["ip"] != ""]
    except: return pd.DataFrame()

def get_embed_url(pres_url):
    m = re.search(r"/d/([^/]+)/", pres_url)
    if not m: return None
    # start=false, loop=false, delayms=3000 -> 기본 설정
    # rm=minimal 제거 (컨트롤바 보이게)
    return f"https://docs.google.com/presentation/d/{m.group(1)}/embed?start=false&loop=false&delayms=60000"


# ==============================================================================
# [4] 뷰 렌더링
# ==============================================================================

# 4-1. 공통 헤더
def render_header(df):
    st.markdown(f'<div class="main-title">{PAGE_TITLE}</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Data-Driven Drama Marketing Insights Archive</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1.2, 1])
    with col1:
        kw = st.text_input("검색", placeholder="IP명, 키워드 검색...", label_visibility="collapsed")
    with col2:
        all_tags = sorted(list(set([t for sub in df["tags_list"] for t in sub])))
        tags = st.multiselect("태그", all_tags, placeholder="해시태그 필터", label_visibility="collapsed")
    
    st.write("") # Spacer
    return kw, tags

# 4-2. 리스트 페이지
def render_list(df):
    kw, tags = render_header(df)
    
    # 필터링
    mask = pd.Series(True, index=df.index)
    if kw:
        k = kw.lower()
        mask &= df["ip"].str.lower().str.contains(k) | df["tags"].str.lower().str.contains(k)
    if tags:
        mask &= df["tags_list"].apply(lambda x: set(tags).issubset(set(x)))
    
    filtered = df[mask]
    
    if filtered.empty:
        st.info("검색 결과가 없습니다.")
        return

    # 그리드 렌더링 (5열)
    cols_per_row = 5
    rows = [filtered.iloc[i:i+cols_per_row] for i in range(0, len(filtered), cols_per_row)]
    
    for row_data in rows:
        cols = st.columns(cols_per_row)
        for idx, (_, row) in enumerate(row_data.iterrows()):
            with cols[idx]:
                # 포스터 URL이 없거나 깨진경우 처리
                img_src = row['img'] if row['img'].startswith("http") else "https://via.placeholder.com/300x450/222/888?text=No+Image"
                
                # 메타 텍스트
                meta_txt = f"{row['cast']}" if row['cast'] else ""
                if row['air']: meta_txt += f"<br>{row['air']}"
                
                # 태그
                tags_html = "".join([f'<span class="tag-badge">{t}</span>' for t in row['tags_list'][:4]])
                
                # 링크
                link = f"?view={VIEW_MODE_DETAIL}&ip={quote(row['ip'])}"
                
                # [핵심 수정] 이미지 태그 단순화 (referrer 등 제거)
                st.markdown(f"""
                <a href="{link}" class="drama-card" target="_self">
                    <div class="poster-wrapper">
                        <img class="drama-poster" src="{img_src}" alt="{row['ip']}">
                        <div class="drama-overlay">
                            <div class="overlay-title">{row['ip']}</div>
                            <div class="overlay-meta">{meta_txt}</div>
                            <div style="line-height:1.2;">{tags_html}</div>
                        </div>
                    </div>
                </a>
                """, unsafe_allow_html=True)

# 4-3. 상세 페이지
def render_detail(df, ip):
    st.markdown(f'<a href="?view={VIEW_MODE_LIST}" class="btn-back" target="_self">← 목록으로 돌아가기</a>', unsafe_allow_html=True)
    
    row = df[df["ip"] == ip]
    if row.empty:
        st.error("데이터를 찾을 수 없습니다.")
        return
    row = row.iloc[0]
    
    # 태그 HTML
    tags_html = " ".join([f'<span class="tag-badge" style="padding:5px 10px; font-size:12px;">{t}</span>' for t in row['tags_list']])
    
    # 상세 메타 정보
    meta_info = []
    if row['date']: meta_info.append(f"📅 작성: {row['date']}")
    if row['air']: meta_info.append(f"📺 방영: {row['air']}")
    if row['cast']: meta_info.append(f"🎭 주연: {row['cast']}")
    meta_str = " &nbsp;|&nbsp; ".join(meta_info)

    # [핵심 수정] 장표 범위 안내 배너 (Range Badge)
    range_html = ""
    if row['range']:
        range_html = f'<div class="range-badge">🎯 핵심 열람 범위: {row["range"]} 페이지</div>'

    st.markdown(f"""
        <div class="detail-header">
            {range_html}
            <div class="detail-title">{row['ip']}</div>
            <div class="detail-meta-row">
                {meta_str}
            </div>
            <div style="margin-top:15px;">{tags_html}</div>
        </div>
    """, unsafe_allow_html=True)
    
    # 임베드
    embed_url = get_embed_url(row['url'])
    if embed_url:
        st.markdown('<div class="embed-frame">', unsafe_allow_html=True)
        # 16:9 비율 유지를 위해 높이 넉넉히 설정 (720px)
        st_iframe(embed_url, height=720, scrolling=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.warning("연결된 프레젠테이션 주소가 없습니다.")

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