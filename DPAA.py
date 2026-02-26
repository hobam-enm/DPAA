import json
import re
from typing import List, Optional
from urllib.parse import urlparse, parse_qs

import pandas as pd
import streamlit as st
from streamlit.components.v1 import iframe as st_iframe
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
    color: #222222;
}
[data-testid="stAppViewContainer"] {
    background-color: #ffffff;
}

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
    color: #666666;
    font-size: 15px;
    margin-bottom: 30px;
    line-height: 1.5;
}

.home-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 40px;
    margin-top: 30px;
}
.home-card {
    position: relative;
    height: 400px;
    padding: 40px;
    border-radius: 24px;
    background: linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%);
    border: 1px solid #e0e0e0;
    box-shadow: 0 20px 40px rgba(0,0,0,0.05);
    text-decoration: none !important;
    color: #222 !important;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
    cursor: pointer;
}
.home-card:hover {
    transform: translateY(-8px);
    border-color: #ff7a50;
    box-shadow: 0 30px 60px rgba(0,0,0,0.1);
}
.home-card-title {
    font-size: 32px;
    font-weight: 800;
    margin-bottom: 12px;
    z-index: 2;
    color: #222 !important;
}
.home-card-desc {
    font-size: 16px;
    color: #555 !important;
    line-height: 1.6;
    z-index: 2;
}
.home-card-tag {
    position: absolute;
    top: 30px;
    right: 30px;
    font-size: 14px;
    font-weight: bold;
    color: #ff4b4b !important;
    letter-spacing: 0.1em;
    z-index: 2;
}

.monthly-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 24px;
    margin-top: 20px;
}
a.monthly-card, a.monthly-card:hover, a.monthly-card:visited {
    text-decoration: none !important;
    color: inherit !important;
}
.monthly-card {
    background: #ffffff;
    border-radius: 16px;
    border: 1px solid #eaeaea;
    box-shadow: 0 4px 12px rgba(0,0,0,0.03);
    overflow: hidden;
    transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
    display: flex;
    flex-direction: column;
}
.monthly-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 30px rgba(0,0,0,0.08);
    border-color: #ff7a50;
}

/* 썸네일 강제 확대 (여백 자르기) 유지 */
.monthly-thumb-box {
    width: 100%;
    aspect-ratio: 16 / 9;
    overflow: hidden;
    border-bottom: 1px solid #eaeaea;
}
.monthly-thumb {
    width: 100%;
    height: 100%;
    object-fit: cover; 
    transform: scale(1.15);
    transition: transform 0.3s ease;
}
.monthly-card:hover .monthly-thumb {
    transform: scale(1.20);
}

.monthly-info {
    padding: 20px;
}
.monthly-title {
    font-size: 18px;
    font-weight: 800;
    color: #111 !important;
    margin-bottom: 8px;
    line-height: 1.4;
    text-decoration: none !important;
}
.monthly-date {
    font-size: 13px;
    color: #777 !important;
}

a.analysis-card {
    text-decoration: none !important;
    color: inherit !important;
}
.analysis-card {
    padding: 20px 24px;
    border-radius: 16px;
    background: #ffffff;
    border: 1px solid #eaeaea;
    box-shadow: 0 4px 12px rgba(0,0,0,0.03);
    margin-bottom: 16px;
    transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.15s ease;
    display: block;
}
.analysis-card:hover {
    border-color: #ff7a50;
    box-shadow: 0 8px 24px rgba(0,0,0,0.08);
    transform: translateY(-2px);
}
.analysis-title-row {
    display: flex;
    align-items: baseline;
    gap: 12px;
    margin-bottom: 8px;
}
.analysis-ip {
    font-size: 18px;
    font-weight: 800;
    color: #111 !important;
}
.analysis-label {
    font-size: 12px;
    padding: 4px 8px;
    border-radius: 999px;
    border: 1px solid #ccc;
    color: #666;
    background: #f9f9f9;
}
.analysis-meta {
    font-size: 14px;
    color: #777;
    margin-bottom: 6px;
}
.analysis-sub {
    font-size: 14px;
    color: #444;
    font-weight: 500;
}

