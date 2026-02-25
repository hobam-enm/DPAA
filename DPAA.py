# -*- coding: utf-8 -*-
# 🎬 드라마 인사이트 아카이브 v2 (월간 리포트 / 배우·장르 분석 리포트)

import json
import re
from typing import List, Optional, Tuple
from urllib.parse import urlparse, parse_qs, quote

import pandas as pd
import streamlit as st
from streamlit.components.v1 import iframe as st_iframe

# 구글 API는 옵션 – secrets에 없으면 임포트 스킵
GOOGLE_API_AVAILABLE = False
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    GOOGLE_API_AVAILABLE = True
except Exception:
    GOOGLE_API_AVAILABLE = False

# ==============================================================================
# [1] 기본 설정 & 공통 스타일
# ==============================================================================

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

/* 탭 제목 */
[data-baseweb="tab"] {
    font-size: 14px !important;
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
}

/* 작은 버튼 */
.small-pill {
    display: inline-block;
    font-size: 11px;
    padding: 3px 8px;
    border-radius: 999px;
    border: 1px solid #555;
    color: #aaa;
    margin-left: 6px;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ==============================================================================
# [2] 데이터 로딩 (CSV 기반)
# ==============================================================================

ARCHIVE_SHEET_URL = st.secrets.get("ARCHIVE_SHEET_URL", "")

def build_csv_url(sheet_url: str) -> Optional[str]:
    if not sheet_url or "docs.google.com" not in sheet_url:
        return None
    try:
        m = re.search(r"/spreadsheets/d/([^/]+)/", sheet_url)
        gid = parse_qs(urlparse(sheet_url).query).get("gid", ["0"])[0]
        return f"https://docs.google.com/spreadsheets/d/{m.group(1)}/export?format=csv&gid={gid}"
    except Exception:
        return None

@st.cache_data(ttl=300, show_spinner=False)
def load_archive_df() -> pd.DataFrame:
    csv = build_csv_url(ARCHIVE_SHEET_URL)
    if not csv:
        return pd.DataFrame()

    try:
        df = pd.read_csv(csv)
    except Exception:
        return pd.DataFrame()

    # 컬럼 매핑 (가능성 넓게 잡기)
    col_map = {
        "IP명": "ip", "IP": "ip", "작품명": "ip",
        "프레젠테이션주소": "url", "프레젠테이션 주소": "url",
        "PPT주소": "url", "PPT 주소": "url",
        "포스터이미지URL": "img", "포스터 이미지 URL": "img",
        "작성월": "date", "작성일": "date",
        "방영일": "air", "방영일자": "air",
        "주연배우": "cast", "배우명": "cast",
        # 배우 분석
        "배우분석 페이지범위": "actor_range",
        "배우분석 페이지 범위": "actor_range",
        "배우 페이지범위": "actor_range",
        "배우 페이지 범위": "actor_range",
        # 장르 분석
        "장르분석 제목": "genre_title",
        "장르분석제목": "genre_title",
        "장르분석": "genre_title",
        "장르분석 페이지범위": "genre_range",
        "장르분석 페이지 범위": "genre_range",
        "장르 페이지범위": "genre_range",
        "장르 페이지 범위": "genre_range",
        # 배우/장르 부분 프레젠테이션 URL (동기화 결과)
        "배우분석주소": "actor_url",
        "배우분석 주소": "actor_url",
        "장르분석주소": "genre_url",
        "장르분석 주소": "genre_url",
    }

    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    # 필수 컬럼 보정
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

    # 배우명 정리
    df["cast_clean"] = df["cast"].apply(
        lambda x: ", ".join([p.strip() for p in re.split(r"[,/]", x) if p.strip()])
        if isinstance(x, str) else ""
    )

    # row_id 부여 (문자열)
    df = df[df["ip"] != ""].copy()
    df.reset_index(drop=True, inplace=True)
    df["row_id"] = df.index.astype(str)

    return df

# 페이지 파라미터
params = st.query_params
VIEW = params.get("view", "home")
MODE = params.get("mode", None)
ROW_ID = params.get("id", None)
ADMIN_FLAG = params.get("admin", "0")

# ==============================================================================
# [3] 구글 API – 배우/장르 분석 슬라이드 동기화 (옵션)
# ==============================================================================

def get_google_services():
    """
    서비스 계정 기반 Google API 클라이언트 생성.
    secrets.toml에 google_api 섹션이 없으면 예외 발생.
    """
    gconf = st.secrets.get("google_api", None)
    if not gconf or not GOOGLE_API_AVAILABLE:
        raise RuntimeError("google_api 설정 또는 라이브러리가 없습니다.")

    info_str = gconf.get("service_account_json", "")
    spreadsheet_id = gconf.get("spreadsheet_id", "")
    sheet_name = gconf.get("sheet_name", "")
    folder_id = gconf.get("folder_id", "")

    if not info_str or not spreadsheet_id or not sheet_name or not folder_id:
        raise RuntimeError("google_api 설정값이 부족합니다.")

    creds = service_account.Credentials.from_service_account_info(
        json.loads(info_str),
        scopes=[
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/presentations",
            "https://www.googleapis.com/auth/spreadsheets",
        ],
    )

    drive = build("drive", "v3", credentials=creds)
    slides = build("slides", "v1", credentials=creds)
    sheets = build("sheets", "v4", credentials=creds)

    return drive, slides, sheets, spreadsheet_id, sheet_name, folder_id


def extract_file_id(url: str) -> str:
    m = re.search(r"/d/([^/]+)/", url)
    return m.group(1) if m else ""


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


def create_sub_presentation(
    drive,
    slides,
    src_file_id: str,
    new_name: str,
    keep_pages: List[int],
    folder_id: str,
) -> str:
    # 1) 원본 프레젠테이션 전체 복사
    copied = drive.files().copy(
        fileId=src_file_id,
        body={"name": new_name, "parents": [folder_id]},
    ).execute()
    new_file_id = copied["id"]

    # 2) 새 프레젠테이션에서 삭제할 슬라이드 결정
    pres = slides.presentations().get(presentationId=new_file_id).execute()
    slides_list = pres.get("slides", [])
    keep_indices = {p - 1 for p in keep_pages if 1 <= p <= len(slides_list)}

    requests = []
    for idx, slide in enumerate(slides_list):
        if idx not in keep_indices:
            requests.append({"deleteObject": {"objectId": slide["objectId"]}})

    if requests:
        slides.presentations().batchUpdate(
            presentationId=new_file_id, body={"requests": requests}
        ).execute()

    return f"https://docs.google.com/presentation/d/{new_file_id}/edit"


def sync_actor_genre_presentations() -> int:
    """
    관리시트 전체를 훑어서:
    - 배우분석 페이지범위(I열)에 값이 있고 배우분석주소(K열)이 비어 있으면 → 새 프레젠테이션 생성
    - 장르분석 페이지범위(J열)에 값이 있고 장르분석주소(L열)이 비어 있으면 → 새 프레젠테이션 생성
    그 후 K/L 열에 URL 기록.
    """
    drive, slides, sheets, spreadsheet_id, sheet_name, folder_id = get_google_services()

    # A2:L 범위 사용 (12열)
    read_range = f"{sheet_name}!A2:L"
    resp = sheets.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=read_range
    ).execute()
    rows = resp.get("values", [])
    if not rows:
        return 0

    updated = 0
    new_values = []

    for row in rows:
        # 길이 패딩
        while len(row) < 12:
            row.append("")

        # 컬럼 인덱스 (0-based)
        url = str(row[1]).strip()          # B열: 원본 PPT URL
        actor_range = str(row[8]).strip()  # I열: 배우 페이지범위
        genre_range = str(row[9]).strip()  # J열: 장르 페이지범위
        actor_url = str(row[10]).strip()   # K열: 배우 분석 주소
        genre_url = str(row[11]).strip()   # L열: 장르 분석 주소

        file_id = extract_file_id(url)
        if not file_id:
            new_values.append(row)
            continue

        # 파일 이름은 가져오면 좋지만 없어도 동작에는 문제 없음
        base_name = row[0] if len(row[0]) else "분석"

        # 배우 분석
        if actor_range and not actor_url:
            pages = parse_page_range(actor_range)
            if pages:
                new_name = f"{base_name}_배우분석"
                try:
                    actor_url = create_sub_presentation(
                        drive, slides, file_id, new_name, pages, folder_id
                    )
                    row[10] = actor_url
                    updated += 1
                except Exception as e:
                    # 실패해도 나머지 행은 계속
                    print("actor sync error:", e)

        # 장르 분석
        if genre_range and not genre_url:
            pages = parse_page_range(genre_range)
            if pages:
                new_name = f"{base_name}_장르분석"
                try:
                    genre_url = create_sub_presentation(
                        drive, slides, file_id, new_name, pages, folder_id
                    )
                    row[11] = genre_url
                    updated += 1
                except Exception as e:
                    print("genre sync error:", e)

        new_values.append(row)

    # 시트 업데이트
    sheets.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=read_range,
        valueInputOption="RAW",
        body={"values": new_values},
    ).execute()

    # 캐시된 CSV도 갱신되도록 캐시 클리어
    load_archive_df.clear()

    return updated

