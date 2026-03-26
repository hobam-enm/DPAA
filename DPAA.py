import json
import re
import io
import base64
from typing import List, Optional
from urllib.parse import urlparse, parse_qs

import pandas as pd
import streamlit as st
from streamlit.components.v1 import iframe as st_iframe
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# ─────────────────────────────────────────────────────────────
# 기본 설정 & 스타일
# ─────────────────────────────────────────────────────────────
PAGE_TITLE = "드라마 인사이트랩"
PAGE_ICON = "🔬"

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
    height: 600px;
    padding: 40px;
    border-radius: 24px;
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
/* ===== 홈 카드 배경 이미지 + 하단 그라데이션 오버레이 ===== */
.home-card::before{
    content:"";
    position:absolute;
    inset:0;
    background-image: var(--bg);
    background-size: cover;
    background-position: center;
    transform: scale(1.02);
    z-index:0;
}
.home-card::after{
    content:"";
    position:absolute;
    inset:0;
    /* 아래로 갈수록 검정이 진하고, 위로 갈수록 투명 */
    background: linear-gradient(to top, rgba(0,0,0,0.78) 0%, rgba(0,0,0,0.35) 35%, rgba(0,0,0,0.00) 72%);
    z-index:1;
}
.home-card-title, .home-card-desc, .home-card-tag{
    position: relative;
    z-index: 2;
    color: #ffffff !important;
}
.home-card-desc{
    color: rgba(255,255,255,0.92) !important;
}
.home-card-tag{
    color: rgba(255,255,255,0.9) !important;
    text-shadow: 0 2px 10px rgba(0,0,0,0.35);
}
.home-card-title{
    text-shadow: 0 6px 20px rgba(0,0,0,0.45);
}

.card-monthly { background: transparent; }

.card-actor { background: transparent; }

/* ===== 수정: 카드 공통 호버 액션 및 중복 코드 제거 ===== */
.home-card:hover {
    transform: translateY(-8px);
    box-shadow: 0 30px 60px rgba(0,0,0,0.1);
}

/* ===== 추가: 월간 리포트 호버 테두리 (파란색 계열) ===== */
.card-monthly:hover {
    border-color: #4a90e2; 
}

/* ===== 추가: 배우/장르 리포트 호버 테두리 (보라색 계열) ===== */
.card-actor:hover {
    border-color: #8b5cf6; 
}

.home-card-title {
    font-size: 32px;
    font-weight: 800;
    margin-bottom: 12px;
    z-index: 2;}
.home-card-desc {
    font-size: 16px;    line-height: 1.6;
    z-index: 2;
}

