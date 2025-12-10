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

# 상단 헤더 / 메뉴 / 푸터 / 사이드바 숨기기
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
CUSTOM_CSS = """
<style>
html, body, [class*="css"]  {
    font-family: -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo",
                 "Noto Sans KR", "Segoe UI", sans-serif;
}

/* 메인 영역 상단 여백 줄이기 */
[data-testid="stAppViewContainer"] > .main > div {
    padding-top: 1.2rem;
}

/* 메인 타이틀 */
.main-title {
    font-size: 32px;
    font-weight: 800;
    background: linear-gradient(90deg, #ff4b4b, #ff9f43);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.3rem;
}

/* 서브타이틀 */
.subtitle {
    color: #888;
    font-size: 14px;
    margin-bottom: 0.8rem;
}

/* ====== 카드 / 포스터 ====== */

/* 카드 컨테이너 – 배경/테두리 제거, 포스터만 보이게 */
.drama-card {
    border-radius: 0;
    padding: 0;
    margin-bottom: 22px;
    background: transparent;
    border: none;
    display: block;
}

/* 카드 전체 클릭 링크 스타일 제거 */
.drama-card-link {
    text-decoration: none;
    color: inherit;
    display: block;
}

/* 포스터 래퍼 + 오버레이 구조 (세로형 카드) */
.poster-wrapper {
    position: relative;
    width: 100%;
    max-width: 230px;           /* 세로 포스터 느낌으로 약간 슬림하게 */
    margin: 0 auto;
}

/* 포스터 이미지 – 세로 포스터 비율, 가운데 기준으로 꽉 채우기 */
.drama-poster {
    width: 100%;
    aspect-ratio: 2 / 3;        /* 전형적인 세로 포스터 비율 */
    border-radius: 18px;
    object-fit: cover;          /* 작은 변에 맞추고 넘치는 부분 잘라냄 */
    object-position: center center;
    border: 1px solid #dddddd;
    display: block;
    box-shadow: 0 10px 24px rgba(0, 0, 0, 0.10);
    transition: transform 0.18s ease-out, box-shadow 0.18s ease-out;
}

/* 호버 시 포스터 살짝 떠오르게 */
.drama-card:hover .drama-poster {
    transform: translateY(-4px);
    box-shadow: 0 16px 32px rgba(0, 0, 0, 0.25);
}

/* 정보 오버레이 – 포스터 위에 검정 그라데이션 */
.drama-overlay {
    position: absolute;
    inset: 0;
    border-radius: 18px;
    background: linear-gradient(
        180deg,
        rgba(0,0,0,0.10) 0%,
        rgba(0,0,0,0.85) 100%
    );
    opacity: 0;
    transition: opacity 0.18s ease-out;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 12px 14px;
    box-sizing: border-box;
}

/* 마우스 올리면 오버레이 등장 */
.drama-card:hover .drama-overlay {
    opacity: 1;
}

/* 오버레이 텍스트 */
.overlay-title {
    font-size: 15px;
    font-weight: 700;
    color: #ffffff;
    margin-bottom: 4px;
}

.overlay-meta {
    font-size: 12px;
    color: #f5f5f5;
    line-height: 1.4;
}

/* 해시태그 뱃지 – 흰 글씨, 점 없이 */
.tag-badge {
    display: inline-block;
    padding: 3px 7px;
    margin: 2px 4px 0 0;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.12);
    border: 1px solid rgba(255, 255, 255, 0.45);
    font-size: 11px;
    color: #ffffff;
}

/* 선택된 IP 하이라이트 (필요 시 사용) */
.selected-label {
    font-size: 12px;
    font-weight: 600;
    color: #ffdf7a;
}

/* 뒤로가기 링크 스타일 */
.back-link {
    font-size: 13px;
    color: #ff6b6b;
    text-decoration: none;
}
.back-link:hover {
    text-decoration: underline;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
# endregion


# region [3. Google Sheets 공개 CSV → DataFrame 로딩]

def build_csv_url_from_sheet_url(sheet_url: str) -> Optional[str]:
    """
    전체 공개된 Google Sheets URL에서 CSV export URL 생성.
      예) https://docs.google.com/spreadsheets/d/{ID}/edit?gid=0#gid=0
       →  https://docs.google.com/spreadsheets/d/{ID}/export?format=csv&gid=0
    """
    if not isinstance(sheet_url, str) or sheet_url.strip() == "":
        return None

    m = re.search(r"/spreadsheets/d/([^/]+)/", sheet_url)
    if not m:
        return None

    sheet_id = m.group(1)
    parsed = urlparse(sheet_url)
    qs = parse_qs(parsed.query)
    gid = qs.get("gid", ["0"])[0]

    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    return csv_url


@st.cache_data(ttl=300, show_spinner=False)
def load_archive_df() -> pd.DataFrame:
    """
    전체 공개된 Google Sheets를 CSV로 읽어와서 DataFrame으로 반환.

    기대 컬럼 (1행은 헤더, 2행부터 데이터):
      - A: IP명
      - B: 프레젠테이션 주소
      - C: 노출 장표
      - D: 해시태그
      - E: 포스터이미지URL
      - F: 작성월
      - G: 방영일
      - H: 주연배우
    """
    csv_url = build_csv_url_from_sheet_url(ARCHIVE_SHEET_URL)

    if not csv_url:
        df_dummy = pd.DataFrame(
            [
                {
                    "IP명": "예시 드라마",
                    "프레젠테이션 주소": "https://docs.google.com/presentation/d/EXAMPLE_ID/edit",
                    "노출 장표": "1-10",
                    "해시태그": "#예시 드라마#로맨스#스릴러",
                    "포스터이미지URL": "",
                    "작성월": "2025-01",
                    "방영일": "2025-02-01",
                    "주연배우": "홍길동, 김영희",
                }
            ]
        )
        df_dummy = normalize_archive_df(df_dummy)
        return df_dummy

    df_raw = pd.read_csv(csv_url)
    df = normalize_archive_df(df_raw)
    return df


def normalize_archive_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    시트에서 읽어온 원본 DF를 앱에서 쓰는 표준 형태로 정리.
    표준 컬럼:
      - ip_name
      - pres_url
      - slide_range
      - hashtags
      - poster_url
      - written_month
      - air_date
      - main_cast
      - hashtags_list
    """
    rename_map = {
        # IP명
        "IP명": "ip_name",
        "IP": "ip_name",

        # 프레젠테이션 URL
        "프레젠테이션주소": "pres_url",
        "프레젠테이션 주소": "pres_url",
        "프레젠테이션 URL": "pres_url",
        "프레젠테이션": "pres_url",

        # 장표 범위
        "장표범위": "slide_range",
        "장표 범위": "slide_range",
        "노출 장표": "slide_range",
        "노출장표": "slide_range",

        # 해시태그
        "해시태그": "hashtags",

        # 포스터 이미지 URL
        "포스터이미지URL": "poster_url",
        "포스터 이미지 URL": "poster_url",
        "포스터URL": "poster_url",
        "포스터 URL": "poster_url",

        # 작성월 / 방영일 / 주연배우
        "작성월": "written_month",
        "방영일": "air_date",
        "주연배우": "main_cast",
    }

    for k, v in rename_map.items():
        if k in df.columns and v not in df.columns:
            df = df.rename(columns={k: v})

    # 필수 컬럼 기본값 처리
    for col in [
        "ip_name",
        "pres_url",
        "slide_range",
        "hashtags",
        "poster_url",
        "written_month",
        "air_date",
        "main_cast",
    ]:
        if col not in df.columns:
            df[col] = ""

    # 문자열 변환 & strip
    str_cols = [
        "ip_name",
        "pres_url",
        "slide_range",
        "hashtags",
        "poster_url",
        "written_month",
        "air_date",
        "main_cast",
    ]
    for c in str_cols:
        df[c] = df[c].astype(str).str.strip()

    # 해시태그 파싱 – #단위로만 자르기
    df["hashtags_list"] = df["hashtags"].apply(parse_hashtags)

    # 빈 IP 제거
    df = df[df["ip_name"] != ""].reset_index(drop=True)
    return df

