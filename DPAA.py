
# -*- coding: utf-8 -*-
# 🎬 드라마 인사이트 아카이브 v3 – 썸네일 방식 (페이지 범위 완전 차단 버전)
#
# - Google Drive 파일 복사 X (용량/쿼터 이슈 회피)
# - Google Slides API로 각 페이지를 썸네일 이미지로 받아와서 표시
#   → 관리 시트 I열 / J열에 적은 "2-3" 범위만 물리적으로 보여줌
#   → 그 외 슬라이드는 앱 화면에서 전혀 노출되지 않음
#
# 📌 전제
# 1) secrets.toml 에 아래 값이 설정되어 있음
#
# ARCHIVE_SHEET_URL = "https://docs.google.com/spreadsheets/d/스프레드시트ID/edit?gid=0#gid=0"
#
# [google_api]
# service_account_json = """{ ... GCP 서비스계정 JSON ... }"""
#
# 2) 서비스계정 이메일을
#    - 관리 시트
#    - 슬라이드 파일
#    에 "보기 권한" 이상으로 공유
#
# 3) requirements.txt 에 추가
#    google-api-python-client
#    google-auth
#    google-auth-httplib2
#
# 📌 동작 요약
# - 리스트 페이지: 기존과 동일 (배우/장르 분석 카드 목록)
# - 상세 페이지:
#   1) 프레젠테이션 ID 추출
#   2) Slides API로 전체 슬라이드 리스트(objectId) 가져옴
#   3) I/J열 범위(예: "2-3") → [2,3] → 인덱스로 objectId 선택
#   4) 각 슬라이드에 대해 thumbnail URL 요청
#   5) 해당 이미지들만 렌더링 (다른 페이지는 전혀 표시 안 함)

import json
import re
from typing import List, Optional
from urllib.parse import urlparse, parse_qs

import pandas as pd
import streamlit as st
from streamlit.components.v1 import iframe as st_iframe  # 여전히 예비용
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ─────────────────────────────────────────────────────────────
# 기본 설정 & 스타일
# ─────────────────────────────────────────────────────────────
PAGE_TITLE = "드라마 인사이트 아카이브"
PAGE_ICON = "🎬"

st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout="wide",
    initial_sidebar_state="collapsed",
)

HIDE_UI = """
<style>
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}
section[data-testid="stSidebar"] {display:none !important;}

.block-container {
    padding-top: 0rem !important;
    padding-bottom: 3rem !important;
    max-width: 100% !important;
}
[data-testid="stHeader"] { display: none; }
</style>
<meta name="referrer" content="no-referrer">
"""
st.markdown(HIDE_UI, unsafe_allow_html=True)

