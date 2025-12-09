import streamlit as st
import pandas as pd
import streamlit.components.v1 as components

# region [설정 및 스타일] ====================================================================
def setup_page():
    st.set_page_config(
        page_title="드라마 사전분석 아카이브",
        page_icon="🎬",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    # 디자인 CSS (다크모드 & 카드 UI)
    st.markdown("""
        <style>
        .main { background-color: #0e1117; }
        div[data-testid="column"] {
            background-color: #1f2937;
            border-radius: 10px;
            padding: 15px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
            border: 1px solid #374151;
            transition: transform 0.2s;
        }
        div[data-testid="column"]:hover {
            transform: translateY(-5px);
            border-color: #60a5fa;
        }
        img { border-radius: 8px; margin-bottom: 10px; }
        h3 { color: #f3f4f6 !important; font-size: 1.2rem !important; margin-bottom: 0.5rem !important; }
        p { color: #9ca3af !important; font-size: 0.9rem; }
        .tag-span {
            background-color: #374151;
            color: #60a5fa;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.8rem;
            margin-right: 5px;
        }
        .stButton > button {
            width: 100%;
            background-color: #2563eb;
            color: white;
            border: none;
            border-radius: 5px;
        }
        .stButton > button:hover { background-color: #1d4ed8; }
        </style>
    """, unsafe_allow_html=True)
# endregion ===================================================================================


# region [데이터 핸들링 (공개 시트 버전)] ====================================================
def load_data():
    """
    오류가 있는 행은 무시하고 데이터를 강제로 읽어옵니다.
    """
    try:
        csv_url = st.secrets["public_sheet_url"]

        # 1. on_bad_lines='skip': 칸 수가 안 맞는 행(에러 주범)은 그냥 버리고 읽음
        # 2. engine='python': 더 강력한 파이썬 엔진 사용
        df = pd.read_csv(csv_url, on_bad_lines='skip', engine='python')

        # --- [디버깅용] 데이터가 잘 읽혔는지 화면 맨 위에 잠시 출력 ---
        st.write(f"✅ 읽어온 데이터 개수: {len(df)}개")
        if len(df) > 0:
            with st.expander("데이터 미리보기 (클릭해서 확인)"):
                st.dataframe(df.head())
        else:
            st.error("데이터를 읽었는데 내용이 텅 비어있습니다!")
        # -------------------------------------------------------
        
        # 컬럼 정리 (A~E열)
        expected_cols = ['Title', 'Url', 'Range', 'Tags', 'Poster']
        
        # 컬럼이 5개보다 적어도 에러 안 나게 처리
        if len(df.columns) < 5:
            # 부족한 만큼 빈 컬럼 추가
            for i in range(5 - len(df.columns)):
                df[f'Col_{i}'] = ""
        
        # 5개로 자르고 이름 부여
        df = df.iloc[:, :5]
        df.columns = expected_cols

        # 필수 데이터(제목) 없는 행 제거 및 정리
        df = df.dropna(subset=['Title'])
        df = df.astype(str)
        df = df.replace('nan', '')
            
        return df

    except Exception as e:
        # 에러가 나면 숨기지 말고 그대로 화면에 보여줌 (디버깅용)
        st.error(f"🚨 심각한 에러 발생: {e}")
        return pd.DataFrame(columns=['Title', 'Url', 'Range', 'Tags', 'Poster'])
    
    
def filter_data(df, search_term):
    if not search_term: return df
    if df.empty: return df

    search_term = search_term.lower()
    mask = (df['Title'].str.lower().str.contains(search_term)) | \
           (df['Tags'].str.lower().str.contains(search_term))
    return df[mask]
# endregion ===================================================================================


# region [UI 컴포넌트] =======================================================================
def render_header():
    st.title("🎬 드라마 사전분석 아카이브")
    st.markdown("마케팅 인사이트와 사전 분석 리포트를 한눈에 확인하세요.")
    st.markdown("---")

def render_search_bar():
    col1, col2 = st.columns([4, 1])
    with col1:
        return st.text_input("검색", placeholder="드라마명 또는 해시태그(#스릴러)로 검색...", label_visibility="collapsed")
    with col2:
        st.write("") 

def render_card(row, index):
    # 포스터
    if row['Poster']:
        st.image(row['Poster'], use_container_width=True)
    else:
        st.markdown("Running Time...") # 이미지 없을 때

    # 타이틀
    st.markdown(f"### {row['Title']}")
    
    # 태그
    if row['Tags']:
        tags = row['Tags'].split()
        tags_html = "".join([f"<span class='tag-span'>{tag}</span>" for tag in tags])
        st.markdown(f"{tags_html}", unsafe_allow_html=True)
    
    st.caption(f"📑 분석 범위: {row['Range']}")
    
    # 버튼
    if st.button("분석 리포트 보기", key=f"btn_{index}"):
        st.session_state['selected_drama'] = row
        st.rerun()

def render_detail_view(row):
    if st.button("← 목록으로 돌아가기"):
        st.session_state['selected_drama'] = None
        st.rerun()

    st.markdown(f"## 📊 {row['Title']} - 사전분석 리포트")
    st.markdown(f"**태그:** {row['Tags']} | **범위:** {row['Range']}")
    st.markdown("---")
    
    embed_url = row['Url']
    if embed_url:
        components.html(
            f"""
            <iframe src="{embed_url}" frameborder="0" width="100%" height="650" 
            allowfullscreen="true" mozallowfullscreen="true" webkitallowfullscreen="true"></iframe>
            """,
            height=670
        )
    else:
        st.warning("등록된 프레젠테이션 URL이 없습니다.")
# endregion ===================================================================================


# region [메인 로직] =========================================================================
def main():
    setup_page()
    if 'selected_drama' not in st.session_state:
        st.session_state['selected_drama'] = None

    df = load_data()

    if st.session_state['selected_drama'] is not None:
        render_detail_view(st.session_state['selected_drama'])
    else:
        render_header()
        if df.empty:
            st.warning("데이터를 불러올 수 없습니다. Secrets 설정을 확인해주세요.")
            return

        search_input = render_search_bar()
        filtered_df = filter_data(df, search_input)

        if filtered_df.empty:
            st.info("검색 결과가 없습니다.")
        else:
            cols = st.columns(3)
            for idx, (_, row) in enumerate(filtered_df.iterrows()):
                with cols[idx % 3]:
                    render_card(row, idx)

if __name__ == "__main__":
    main()
# endregion ===================================================================================