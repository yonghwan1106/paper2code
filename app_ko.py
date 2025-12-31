"""
Paper2Code - Streamlit 웹 애플리케이션 (한글 버전)

AI를 활용하여 과학 논문을 실행 가능한 Python 코드로 변환합니다.
"""

import io
import os
import tempfile
import zipfile
from pathlib import Path

import streamlit as st

# 페이지 설정
st.set_page_config(
    page_title="Paper2Code - AI 논문→코드 변환기",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 커스텀 CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .status-box {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .status-success {
        background-color: #E8F5E9;
        border-left: 4px solid #4CAF50;
    }
    .status-error {
        background-color: #FFEBEE;
        border-left: 4px solid #F44336;
    }
    .status-processing {
        background-color: #E3F2FD;
        border-left: 4px solid #2196F3;
    }
    .code-file-header {
        background-color: #263238;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem 0.5rem 0 0;
        font-family: monospace;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
    }
    .challenge-badge {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 1rem;
        font-size: 0.8rem;
        text-align: center;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)


def check_api_key():
    """API 키가 설정되었는지 확인합니다."""
    api_key = os.environ.get("ANTHROPIC_API_KEY") or st.session_state.get("api_key")
    return api_key is not None and len(api_key) > 0


def init_session_state():
    """세션 상태 변수를 초기화합니다."""
    if "processing" not in st.session_state:
        st.session_state.processing = False
    if "result" not in st.session_state:
        st.session_state.result = None
    if "current_step" not in st.session_state:
        st.session_state.current_step = ""
    if "api_key" not in st.session_state:
        st.session_state.api_key = None


def process_paper(pdf_file, api_key):
    """업로드된 PDF를 처리하고 코드를 생성합니다."""
    # API 키 설정
    os.environ["ANTHROPIC_API_KEY"] = api_key

    # API 키 설정 후 임포트 (지연 로딩)
    from src.agents import Paper2CodeOrchestrator

    # 업로드된 파일을 임시 위치에 저장
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(pdf_file.getvalue())
        tmp_path = tmp.name

    try:
        # 출력 디렉토리 생성
        output_dir = tempfile.mkdtemp()

        # Orchestrator 초기화 (Streamlit Cloud에서는 Docker 비활성화)
        orchestrator = Paper2CodeOrchestrator(
            use_docker=False,
            max_debug_attempts=2,
        )

        # 파이프라인 실행
        result = orchestrator.run(
            paper_path=tmp_path,
            output_dir=output_dir,
            verbose=False,
        )

        return result, output_dir

    finally:
        # 임시 PDF 파일 정리
        os.unlink(tmp_path)


def create_zip_download(output_dir, project_name):
    """다운로드용 ZIP 파일을 생성합니다."""
    zip_buffer = io.BytesIO()

    project_path = Path(output_dir) / project_name

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        if project_path.exists():
            for file_path in project_path.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(project_path)
                    zip_file.write(file_path, arcname)

    zip_buffer.seek(0)
    return zip_buffer


def render_sidebar():
    """사이드바를 렌더링합니다."""
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/document.png", width=80)
        st.title("Paper2Code")
        st.markdown('<div class="challenge-badge">2026 AI Co-Scientist Challenge Korea</div>', unsafe_allow_html=True)
        st.markdown("---")

        # API 키 입력
        st.subheader("설정")

        api_key = st.text_input(
            "Anthropic API 키",
            type="password",
            value=st.session_state.get("api_key", ""),
            help="Claude AI를 사용하기 위한 Anthropic API 키를 입력하세요",
        )

        if api_key:
            st.session_state.api_key = api_key
            os.environ["ANTHROPIC_API_KEY"] = api_key

        if check_api_key():
            st.success("API 키 설정 완료")
        else:
            st.warning("API 키를 입력해주세요")

        st.markdown("---")

        # 사용 방법
        st.subheader("사용 방법")
        st.markdown("""
        1. **업로드** - 과학 논문 PDF 파일 업로드
        2. **파싱** - 텍스트 및 구조 추출
        3. **분석** - 알고리즘 식별 및 분석
        4. **생성** - Python 코드 생성
        5. **실행** - 코드 테스트
        6. **다운로드** - 생성된 코드 받기!
        """)

        st.markdown("---")

        # 링크
        st.subheader("링크")
        st.markdown("""
        - [GitHub 저장소](https://github.com/yonghwan1106/paper2code)
        - [영문 버전](https://paper2code.streamlit.app)
        """)

        st.markdown("---")
        st.caption("Paper2Code MVP v0.1.0")
        st.caption("Powered by Claude AI (Anthropic)")


def render_main():
    """메인 콘텐츠 영역을 렌더링합니다."""
    # 헤더
    st.markdown('<p class="main-header">Paper2Code</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">과학 논문을 실행 가능한 Python 코드로 변환하는 AI Agent</p>', unsafe_allow_html=True)

    # 소개 섹션
    with st.expander("Paper2Code란?", expanded=False):
        st.markdown("""
        **Paper2Code**는 과학 논문에 기술된 알고리즘을 자동으로 분석하고,
        실행 가능한 Python 코드로 변환하는 AI 에이전트 시스템입니다.

        **주요 기능:**
        - PDF 논문 자동 파싱 및 구조 분석
        - 알고리즘 추출 및 의사코드 해석
        - Python 코드 자동 생성
        - 생성된 코드 자동 테스트 및 디버깅

        **기술 스택:**
        - LangGraph 기반 Multi-Agent 시스템
        - Claude AI (Anthropic)
        - PyMuPDF PDF 파싱
        """)

    # 파일 업로드 섹션
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        uploaded_file = st.file_uploader(
            "과학 논문 업로드 (PDF)",
            type=["pdf"],
            help="알고리즘이 포함된 PDF 논문 파일을 업로드하세요",
        )

        if uploaded_file:
            st.info(f"업로드됨: **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} KB)")

    # 처리 버튼
    col1, col2, col3 = st.columns([1, 1, 1])

    with col2:
        process_btn = st.button(
            "코드 생성하기",
            type="primary",
            disabled=not (uploaded_file and check_api_key()),
            use_container_width=True,
        )

    if not check_api_key():
        st.warning("계속하려면 사이드바에서 Anthropic API 키를 입력해주세요.")
        return

    # 처리 중
    if process_btn and uploaded_file:
        with st.spinner("논문을 처리 중입니다... 몇 분 정도 소요될 수 있습니다."):
            # 진행 상태 표시
            progress_container = st.empty()

            try:
                # 논문 처리
                result, output_dir = process_paper(
                    uploaded_file,
                    st.session_state.api_key,
                )

                st.session_state.result = result
                st.session_state.output_dir = output_dir

            except Exception as e:
                st.error(f"논문 처리 중 오류 발생: {str(e)}")
                return

    # 결과 표시
    if st.session_state.result:
        render_results(st.session_state.result, st.session_state.get("output_dir"))


def render_results(result, output_dir):
    """처리 결과를 렌더링합니다."""
    st.markdown("---")
    st.subheader("결과")

    # 상태
    status = result.get("status", "unknown")

    if status == "success":
        st.success("코드가 성공적으로 생성되고 실행되었습니다!")
    else:
        st.error(f"파이프라인 완료 상태: {status}")
        if result.get("error_message"):
            st.error(result["error_message"])

    # 메트릭
    col1, col2, col3, col4 = st.columns(4)

    final_output = result.get("final_output", {})

    with col1:
        st.metric("생성된 파일", final_output.get("file_count", 0))

    with col2:
        st.metric("디버그 시도", final_output.get("debug_attempts", 0))

    with col3:
        st.metric("사용된 토큰", f"{final_output.get('total_tokens', 0):,}")

    with col4:
        algo_name = (result.get("main_algorithm") or {}).get("name", "N/A")
        st.metric("알고리즘", algo_name[:15] + "..." if len(algo_name) > 15 else algo_name)

    # 논문 정보
    if result.get("paper_summary"):
        with st.expander("논문 정보", expanded=False):
            summary = result["paper_summary"]
            st.write(f"**제목:** {summary.get('title', 'N/A')}")
            st.write(f"**섹션 수:** {summary.get('section_count', 0)}")
            st.write(f"**수식 수:** {summary.get('equation_count', 0)}")

    # 알고리즘 정보
    if result.get("main_algorithm"):
        with st.expander("알고리즘 분석", expanded=False):
            algo = result["main_algorithm"]
            st.write(f"**이름:** {algo.get('name', 'N/A')}")
            st.write(f"**목적:** {algo.get('purpose', 'N/A')}")
            st.write(f"**설명:** {algo.get('description', 'N/A')}")

            if algo.get("steps"):
                st.write("**단계:**")
                for i, step in enumerate(algo["steps"], 1):
                    st.write(f"{i}. {step}")

    # 생성된 코드
    if result.get("code_project"):
        st.subheader("생성된 코드")

        code_project = result["code_project"]
        files = code_project.get("files", [])

        # 각 파일에 대한 탭 생성
        if files:
            tab_names = [f["filename"] for f in files]
            tabs = st.tabs(tab_names)

            for tab, file_info in zip(tabs, files):
                with tab:
                    st.code(file_info["content"], language="python")

        # 다운로드 버튼
        project_name = code_project.get("name", "generated_code")

        if output_dir:
            zip_buffer = create_zip_download(output_dir, project_name)

            st.download_button(
                label="코드 다운로드 (ZIP)",
                data=zip_buffer,
                file_name=f"{project_name}.zip",
                mime="application/zip",
                type="primary",
            )

    # 실행 결과
    if result.get("execution_result"):
        exec_result = result["execution_result"]

        with st.expander("실행 결과", expanded=True):
            if exec_result.get("stdout"):
                st.code(exec_result["stdout"], language="text")

            if exec_result.get("stderr") and status != "success":
                st.error("오류:")
                st.code(exec_result["stderr"], language="text")


def main():
    """메인 애플리케이션 진입점."""
    init_session_state()
    render_sidebar()
    render_main()


if __name__ == "__main__":
    main()
