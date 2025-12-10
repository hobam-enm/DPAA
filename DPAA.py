# -*- coding: utf-8 -*-
# 🎬 드라마 사전분석 아카이브 (Streamlit + 공개 Google Sheets CSV + Google Slides Embed)

import re
from typing import List, Optional
from urllib.parse import urlparse, parse_qs, quote

import pandas as pd
import streamlit as st
from streamlit.components.v1 import iframe as st_iframe

# ==============================================================================
# [1] 기본 설정 (메타 태그로 이미지 차단 방지)
# ==============================================================================
PAGE_TITLE = "드라마 사전분석 아카이브"
PAGE_ICON = "🎬"

st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# [핵심] Referrer 메타 태그 추가 (이미지 로딩 차단 방지) + 상단 여백 제거
HIDE_UI = """
<style>
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}
section[data-testid="stSidebar"] {display:none !important;}

/* 상단 여백 제거 */
.block-container {
    padding-top: 0rem !important;
    padding-bottom: 5rem !important;
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
# [2] 스타일 (CSS) 정의 - 이미지 노출 최우선 & 전문가 UI
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

/* ---- 메인 타이틀 (요청하신 오렌지 그라데이션 복구) ---- */
.main-title {
    font-size: 32px;
    font-weight: 800;
    background: linear-gradient(90deg, #ff4b4b, #ff9f43);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-top: 30px;
    margin-bottom: 8px;
}
.subtitle {
    color: #999;
    font-size: 14px;
    margin-bottom: 25px;
    line-height: 1.5;
}

/* ---- 필터 UI (다크모드 + 플레이스홀더 밝게) ---- */
[data-testid="stTextInput"] input {
    background-color: #2b2b2b !important;
    color: #fff !important;
    border: 1px solid #444 !important;
}
[data-testid="stTextInput"] input::placeholder {
    color: #bbb !important; /* 안내 문구 잘 보이게 */
}
[data-baseweb="select"] > div {
    background-color: #2b2b2b !important;
    border-color: #444 !important;
    color: #fff !important;
}
[data-baseweb="tag"] {
    background-color: #555 !important;
    color: #fff !important;
}

/* ---- 카드 & 포스터 (이미지 100% 뜨게 하는 구조) ---- */
.drama-card {
    display: block;
    margin-bottom: 24px;
    text-decoration: none;
    color: inherit;
    position: relative;
    border: none;
    background: transparent;
}

/* [핵심 수정] aspect-ratio 대신 padding-bottom 기법 사용 (호환성 100%) */
.poster-wrapper {
    position: relative;
    width: 100%;
    height: 0;
    padding-bottom: 150%; /* 2:3 비율 강제 확보 */
    border-radius: 12px;
    overflow: hidden;
    background-color: #1a1a1a; /* 로딩 전 배경 */
    box-shadow: 0 4px 10px rgba(0,0,0,0.5);
    transition: transform 0.2s ease-out;
}

/* 이미지를 덮어씌우기 (꽉 차게) */
.drama-poster {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    object-fit: cover; /* 여백 없이 꽉 채움 */
    border: none;
    display: block;
    z-index: 1; /* 제일 아래 */
}

/* 호버 애니메이션 */
.drama-card:hover .poster-wrapper {
    transform: translateY(-6px);
    box-shadow: 0 15px 30px rgba(0,0,0,0.7);
    z-index: 10;
}

/* 오버레이 (정보창) */
.drama-overlay {
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background: linear-gradient(
        180deg,
        rgba(0,0,0,0) 0%,
        rgba(0,0,0,0.5) 40%,
        rgba(0,0,0,0.95) 100%
    );
    opacity: 0;
    transition: opacity 0.2s;
    z-index: 2; /* 이미지 위 */
    padding: 15px;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
}
.drama-card:hover .drama-overlay { opacity: 1; }

.overlay-title {
    font-size: 17px;
    font-weight: 700;
    color: #fff;
    margin-bottom: 4px;
    text-shadow: 0 1px 3px rgba(0,0,0,0.8);
}
.overlay-meta {
    font-size: 12px;
    color: #ddd;
    margin-bottom: 8px;
}

/* 태그 영역: 제한 없이 모두 노출 */
.overlay-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
}
.tag-badge {
    padding: 3px 6px;
    background: rgba(255,255,255,0.2);
    border: 1px solid rgba(255,255,255,0.3);
    border-radius: 4px;
    font-size: 10px;
    color: #fff;
    backdrop-filter: blur(2px);
}

/* ---- 상세 페이지 ---- */
.detail-title {
    font-size: 32px;
    font-weight: 700;
    color: #fff;
    margin-bottom: 10px;
}
.detail-meta {
    font-size: 14px;
    color: #aaa;
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
        # 더미 데이터
        return pd.DataFrame([{
            "ip": "데이터 연동 필요", "tags_list": ["#예시"], "img": "", "url": "", "cast": "", "date": "", "air": ""
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
# [4] 화면 렌더링
# ==============================================================================

# 4-1. 공통 헤더 (검색 & 필터)
def render_header(df):
    st.markdown(f'<div class="main-title">{PAGE_TITLE}</div>', unsafe_allow_html=True)
    # 한글 안내 문구 복구
    st.markdown(
        '<div class="subtitle">드라마 마케팅 사전분석 리포트를 한 곳에 모은 아카이브입니다.<br>'
        'IP별 기획 방향성과 인사이트를 빠르게 찾아보세요.</div>',
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
    
    # 필터링
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
                # 이미지 주소 처리 (빈값인 경우 플레이스홀더)
                img_src = row['img'] if row['img'].startswith("http") else "https://via.placeholder.com/300x450/333/999?text=No+Img"
                
                # 메타 정보 (주연, 방영일 등)
                meta_infos = []
                if row['cast']: meta_infos.append(f"{row['cast']}")
                if row['air']: meta_infos.append(f"{row['air']}")
                meta_html = "<br>".join(meta_infos)
                
                # 태그
                tags_html = "".join([f'<span class="tag-badge">{t}</span>' for t in row['tags_list']])
                
                # 링크 (동일 탭 이동)
                link = f"?view={VIEW_MODE_DETAIL}&ip={quote(row['ip'])}"
                
                # [이미지 강제 노출] img 태그 단순화 + 100% 채우기
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

    # 뱃지 제거 및 타이틀 디자인 깔끔하게
    st.markdown(f"""
        <div style="margin: 10px 0 25px 0;">
            <div class="detail-title">{row['ip']}</div>
            <div class="detail-meta">{meta_str}</div>
            <div>{tags_html}</div>
        </div>
    """, unsafe_allow_html=True)
    
    # [우회 방법] PDF 파일 감지 로직
    # 시트에 PDF 링크(구글드라이브 등)를 넣으면 자동으로 PDF 뷰어로 띄웁니다.
    target_url = row['url']
    is_pdf = False
    
    # 구글 드라이브 파일 중 PDF인지 체크 or URL 끝이 .pdf인지 체크
    if target_url:
        target_url = target_url.strip()
        if target_url.lower().endswith(".pdf"):
            is_pdf = True
        elif "/file/d/" in target_url:
            # 구글 드라이브 파일 링크는 내용물을 모르지만 일단 PDF 뷰어 방식으로 시도해볼 수 있음
            # (핵심 페이지만 자른 PDF를 올리는 것을 권장)
            is_pdf = True
            
    st.markdown('<div class="embed-frame">', unsafe_allow_html=True)
    
    if is_pdf:
        # PDF 미리보기 모드 (/preview) -> 깔끔하게 문서만 나옴
        # 구글 드라이브 링크의 /view를 /preview로 변경
        pdf_url = target_url.replace("/view", "/preview")
        st_iframe(pdf_url, height=800, scrolling=True)
        
    elif "docs.google.com/presentation" in target_url:
        # 기존 슬라이드 임베드
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