# ==============================================================================
# [4] 화면 렌더링 – 홈 / 월간 / 배우·장르 리스트 / 상세
# ==============================================================================

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

    base = st.get_query_params()
    # 홈 진입 시 불필요한 query param 제거
    base.clear()

    monthly_link = "?view=monthly"
    actor_link = "?view=actor_genre"

    st.markdown(
        f"""
        <div class="home-grid">
          <a href="{monthly_link}" class="home-card">
            <div class="home-card-tag">MONTHLY</div>
            <div class="home-card-title">월간 드라마 인사이트 리포트</div>
            <div class="home-card-desc">
              월 단위로 정리한 시장 인사이트, 핵심 작품, 시청자 반응 변화를 다룬 리포트입니다.
              (구성은 추후 추가 예정)
            </div>
          </a>
          <a href="{actor_link}" class="home-card">
            <div class="home-card-tag">CAST / GENRE</div>
            <div class="home-card-title">배우 / 장르 분석 리포트</div>
            <div class="home-card-desc">
              IP별 배우 캐스팅 포인트와 장르 포지셔닝을 한눈에 볼 수 있는 리포트입니다.
              분석용 슬라이드만 모아 빠르게 검토할 수 있습니다.
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
    st.markdown(
        """
        <div class="detail-subtitle">
        이 영역은 월별 시장 리포트를 위한 플레이스홀더입니다.<br>
        나중에 월 선택, 주요 지표, 키 인사이트 카드 등을 붙일 수 있게 구조만 먼저 열어둔 상태입니다.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.info("월간 리포트 페이지 구성은 추후 설계 예정입니다.")


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
        한 작품의 슬라이드 중, 배우 분석/장르 분석에 해당하는 페이지만 따로 모아둔 리포트입니다.<br>
        아래 탭에서 유형을 선택하고, 카드 클릭 시 해당 분석 슬라이드가 열립니다.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 관리자 모드에서만 동기화 버튼 노출 (admin=1 & google_api 사용 가능)
    if ADMIN_FLAG == "1" and GOOGLE_API_AVAILABLE and "google_api" in st.secrets:
        if st.button("배우/장르 분석 슬라이드 동기화 실행", type="secondary"):
            with st.spinner("슬라이드 동기화 중..."):
                cnt = sync_actor_genre_presentations()
            st.success(f"{cnt}개 행에 대해 분석 프레젠테이션을 생성/갱신했습니다.")

    tab_actor, tab_genre = st.tabs(["배우 분석", "장르 분석"])

    # 배우 분석 리스트: actor_range가 있는 행
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

    # 장르 분석 리스트: genre_range가 있는 행
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


def _build_embed_url_from_slide_url(url: str, page_range: str = "") -> str:
    """
    Google Slides URL 또는 PDF URL을 embed용 URL로 변환.
    - actor_url / genre_url 이 따로 있을 경우: 해당 URL 그대로 embed.
    - 부분 프레젠테이션이 없고 원본 URL만 있는 경우:
      page_range의 첫 페이지를 시작 슬라이드로 지정 (단, 다른 슬라이드로 넘어가는 것은 막지 않음)
    """
    if not url:
        return ""

    is_pdf = url.lower().endswith(".pdf") or "/file/d/" in url
    if is_pdf:
        # PDF는 /preview 로 변경해서 iframe으로 보여줌
        if "/preview" in url:
            return url
        return url.replace("/view", "/preview")

    if "docs.google.com/presentation" in url:
        # /d/{id}/ 추출
        m = re.search(r"/d/([^/]+)/", url)
        if not m:
            return url
        file_id = m.group(1)
        base = f"https://docs.google.com/presentation/d/{file_id}/embed?start=false&loop=false&delayms=60000"

        # page_range에서 첫 번호만 추출하여 시작 슬라이드 지정 (선택)
        pages = parse_page_range(page_range)
        if pages:
            start_slide = pages[0]
            # Google이 내부적으로 id.p{N} 형태를 쓰는 케이스가 많음
            base += f"&slide=id.p{start_slide}"
        return base

    # 기타 URL은 그대로 사용
    return url


def render_actor_detail(df: pd.DataFrame, row_id: str):
    row = df[df["row_id"] == row_id]
    if row.empty:
        st.error("유효하지 않은 접근입니다.")
        return
    row = row.iloc[0]

    back_link = "?view=actor_genre"
    st.markdown(
        f'<a href="{back_link}" class="detail-back">← 배우/장르 분석 목록으로</a>',
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

    # URL 선택: 배우분석용 프레젠테이션이 있으면 우선 사용
    target_url = row.get("actor_url") or row.get("url")
    page_range = row.get("actor_range", "")

    embed_url = _build_embed_url_from_slide_url(target_url, page_range)
    if not embed_url:
        st.warning("연결된 프레젠테이션 링크가 없습니다.")
        return

    st.markdown('<div class="embed-frame">', unsafe_allow_html=True)
    st_iframe(embed_url, height=800, scrolling=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_genre_detail(df: pd.DataFrame, row_id: str):
    row = df[df["row_id"] == row_id]
    if row.empty:
        st.error("유효하지 않은 접근입니다.")
        return
    row = row.iloc[0]

    back_link = "?view=actor_genre"
    st.markdown(
        f'<a href="{back_link}" class="detail-back">← 배우/장르 분석 목록으로</a>',
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

    embed_url = _build_embed_url_from_slide_url(target_url, page_range)
    if not embed_url:
        st.warning("연결된 프레젠테이션 링크가 없습니다.")
        return

    st.markdown('<div class="embed-frame">', unsafe_allow_html=True)
    st_iframe(embed_url, height=800, scrolling=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ==============================================================================
# [5] 메인 실행
# ==============================================================================

def main():
    if VIEW == "home":
        render_home()
        return

    # 홈이 아닐 때만 데이터 로딩
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
        # 알 수 없는 view 값이면 홈으로
        render_home()


if __name__ == "__main__":
    main()