# endregion


# region [4. 헬퍼 함수들]

def parse_hashtags(tag_str: str) -> List[str]:
    """
    해시태그는 '#단위'로만 구분.
    예) "#얄미운 사랑#복수드라마 #스릴러" →
        ['#얄미운 사랑', '#복수드라마', '#스릴러']
    """
    if not isinstance(tag_str, str) or tag_str.strip() == "":
        return []

    tokens: List[str] = []
    # '#' 기준으로 split 후, 뒤쪽 덩어리들을 다시 '#' 붙여서 사용
    for part in tag_str.split("#"):
        part = part.strip()
        if not part:
            continue
        token = "#" + part  # 공백 포함 전체를 하나의 태그로 취급
        if token not in tokens:
            tokens.append(token)
    return tokens


def collect_all_hashtags(df: pd.DataFrame) -> List[str]:
    tags = []
    for row_tags in df.get("hashtags_list", []):
        if not isinstance(row_tags, list):
            continue
        tags.extend(row_tags)
    return sorted(set(tags))


def build_embed_url(pres_url: str) -> Optional[str]:
    """
    Google Slides 편집 URL → embed URL로 변환.

    슬라이드 URL 파라미터는 start/loop/delayms, 시작 슬라이드 정도만 지원되며,
    특정 범위(예: 1–9페이지만 허용)를 강제로 제한하는 옵션은 없다.:contentReference[oaicite:1]{index=1}
    """
    if not isinstance(pres_url, str) or "docs.google.com/presentation" not in pres_url:
        return None

    m = re.search(r"/d/([^/]+)/", pres_url)
    if not m:
        return None

    file_id = m.group(1)
    embed_url = (
        f"https://docs.google.com/presentation/d/{file_id}/embed?"
        "start=false&loop=false&delayms=3000"
    )
    return embed_url