/* ===== 수정: 공통 태그 스타일에서 고정 색상 제거 ===== */
.home-card-tag {
    position: absolute;
    top: 30px;
    right: 30px;
    font-size: 14px;
    font-weight: bold;
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

/* 썸네일 강제 확대 1.10 유지 */
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
    transform: scale(1.05); 
    transition: transform 0.3s ease;
}
.monthly-card:hover .monthly-thumb {
    transform: scale(1.15);
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

/* =========================================
   상세 뷰어 공통 및 텍스트 스타일
========================================= */
.viewer-wrapper {
    max-width: 1200px; /* 너무 꽉 차는 현상을 방지하기 위해 가로폭 제한 */
    margin: 0 auto;    /* 화면 중앙 정렬 */
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

/* =========================================
   PDF 및 슬라이드 컨테이너 스타일
========================================= */
/* PDF 개별 페이지 이미지 (테두리 추가) */
.pdf-page-img {
    width: 100%;
    display: block;
    border: 1px solid #d4d4d4; /* 너무 진하지 않은 부드러운 테두리 */
    box-shadow: 0 4px 12px rgba(0,0,0,0.06); /* 페이지 간 구분용 가벼운 그림자 */
    margin-bottom: 30px; /* 페이지 사이 간격 넓게 확보 */
    border-radius: 6px; /* 끝부분 살짝 둥글게 */
    background-color: #ffffff;
}

/* 슬라이드 썸네일 전용 임베드 컨테이너 */
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

/* 구글 드라이브 기본 뷰어 폴백용 */
.pdf-native-container {
    width: 100%;
    height: 85vh; 
    border-radius: 12px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.08);
    background: #f5f5f5;
    border: 1px solid #eaeaea;
    margin-bottom: 18px;
    overflow: hidden;
}
.pdf-native-container iframe {
    width: 100%;
    height: 100%;
    border: 0;
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

# 홈 카드 배경 이미지(Secrets)
HOME_IMG1 = st.secrets.get("img1", "")
HOME_IMG2 = st.secrets.get("img2", "")


APP_BASE_URL = "https://dmkt-insight.streamlit.app"

def _norm_text(v) -> str:
    if v is None:
        return ""
    s = str(v).strip()
    if s.lower() == "nan":
        return ""
    return s

def make_stable_key(*parts: str) -> str:
    raw = "|".join([_norm_text(p) for p in parts if _norm_text(p)])
    raw = raw.lower()
    raw = re.sub(r"\s+", "-", raw)
    raw = re.sub(r"[^0-9a-z가-힣_-]+", "-", raw)
    raw = re.sub(r"-+", "-", raw).strip("-")
    return raw[:220]

def find_row_by_identifier(df: pd.DataFrame, identifier: str, stable_col: str) -> pd.DataFrame:
    if identifier is None or df.empty:
        return df.iloc[0:0]
    if "row_id" in df.columns:
        row = df[df["row_id"] == identifier]
        if not row.empty:
            return row
    if stable_col in df.columns:
        row = df[df[stable_col] == identifier]
        if not row.empty:
            return row
    return df.iloc[0:0]

def build_share_url(view: str, item_key: str) -> str:
    return f"{APP_BASE_URL}/?view={view}&id={item_key}"

def render_detail_action_bar(back_href: str, back_label: str, share_url: str, key_suffix: str):
    safe_key = re.sub(r"[^0-9a-zA-Z_-]", "-", str(key_suffix))
    back_url = f"{APP_BASE_URL}/{back_href.lstrip('/')}" if not back_href.startswith("http") else back_href
    safe_share_url = share_url.replace("\\", "\\\\").replace("'", "\\'")
    pill_style = (
        "display:inline-flex; align-items:center; justify-content:center; "
        "border:1px solid #d9d9d9; background:#ffffff; color:#333333; "
        "border-radius:999px; padding:8px 18px; min-height:40px; "
        "font-size:13px; font-weight:600; cursor:pointer; "
        "box-shadow:0 2px 8px rgba(0,0,0,0.04); white-space:nowrap; text-decoration:none;"
    )

    back_html = f'''
    <div style="display:flex; align-items:center; justify-content:flex-start; margin:6px 0 18px 0;">
      <a href="{back_url}" target="_self" style="{pill_style}">{back_label}</a>
    </div>
    '''

    share_html = f"""
    <div style="display:flex; align-items:center; justify-content:flex-start; margin:6px 0 18px 0;">
      <button id="share-btn-{safe_key}" type="button" style="{pill_style}">공유하기</button>
    </div>
    <script>
    const shareBtn = document.getElementById("share-btn-{safe_key}");
    if (shareBtn) {{
      shareBtn.onclick = async function () {{
        try {{
          await window.parent.navigator.clipboard.writeText('{safe_share_url}');
          const original = shareBtn.innerText;
          shareBtn.innerText = '복사 완료';
          setTimeout(() => {{ shareBtn.innerText = original; }}, 1400);
        }} catch (e) {{
          shareBtn.innerText = '복사 실패';
          setTimeout(() => {{ shareBtn.innerText = '공유하기'; }}, 1400);
        }}
      }};
    }}
    </script>
    """

    _, center, _ = st.columns([1.15, 5.0, 1.15])
    with center:
        c1, c2, c3 = st.columns([1.55, 1.0, 4.45])
        with c1:
            st.markdown(back_html, unsafe_allow_html=True)
        with c2:
            st.components.v1.html(share_html, height=66)
        with c3:
            st.empty()
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
    df["actor_stable_id"] = df.apply(lambda r: make_stable_key("actor", r.get("ip", ""), r.get("cast_clean", "") or r.get("cast", ""), r.get("date", ""), r.get("air", "")), axis=1)
    df["genre_stable_id"] = df.apply(lambda r: make_stable_key("genre", r.get("ip", ""), r.get("genre_title", ""), r.get("date", ""), r.get("air", "")), axis=1)
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
        df["stable_id"] = df.apply(lambda r: make_stable_key("monthly", r.get("title", ""), r.get("date", "")), axis=1)
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

@st.cache_data(ttl=3600, max_entries=5, show_spinner=False)
def get_drive_pdf_bytes(file_id: str) -> Optional[bytes]:
    """Drive API를 사용해 PDF 원본을 바이트로 다운로드합니다."""
    service = get_drive_service()
    if service is None: return None
    try:
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        return fh.getvalue()
    except Exception as e:
        st.error(f"PDF 파일 다운로드 실패: {e}")
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
    st.markdown(
        f'''
        <div style="display: flex; align-items: center; gap: 8px; margin-top: 30px; margin-bottom: 8px;">
            <span style="font-size: 34px;">🔬</span>
            <div class="main-title" style="margin: 0;">{PAGE_TITLE}</div>
        </div>
        ''', 
        unsafe_allow_html=True
    )

    img1 = HOME_IMG1
    img2 = HOME_IMG2

    monthly_link = "?view=monthly"
    actor_link = "?view=actor_genre"

    st.markdown(
        f"""
        <div class="home-grid">
          <a href="{monthly_link}" target="_self" class="home-card card-monthly" style="--bg:url('{img1}')">
            <div class="home-card-tag">MONTHLY</div>
            <div class="home-card-title">월간 드라마 인사이트 리포트</div>
            <div class="home-card-desc">
              드라마 시장에 대한 온라인 반응 및 지표 데이터를 분석하여, <br>
              IP 마케팅 및 콘텐츠 기획 단계에서 적용할 수 있는 다양한 관점의 인사이트를 제공합니다.
            </div>
          </a>
          <a href="{actor_link}" target="_self" class="home-card card-actor" style="--bg:url('{img2}')">
            <div class="home-card-tag">CAST / GENRE</div>
            <div class="home-card-title">캐스팅 / 장르 분석 리포트</div>
            <div class="home-card-desc">
              마케팅 관점의 배우-캐스팅분석 및 장르분석 리포트입니다.
            </div>
          </a>
        </div>
        """, unsafe_allow_html=True
    )

def render_monthly_list(df_monthly: pd.DataFrame):
    st.markdown('<a href="?view=home" target="_self" class="detail-back">← 메인으로 돌아가기</a>', unsafe_allow_html=True)
    st.markdown('<div class="detail-title">월간 드라마 인사이트 리포트</div>', unsafe_allow_html=True)
    st.markdown('<div class="detail-subtitle">드라마 시장에 대한 온라인 반응 및 지표 데이터를 분석하여, IP 마케팅 및 콘텐츠 기획 단계에서 적용할 수 있는 다양한 관점의 인사이트를 제공합니다.</div>', unsafe_allow_html=True)

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

        link = f"?view=monthly_detail&id={row.get('stable_id') or row['row_id']}"
        
        card_html = f'<a href="{link}" target="_self" class="monthly-card"><div class="monthly-thumb-box"><img src="{thumb_url}" class="monthly-thumb" alt="{title}"></div><div class="monthly-info"><div class="monthly-title">{title}</div><div class="monthly-date">발행시점 : {date}</div></div></a>'
        cols_html.append(card_html)
        
    cols_html.append("</div>")
    st.markdown("".join(cols_html), unsafe_allow_html=True)

# ===== 수정: 상세 뷰어 가로폭 제한 래퍼(viewer-wrapper) 및 페이지 이미지 테두리 적용 =====
def render_monthly_detail(df_monthly: pd.DataFrame, row_id: str):
    row = find_row_by_identifier(df_monthly, row_id, "stable_id")
    if row.empty:
        st.error("유효하지 않은 접근입니다.")
        return
    row = row.iloc[0]

    title = row["title"]
    date = row["date"]
    url = row["url"]

    render_detail_action_bar(
        "?view=monthly",
        "← 월간 리포트 목록으로",
        build_share_url("monthly_detail", row.get("stable_id") or row_id),
        f"monthly-{row.get('stable_id') or row_id}"
    )

    _, center, _ = st.columns([1.15, 5.0, 1.15])
    with center:
        st.markdown(f"""
        <div class="detail-title">{title}</div>
        <div class="detail-subtitle">발행시점 : {date}</div>
        """, unsafe_allow_html=True)

    file_id = extract_drive_file_id(url)
    rendered_native = False

    if file_id:
        with st.spinner("🚀 로딩중 (약 2~4초 소요)"):
            pdf_bytes = get_drive_pdf_bytes(file_id)
            if pdf_bytes:
                try:
                    import fitz
                    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

                    # 뷰어 컨테이너 시작 (회색 배경, 넉넉한 여백)
                    img_htmls = ['<div class="viewer-wrapper"><div style="background:#f9f9f9; padding:40px; border-radius:16px; border:1px solid #eaeaea; box-shadow:0 10px 30px rgba(0,0,0,0.03);">']

                    for page_num in range(len(doc)):
                        page = doc.load_page(page_num)
                        mat = fitz.Matrix(2.0, 2.0)
                        pix = page.get_pixmap(matrix=mat, alpha=False)

                        # st.image 대신 HTML 태그를 사용해 완벽한 CSS(테두리, 여백 등) 제어 적용
                        b64_img = base64.b64encode(pix.tobytes("png")).decode("utf-8")
                        img_htmls.append(f'<img src="data:image/png;base64,{b64_img}" class="pdf-page-img">')

                    img_htmls.append('</div></div>')
                    st.markdown("".join(img_htmls), unsafe_allow_html=True)
                    rendered_native = True
                except ImportError:
                    st.error("💡 완벽한 PDF 렌더링을 위해 `PyMuPDF` 라이브러리가 필요합니다.\n\n터미널에 `pip install PyMuPDF`를 입력하거나, `requirements.txt`에 `PyMuPDF`를 추가해 주세요!")
                except Exception as e:
                    st.error(f"PDF 렌더링 중 오류가 발생했습니다: {e}")

    if not rendered_native:
        embed_url = build_embed_url_if_possible(url)
        if embed_url:
            st.warning("⚠️ 구글 드라이브 기본 뷰어로 임시 렌더링합니다.")
            st.markdown(f"""
            <div class="viewer-wrapper">
                <div class="pdf-native-container">
                    <iframe src="{embed_url}" allowfullscreen="true"></iframe>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.error("PDF를 불러올 수 없습니다. 올바른 구글 드라이브 링크인지 확인해 주세요.")

def render_slide_range_as_thumbnails(target_url: str, page_range: str):
    pres_id = extract_presentation_id(target_url)
    if not pres_id:
        embed_url = build_embed_url_if_possible(target_url, page_range)
        if not embed_url:
            st.warning("연결된 프레젠테이션 링크가 없습니다.")
            return
        st.markdown(f"""
        <div class="viewer-wrapper">
            <div class="embed-container">
                <iframe src="{embed_url}" allowfullscreen="true"></iframe>
            </div>
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
        <div class="viewer-wrapper">
            <div class="embed-container">
                <iframe src="{embed_url}" allowfullscreen="true"></iframe>
            </div>
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
        html_blocks = ['<div class="viewer-wrapper">']
        for p in pages:
            idx = p - 1
            if 0 <= idx < len(page_ids):
                page_obj_id = page_ids[idx]
                thumb_url = get_slide_thumbnail_url(pres_id, page_obj_id)
                if thumb_url:
                    rendered_any = True
                    # 마크다운 파서 오류(코드블록 노출)를 방지하기 위해 HTML을 한 줄로 압축
                    html_blocks.append(f'<div class="embed-container" style="background:transparent; border:none; box-shadow:none; margin-bottom:30px;"><img src="{thumb_url}" style="position:absolute; top:0; left:0; width:100%; height:100%; object-fit:contain; border-radius:6px; border:1px solid #d4d4d4; box-shadow:0 4px 12px rgba(0,0,0,0.06);"></div>')
        html_blocks.append('</div>')
        
        if rendered_any:
            st.markdown("".join(html_blocks), unsafe_allow_html=True)
            return

        embed_url = build_embed_url_if_possible(target_url, page_range)
        if embed_url:
            st.markdown(f"""
            <div class="viewer-wrapper">
                <div class="embed-container">
                    <iframe src="{embed_url}" allowfullscreen="true"></iframe>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("해당 페이지 범위를 렌더링할 수 없습니다.")


def render_actor_detail(df: pd.DataFrame, row_id: str):
    row = find_row_by_identifier(df, row_id, "actor_stable_id")
    if row.empty:
        st.error("유효하지 않은 접근입니다.")
        return
    row = row.iloc[0]

    ip = row["ip"]
    cast = row["cast_clean"] or row["cast"]
    date = row["date"]
    air = row["air"]

    date_str = date if date else "미상"
    air_str = air if air else "미상"
    meta = f"분석시점 : {date_str} / IP방영시점 : {air_str}"

    cast_text = cast if cast else "배우 정보 없음"
    title_display = f"{cast_text} ({ip})"

    render_detail_action_bar(
        "?view=actor_genre",
        "← 캐스팅/장르 분석 목록으로",
        build_share_url("actor_detail", row.get("actor_stable_id") or row_id),
        f"actor-{row.get('actor_stable_id') or row_id}"
    )

    _, center, _ = st.columns([1.15, 5.0, 1.15])
    with center:
        st.markdown(f"""
        <div class="detail-title">{title_display}</div>
        <div class="detail-subtitle">캐스팅 분석 리포트<br>{meta}</div>
        """, unsafe_allow_html=True)

    target_url = row.get("actor_url") or row.get("url")
    page_range = row.get("actor_range", "")

    render_slide_range_as_thumbnails(target_url, page_range)

def render_genre_detail(df: pd.DataFrame, row_id: str):
    row = find_row_by_identifier(df, row_id, "genre_stable_id")
    if row.empty:
        st.error("유효하지 않은 접근입니다.")
        return
    row = row.iloc[0]

    ip = row["ip"]
    title = row["genre_title"] or "장르 분석"
    date = row["date"]
    air = row["air"]

    date_str = date if date else "미상"
    air_str = air if air else "미상"
    meta = f"분석시점 : {date_str} / IP방영시점 : {air_str}"

    title_display = f"{title} ({ip})"

    render_detail_action_bar(
        "?view=actor_genre",
        "← 캐스팅/장르 분석 목록으로",
        build_share_url("genre_detail", row.get("genre_stable_id") or row_id),
        f"genre-{row.get('genre_stable_id') or row_id}"
    )

    _, center, _ = st.columns([1.15, 5.0, 1.15])
    with center:
        st.markdown(f"""
        <div class="detail-title">{title_display}</div>
        <div class="detail-subtitle">장르 분석 리포트<br>{meta}</div>
        """, unsafe_allow_html=True)

    target_url = row.get("genre_url") or row.get("url")
    page_range = row.get("genre_range", "")

    render_slide_range_as_thumbnails(target_url, page_range)

# ===== 캐스팅 / 장르 분석 리스트 렌더링 =====
def render_actor_genre_list(df: pd.DataFrame):
    st.markdown('<a href="?view=home" target="_self" class="detail-back">← 메인으로 돌아가기</a>', unsafe_allow_html=True)
    st.markdown('<div class="detail-title">캐스팅 / 장르 분석 리포트</div>', unsafe_allow_html=True)

    # ===== 데이터에서 존재하는 모든 배우명과 장르 키워드 추출 및 정렬 =====
    actor_list = df[df["actor_range"] != ""]["cast_clean"].str.split(r",\s*").explode().str.strip().dropna().unique().tolist()
    actor_list = sorted([a for a in actor_list if a])
    
    genre_list = df[df["genre_range"] != ""]["genre_title"].str.strip().dropna().unique().tolist()
    genre_list = sorted([g for g in genre_list if g])
    
    unique_ips = sorted(df["ip"].dropna().unique().tolist())

    # ===== 통합 검색 필터 영역 (4단 분할로 좌측 몰기) =====
    col_filter1, col_filter2, col_filter3, col_dummy = st.columns([1, 1, 1, 1.5])
    
    with col_filter1:
        selected_actors = st.multiselect("👤 배우 필터", options=actor_list, default=[])
    with col_filter2:
        selected_genres = st.multiselect("🏷️ 분석주제 필터", options=genre_list, default=[])
    with col_filter3:
        selected_ips = st.multiselect("📌 작품명 필터", options=unique_ips, default=[])
    with col_dummy:
        pass # 우측 여백을 위한 투명(더미) 공간

    # ===== 필터와 리스트 사이의 명확한 구분선 =====
    st.markdown("<hr style='margin: 30px 0; border: none; border-top: 1px solid #eaeaea;'>", unsafe_allow_html=True)

    # ===== 필터 동시 선택 예외 처리 =====
    if selected_actors and selected_genres:
        st.warning("⚠️ 배우 필터와 분석주제 필터는 동시에 사용할 수 없습니다. 한 쪽 필터를 비워주세요.")

    # ===== 분석 리스트 영역 (좌우 2단 컬럼 분리) =====
    col_actor, col_genre = st.columns(2)

    # ===== 2. 캐스팅 분석 리스트 영역 (좌측) =====
    with col_actor:
        # 장르(분석주제) 필터가 비어있을 때만 렌더링
        if not selected_genres: 
            actor_df = df[df["actor_range"] != ""].copy()
            
            # 필터 로직
            if selected_actors:
                mask = actor_df["cast"].apply(lambda x: any(k.lower() in str(x).lower() for k in selected_actors))
                actor_df = actor_df[mask]
            if selected_ips:
                actor_df = actor_df[actor_df["ip"].isin(selected_ips)]

            # 배경을 감싸기 위해 전체 HTML을 리스트로 모음 (연한 보라색 배경 추가)
            actor_html = [
                '<div style="background-color: #faf5ff; padding: 20px; border-radius: 12px; border: 1px solid #f3e8ff;">',
                '<div style="background-color: #f5f3ff; padding: 12px 20px; border-radius: 8px; font-weight: 700; font-size: 16px; margin-bottom: 16px; border-left: 5px solid #8b5cf6; color: #4c1d95;">👤 캐스팅 분석</div>'
            ]

            if actor_df.empty:
                actor_html.append('<div style="padding: 16px; background-color: #ffffff; border-radius: 8px; border: 1px solid #eaeaea; color: #666; font-size: 14px;">조건에 맞는 캐스팅 분석 페이지가 없습니다.</div>')
            else:
                for _, row in actor_df.iterrows():
                    link = f"?view=actor_detail&id={row.get('actor_stable_id') or row['row_id']}"
                    ip = row["ip"]
                    cast = row["cast_clean"] or row["cast"]
                    date = row["date"]
                    air = row["air"]
                    
                    date_str = date if date else "미상"
                    air_str = air if air else "미상"
                    meta = f"분석시점 : {date_str} / IP방영시점 : {air_str}"
                    cast_text = cast if cast else "배우 정보 없음"
                    title_display = f"{cast_text} ({ip})"

                    # 들여쓰기로 인한 코드블록 인식 오류를 막기 위해 한 줄 문자열 연결 방식 사용
                    actor_html.append(
                        f'<a href="{link}" target="_self" class="analysis-card" style="margin-bottom: 12px;">'
                        f'<div class="analysis-title-row"><div class="analysis-ip">{title_display}</div>'
                        f'<div class="analysis-label">캐스팅 분석</div></div>'
                        f'<div class="analysis-meta">{meta}</div>'
                        f'<div class="analysis-sub">작품: {ip}</div></a>'
                    )
            actor_html.append('</div>')
            st.markdown("".join(actor_html), unsafe_allow_html=True)

    # ===== 3. 장르 분석 리스트 영역 (우측) =====
    with col_genre:
        # 배우 필터가 비어있을 때만 렌더링
        if not selected_actors: 
            genre_df = df[df["genre_range"] != ""].copy()
            
            # 필터 로직
            if selected_genres:
                mask = genre_df["genre_title"].apply(lambda x: any(k.lower() in str(x).lower() for k in selected_genres))
                genre_df = genre_df[mask]
            if selected_ips:
                genre_df = genre_df[genre_df["ip"].isin(selected_ips)]

            # 배경을 감싸기 위해 전체 HTML을 리스트로 모음 (연한 파란색 배경 추가)
            genre_html = [
                '<div style="background-color: #f8fbff; padding: 20px; border-radius: 12px; border: 1px solid #e0f2fe;">',
                '<div style="background-color: #eff6ff; padding: 12px 20px; border-radius: 8px; font-weight: 700; font-size: 16px; margin-bottom: 16px; border-left: 5px solid #4a90e2; color: #1e3a8a;">🏷️ 장르 분석</div>'
            ]

            if genre_df.empty:
                genre_html.append('<div style="padding: 16px; background-color: #ffffff; border-radius: 8px; border: 1px solid #eaeaea; color: #666; font-size: 14px;">조건에 맞는 장르 분석 페이지가 없습니다.</div>')
            else:
                for _, row in genre_df.iterrows():
                    link = f"?view=genre_detail&id={row.get('genre_stable_id') or row['row_id']}"
                    ip = row["ip"]
                    title = row["genre_title"] or "장르 분석"
                    date = row["date"]
                    air = row["air"]

                    date_str = date if date else "미상"
                    air_str = air if air else "미상"
                    meta = f"분석시점 : {date_str} / IP방영시점 : {air_str}"
                    title_display = f"{title} ({ip})"

                    # 들여쓰기로 인한 코드블록 인식 오류를 막기 위해 한 줄 문자열 연결 방식 사용
                    genre_html.append(
                        f'<a href="{link}" target="_self" class="analysis-card" style="margin-bottom: 12px;">'
                        f'<div class="analysis-title-row"><div class="analysis-ip">{title_display}</div>'
                        f'<div class="analysis-label">장르 분석</div></div>'
                        f'<div class="analysis-meta">{meta}</div>'
                        f'<div class="analysis-sub">작품: {ip}</div></a>'
                    )
            genre_html.append('</div>')
            st.markdown("".join(genre_html), unsafe_allow_html=True)


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
