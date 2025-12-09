# -*- coding: utf-8 -*-
# 🎬 드라마 사전분석 아카이브 (Streamlit + 공개 Google Sheets CSV + Google Slides Embed)

# region [1. Imports & 기본 설정]
import re
from typing import List, Optional
from urllib.parse import urlparse, parse_qs

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
)

# 시크릿에서 관리시트 URL 읽기
ARCHIVE_SHEET_URL = st.secrets.get("ARCHIVE_SHEET_URL", "")

# 뷰 모드 (리스트 / 상세)
VIEW_MODE_LIST = "list"
VIEW_MODE_DETAIL = "detail"

if "view_mode" not in st.session_state:
    st.session_state["view_mode"] = VIEW_MODE_LIST

if "selected_ip" not in st.session_state:
    st.session_state["selected_ip"] = None

# endregion


# region [2. 스타일 (CSS) 정의]
CUSTOM_CSS = """
<style>
/* 전체 배경 / 폰트 */
html, body, [class*="css"]  {
    font-family: -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo",
                 "Noto Sans KR", "Segoe UI", sans-serif;
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
    margin-bottom: 1.5rem;
}

/* 카드 컨테이너 */
.drama-card {
    border-radius: 16px;
    padding: 10px 12px;
    margin-bottom: 10px;
    background: #111111;
    border: 1px solid #262626;
    display: flex;
    gap: 10px;
    transition: all 0.18s ease-out;
}

.drama-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 24px rgba(0, 0, 0, 0.35);
    border-color: #ff6b6b;
}

/* 포스터 이미지 */
.drama-poster {
    width: 70px;
    height: 100px;
    border-radius: 10px;
    object-fit: cover;
    border: 1px solid #333;
}

/* 카드 텍스트 */
.drama-meta {
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    flex: 1;
}

.drama-title {
    font-size: 15px;
    font-weight: 700;
    margin-bottom: 0.2rem;
}

.drama-subtitle {
    font-size: 12px;
    color: #bbbbbb;
}

/* 해시태그 뱃지 */
.tag-badge {
    display: inline-block;
    padding: 3px 7px;
    margin: 2px 4px 0 0;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);
    font-size: 11px;
    color: #ddd;
}

/* 버튼 커스터마이징 (모든 st.button 공통) */
.stButton>button {
    width: 100%;
    border-radius: 999px;
    border: 1px solid #ff6b6b;
    background: #ffffff;
    color: #111111;
    font-size: 12px;
    font-weight: 600;
    padding: 4px 0;
    margin-top: 4px;
    cursor: pointer;
}

.stButton>button:hover {
    background: linear-gradient(90deg, #ff6b6b, #ff9f43);
    color: #ffffff;
}

/* 선택된 IP 하이라이트 */
.selected-label {
    font-size: 12px;
    font-weight: 600;
    color: #ff9f43;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
# endregion


# region [3. Google Sheets 공개 CSV → DataFrame 로딩]

def build_csv_url_from_sheet_url(sheet_url: str) -> Optional[str]:
    """
    전체 공개된 Google Sheets URL에서 CSV export URL 생성.
    예) 
      입력: https://docs.google.com/spreadsheets/d/{ID}/edit?gid=0#gid=0
      출력: https://docs.google.com/spreadsheets/d/{ID}/export?format=csv&gid=0
    """
    if not isinstance(sheet_url, str) or sheet_url.strip() == "":
        return None

    m = re.search(r"/spreadsheets/d/([^/]+)/", sheet_url)
    if not m:
        return None

    sheet_id = m.group(1)
    parsed = urlparse(sheet_url)
    qs = parse_qs(parsed.query)
    gid = qs.get("gid", ["0"])[0]  # 기본 탭은 보통 gid=0

    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    return csv_url


@st.cache_data(ttl=300, show_spinner=False)
def load_archive_df() -> pd.DataFrame:
    """
    전체 공개된 Google Sheets를 CSV로 읽어와서 DataFrame으로 반환.

    기대 컬럼 (1행은 헤더, 2행부터 데이터):
      - IP명
      - 프레젠테이션 주소
      - 노출 장표
      - 해시태그
      - 포스터이미지URL
    """
    csv_url = build_csv_url_from_sheet_url(ARCHIVE_SHEET_URL)

    if not csv_url:
        df_dummy = pd.DataFrame(
            [
                {
                    "IP명": "예시 드라마",
                    "프레젠테이션 주소": "https://docs.google.com/presentation/d/EXAMPLE_ID/edit",
                    "노출 장표": "1-10",
                    "해시태그": "#로맨스#스릴러#복수",
                    "포스터이미지URL": "",
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
      - hashtags_list (파싱된 해시태그 리스트)
    """
    # 컬럼명 매핑
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
    }

    for k, v in rename_map.items():
        if k in df.columns and v not in df.columns:
            df = df.rename(columns={k: v})

    # 필수 컬럼 기본값 처리
    for col in ["ip_name", "pres_url", "slide_range", "hashtags", "poster_url"]:
        if col not in df.columns:
            df[col] = ""

    # 문자열 변환 & strip
    df["ip_name"] = df["ip_name"].astype(str).str.strip()
    df["pres_url"] = df["pres_url"].astype(str).str.strip()
    df["slide_range"] = df["slide_range"].astype(str).str.strip()
    df["hashtags"] = df["hashtags"].astype(str).str.strip()
    df["poster_url"] = df["poster_url"].astype(str).str.strip()

    # 해시태그 파싱 (# 단위 기준)
    df["hashtags_list"] = df["hashtags"].apply(parse_hashtags)

    # 빈 IP 제거
    df = df[df["ip_name"] != ""].reset_index(drop=True)
    return df