CUSTOM_CSS = """
<style>
html, body, [class*="css"]  {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Noto Sans KR", sans-serif;
    color: #e0e0e0;
}
[data-testid="stAppViewContainer"] {
    background-color: #141414;
}

/* 메인 타이틀 */
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
    margin-bottom: 30px;
    line-height: 1.5;
}

/* 홈 카드 */
.home-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 24px;
    margin-top: 30px;
}
.home-card {
    position: relative;
    padding: 28px 24px;
    border-radius: 18px;
    background: radial-gradient(circle at top left, #ff4b4b25, #222);
    border: 1px solid #333;
    box-shadow: 0 18px 50px rgba(0,0,0,0.65);
    text-decoration: none;
    color: #fff;
    overflow: hidden;
    transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
    cursor: pointer;
}
.home-card:hover {
    transform: translateY(-4px);
    border-color: #ff7a50;
    box-shadow: 0 26px 70px rgba(0,0,0,0.85);
}
.home-card-title {
    font-size: 22px;
    font-weight: 700;
    margin-bottom: 8px;
}
.home-card-desc {
    font-size: 14px;
    color: #ccc;
    line-height: 1.5;
}
.home-card-tag {
    position: absolute;
    top: 16px;
    right: 18px;
    font-size: 11px;
    color: #ffb199;
    letter-spacing: 0.06em;
}

/* 분석 리스트 카드 */
.analysis-card {
    padding: 16px 18px;
    border-radius: 12px;
    background: #1b1b1b;
    border: 1px solid #333;
    margin-bottom: 12px;
    transition: border-color 0.2s ease, background 0.2s ease, transform 0.15s ease;
}
.analysis-card:hover {
    border-color: #ff7a50;
    background: #222;
    transform: translateY(-2px);
}
.analysis-title-row {
    display: flex;
    align-items: baseline;
    gap: 8px;
    margin-bottom: 4px;
}
.analysis-ip {
    font-size: 16px;
    font-weight: 700;
}
.analysis-label {
    font-size: 11px;
    padding: 2px 6px;
    border-radius: 999px;
    border: 1px solid #555;
    color: #ccc;
}
.analysis-meta {
    font-size: 13px;
    color: #bbb;
    margin-bottom: 2px;
}
.analysis-sub {
    font-size: 12px;
    color: #888;
}

/* 상세 페이지 */
.detail-back {
    display: inline-block;
    padding: 6px 12px;
    margin: 10px 0 16px 0;
    border-radius: 999px;
    border: 1px solid #444;
    font-size: 12px;
    color: #ddd !important;
    text-decoration: none;
}
.detail-back:hover {
    border-color: #ff7a50;
    background: #222;
}
.detail-title {
    font-size: 28px;
    font-weight: 700;
    margin-bottom: 6px;
}
.detail-subtitle {
    font-size: 14px;
    color: #bbb;
    margin-bottom: 12px;
}
.embed-frame {
    width: 100%;
    border-radius: 12px;
    overflow: hidden;
    background: #000;
    border: 1px solid #333;
    box-shadow: 0 20px 60px rgba(0,0,0,0.7);
    margin-bottom: 18px;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# 쿼리 파라미터
# ─────────────────────────────────────────────────────────────
params = st.query_params
VIEW = params.get("view", "home")
ROW_ID = params.get("id", None)

ARCHIVE_SHEET_URL = st.secrets.get("ARCHIVE_SHEET_URL", "")


# ─────────────────────────────────────────────────────────────
# 데이터 로딩
# ─────────────────────────────────────────────────────────────
def build_csv_url(sheet_url: str) -> Optional[str]:
    if not sheet_url or "docs.google.com" not in sheet_url:
        return None
    m = re.search(r"/spreadsheets/d/([^/]+)/", sheet_url)
    if not m:
        return None
    gid = parse_qs(urlparse(sheet_url).query).get("gid", ["0"])[0]
    return f"https://docs.google.com/spreadsheets/d/{m.group(1)}/export?format=csv&gid={gid}"


@st.cache_data(ttl=300, show_spinner=False)
def load_archive_df() -> pd.DataFrame:
    csv = build_csv_url(ARCHIVE_SHEET_URL)
    if not csv:
        return pd.DataFrame()
    try:
        df = pd.read_csv(csv)
    except Exception:
        return pd.DataFrame()

    # 헤더 매핑
    col_map = {
        "IP": "ip",
        "IP명": "ip",
        "작품명": "ip",

        "프레젠테이션주소": "url",
        "프레젠테이션 주소": "url",
        "PPT주소": "url",
        "PPT 주소": "url",

        "포스터이미지URL": "img",
        "포스터 이미지URL": "img",
        "포스터 이미지 URL": "img",

        "작성월": "date",
        "작성일": "date",

        "방영일": "air",
        "방영일자": "air",

        "주연배우": "cast",
        "배우명": "cast",

        # 장르/분석 내용 (장르 페이지 제목)
        "장르/분석내용": "genre_title",
        "장르분석제목": "genre_title",
        "장르분석 제목": "genre_title",

        # 배우/장르 페이지 범위
        "배우분석": "actor_range",
        "장르분석": "genre_range",
        "배우분석 페이지범위": "actor_range",
        "배우분석 페이지 범위": "actor_range",
        "장르분석 페이지범위": "genre_range",
        "장르분석 페이지 범위": "genre_range",

        # 선택적으로 존재할 수 있는 URL 컬럼
        "배우분석 URL": "actor_url",
        "장르분석 URL": "genre_url",
        "배우분석URL": "actor_url",
        "장르분석URL": "genre_url",
    }

    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    req_cols = [
        "ip", "url",
        "img", "date", "air", "cast",
        "actor_range", "genre_title", "genre_range",
        "actor_url", "genre_url",
    ]
    for c in req_cols:
        if c not in df.columns:
            df[c] = ""
        df[c] = df[c].astype(str).fillna("").str.strip().replace("nan", "")

    df["cast_clean"] = df["cast"].apply(
        lambda x: ", ".join([p.strip() for p in re.split(r"[,/]", x) if p.strip()])
        if isinstance(x, str) else ""
    )

    df = df[df["ip"] != ""].copy()
    df.reset_index(drop=True, inplace=True)
    df["row_id"] = df.index.astype(str)
    return df


# ─────────────────────────────────────────────────────────────
# Google Slides API – 서비스 계정 인증 & 썸네일
# ─────────────────────────────────────────────────────────────
SLIDES_SCOPES = ["https://www.googleapis.com/auth/presentations.readonly"]


@st.cache_resource(show_spinner=False)
def get_slides_service():
    google_api_conf = st.secrets.get("google_api", {})
    info_str = google_api_conf.get("service_account_json", "")
    if not info_str:
        return None
    try:
        info = json.loads(info_str)
        creds = service_account.Credentials.from_service_account_info(
            info,
            scopes=SLIDES_SCOPES,
        )
        service = build("slides", "v1", credentials=creds, cache_discovery=False)
        return service
    except Exception as e:
        st.warning(f"Slides API 초기화 실패: {e}")
        return None


@st.cache_data(ttl=600, show_spinner=False)
def get_presentation_page_ids(presentation_id: str) -> List[str]:
    """
    프레젠테이션 내 슬라이드들의 pageObjectId 리스트를 순서대로 가져옴.
    """
    service = get_slides_service()
    if service is None:
        return []
    try:
        pres = service.presentations().get(presentationId=presentation_id).execute()
        slides = pres.get("slides", [])
        page_ids = [s.get("objectId") for s in slides if s.get("objectId")]
        return page_ids
    except Exception as e:
        st.warning(f"프레젠테이션 메타 로딩 실패: {e}")
        return []


@st.cache_data(ttl=600, show_spinner=False)
def get_slide_thumbnail_url(presentation_id: str, page_object_id: str) -> Optional[str]:
    """
    특정 슬라이드(pageObjectId)에 대한 썸네일 이미지 URL 반환.
    """
    service = get_slides_service()
    if service is None:
        return None
    try:
        resp = (
            service.presentations()
            .pages()
            .getThumbnail(
                presentationId=presentation_id,
                pageObjectId=page_object_id,
                thumbnailProperties_thumbnailSize="LARGE",
            )
            .execute()
        )
        return resp.get("contentUrl")
    except Exception as e:
        st.warning(f"썸네일 로딩 실패: {e}")
        return None


# ─────────────────────────────────────────────────────────────
# 유틸 – 슬라이드 ID, 페이지 범위 파싱
# ─────────────────────────────────────────────────────────────
def parse_page_range(page_range: str) -> List[int]:
    page_range = (page_range or "").strip()
    if not page_range:
        return []
    m = re.match(r"(\d+)\s*-\s*(\d+)", page_range)
    if m:
        start, end = int(m.group(1)), int(m.group(2))
        if start > end:
            start, end = end, start
        return list(range(start, end + 1))
    m = re.match(r"(\d+)", page_range)
    if m:
        return [int(m.group(1))]
    return []


def extract_presentation_id(url: str) -> Optional[str]:
    if not url or "docs.google.com/presentation" not in url:
        return None
    m = re.search(r"/d/([^/]+)/", url)
    if not m:
        return None
    return m.group(1)


def build_embed_url_if_possible(url: str, page_range: str = "") -> str:
    """
    Slides API 사용이 불가능할 때를 위한 fallback.
    - Google Slides URL이면 embed 링크로 변환 + 첫 페이지부터 시작
    - PDF면 /preview
    - 기타는 그대로
    """
    if not url:
        return ""
    is_pdf = url.lower().endswith(".pdf") or "/file/d/" in url
    if is_pdf:
        if "/preview" in url:
            return url
        return url.replace("/view", "/preview")

    if "docs.google.com/presentation" in url:
        pres_id = extract_presentation_id(url)
        if not pres_id:
            return url
        base = f"https://docs.google.com/presentation/d/{pres_id}/embed?start=false&loop=false&delayms=60000"
        pages = parse_page_range(page_range)
        if pages:
            base += f"&slide=id.p{pages[0]}"
        return base

    return url


# ─────────────────────────────────────────────────────────────
# 렌더링 – 홈 / 월간 / 배우·장르 리스트 / 상세
# ─────────────────────────────────────────────────────────────
def render_home():
    st.markdown(f'<div class="main-title">{PAGE_TITLE}</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="subtitle">
        드라마 마케팅·인사이트 리포트를 한 곳에 모은 아카이브입니다.<br>
        상단의 카드에서 보고 싶은 리포트 유형을 선택하세요.
        </div>
        """,
        unsafe_allow_html=True,
    )

    monthly_link = "?view=monthly"
    actor_link = "?view=actor_genre"

    st.markdown(
        f"""
        <div class="home-grid">
          <a href="{monthly_link}" target="_self" class="home-card">
            <div class="home-card-tag">MONTHLY</div>
            <div class="home-card-title">월간 드라마 인사이트 리포트</div>
            <div class="home-card-desc">
              월 단위로 정리한 시장 인사이트, 핵심 작품, 시청자 반응 변화를 다룬 리포트입니다.
            </div>
          </a>
          <a href="{actor_link}" target="_self" class="home-card">
            <div class="home-card-tag">CAST / GENRE</div>
            <div class="home-card-title">배우 / 장르 분석 리포트</div>
            <div class="home-card-desc">
              IP별 배우 캐스팅 포인트와 장르 포지셔닝을 한눈에 볼 수 있는 리포트입니다.
            </div>
          </a>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_monthly_stub():
    st.markdown(
        '<a href="?view=home" class="detail-back">← 메인으로 돌아가기</a>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="detail-title">월간 드라마 인사이트 리포트</div>',
        unsafe_allow_html=True,
    )
    st.info("월간 리포트 페이지 구성은 추후 설계 예정입니다.")


def render_slide_range_as_thumbnails(target_url: str, page_range: str):
    """
    핵심 함수:
    - target_url 에서 프레젠테이션 ID 추출
    - page_range(예: "2-3") 기준으로 해당 페이지들만 썸네일로 렌더링
    - Slides API 사용 불가 시 iframe embed로 fallback
    """
    pres_id = extract_presentation_id(target_url)
    if not pres_id:
        # Slides URL이 아니면 그냥 embed
        embed_url = build_embed_url_if_possible(target_url, page_range)
        if not embed_url:
            st.warning("연결된 프레젠테이션 링크가 없습니다.")
            return
        st.markdown('<div class="embed-frame">', unsafe_allow_html=True)
        st_iframe(embed_url, height=800, scrolling=True)
        st.markdown("</div>", unsafe_allow_html=True)
        return

    # 페이지 범위 파싱
    pages = parse_page_range(page_range)
    if not pages:
        # 범위 명시가 없으면 전체를 embed로 fallback
        embed_url = build_embed_url_if_possible(target_url, page_range)
        if not embed_url:
            st.warning("페이지 범위가 설정되지 않았고, 프레젠테이션을 불러올 수 없습니다.")
            return
        st.markdown('<div class="embed-frame">', unsafe_allow_html=True)
        st_iframe(embed_url, height=800, scrolling=True)
        st.markdown("</div>", unsafe_allow_html=True)
        return

    # Slides API로 pageObjectId 리스트 가져오기
    page_ids = get_presentation_page_ids(pres_id)
    if not page_ids:
        # 메타를 못 가져오면 embed fallback
        embed_url = build_embed_url_if_possible(target_url, page_range)
        if not embed_url:
            st.warning("프레젠테이션 정보를 불러오지 못했습니다.")
            return
    else:
        # 요청한 범위 내에서만 썸네일 렌더링
        rendered_any = False
        for p in pages:
            idx = p - 1
            if 0 <= idx < len(page_ids):
                page_obj_id = page_ids[idx]
                thumb_url = get_slide_thumbnail_url(pres_id, page_obj_id)
                if thumb_url:
                    rendered_any = True
                    st.markdown('<div class="embed-frame">', unsafe_allow_html=True)
                    st.markdown(
                        f'<img src="{thumb_url}" style="width:100%;display:block;">',
                        unsafe_allow_html=True,
                    )
                    st.markdown("</div>", unsafe_allow_html=True)
        if rendered_any:
            return

        # 여기까지 왔는데도 아무것도 못 그렸다면 embed fallback
        embed_url = build_embed_url_if_possible(target_url, page_range)
        if embed_url:
            st.markdown('<div class="embed-frame">', unsafe_allow_html=True)
            st_iframe(embed_url, height=800, scrolling=True)
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.warning("해당 페이지 범위를 렌더링할 수 없습니다.")


def render_actor_detail(df: pd.DataFrame, row_id: str):
    row = df[df["row_id"] == row_id]
    if row.empty:
        st.error("유효하지 않은 접근입니다.")
        return
    row = row.iloc[0]

    st.markdown(
        '<a href="?view=actor_genre" class="detail-back">← 배우/장르 분석 목록으로</a>',
        unsafe_allow_html=True,
    )

    ip = row["ip"]
    cast = row["cast_clean"] or row["cast"]
    date = row["date"]
    air = row["air"]
    meta = " / ".join([x for x in [date, air] if x])

    st.markdown(
        f'<div class="detail-title">{ip} – 배우 분석</div>',
        unsafe_allow_html=True,
    )
    sub = f"배우: {cast}" if cast else "배우 분석 슬라이드"
    st.markdown(
        f'<div class="detail-subtitle">{sub}<br>{meta}</div>',
        unsafe_allow_html=True,
    )

    target_url = row.get("actor_url") or row.get("url")
    page_range = row.get("actor_range", "")

    render_slide_range_as_thumbnails(target_url, page_range)


def render_genre_detail(df: pd.DataFrame, row_id: str):
    row = df[df["row_id"] == row_id]
    if row.empty:
        st.error("유효하지 않은 접근입니다.")
        return
    row = row.iloc[0]

    st.markdown(
        '<a href="?view=actor_genre" class="detail-back">← 배우/장르 분석 목록으로</a>',
        unsafe_allow_html=True,
    )

    ip = row["ip"]
    title = row["genre_title"] or "장르 분석"
    date = row["date"]
    air = row["air"]
    meta = " / ".join([x for x in [date, air] if x])

    st.markdown(
        f'<div class="detail-title">{ip} – 장르 분석</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="detail-subtitle">{title}<br>{meta}</div>',
        unsafe_allow_html=True,
    )

    target_url = row.get("genre_url") or row.get("url")
    page_range = row.get("genre_range", "")

    render_slide_range_as_thumbnails(target_url, page_range)


def render_actor_genre_list(df: pd.DataFrame):
    st.markdown(
        '<a href="?view=home" class="detail-back">← 메인으로 돌아가기</a>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="detail-title">배우 / 장르 분석 리포트</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="detail-subtitle">
        한 작품의 슬라이드 중, 배우 분석/장르 분석에 해당하는 페이지만 따로 모아본 리포트입니다.<br>
        아래 탭에서 유형을 선택하고, 카드 클릭 시 해당 분석 슬라이드가 열립니다.
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_actor, tab_genre = st.tabs(["배우 분석", "장르 분석"])

    with tab_actor:
        actor_df = df[df["actor_range"] != ""].copy()
        if actor_df.empty:
            st.info("배우 분석 페이지가 설정된 행이 없습니다.")
        else:
            for _, row in actor_df.iterrows():
                link = f"?view=actor_detail&id={row['row_id']}"
                ip = row["ip"]
                cast = row["cast_clean"] or row["cast"]
                date = row["date"]
                air = row["air"]
                meta = " / ".join([x for x in [date, air] if x])
                cast_text = cast if cast else "(배우 정보 없음)"

                st.markdown(
                    f"""
                    <a href="{link}" target="_self" style="text-decoration:none;color:inherit;">
                      <div class="analysis-card">
                        <div class="analysis-title-row">
                          <div class="analysis-ip">{ip}</div>
                          <div class="analysis-label">배우 분석</div>
                        </div>
                        <div class="analysis-meta">{meta}</div>
                        <div class="analysis-sub">배우: {cast_text}</div>
                      </div>
                    </a>
                    """,
                    unsafe_allow_html=True,
                )

    with tab_genre:
        genre_df = df[df["genre_range"] != ""].copy()
        if genre_df.empty:
            st.info("장르 분석 페이지가 설정된 행이 없습니다.")
        else:
            for _, row in genre_df.iterrows():
                link = f"?view=genre_detail&id={row['row_id']}"
                ip = row["ip"]
                title = row["genre_title"] or "장르 분석"
                date = row["date"]
                air = row["air"]
                meta = " / ".join([x for x in [date, air] if x])

                st.markdown(
                    f"""
                    <a href="{link}" target="_self" style="text-decoration:none;color:inherit;">
                      <div class="analysis-card">
                        <div class="analysis-title-row">
                          <div class="analysis-ip">{ip}</div>
                          <div class="analysis-label">장르 분석</div>
                        </div>
                        <div class="analysis-meta">{meta}</div>
                        <div class="analysis-sub">{title}</div>
                      </div>
                    </a>
                    """,
                    unsafe_allow_html=True,
                )


# ─────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────
def main():
    if VIEW == "home":
        render_home()
        return

    df = load_archive_df()
    if df.empty:
        st.error("아카이브 데이터를 불러오지 못했습니다. ARCHIVE_SHEET_URL 설정을 확인하세요.")
        return

    if VIEW == "monthly":
        render_monthly_stub()
    elif VIEW == "actor_genre":
        render_actor_genre_list(df)
    elif VIEW == "actor_detail" and ROW_ID is not None:
        render_actor_detail(df, ROW_ID)
    elif VIEW == "genre_detail" and ROW_ID is not None:
        render_genre_detail(df, ROW_ID)
    else:
        render_home()


if __name__ == "__main__":
    main()
