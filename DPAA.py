import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
from streamlit_gsheets import GSheetsConnection

# region [설정 및 스타일] ===================================================================
def setup_page():
    """
    페이지 기본 설정 및 커스텀 CSS 로드
    """
    st.set_page_config(
        page_title="드라마 사전분석 아카이브",
        page_icon="🎬",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    # 세련된 다크 모드 & 카드 UI를 위한 커스텀 CSS
    st.markdown("""
        <style>
        /* 전체 폰트 및 배경 설정 */
        .main {
            background-color: #0e1117;
        }
        
        /* 카드 디자인 스타일 */
        div[data-testid="column"] {
            background-color: #1f2937;
            border-radius: 10px;
            padding: 15px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
            transition: transform 0.2s;
            border: 1px solid #374151;
        }
        
        /* 카드 호버 효과 */
        div[data-testid="column"]:hover {
            transform: translateY(-5px);
            border-color: #60a5fa;
        }

        /* 이미지 스타일 */
        img {
            border-radius: 8px;
            margin-bottom: 10px;
        }

        /* 텍스트 스타일 */
        h3 {
            color: #f3f4f6 !important;
            font-size: 1.2rem !important;
            margin-bottom: 0.5rem !important;
        }
        p {
            color: #9ca3af !important;
            font-size: 0.9rem;
        }
        
        /* 태그 스타일 */
        .tag-span {
            background-color: #374151;
            color: #60a5fa;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.8rem;
            margin-right: 5px;
        }
        
        /* 버튼 스타일 커스터마이징 */
        .stButton > button {
            width: 100%;
            background-color: #2563eb;
            color: white;
            border: none;
            border-radius: 5px;
        }
        .stButton > button:hover {
            background-color: #1d4ed8;
        }
        </style>
    """, unsafe_allow_html=True)
# endregion ===================================================================================


# region [데이터 핸들링] =====================================================================
def load_data():
    """
    구글 스프레드시트 데이터 로드 (Secrets 활용)
    Secrets의 [connections.gsheets] 및 ARCHIVE_SHEET_ID 정보를 사용합니다.
    """
    try:
        # 1. Secrets에서 시트 ID와 시트명 가져오기
        # (secrets.toml 파일에 해당 키값이 정의되어 있어야 합니다)
        sheet_id = st.secrets["ARCHIVE_SHEET_ID"]
        sheet_name = st.secrets["ARCHIVE_SHEET_NAME"]

        # 2. 구글 시트 연결 (st-gsheets-connection 라이브러리 사용)
        # type="service_account" 정보는 secrets의 [connections.gsheets]에서 자동 로드됨
        conn = st.connection("gsheets", type=GSheetsConnection)

        # 3. 데이터 읽기
        df = conn.read(
            spreadsheet=sheet_id,
            worksheet=sheet_name,
            usecols=[0, 1, 2, 3, 4],  # A, B, C, D, E열만 가져옴
            ttl="10m"  # 10분 캐싱 (API 호출 절약)
        )
        
        # 4. 컬럼명 강제 통일 (시트 헤더가 달라도 코드 동작 보장)
        # A: Title, B: Url, C: Range, D: Tags, E: Poster
        if not df.empty:
            df.columns = ['Title', 'Url', 'Range', 'Tags', 'Poster']
            
            # 필수 데이터(제목, URL)가 없는 행 제거
            df = df.dropna(subset=['Title', 'Url'])
            
            # 데이터 타입 정리 (모두 문자열로 변환하여 에러 방지)
            df = df.astype(str)
            
        return df

    except Exception as e:
        st.error(f"🚨 데이터 로드 중 오류 발생: {e}")
        # 오류 발생 시 빈 데이터프레임 반환
        return pd.DataFrame(columns=['Title', 'Url', 'Range', 'Tags', 'Poster'])

def filter_data(df, search_term):
    """
    검색어(드라마명, 해시태그)를 기준으로 데이터 필터링
    """
    if not search_term:
        return df
    
    if df.empty:
        return df

    search_term = search_term.lower()
    
    # 드라마명 또는 해시태그에 검색어가 포함된 행 필터링
    # nan 값 처리를 위해 astype(str) 사용
    mask = (df['Title'].str.lower().str.contains(search_term)) | \
           (df['Tags'].str.lower().str.contains(search_term))
           
    return df[mask]
# endregion ===================================================================================


# region [UI 컴포넌트] =======================================================================
def render_header():
    """헤더 영역 렌더링"""
    st.title("🎬 드라마 사전분석 아카이브")
    st.markdown("마케팅 인사이트와 사전 분석 리포트를 한눈에 확인하세요.")
    st.markdown("---")

def render_search_bar():
    """검색바 렌더링"""
    col1, col2 = st.columns([4, 1])
    with col1:
        # 라벨 숨김 처리 후 플레이스홀더로 안내
        search_term = st.text_input("검색", placeholder="드라마명 또는 해시태그(#스릴러)로 검색...", label_visibility="collapsed")
    with col2:
        st.write("") # 레이아웃 균형을 위한 빈 공간

    return search_term

def render_card(row, index):
    """개별 드라마 카드 렌더링"""
    # 1. 포스터 이미지 표시
    try:
        # 이미지가 없거나 'nan'인 경우 대체 텍스트 표시 가능
        if row['Poster'] and row['Poster'].lower() != 'nan':
            st.image(row['Poster'], use_container_width=True)
        else:
            st.markdown("Running Time...") # 이미지가 없을 때
    except:
        st.error("이미지 로드 실패")
        
    # 2. 타이틀 및 태그
    st.markdown(f"### {row['Title']}")
    
    # 태그를 예쁘게 표시하기 위한 HTML 처리 (공백 기준으로 분리)
    if row['Tags'] and row['Tags'].lower() != 'nan':
        tags = row['Tags'].split()
        tags_html = "".join([f"<span class='tag-span'>{tag}</span>" for tag in tags])
        st.markdown(f"{tags_html}", unsafe_allow_html=True)
    
    st.caption(f"📑 분석 범위: {row['Range']}")
    
    # 3. 상세보기 버튼 (클릭 시 세션 상태 업데이트하여 화면 전환)
    if st.button("분석 리포트 보기", key=f"btn_{index}"):
        st.session_state['selected_drama'] = row
        st.rerun()

def render_detail_view(row):
    """상세 리포트 뷰 렌더링 (구글 프레젠테이션 임베드 포함)"""
    
    # 뒤로가기 버튼
    if st.button("← 목록으로 돌아가기"):
        st.session_state['selected_drama'] = None
        st.rerun()

    st.markdown(f"## 📊 {row['Title']} - 사전분석 리포트")
    st.markdown(f"**태그:** {row['Tags']} | **범위:** {row['Range']}")
    st.markdown("---")
    
    # 구글 프레젠테이션 임베드
    embed_url = row['Url']
    
    if embed_url and embed_url.lower() != 'nan':
        # 아이프레임 렌더링 (화면 꽉 차게 높이 설정)
        components.html(
            f"""
            <iframe src="{embed_url}" 
                frameborder="0" 
                width="100%" 
                height="650" 
                allowfullscreen="true" 
                mozallowfullscreen="true" 
                webkitallowfullscreen="true">
            </iframe>
            """,
            height=670
        )
    else:
        st.warning("등록된 프레젠테이션 URL이 없습니다.")
# endregion ===================================================================================


# region [메인 로직] =========================================================================
def main():
    setup_page()
    
    # 세션 상태 초기화 (현재 선택된 드라마 저장용)
    if 'selected_drama' not in st.session_state:
        st.session_state['selected_drama'] = None

    # 데이터 로드
    df = load_data()

    # --- 화면 라우팅 ---
    
    # 1. 상세 뷰 (드라마가 선택된 경우)
    if st.session_state['selected_drama'] is not None:
        render_detail_view(st.session_state['selected_drama'])
        
    # 2. 리스트 뷰 (기본 화면)
    else:
        render_header()
        
        # 데이터가 없을 경우 안내
        if df.empty:
            st.warning("데이터를 불러올 수 없습니다. 구글 시트 연결을 확인해주세요.")
            return

        search_input = render_search_bar()
        filtered_df = filter_data(df, search_input)

        if filtered_df.empty:
            st.info("검색 결과가 없습니다.")
        else:
            # 3열 그리드 레이아웃 생성
            cols = st.columns(3)
            # 데이터프레임 순회하며 카드 렌더링
            for idx, (_, row) in enumerate(filtered_df.iterrows()):
                with cols[idx % 3]: # 0, 1, 2 열 순환 배치
                    render_card(row, idx)

# 앱 실행 진입점
if __name__ == "__main__":
    main()
# endregion ===================================================================================