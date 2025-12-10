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
    initial_sidebar_state="collapsed",  # [7] 사이드바 닫힘 디폴트
)

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

/* 카드 컨테이너 – [1][2][5] 흰 카드 + 크기 키움 */
.drama-card {
    border-radius: 18px;
    padding: 16px 18px;
    margin-bottom: 16px;
    background: #ffffff;
    border: 1px solid #e4e4e4;
    display: flex;
    gap: 12px;
    transition: all 0.18s ease-out;
}

.drama-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 24px rgba(0, 0, 0, 0.12);
    border-color: #ff6b6b;
}

/* 카드 전체 클릭 링크 스타일 제거 */
.drama-card-link {
    text-decoration: none;
    color: inherit;
}

/* 포스터 이미지 – [5] 더 크게 */
.drama-poster {
    width: 90px;
    height: 130px;
    border-radius: 12px;
    object-fit: cover;
    border: 1px solid #dddddd;
}

/* 카드 텍스트 */
.drama-meta {
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    flex: 1;
}

.drama-title {
    font-size: 16px;
    font-weight: 700;
    margin-bottom: 0.2rem;
    color: #111111;
}

.drama-subtitle {
    font-size: 12px;
    color: #555555;
}

/* 해시태그 뱃지 */
.tag-badge {
    display: inline-block;
    padding: 3px 7px;
    margin: 2px 4px 0 0;
    border-radius: 999px;
    background: #f5f5f5;
    border: 1px solid #dddddd;
    font-size: 11px;
    color: #555555;
}

/* 선택된 IP 하이라이트 */
.selected-label {
    font-size: 12px;
    font-weight: 600;
    color: #ff9f43;
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

    # [6] 해시태그 파싱 – '#단위'로만 자르기
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
    (띄어쓰기는 완전히 무시하고, 문자열 안의 '#' 토큰만 추출)
    """
    if not isinstance(tag_str, str) or tag_str.strip() == "":
        return []

    found = re.findall(r"#\S+", tag_str)
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
    return sorted(set(tags))


def build_embed_url(pres_url: str) -> Optional[str]:
    """
    Google Slides 편집 URL → embed URL로 변환.

    ⚠ 슬라이드 범위를 1–9페이지로 '강제 제한'하는 파라미터는
       Google Slides 임베드에서 제공되지 않는다.
       (시작 슬라이드만 지정하거나, 아예 별도 파일로 잘라서 쓰는 방식이 권장됨):contentReference[oaicite:0]{index=0}
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


# region [6-A. 리스트 페이지 (그리드 4열)]

def render_list_view(filtered_df: pd.DataFrame, selected_ip: Optional[str]):
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
                # slide_range = row.get("slide_range", "")  # [2] 표시는 안 함

                if poster_url:
                    poster_html = (
                        f'<img class="drama-poster" src="{poster_url}" alt="{ip_name} 포스터" />'
                    )
                else:
                    poster_html = (
                        '<div class="drama-poster" style="display:flex;align-items:center;'
                        'justify-content:center;font-size:10px;color:#999;background:#f0f0f0;">NO IMAGE</div>'
                    )

                tags_html = " ".join(
                    f'<span class="tag-badge">{t}</span>' for t in hashtags_list
                )

                selected_label = ""
                if selected_ip and selected_ip == ip_name:
                    selected_label = '<span class="selected-label">선택됨</span>'

                # [4] 현재 탭에서 쿼리파라미터만 바꿔서 전환 (새탭 X)
                link = f"?view={VIEW_MODE_DETAIL}&ip={quote(ip_name)}"

                card_html = f"""
                <a href="{link}" class="drama-card-link" target="_self">
                    <div class="drama-card">
                        {poster_html}
                        <div class="drama-meta">
                            <div>
                                <div class="drama-title">{ip_name} {selected_label}</div>
                            </div>
                            <div>{tags_html}</div>
                        </div>
                    </div>
                </a>
                """

                st.markdown(card_html, unsafe_allow_html=True)

# endregion


# region [6-B. 상세 페이지]

def render_detail_view(df: pd.DataFrame, selected_ip: str):
    st.markdown(f'<div class="main-title">{PAGE_TITLE}</div>', unsafe_allow_html=True)

    # [4] 뒤로가기 – 현재 탭에서 메인으로 복귀
    st.markdown(
        '<a href="?" class="back-link">← 드라마 리스트로 돌아가기</a>',
        unsafe_allow_html=True,
    )
    st.markdown("")  # 간격

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
    # slide_range = row.get("slide_range", "")  # [2] 사용자 표시는 생략
    hashtags_list = row.get("hashtags_list", [])

    tags_html = " ".join(
        f'<span class="tag-badge">{t}</span>' for t in hashtags_list
    )

    st.markdown(
        f"""
        <div style="margin-bottom:0.5rem;">
            <div style="font-size:20px;font-weight:700;margin-bottom:0.2rem;">
                {ip_name}
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

    if CURRENT_VIEW_MODE == VIEW_MODE_DETAIL and CURRENT_SELECTED_IP:
        render_detail_view(df, CURRENT_SELECTED_IP)
    else:
        render_list_view(filtered_df, CURRENT_SELECTED_IP)


if __name__ == "__main__":
    main()

# endregion
