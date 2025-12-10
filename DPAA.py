# -*- coding: utf-8 -*-
# 🎬 드라마 사전분석 아카이브 (Streamlit + 공개 Google Sheets CSV + Google Slides Embed)

# region [1. Imports & 기본 설정]
# ==============================================================================
# 1. Imports & 기본 설정
# ==============================================================================
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
</style>
"""
st.markdown(HIDE_STREAMLIT_UI, unsafe_allow_html=True)

# 시크릿에서 관리시트 URL 읽기
ARCHIVE_SHEET_URL = st.secrets.get("ARCHIVE_SHEET_URL", "")

# 뷰 모드 (리스트 / 상세) – 쿼리파라미터 기반
VIEW_MODE_LIST = "list"
VIEW_MODE_DETAIL = "detail"

params = st.experimental_get_query_params()
CURRENT_VIEW_MODE = params.get("view", [VIEW_MODE_LIST])[0]
CURRENT_SELECTED_IP = params.get("ip", [None])[0]
# endregion


# region [2. 스타일 (CSS) 정의]
# ==============================================================================
# 2. 스타일 (CSS) 정의 - UI/UX 디자인 고도화
# ==============================================================================
CUSTOM_CSS = """
<style>
/* 기본 폰트 및 배경 설정 */
html, body, [class*="css"]  {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, 'Helvetica Neue', 'Segoe UI', 'Apple SD Gothic Neo', 'Noto Sans KR', 'Malgun Gothic', sans-serif;
    color: #e0e0e0; /* 기본 텍스트 색상 밝게 */
}

/* 앱 전체 배경 (약간 어두운 톤으로 전문적인 느낌) */
[data-testid="stAppViewContainer"] {
    background-color: #141414;
}

/* 메인 영역 상단 여백 제거 */
[data-testid="stAppViewContainer"] > .main > div {
    padding-top: 1rem;
}