# endregion


# region [4. 헬퍼 함수들]

def parse_hashtags(tag_str: str) -> List[str]:
    """
    해시태그는 '#단위'로만 구분.
    예) "#로맨스#스릴러 #복수" → ['#로맨스', '#스릴러', '#복수']
    (띄어쓰기는 무시하고, 문자열 안의 '#' 토큰만 추출)
    """
    if not isinstance(tag_str, str) or tag_str.strip() == "":
        return []

    # '#무언가' 패턴을 전부 추출
    found = re.findall(r"#\S+", tag_str)
    # 순서 유지 + 중복 제거
    seen = []
    for t in found:
        if t not in seen:
            seen.append(t)
    return seen


def collect_all_hashtags(df: pd.DataFrame) -> List[str]:
    tags = []
    for row_tags in df.get("hashtags_list", []):
        if not isinstance(row_tags, list):
            continue
        tags.extend(row_tags)
    # 유니크 + 정렬
    return sorted(set(tags))


def build_embed_url(pres_url: str) -> Optional[str]:
    """
    Google Slides 편집 URL → embed URL로 변환.
    예)
      입력: https://docs.google.com/presentation/d/FILE_ID/edit?slide=...
      출력: https://docs.google.com/presentation/d/FILE_ID/embed?start=false&loop=false&delayms=3000
    (슬라이드 "범위 제한"은 Google Slides embed에서 기술적으로 막기 어렵기 때문에
     여기서는 전체 장표를 임베딩하고, 범위는 안내용 메타로만 사용)
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


def parse_slide_range_text(slide_range: str) -> tuple[Optional[int], Optional[int]]:
    """
    텍스트 '1-10' / '5' 형태를 (start, end) 튜플로 변환.
    - '1-10' → (1, 10)
    - '5'    → (5, 5)
    - 이상하면 (None, None)
    """
    if not isinstance(slide_range, str):
        return None, None

    s = slide_range.strip()
    if s == "":
        return None, None

    m = re.match(r"^(\d+)\s*-\s*(\d+)$", s)
    if m:
        return int(m.group(1)), int(m.group(2))

    m = re.match(r"^(\d+)$", s)
    if m:
        v = int(m.group(1))
        return v, v

    return None, None


def filter_archive(
    df: pd.DataFrame,
    keyword: str = "",
    selected_tags: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    IP명 / 해시태그 기준으로 필터링.
    - keyword: IP명, 해시태그 텍스트 검색 (대소문자 무시)
    - selected_tags: 해시태그 멀티선택 필터
    """
    if df.empty:
        return df

    temp = df.copy()
    keyword = (keyword or "").strip()
    selected_tags = selected_tags or []

    # 키워드 필터
    if keyword:
        low_kw = keyword.lower()
        temp = temp[
            temp["ip_name"].str.lower().str.contains(low_kw)
            | temp["hashtags"].str.lower().str.contains(low_kw)
        ]

    # 해시태그 멀티 선택 필터
    if selected_tags:
        selected_set = set(selected_tags)

        def _has_all_tags(row_tags: List[str]) -> bool:
            if not isinstance(row_tags, list):
                return False
            return selected_set.issubset(set(row_tags))

        temp = temp[temp["hashtags_list"].apply(_has_all_tags)]

    return temp.reset_index(drop=True)


def ensure_session_selected_ip(df: pd.DataFrame):
    """
    session_state에 선택된 IP가 없다면, 현재 필터된 df의 첫 번째 IP를 선택.
    """
    if "selected_ip" not in st.session_state or st.session_state["selected_ip"] is None:
        if not df.empty:
            st.session_state["selected_ip"] = df.iloc[0]["ip_name"]
        else:
            st.session_state["selected_ip"] = None


def select_ip(ip_name: str):
    """
    카드 버튼 클릭 시 호출해서 선택 IP를 세션에 저장하고,
    상세 페이지(view_mode=detail)로 전환.
    """
    st.session_state["selected_ip"] = ip_name
    st.session_state["view_mode"] = VIEW_MODE_DETAIL

# endregion


# region [5. 사이드바 UI - 검색 & 필터]