def filter_archive(
    df: pd.DataFrame,
    keyword: str = "",
    selected_tags: Optional[List[str]] = None,
) -> pd.DataFrame:
    """IP명 / 해시태그 기준 필터."""
    if df.empty:
        return df

    temp = df.copy()
    keyword = (keyword or "").strip()
    selected_tags = selected_tags or []

    if keyword:
        low_kw = keyword.lower()
        temp = temp[
            temp["ip_name"].str.lower().str.contains(low_kw)
            | temp["hashtags"].str.lower().str.contains(low_kw)
        ]

    if selected_tags:
        selected_set = set(selected_tags)

        def _has_all_tags(row_tags: List[str]) -> bool:
            if not isinstance(row_tags, list):
                return False
            return selected_set.issubset(set(row_tags))

        temp = temp[temp["hashtags_list"].apply(_has_all_tags)]

    return temp.reset_index(drop=True)

# endregion


# region [5. 페이지 내 검색 / 필터 UI]

def render_filters_inline(df: pd.DataFrame):
    # 한 줄에: [라벨] [키워드 검색] [해시태그 필터]
    col_label, col_kw, col_tags = st.columns([1, 2, 2])

    with col_label:
        st.markdown("**검색 · 필터**")

    with col_kw:
        keyword = st.text_input(
            "키워드 검색",
            value="",
            placeholder="IP명 또는 해시태그 입력",
            label_visibility="collapsed",
        )

    with col_tags:
        all_tags = collect_all_hashtags(df)
        if all_tags:
            selected_tags = st.multiselect(
                "해시태그 필터",
                options=all_tags,
                default=[],
                label_visibility="collapsed",
            )
        else:
            selected_tags = []

    st.markdown("---")
    return keyword, selected_tags

# endregion


# region [6-A. 리스트 페이지 (4열 그리드)]