/* ---- [Typo] ---- */
/* 메인 타이틀 */
.main-title {
    font-size: 36px;
    font-weight: 800;
    letter-spacing: -0.02em;
    background: linear-gradient(135deg, #FF5F6D 0%, #FFC371 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.5rem;
}

/* 서브타이틀 */
.subtitle {
    color: #9e9e9e;
    font-size: 15px;
    font-weight: 400;
    line-height: 1.5;
    margin-bottom: 1.5rem;
}

/* 상세 페이지용 큰 타이틀 */
.detail-title {
    font-size: 40px;
    font-weight: 700;
    color: #ffffff;
    margin-bottom: 0.5rem;
    line-height: 1.2;
}

/* 상세 페이지 메타 정보 텍스트 */
.detail-meta {
    font-size: 15px;
    color: #b3b3b3;
    margin-bottom: 1rem;
}

/* ---- [Card & Poster] ---- */
/* 카드 컨테이너 */
.drama-card {
    border-radius: 0;
    padding: 0;
    margin-bottom: 24px;
    background: transparent;
    border: none;
    display: block;
    cursor: pointer;
}

/* 카드 링크 스타일 제거 */
.drama-card-link {
    text-decoration: none;
    color: inherit;
    display: block;
}

/* 포스터 래퍼 (비율 유지 및 넘치는 부분 숨김) */
.poster-wrapper {
    position: relative;
    width: 100%;
    /* 2:3 비율 강제 설정 (padding-bottom 방식 사용) */
    padding-bottom: 150%; 
    border-radius: 12px;
    overflow: hidden;
    background-color: #2b2b2b; /* 이미지 로딩 전 배경색 */
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    transition: transform 0.25s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

/* 포스터 이미지 (꽉 채우기) */
.drama-poster {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    object-fit: cover; /* 비율 유지하며 꽉 채움 */
    object-position: center;
    display: block;
    border: none;
}

/* 호버 효과 */
.drama-card:hover .poster-wrapper {
    transform: scale(1.03);
    box-shadow: 0 12px 24px rgba(0, 0, 0, 0.5);
    z-index: 2;
}

/* 정보 오버레이 (그라데이션) */
.drama-overlay {
    position: absolute;
    inset: 0;
    background: linear-gradient(
        to bottom,
        rgba(0,0,0,0) 20%,
        rgba(0,0,0,0.6) 60%,
        rgba(0,0,0,0.95) 100%
    );
    opacity: 0;
    transition: opacity 0.3s ease;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    padding: 16px;
}

.drama-card:hover .drama-overlay {
    opacity: 1;
}

/* 오버레이 텍스트 스타일 */
.overlay-title {
    font-size: 16px;
    font-weight: 700;
    color: #fff;
    margin-bottom: 4px;
    text-shadow: 0 1px 2px rgba(0,0,0,0.5);
}
.overlay-meta {
    font-size: 12px;
    color: #d1d1d1;
    line-height: 1.3;
}
.overlay-tags {
    margin-top: 8px;
}

/* ---- [Components] ---- */
/* 해시태그 뱃지 */
.tag-badge {
    display: inline-block;
    padding: 4px 8px;
    margin: 0 4px 4px 0;
    border-radius: 4px;
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.2);
    font-size: 11px;
    color: #e0e0e0;
    backdrop-filter: blur(4px);
}

/* 선택된 라벨 */
.selected-label {
    color: #ffd700;
    font-size: 11px;
    margin-left: 4px;
    vertical-align: middle;
}

/* 뒤로가기 버튼 스타일 */
.back-button {
    display: inline-flex;
    align-items: center;
    padding: 8px 16px;
    margin-bottom: 20px;
    background-color: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    color: #fff !important;
    text-decoration: none !important;
    font-size: 14px;
    transition: background 0.2s;
}
.back-button:hover {
    background-color: rgba(255, 255, 255, 0.15);
}

/* 상세페이지 임베드 컨테이너 */
.embed-container {
    margin-top: 30px;
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 20px 50px rgba(0,0,0,0.5);
    background: #000;
    border: 1px solid #333;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
# endregion


# region [3. Google Sheets 공개 CSV → DataFrame 로딩]
# ==============================================================================
# 3. 데이터 로딩 (Google Sheets -> DataFrame)
# ==============================================================================
def build_csv_url_from_sheet_url(sheet_url: str) -> Optional[str]:
    """공개 시트 URL -> CSV 다운로드 URL 변환"""
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
    """데이터 로딩 및 정규화"""
    csv_url = build_csv_url_from_sheet_url(ARCHIVE_SHEET_URL)

    if not csv_url:
        # 더미 데이터 (URL 없을 시)
        df_dummy = pd.DataFrame(
            [
                {
                    "IP명": "데이터 연동 필요",
                    "프레젠테이션 주소": "",
                    "해시태그": "#시스템#알림",
                    "포스터이미지URL": "",
                    "작성월": "-",
                    "방영일": "-",
                    "주연배우": "-",
                }
            ]
        )
        return normalize_archive_df(df_dummy)

    try:
        df_raw = pd.read_csv(csv_url)
        return normalize_archive_df(df_raw)
    except Exception:
        return pd.DataFrame()


def normalize_archive_df(df: pd.DataFrame) -> pd.DataFrame:
    """컬럼명 통일 및 데이터 전처리"""
    rename_map = {
        "IP명": "ip_name", "IP": "ip_name",
        "프레젠테이션주소": "pres_url", "프레젠테이션 주소": "pres_url",
        "프레젠테이션 URL": "pres_url", "프레젠테이션": "pres_url",
        "장표범위": "slide_range", "노출 장표": "slide_range",
        "해시태그": "hashtags",
        "포스터이미지URL": "poster_url", "포스터 이미지 URL": "poster_url",
        "작성월": "written_month", "방영일": "air_date", "주연배우": "main_cast",
    }

    # 컬럼 리네임
    for k, v in rename_map.items():
        if k in df.columns and v not in df.columns:
            df = df.rename(columns={k: v})

    # 필수 컬럼 생성
    required_cols = ["ip_name", "pres_url", "slide_range", "hashtags", "poster_url", "written_month", "air_date", "main_cast"]
    for col in required_cols:
        if col not in df.columns:
            df[col] = ""

    # 문자열 처리
    for c in required_cols:
        df[c] = df[c].astype(str).str.strip()

    # 해시태그 리스트화
    df["hashtags_list"] = df["hashtags"].apply(parse_hashtags)

    # 빈 데이터 제거
    df = df[df["ip_name"] != ""].reset_index(drop=True)
    return df

# endregion


# region [4. 헬퍼 함수들]
# ==============================================================================
# 4. 헬퍼 함수 (해시태그 파싱, URL 생성 등)
# ==============================================================================
def parse_hashtags(tag_str: str) -> List[str]:
    """'#태그 #태그' 문자열을 리스트로 변환"""
    if not tag_str:
        return []
    tokens = []
    for part in tag_str.split("#"):
        part = part.strip()
        if part:
            tokens.append("#" + part)
    return tokens


def collect_all_hashtags(df: pd.DataFrame) -> List[str]:
    """전체 해시태그 목록 추출 (필터용)"""
    tags = set()
    for row_tags in df["hashtags_list"]:
        tags.update(row_tags)
    return sorted(tags)


def build_embed_url(pres_url: str) -> Optional[str]:
    """Google Slides Embed URL 생성"""
    if not pres_url or "docs.google.com/presentation" not in pres_url:
        return None
    m = re.search(r"/d/([^/]+)/", pres_url)
    if not m:
        return None
    
    file_id = m.group(1)
    # 컨트롤바 최소화 및 자동재생 방지 설정
    return f"https://docs.google.com/presentation/d/{file_id}/embed?start=false&loop=false&delayms=3000&rm=minimal"


def filter_archive(df: pd.DataFrame, keyword: str, selected_tags: List[str]) -> pd.DataFrame:
    """검색어 및 태그 필터링"""
    temp = df.copy()
    if keyword:
        kw = keyword.lower()
        temp = temp[
            temp["ip_name"].str.lower().str.contains(kw) | 
            temp["hashtags"].str.lower().str.contains(kw)
        ]
    
    if selected_tags:
        selected_set = set(selected_tags)
        temp = temp[temp["hashtags_list"].apply(lambda x: selected_set.issubset(set(x)))]
        
    return temp.reset_index(drop=True)

# endregion


# region [5. 상단 헤더 및 필터 UI]
# ==============================================================================
# 5. 상단 헤더 및 필터 UI 렌더링
# ==============================================================================
def render_title_and_filters(df: pd.DataFrame):
    st.markdown(f'<div class="main-title">{PAGE_TITLE}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">마케팅 기획과 인사이트를 공유하는 아카이브입니다.<br>'
        'IP별 분석 리포트를 클릭하여 상세 내용을 확인하세요.</div>', 
        unsafe_allow_html=True
    )

    # 검색 및 필터 영역 (여백 조정)
    st.write("") # Spacer
    col1, col2 = st.columns([1, 1])
    
    with col1:
        keyword = st.text_input(
            "통합 검색",
            placeholder="IP명 또는 키워드 입력...",
            label_visibility="collapsed"
        )
    with col2:
        all_tags = collect_all_hashtags(df)
        selected_tags = st.multiselect(
            "태그 필터",
            options=all_tags,
            placeholder="해시태그 선택",
            label_visibility="collapsed"
        )
    
    st.markdown("---")
    return keyword, selected_tags

# endregion


# region [6-A. 리스트 뷰]
# ==============================================================================
# 6-A. 리스트 뷰 렌더링 (그리드 시스템)
# ==============================================================================
def render_list_view(df: pd.DataFrame, selected_ip: Optional[str]):
    keyword, selected_tags = render_title_and_filters(df)
    filtered_df = filter_archive(df, keyword, selected_tags)

    if filtered_df.empty:
        st.info("🔎 검색 결과가 없습니다.")
        return

    st.markdown(f"##### 총 {len(filtered_df)}개의 작품이 있습니다.")
    st.write("")

    # 그리드 설정 (반응형 대응을 위해 5열 정도로 조정 권장, 여기선 요청대로 유지하되 CSS로 제어)
    per_row = 5 
    rows = [filtered_df.iloc[i:i+per_row] for i in range(0, len(filtered_df), per_row)]

    for row_data in rows:
        cols = st.columns(per_row)
        for idx, (_, row) in enumerate(row_data.iterrows()):
            with cols[idx]:
                ip_name = row["ip_name"]
                poster_url = row["poster_url"]
                
                # 메타 정보 구성
                meta_info = []
                if row["main_cast"] and row["main_cast"] != "nan":
                    meta_info.append(f"{row['main_cast']}")
                if row["air_date"] and row["air_date"] != "nan":
                    meta_info.append(f"{row['air_date']}")
                
                meta_html = "<br>".join(meta_info)
                tags_html = "".join([f'<span class="tag-badge">{t}</span>' for t in row["hashtags_list"][:3]])

                # 포스터 없을 경우 대체
                poster_src = poster_url if poster_url else "https://via.placeholder.com/300x450/333/FFF?text=No+Image"

                # 상세 페이지 링크 (쿼리 파라미터)
                link = f"?view={VIEW_MODE_DETAIL}&ip={quote(ip_name)}"

                # 카드 HTML (target="_self" 명시)
                card_html = f"""
                <a href="{link}" class="drama-card-link" target="_self">
                    <div class="drama-card">
                        <div class="poster-wrapper">
                            <img class="drama-poster" src="{poster_src}" alt="{ip_name}" loading="lazy" />
                            <div class="drama-overlay">
                                <div class="overlay-title">{ip_name}</div>
                                <div class="overlay-meta">{meta_html}</div>
                                <div class="overlay-tags">{tags_html}</div>
                            </div>
                        </div>
                    </div>
                </a>
                """
                st.markdown(card_html, unsafe_allow_html=True)

# endregion


# region [6-B. 상세 뷰]
# ==============================================================================
# 6-B. 상세 뷰 렌더링 (디자인 고도화 & Embed 사이즈 최적화)
# ==============================================================================
def render_detail_view(df: pd.DataFrame, selected_ip: str):
    # 뒤로가기 버튼 (target="_self"로 동일 탭 이동 보장)
    st.markdown(
        f'<a href="?view={VIEW_MODE_LIST}" class="back-button" target="_self">← 목록으로 돌아가기</a>', 
        unsafe_allow_html=True
    )

    # 데이터 조회
    row = df[df["ip_name"] == selected_ip]
    if row.empty:
        st.error("해당 IP 정보를 찾을 수 없습니다.")
        return
    
    row = row.iloc[0]
    
    # 1. 헤더 섹션 (깔끔한 타이틀 & 메타 정보)
    # 해시태그
    tags_html = "".join([f'<span class="tag-badge" style="font-size:13px; padding:6px 12px;">{t}</span>' for t in row["hashtags_list"]])
    
    # 메타 텍스트
    meta_parts = []
    if row["written_month"] and row["written_month"] != "nan":
        meta_parts.append(f"📅 작성: {row['written_month']}")
    if row["air_date"] and row["air_date"] != "nan":
        meta_parts.append(f"📺 방영: {row['air_date']}")
    if row["main_cast"] and row["main_cast"] != "nan":
        meta_parts.append(f"🎭 주연: {row['main_cast']}")
    
    meta_str = " &nbsp; | &nbsp; ".join(meta_parts)

    st.markdown(
        f"""
        <div style="padding: 10px 0 30px 0;">
            <div class="detail-title">{row['ip_name']}</div>
            <div class="detail-meta">{meta_str}</div>
            <div style="margin-top:15px;">{tags_html}</div>
        </div>
        """, 
        unsafe_allow_html=True
    )

    # 2. 임베딩 영역 (16:9 비율 고려한 대형 사이즈)
    embed_url = build_embed_url(row["pres_url"])
    
    if embed_url:
        st.markdown('<div class="embed-container">', unsafe_allow_html=True)
        # 16:9 비율을 위해 width에 맞춰 height 계산 (Streamlit Wide 모드 기준 약 1000px~ 이상)
        # iframe 높이를 700px 정도로 넉넉하게 주어 레터박스 최소화
        st_iframe(embed_url, height=720, scrolling=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.warning("🔗 연결된 프레젠테이션 주소가 없거나 형식이 올바르지 않습니다.")

# endregion


# region [7. 메인 실행부]
# ==============================================================================
# 7. 메인 실행 로직
# ==============================================================================
def main():
    df = load_archive_df()

    if CURRENT_VIEW_MODE == VIEW_MODE_DETAIL and CURRENT_SELECTED_IP:
        render_detail_view(df, CURRENT_SELECTED_IP)
    else:
        render_list_view(df, CURRENT_SELECTED_IP)

if __name__ == "__main__":
    main()

# endregion