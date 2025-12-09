# -*- coding: utf-8 -*-
# 🎬 드라마 사전분석 아카이브 (Streamlit + Google Sheets + Google Slides Embed)

# region [1. Imports & 기본 설정]
import re
from typing import List, Optional

import pandas as pd
import streamlit as st
from streamlit.components.v1 import iframe as st_iframe

import gspread
from google.oauth2.service_account import Credentials

# 페이지 설정
PAGE_TITLE = "드라마 사전분석 아카이브"
PAGE_ICON = "🎬"

st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout="wide",
)

# Google Sheets 설정 (st.secrets 사용 가정)
# - st.secrets["GCP_SERVICE_ACCOUNT"]: 서비스 계정 JSON
# - st.secrets["ARCHIVE_SHEET_ID"]: 아카이브용 스프레드시트 ID
GCP_SERVICE_ACCOUNT = dict(st.secrets["gcp_service_account"])  # 섹션 전체를 dict로
ARCHIVE_SHEET_ID = st.secrets.get("ARCHIVE_SHEET_ID", "")
ARCHIVE_SHEET_NAME = st.secrets.get("ARCHIVE_SHEET_NAME", "아카이브")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]
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

/* 버튼 커스터마이징 (카드 안 "리포트 열기") */
.stButton>button {
    width: 100%;
    border-radius: 999px;
    border: 1px solid #ff6b6b;
    background: linear-gradient(90deg, #ff6b6b, #ff9f43);
    color: white;
    font-size: 12px;
    font-weight: 600;
    padding: 4px 0;
    margin-top: 4px;
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


# region [3. Google Sheets 연동 & 데이터 로딩]

@st.cache_data(ttl=300, show_spinner=False)
def load_archive_df() -> pd.DataFrame:
    """
    Google Sheets에서 아카이브 정보를 읽어 DataFrame으로 반환.

    기대 컬럼:
      - A열: IP명           -> 'ip_name'
      - B열: 프레젠테이션 URL -> 'pres_url'
      - C열: 노출 장표 범위   -> 'slide_range' (예: '1-10')
      - D열: 해시태그         -> 'hashtags' (ex: "#스릴러 #복수")
      - E열: 포스터 이미지 URL -> 'poster_url'
    """
    if not GCP_SERVICE_ACCOUNT or not ARCHIVE_SHEET_ID:
        # 최소 동작을 보장하기 위한 더미 DataFrame (로컬 개발용)
        df_dummy = pd.DataFrame(
            [
                {
                    "ip_name": "예시 드라마",
                    "pres_url": "https://docs.google.com/presentation/d/EXAMPLE_ID/edit",
                    "slide_range": "1-10",
                    "hashtags": "#로맨스 #스릴러",
                    "poster_url": "",
                }
            ]
        )
        df_dummy["hashtags_list"] = df_dummy["hashtags"].apply(parse_hashtags)
        return df_dummy

    credentials = Credentials.from_service_account_info(
        GCP_SERVICE_ACCOUNT,
        scopes=SCOPES,
    )
    gc = gspread.authorize(credentials)
    ws = gc.open_by_key(ARCHIVE_SHEET_ID).worksheet(ARCHIVE_SHEET_NAME)
    records = ws.get_all_records()

    df = pd.DataFrame(records)

    # 컬럼명 매핑 (실제 한글 컬럼명과 맞춰서 필요 시 수정)
    rename_map = {
        "IP명": "ip_name",
        "IP": "ip_name",
        "프레젠테이션주소": "pres_url",
        "프레젠테이션 URL": "pres_url",
        "프레젠테이션": "pres_url",
        "장표범위": "slide_range",
        "노출장표": "slide_range",
        "해시태그": "hashtags",
        "포스터이미지URL": "poster_url",
        "포스터URL": "poster_url",
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

    # 해시태그 파싱
    df["hashtags_list"] = df["hashtags"].apply(parse_hashtags)

    # 빈 IP 제거
    df = df[df["ip_name"] != ""].reset_index(drop=True)
    return df

# endregion


# region [4. 헬퍼 함수들]

def parse_hashtags(tag_str: str) -> List[str]:
    """
    '#스릴러 #복수 #로맨스' 형태 문자열을 ['#스릴러', '#복수', '#로맨스'] 로 변환.
    '#'가 빠진 텍스트도 자동으로 '#' 붙여서 처리.
    """
    if not isinstance(tag_str, str) or tag_str.strip() == "":
        return []

    # 공백 기준으로 split
    raw_tokens = re.split(r"\s+", tag_str.strip())
    tokens = []
    for t in raw_tokens:
        if t == "":
            continue
        if not t.startswith("#"):
            t = "#" + t
        tokens.append(t)
    # 중복 제거
    return sorted(set(tokens), key=tokens.index)


def collect_all_hashtags(df: pd.DataFrame) -> List[str]:
    """
    전체 DataFrame에서 등장하는 해시태그를 유니크하게 수집.
    """
    tags = []
    for row_tags in df.get("hashtags_list", []):
        if not isinstance(row_tags, list):
            continue
        tags.extend(row_tags)
    # 유니크 & 정렬
    return sorted(set(tags))


def build_embed_url(pres_url: str) -> Optional[str]:
    """
    일반 Google Slides URL을 embed용 URL로 변환.
    예)
      - 입력: https://docs.google.com/presentation/d/FILE_ID/edit#slide=id.p
      - 출력: https://docs.google.com/presentation/d/FILE_ID/embed?start=false&loop=false&delayms=3000
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

    # 키워드 필터: IP명, 해시태그 문자열에 포함 여부
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

        temp = temp[
            temp["hashtags_list"].apply(_has_all_tags)
        ]

    return temp.reset_index(drop=True)


def ensure_session_selected_ip(df: pd.DataFrame):
    """
    session_state에 선택된 IP가 없다면, 현재 필터된 df의 첫 번째 IP를 선택.
    """
    if "selected_ip" not in st.session_state:
        if not df.empty:
            st.session_state["selected_ip"] = df.iloc[0]["ip_name"]
        else:
            st.session_state["selected_ip"] = None


def select_ip(ip_name: str):
    """
    카드 버튼 클릭 시 호출해서 선택 IP를 세션에 저장.
    """
    st.session_state["selected_ip"] = ip_name
# endregion


# region [5. 사이드바 UI - 검색 & 필터]

def render_sidebar(df: pd.DataFrame):
    st.sidebar.markdown("### 🔍 검색 / 필터")

    # 키워드 검색
    keyword = st.sidebar.text_input(
        "IP명 또는 해시태그 검색",
        value="",
        placeholder="예) 악의꽃, #스릴러, #복수",
    )

    # 전체 해시태그 목록 수집
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
    st.sidebar.caption("※ 데이터 소스: Google Sheets - 드라마 사전분석 리스트")

    return keyword, selected_tags

# endregion


# region [6. 메인 레이아웃 - 카드 리스트 + 상세 리포트]

def render_main_layout(df: pd.DataFrame, filtered_df: pd.DataFrame):
    # 타이틀
    st.markdown(f'<div class="main-title">{PAGE_TITLE}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">드라마 마케팅 사전분석 리포트를 한 곳에 모은 아카이브입니다. '
        'IP별 기획 방향성과 인사이트를 빠르게 찾아보세요.</div>',
        unsafe_allow_html=True,
    )

    # 2-컬럼 레이아웃 (좌: 카드, 우: 프레젠테이션)
    col_left, col_right = st.columns([1.0, 1.6])

    # --- 좌측: 드라마 카드 리스트 ---
    with col_left:
        st.markdown("#### 📚 드라마 리스트")

        if filtered_df.empty:
            st.info("조건에 맞는 드라마가 없습니다. 검색어 또는 해시태그를 변경해보세요.")
        else:
            for idx, row in filtered_df.iterrows():
                ip_name = row.get("ip_name", "")
                hashtags_list = row.get("hashtags_list", [])
                poster_url = row.get("poster_url", "")
                slide_range = row.get("slide_range", "")

                # 카드 HTML
                poster_html = ""
                if poster_url:
                    poster_html = (
                        f'<img class="drama-poster" src="{poster_url}" alt="{ip_name} 포스터" />'
                    )
                else:
                    # 포스터 없는 경우 Placeholder 박스
                    poster_html = (
                        '<div class="drama-poster" style="display:flex;align-items:center;'
                        'justify-content:center;font-size:10px;color:#555;background:#181818;">NO IMAGE</div>'
                    )

                tags_html = " ".join(
                    f'<span class="tag-badge">{t}</span>' for t in hashtags_list
                )

                slide_html = ""
                if slide_range:
                    slide_html = f'<div class="drama-subtitle">📑 권장 장표: {slide_range}</div>'

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

                # 카드 하단 버튼
                btn_key = f"open_{idx}_{ip_name}"
                if st.button("리포트 열기", key=btn_key):
                    select_ip(ip_name)

    # --- 우측: 선택된 IP의 프레젠테이션 영역 ---
    with col_right:
        st.markdown("#### 📊 사전분석 리포트 뷰어")

        selected_ip = st.session_state.get("selected_ip")
        if not selected_ip:
            if df.empty:
                st.info("등록된 드라마가 없습니다. Google Sheets에 데이터를 추가해 주세요.")
            else:
                st.info("좌측 카드에서 보고 싶은 드라마를 선택해 주세요.")
            return

        # 선택된 IP의 row 찾기
        hit = df[df["ip_name"] == selected_ip]
        if hit.empty:
            st.warning("선택된 IP를 데이터에서 찾을 수 없습니다.")
            return

        row = hit.iloc[0]

        ip_name = row.get("ip_name", "")
        pres_url = row.get("pres_url", "")
        slide_range = row.get("slide_range", "")
        hashtags_list = row.get("hashtags_list", [])

        # 메타 정보 영역
        tags_html = " ".join(
            f'<span class="tag-badge">{t}</span>' for t in hashtags_list
        )
        slide_text = slide_range if slide_range else "전체 장표"

        st.markdown(
            f"""
            <div style="margin-bottom:0.5rem;">
                <div style="font-size:20px;font-weight:700;margin-bottom:0.2rem;">
                    {ip_name}
                </div>
                <div style="font-size:12px;color:#bbbbbb;margin-bottom:0.4rem;">
                    📑 노출 장표 범위: {slide_text}
                </div>
                <div>{tags_html}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Google Slides 임베딩
        embed_url = build_embed_url(pres_url)
        if not embed_url:
            st.warning("Google 프레젠테이션 URL 형식이 올바르지 않습니다. (B열 URL을 확인해 주세요)")
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
    render_main_layout(df, filtered_df)


if __name__ == "__main__":
    main()

# endregion