.detail-back {
    display: inline-block;
    padding: 8px 16px;
    margin: 10px 0 20px 0;
    border-radius: 999px;
    border: 1px solid #ddd;
    font-size: 13px;
    font-weight: 500;
    color: #444 !important;
    text-decoration: none !important;
    background: #fff;
    transition: all 0.2s;
}
.detail-back:hover {
    border-color: #ff7a50;
    color: #ff7a50 !important;
    background: #fff5f2;
}
.detail-title {
    font-size: 30px;
    font-weight: 800;
    margin-bottom: 8px;
    color: #111;
}
.detail-subtitle {
    font-size: 15px;
    color: #666;
    margin-bottom: 20px;
    line-height: 1.6;
}

/* 일반 임베드 컨테이너 */
.embed-container {
    position: relative;
    width: 100%;
    padding-bottom: 56.25%; /* 16:9 */
    overflow: hidden;
    border-radius: 12px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.05);
    background: #1e1e1e;
    border: 1px solid #eaeaea;
    margin-bottom: 18px;
}
.embed-container iframe {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    border: 0;
}

/* ===== 수정: PDF 전용 뷰어 컨테이너 (위아래 잘림 방지) ===== */
.pdf-embed-container {
    position: relative;
    width: 100%;
    height: 85vh; /* 비율 강제 고정 대신 화면 높이에 맞춰 길게 뻗도록 변경 */
    border-radius: 12px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.05);
    background: #1e1e1e;
    border: 1px solid #eaeaea;
    margin-bottom: 18px;
}
.pdf-embed-container iframe {
    width: 100%;
    height: 100%;
    border: 0;
    /* transform: scale(1.18); <- 위아래 잘리는 주범 삭제! */
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

    col_map = {
        "IP": "ip", "IP명": "ip", "작품명": "ip",
        "프레젠테이션주소": "url", "프레젠테이션 주소": "url", "PPT주소": "url", "PPT 주소": "url",
        "포스터이미지URL": "img", "포스터 이미지URL": "img", "포스터 이미지 URL": "img",
        "작성월": "date", "작성일": "date",
        "방영일": "air", "방영일자": "air",
        "주연배우": "cast", "배우명": "cast",
        "장르/분석내용": "genre_title", "장르분석제목": "genre_title", "장르분석 제목": "genre_title",
        "배우분석": "actor_range", "장르분석": "genre_range",
        "배우분석 페이지범위": "actor_range", "배우분석 페이지 범위": "actor_range",
        "장르분석 페이지범위": "genre_range", "장르분석 페이지 범위": "genre_range",
        "배우분석 URL": "actor_url", "장르분석 URL": "genre_url",
        "배우분석URL": "actor_url", "장르분석URL": "genre_url",
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    req_cols = [
        "ip", "url", "img", "date", "air", "cast",
        "actor_range", "genre_title", "genre_range", "actor_url", "genre_url",
    ]
    for c in req_cols:
        if c not in df.columns: df[c] = ""
        df[c] = df[c].astype(str).fillna("").str.strip().replace("nan", "")

    df["cast_clean"] = df["cast"].apply(
        lambda x: ", ".join([p.strip() for p in re.split(r"[,/]", x) if p.strip()])
        if isinstance(x, str) else ""
    )
    df = df[df["ip"] != ""].copy()
    df.reset_index(drop=True, inplace=True)
    df["row_id"] = df.index.astype(str)
    return df

@st.cache_data(ttl=300, show_spinner=False)
def load_monthly_df() -> pd.DataFrame:
    if not ARCHIVE_SHEET_URL:
        return pd.DataFrame()
    m = re.search(r"/spreadsheets/d/([^/]+)/", ARCHIVE_SHEET_URL)
    if not m:
        return pd.DataFrame()
    
    sheet_id = m.group(1)
    xlsx_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
    
    try:
        df = pd.read_excel(xlsx_url, sheet_name="월간 드라마인사이트")
        df = df.iloc[:, :3]
        df.columns = ["title", "date", "url"]
        
        df = df.dropna(subset=["title", "url"])
        for c in ["title", "date", "url"]:
            df[c] = df[c].astype(str).fillna("").str.strip().replace("nan", "")
            
        df = df[df["title"] != ""].copy()
        df.reset_index(drop=True, inplace=True)
        df["row_id"] = "monthly_" + df.index.astype(str)
        return df
    except Exception as e:
        st.error(f"월간 드라마인사이트 시트 로딩 실패: {e}\n(openpyxl 패키지가 설치되어 있는지 확인하세요.)")
        return pd.DataFrame()


# ─────────────────────────────────────────────────────────────
# Google API – Slides / Drive 인증 및 썸네일
# ─────────────────────────────────────────────────────────────
SLIDES_SCOPES = ["https://www.googleapis.com/auth/presentations.readonly"]
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

@st.cache_resource(show_spinner=False)
def get_google_credentials(scopes: List[str]):
    google_api_conf = st.secrets.get("google_api", {})
    info_str = google_api_conf.get("service_account_json", "")
    if not info_str:
        return None
    try:
        info = json.loads(info_str)
        return service_account.Credentials.from_service_account_info(info, scopes=scopes)
    except Exception as e:
        st.warning(f"GCP 인증 실패: {e}")
        return None

@st.cache_resource(show_spinner=False)
def get_slides_service():
    creds = get_google_credentials(SLIDES_SCOPES)
    if not creds: return None
    return build("slides", "v1", credentials=creds, cache_discovery=False)

@st.cache_resource(show_spinner=False)
def get_drive_service():
    creds = get_google_credentials(DRIVE_SCOPES)
    if not creds: return None
    return build("drive", "v3", credentials=creds, cache_discovery=False)

@st.cache_data(ttl=600, show_spinner=False)
def get_presentation_page_ids(presentation_id: str) -> List[str]:
    service = get_slides_service()
    if service is None: return []
    try:
        pres = service.presentations().get(presentationId=presentation_id).execute()
        slides = pres.get("slides", [])
        return [s.get("objectId") for s in slides if s.get("objectId")]
    except Exception as e:
        return []

@st.cache_data(ttl=600, show_spinner=False)
def get_slide_thumbnail_url(presentation_id: str, page_object_id: str) -> Optional[str]:
    service = get_slides_service()
    if service is None: return None
    try:
        resp = service.presentations().pages().getThumbnail(
            presentationId=presentation_id,
            pageObjectId=page_object_id,
            thumbnailProperties_thumbnailSize="LARGE",
        ).execute()
        return resp.get("contentUrl")
    except Exception as e:
        return None

@st.cache_data(ttl=600, show_spinner=False)
def get_drive_thumbnail_url(file_id: str) -> Optional[str]:
    service = get_drive_service()
    if service is None: return None
    try:
        file_meta = service.files().get(fileId=file_id, fields="thumbnailLink").execute()
        link = file_meta.get("thumbnailLink")
        if link:
            link = re.sub(r'=s\d+$', '=s1000', link)
        return link
    except Exception as e:
        return None


# ─────────────────────────────────────────────────────────────
# 유틸 – URL 파싱 및 임베드
# ─────────────────────────────────────────────────────────────
def parse_page_range(page_range: str) -> List[int]:
    page_range = (page_range or "").strip()
    if not page_range: return []
    m = re.match(r"(\d+)\s*-\s*(\d+)", page_range)
    if m:
        start, end = int(m.group(1)), int(m.group(2))
        if start > end: start, end = end, start
        return list(range(start, end + 1))
    m = re.match(r"(\d+)", page_range)
    if m: return [int(m.group(1))]
    return []

def extract_presentation_id(url: str) -> Optional[str]:
    if not url or "docs.google.com/presentation" not in url: return None
    m = re.search(r"/d/([^/]+)/", url)
    return m.group(1) if m else None

def extract_drive_file_id(url: str) -> Optional[str]:
    if not url: return None
    m = re.search(r"/file/d/([^/]+)", url)
    if m: return m.group(1)
    m = re.search(r"id=([^&]+)", url)
    if m: return m.group(1)
    return None

def build_embed_url_if_possible(url: str, page_range: str = "") -> str:
    if not url: return ""
    is_pdf = url.lower().endswith(".pdf") or "/file/d/" in url
    if is_pdf:
        if "/preview" in url: return url
        return url.replace("/view", "/preview")

    if "docs.google.com/presentation" in url:
        pres_id = extract_presentation_id(url)
        if not pres_id: return url
        base = f"https://docs.google.com/presentation/d/{pres_id}/embed?start=false&loop=false&delayms=60000"
        pages = parse_page_range(page_range)
        if pages: base += f"&slide=id.p{pages[0]}"
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
        """, unsafe_allow_html=True
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
        """, unsafe_allow_html=True
    )

def render_monthly_list(df_monthly: pd.DataFrame):
    st.markdown('<a href="?view=home" target="_self" class="detail-back">← 메인으로 돌아가기</a>', unsafe_allow_html=True)
    st.markdown('<div class="detail-title">월간 드라마 인사이트 리포트</div>', unsafe_allow_html=True)
    st.markdown('<div class="detail-subtitle">월 단위 시장 인사이트와 시청자 반응을 분석한 PDF 리포트입니다.</div>', unsafe_allow_html=True)

    if df_monthly.empty:
        st.info("등록된 월간 리포트가 없습니다. 시트를 확인해 주세요.")
        return

    cols_html = ['<div class="monthly-grid">']
    
    for _, row in df_monthly.iterrows():
        title = row["title"]
        date = row["date"]
        url = row["url"]
        
        file_id = extract_drive_file_id(url)
        thumb_url = ""
        
        if file_id:
            thumb_url = get_drive_thumbnail_url(file_id) or "https://via.placeholder.com/640x360?text=No+Thumbnail"
        else:
            thumb_url = "https://via.placeholder.com/640x360?text=Invalid+Link"

        link = f"?view=monthly_detail&id={row['row_id']}"
        
        card_html = f'<a href="{link}" target="_self" class="monthly-card"><div class="monthly-thumb-box"><img src="{thumb_url}" class="monthly-thumb" alt="{title}"></div><div class="monthly-info"><div class="monthly-title">{title}</div><div class="monthly-date">발행시점 : {date}</div></div></a>'
        cols_html.append(card_html)
        
    cols_html.append("</div>")
    st.markdown("".join(cols_html), unsafe_allow_html=True)

def render_monthly_detail(df_monthly: pd.DataFrame, row_id: str):
    row = df_monthly[df_monthly["row_id"] == row_id]
    if row.empty:
        st.error("유효하지 않은 접근입니다.")
        return
    row = row.iloc[0]

    st.markdown('<a href="?view=monthly" target="_self" class="detail-back">← 월간 리포트 목록으로</a>', unsafe_allow_html=True)

    title = row["title"]
    date = row["date"]
    url = row["url"]

    st.markdown(f'<div class="detail-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="detail-subtitle">발행시점 : {date}</div>', unsafe_allow_html=True)

    embed_url = build_embed_url_if_possible(url)
    if embed_url:
        st.markdown(f"""
        <div class="pdf-embed-container">
            <iframe src="{embed_url}" allowfullscreen="true"></iframe>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("PDF를 불러올 수 없습니다. 올바른 구글 드라이브 링크인지 확인해 주세요.")

def render_slide_range_as_thumbnails(target_url: str, page_range: str):
    pres_id = extract_presentation_id(target_url)
    if not pres_id:
        embed_url = build_embed_url_if_possible(target_url, page_range)
        if not embed_url:
            st.warning("연결된 프레젠테이션 링크가 없습니다.")
            return
        st.markdown(f"""
        <div class="embed-container">
            <iframe src="{embed_url}" allowfullscreen="true"></iframe>
        </div>
        """, unsafe_allow_html=True)
        return

    pages = parse_page_range(page_range)
    if not pages:
        embed_url = build_embed_url_if_possible(target_url, page_range)
        if not embed_url:
            st.warning("페이지 범위가 설정되지 않았고, 프레젠테이션을 불러올 수 없습니다.")
            return
        st.markdown(f"""
        <div class="embed-container">
            <iframe src="{embed_url}" allowfullscreen="true"></iframe>
        </div>
        """, unsafe_allow_html=True)
        return

    page_ids = get_presentation_page_ids(pres_id)
    if not page_ids:
        embed_url = build_embed_url_if_possible(target_url, page_range)
        if not embed_url:
            st.warning("프레젠테이션 정보를 불러오지 못했습니다.")
            return
    else:
        rendered_any = False
        for p in pages:
            idx = p - 1
            if 0 <= idx < len(page_ids):
                page_obj_id = page_ids[idx]
                thumb_url = get_slide_thumbnail_url(pres_id, page_obj_id)
                if thumb_url:
                    rendered_any = True
                    st.markdown(f"""
                    <div class="embed-container" style="background:transparent; border:none; box-shadow:none; margin-bottom:12px;">
                        <img src="{thumb_url}" style="position:absolute; top:0; left:0; width:100%; height:100%; object-fit:contain; border-radius:12px; border:1px solid #eaeaea; box-shadow:0 10px 30px rgba(0,0,0,0.05);">
                    </div>
                    """, unsafe_allow_html=True)
        if rendered_any:
            return

        embed_url = build_embed_url_if_possible(target_url, page_range)
        if embed_url:
            st.markdown(f"""
            <div class="embed-container">
                <iframe src="{embed_url}" allowfullscreen="true"></iframe>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("해당 페이지 범위를 렌더링할 수 없습니다.")


def render_actor_detail(df: pd.DataFrame, row_id: str):
    row = df[df["row_id"] == row_id]
    if row.empty:
        st.error("유효하지 않은 접근입니다.")
        return
    row = row.iloc[0]

    st.markdown('<a href="?view=actor_genre" target="_self" class="detail-back">← 배우/장르 분석 목록으로</a>', unsafe_allow_html=True)

    ip = row["ip"]
    cast = row["cast_clean"] or row["cast"]
    date = row["date"]
    air = row["air"]

    date_str = date if date else "미상"
    air_str = air if air else "미상"
    meta = f"분석시점 : {date_str} / IP방영시점 : {air_str}"

    cast_text = cast if cast else "배우 정보 없음"
    title_display = f"{cast_text} ({ip})"

    st.markdown(f'<div class="detail-title">{title_display}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="detail-subtitle">배우 분석 리포트<br>{meta}</div>', unsafe_allow_html=True)

    target_url = row.get("actor_url") or row.get("url")
    page_range = row.get("actor_range", "")

    render_slide_range_as_thumbnails(target_url, page_range)


def render_genre_detail(df: pd.DataFrame, row_id: str):
    row = df[df["row_id"] == row_id]
    if row.empty:
        st.error("유효하지 않은 접근입니다.")
        return
    row = row.iloc[0]

    st.markdown('<a href="?view=actor_genre" target="_self" class="detail-back">← 배우/장르 분석 목록으로</a>', unsafe_allow_html=True)

    ip = row["ip"]
    title = row["genre_title"] or "장르 분석"
    date = row["date"]
    air = row["air"]

    date_str = date if date else "미상"
    air_str = air if air else "미상"
    meta = f"분석시점 : {date_str} / IP방영시점 : {air_str}"

    title_display = f"{title} ({ip})"

    st.markdown(f'<div class="detail-title">{title_display}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="detail-subtitle">장르 분석 리포트<br>{meta}</div>', unsafe_allow_html=True)

    target_url = row.get("genre_url") or row.get("url")
    page_range = row.get("genre_range", "")

    render_slide_range_as_thumbnails(target_url, page_range)


def render_actor_genre_list(df: pd.DataFrame):
    st.markdown('<a href="?view=home" target="_self" class="detail-back">← 메인으로 돌아가기</a>', unsafe_allow_html=True)
    st.markdown('<div class="detail-title">배우 / 장르 분석 리포트</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="detail-subtitle">
        한 작품의 슬라이드 중, 배우 분석/장르 분석에 해당하는 페이지만 따로 모아본 리포트입니다.<br>
        아래 검색이나 탭에서 유형을 선택하고, 카드 클릭 시 해당 분석 슬라이드가 열립니다.
        </div>
        """, unsafe_allow_html=True
    )

    col1, col2 = st.columns(2)
    with col1:
        search_query = st.text_input("🔍 텍스트 검색 (배우, 장르 등)", placeholder="검색어를 입력하세요...")
    with col2:
        unique_ips = sorted(df["ip"].dropna().unique().tolist())
        selected_ips = st.multiselect("📌 작품명 필터 (리스트 선택)", options=unique_ips, default=[])

    tab_actor, tab_genre = st.tabs(["배우 분석", "장르 분석"])

    with tab_actor:
        actor_df = df[df["actor_range"] != ""].copy()
        if search_query:
            mask = actor_df["ip"].str.contains(search_query, case=False, na=False) | \
                   actor_df["cast"].str.contains(search_query, case=False, na=False)
            actor_df = actor_df[mask]
        
        if selected_ips:
            actor_df = actor_df[actor_df["ip"].isin(selected_ips)]

        if actor_df.empty:
            st.info("조건에 맞는 배우 분석 페이지가 없습니다.")
        else:
            for _, row in actor_df.iterrows():
                link = f"?view=actor_detail&id={row['row_id']}"
                ip = row["ip"]
                cast = row["cast_clean"] or row["cast"]
                date = row["date"]
                air = row["air"]
                
                date_str = date if date else "미상"
                air_str = air if air else "미상"
                meta = f"분석시점 : {date_str} / IP방영시점 : {air_str}"

                cast_text = cast if cast else "배우 정보 없음"
                title_display = f"{cast_text} ({ip})"

                st.markdown(
                    f"""
                    <a href="{link}" target="_self" class="analysis-card">
                      <div class="analysis-title-row">
                        <div class="analysis-ip">{title_display}</div>
                        <div class="analysis-label">배우 분석</div>
                      </div>
                      <div class="analysis-meta">{meta}</div>
                      <div class="analysis-sub">작품: {ip}</div>
                    </a>
                    """, unsafe_allow_html=True
                )

    with tab_genre:
        genre_df = df[df["genre_range"] != ""].copy()
        if search_query:
            mask = genre_df["ip"].str.contains(search_query, case=False, na=False) | \
                   genre_df["genre_title"].str.contains(search_query, case=False, na=False)
            genre_df = genre_df[mask]
            
        if selected_ips:
            genre_df = genre_df[genre_df["ip"].isin(selected_ips)]

        if genre_df.empty:
            st.info("조건에 맞는 장르 분석 페이지가 없습니다.")
        else:
            for _, row in genre_df.iterrows():
                link = f"?view=genre_detail&id={row['row_id']}"
                ip = row["ip"]
                title = row["genre_title"] or "장르 분석"
                date = row["date"]
                air = row["air"]

                date_str = date if date else "미상"
                air_str = air if air else "미상"
                meta = f"분석시점 : {date_str} / IP방영시점 : {air_str}"

                title_display = f"{title} ({ip})"

                st.markdown(
                    f"""
                    <a href="{link}" target="_self" class="analysis-card">
                      <div class="analysis-title-row">
                        <div class="analysis-ip">{title_display}</div>
                        <div class="analysis-label">장르 분석</div>
                      </div>
                      <div class="analysis-meta">{meta}</div>
                      <div class="analysis-sub">작품: {ip}</div>
                    </a>
                    """, unsafe_allow_html=True
                )


# ─────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────
def main():
    if VIEW == "home":
        render_home()
        return

    if VIEW == "monthly":
        df_monthly = load_monthly_df()
        render_monthly_list(df_monthly)
    elif VIEW == "monthly_detail" and ROW_ID is not None:
        df_monthly = load_monthly_df()
        render_monthly_detail(df_monthly, ROW_ID)
    else:
        df = load_archive_df()
        if df.empty:
            st.error("아카이브 데이터를 불러오지 못했습니다. ARCHIVE_SHEET_URL 설정을 확인하세요.")
            return

        if VIEW == "actor_genre":
            render_actor_genre_list(df)
        elif VIEW == "actor_detail" and ROW_ID is not None:
            render_actor_detail(df, ROW_ID)
        elif VIEW == "genre_detail" and ROW_ID is not None:
            render_genre_detail(df, ROW_ID)
        else:
            render_home()

if __name__ == "__main__":
    main()