def render_list_view(df: pd.DataFrame, selected_ip: Optional[str]):
    # 타이틀 & 서브타이틀
    st.markdown(f'<div class="main-title">{PAGE_TITLE}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">드라마 마케팅 사전분석 리포트를 한 곳에 모은 아카이브입니다. '
        'IP별 기획 방향성과 인사이트를 빠르게 찾아보세요.</div>',
        unsafe_allow_html=True,
    )

    # 제목 바로 아래 검색/필터
    keyword, selected_tags = render_filters_inline(df)
    filtered_df = filter_archive(
        df=df,
        keyword=keyword,
        selected_tags=selected_tags,
    )

    if filtered_df.empty:
        st.info("조건에 맞는 드라마가 없습니다. 검색어 또는 해시태그를 변경해보세요.")
        return

    st.markdown("#### 📚 드라마 리스트")

    n = len(filtered_df)
    per_row = 4  # 1행 4개

    for row_start in range(0, n, per_row):
        cols = st.columns(per_row)
        for i in range(per_row):
            idx = row_start + i
            with cols[i]:
                if idx >= n:
                    st.empty()
                    continue

                row = filtered_df.iloc[idx]
                ip_name = row.get("ip_name", "")
                hashtags_list = row.get("hashtags_list", [])
                poster_url = row.get("poster_url", "")
                written_month = row.get("written_month", "")
                air_date = row.get("air_date", "")
                main_cast = row.get("main_cast", "")

                # 포스터 HTML (이제 이게 카드의 전부)
                if poster_url:
                    poster_html = (
                        f'<img class="drama-poster" src="{poster_url}" alt="{ip_name} 포스터" />'
                    )
                else:
                    poster_html = (
                        '<div class="drama-poster" '
                        'style="display:flex;align-items:center;justify-content:center;'
                        'font-size:12px;color:#ffffff;background:#777;">NO IMAGE</div>'
                    )

                # 해시태그 – 점 없이 span만 이어붙이기
                tags_html = "".join(
                    f'<span class="tag-badge">{t}</span>' for t in hashtags_list
                )

                # 메타 정보 (주연 / 작성월 / 방영일)
                meta_lines = []
                if main_cast and main_cast != "nan":
                    meta_lines.append(f"주연: {main_cast}")
                date_line_parts = []
                if written_month and written_month != "nan":
                    date_line_parts.append(f"작성월 {written_month}")
                if air_date and air_date != "nan":
                    date_line_parts.append(f"방영일 {air_date}")
                if date_line_parts:
                    meta_lines.append(" / ".join(date_line_parts))

                meta_html = "<br/>".join(meta_lines)

                selected_label = ""
                if selected_ip and selected_ip == ip_name:
                    selected_label = '<span class="selected-label">선택됨</span>'

                # 현재 탭에서 상세 페이지로 전환 (쿼리파라미터)
                link = f"?view={VIEW_MODE_DETAIL}&ip={quote(ip_name)}"

                card_html = f"""
                <a href="{link}" class="drama-card-link" target="_self">
                    <div class="drama-card">
                        <div class="poster-wrapper">
                            {poster_html}
                            <div class="drama-overlay">
                                <div>
                                    <div class="overlay-title">{ip_name} {selected_label}</div>
                                    <div class="overlay-meta">{meta_html}</div>
                                </div>
                                <div>{tags_html}</div>
                            </div>
                        </div>
                    </div>
                </a>
                """

                st.markdown(card_html, unsafe_allow_html=True)

# endregion


# region [6-B. 상세 페이지]

def render_detail_view(df: pd.DataFrame, selected_ip: str):
    st.markdown(f'<div class="main-title">{PAGE_TITLE}</div>', unsafe_allow_html=True)

    st.markdown(
        '<a href="?" class="back-link">← 드라마 리스트로 돌아가기</a>',
        unsafe_allow_html=True,
    )
    st.markdown("")

    if not selected_ip:
        st.info("선택된 드라마가 없습니다. 먼저 리스트에서 드라마를 선택해 주세요.")
        return

    hit = df[df["ip_name"] == selected_ip]
    if hit.empty:
        st.warning("선택된 IP를 데이터에서 찾을 수 없습니다.")
        return

    row = hit.iloc[0]
    ip_name = row.get("ip_name", "")
    pres_url = row.get("pres_url", "")
    hashtags_list = row.get("hashtags_list", [])
    written_month = row.get("written_month", "")
    air_date = row.get("air_date", "")
    main_cast = row.get("main_cast", "")

    tags_html = "".join(
        f'<span class="tag-badge">{t}</span>' for t in hashtags_list
    )

    meta_lines = []
    if main_cast and main_cast != "nan":
        meta_lines.append(f"주연: {main_cast}")
    date_line_parts = []
    if written_month and written_month != "nan":
        date_line_parts.append(f"작성월 {written_month}")
    if air_date and air_date != "nan":
        date_line_parts.append(f"방영일 {air_date}")
    if date_line_parts:
        meta_lines.append(" / ".join(date_line_parts))

    meta_html = "<br/>".join(
        f'<div class="drama-subtitle">{line}</div>' for line in meta_lines
    )

    st.markdown(
        f"""
        <div style="margin-bottom:0.5rem;">
            <div style="font-size:20px;font-weight:700;margin-bottom:0.2rem;">
                {ip_name}
            </div>
            {meta_html}
            <div style="margin-top:0.3rem;">{tags_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    embed_url = build_embed_url(pres_url)
    if not embed_url:
        st.warning("Google 프레젠테이션 URL 형식이 올바르지 않습니다. (관리 시트 B열 URL을 확인해 주세요)")
    else:
        st_iframe(embed_url, height=620)

# endregion


# region [7. 메인 실행부]

def main():
    df = load_archive_df()

    if CURRENT_VIEW_MODE == VIEW_MODE_DETAIL and CURRENT_SELECTED_IP:
        render_detail_view(df, CURRENT_SELECTED_IP)
    else:
        render_list_view(df, CURRENT_SELECTED_IP)


if __name__ == "__main__":
    main()

# endregion