def render_sidebar(df: pd.DataFrame):
    st.sidebar.markdown("### 🔍 검색 / 필터")

    keyword = st.sidebar.text_input(
        "IP명 또는 해시태그 검색",
        value="",
        placeholder="예) 악의꽃, #스릴러, #복수",
    )

    all_tags = collect_all_hashtags(df)
    if all_tags:
        selected_tags = st.sidebar.multiselect(
            "해시태그 필터",
            options=all_tags,
            default=[],
        )
    else:
        selected_tags = []

    st.sidebar.markdown("---")
    st.sidebar.caption("※ 데이터 소스: 공개 Google Sheets - 드라마 사전분석 리스트")

    return keyword, selected_tags

# endregion


# region [6-A. 메인 레이아웃 - 리스트 페이지]

def render_list_view(filtered_df: pd.DataFrame):
    """전체 리스트 페이지 (1컬럼 카드 나열)"""
    st.markdown(f'<div class="main-title">{PAGE_TITLE}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">드라마 마케팅 사전분석 리포트를 한 곳에 모은 아카이브입니다. '
        'IP별 기획 방향성과 인사이트를 빠르게 찾아보세요.</div>',
        unsafe_allow_html=True,
    )

    st.markdown("#### 📚 드라마 리스트")

    if filtered_df.empty:
        st.info("조건에 맞는 드라마가 없습니다. 검색어 또는 해시태그를 변경해보세요.")
        return

    for idx, row in filtered_df.iterrows():
        ip_name = row.get("ip_name", "")
        hashtags_list = row.get("hashtags_list", [])
        poster_url = row.get("poster_url", "")
        slide_range = row.get("slide_range", "")

        if poster_url:
            poster_html = (
                f'<img class="drama-poster" src="{poster_url}" alt="{ip_name} 포스터" />'
            )
        else:
            poster_html = (
                '<div class="drama-poster" style="display:flex;align-items:center;'
                'justify-content:center;font-size:10px;color:#555;background:#181818;">NO IMAGE</div>'
            )

        tags_html = " ".join(
            f'<span class="tag-badge">{t}</span>' for t in hashtags_list
        )

        slide_html = ""
        if slide_range:
            slide_html = f'<div class="drama-subtitle">📑 노출 장표: {slide_range}</div>'

        selected_label = ""
        if st.session_state.get("selected_ip") == ip_name:
            selected_label = '<span class="selected-label">선택됨</span>'

        card_html = f"""
        <div class="drama-card">
            {poster_html}
            <div class="drama-meta">
                <div>
                    <div class="drama-title">{ip_name} {selected_label}</div>
                    {slide_html}
                </div>
                <div>{tags_html}</div>
            </div>
        </div>
        """

        st.markdown(card_html, unsafe_allow_html=True)

        btn_key = f"open_{idx}_{ip_name}"
        if st.button("리포트 열기", key=btn_key):
            select_ip(ip_name)
            st.experimental_rerun()

# endregion


# region [6-B. 상세 페이지 - 리포트 뷰어]

def render_detail_view(df: pd.DataFrame):
    """선택된 IP의 상세 리포트 페이지"""
    selected_ip = st.session_state.get("selected_ip")

    # 상단 타이틀 & 뒤로가기 버튼
    st.markdown(f'<div class="main-title">{PAGE_TITLE}</div>', unsafe_allow_html=True)

    col_back, col_title = st.columns([0.2, 0.8])
    with col_back:
        if st.button("← 드라마 리스트로 돌아가기"):
            st.session_state["view_mode"] = VIEW_MODE_LIST
            st.experimental_rerun()
    with col_title:
        st.markdown(
            '<div class="subtitle">선택한 작품의 사전분석 리포트를 확인할 수 있습니다.</div>',
            unsafe_allow_html=True,
        )

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
    slide_range = row.get("slide_range", "")
    hashtags_list = row.get("hashtags_list", [])

    tags_html = " ".join(
        f'<span class="tag-badge">{t}</span>' for t in hashtags_list
    )

    start_page, end_page = parse_slide_range_text(slide_range)
    if start_page is not None and end_page is not None:
        range_text = f"{start_page}–{end_page}p"
    else:
        range_text = "전체 장표"

    st.markdown(
        f"""
        <div style="margin-bottom:0.5rem;">
            <div style="font-size:20px;font-weight:700;margin-bottom:0.2rem;">
                {ip_name}
            </div>
            <div style="font-size:12px;color:#bbbbbb;margin-bottom:0.4rem;">
                📑 노출 장표 범위: {range_text}
            </div>
            <div>{tags_html}</div>
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

    keyword, selected_tags = render_sidebar(df)

    filtered_df = filter_archive(
        df=df,
        keyword=keyword,
        selected_tags=selected_tags,
    )

    ensure_session_selected_ip(filtered_df)

    # 뷰 모드에 따라 다른 페이지 렌더링
    if st.session_state.get("view_mode") == VIEW_MODE_DETAIL:
        render_detail_view(df)
    else:
        render_list_view(filtered_df)


if __name__ == "__main__":
    main()

# endregion
