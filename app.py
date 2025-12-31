"""
Paper2Code - Streamlit Web Application (Bilingual: EN/KO)

Convert scientific papers to executable Python code using AI.
AI를 활용하여 과학 논문을 실행 가능한 Python 코드로 변환합니다.
"""

import io
import os
import tempfile
import zipfile
from pathlib import Path

import streamlit as st

# =============================================================================
# Translations / 번역
# =============================================================================
TRANSLATIONS = {
    "en": {
        "page_title": "Paper2Code - AI Paper to Code",
        "main_header": "Paper2Code",
        "sub_header": "Transform Scientific Papers into Executable Python Code",
        "config": "Configuration",
        "api_key_label": "Anthropic API Key",
        "api_key_help": "Enter your Anthropic API key to use Claude for code generation",
        "api_key_success": "API Key configured",
        "api_key_warning": "Please enter your API key",
        "how_it_works": "How it works",
        "step_1": "1. **Upload** a scientific paper (PDF)",
        "step_2": "2. **Parse** - Extract text and structure",
        "step_3": "3. **Analyze** - Identify algorithms",
        "step_4": "4. **Generate** - Create Python code",
        "step_5": "5. **Execute** - Test the code",
        "step_6": "6. **Download** - Get your code!",
        "links": "Links",
        "github_repo": "GitHub Repository",
        "upload_label": "Upload a Scientific Paper (PDF)",
        "upload_help": "Upload a PDF file containing algorithm descriptions",
        "uploaded": "Uploaded",
        "generate_btn": "Generate Code",
        "api_key_required": "Please enter your Anthropic API key in the sidebar to continue.",
        "processing": "Processing paper... This may take a few minutes.",
        "error_processing": "Error processing paper",
        "results": "Results",
        "success_msg": "Code generated and executed successfully!",
        "status_msg": "Pipeline completed with status",
        "files_generated": "Files Generated",
        "debug_attempts": "Debug Attempts",
        "tokens_used": "Tokens Used",
        "algorithm": "Algorithm",
        "paper_info": "Paper Information",
        "title": "Title",
        "sections": "Sections",
        "equations": "Equations",
        "algo_analysis": "Algorithm Analysis",
        "name": "Name",
        "purpose": "Purpose",
        "description": "Description",
        "steps": "Steps",
        "generated_code": "Generated Code",
        "download_zip": "Download Code (ZIP)",
        "exec_output": "Execution Output",
        "errors": "Errors",
        "about_title": "What is Paper2Code?",
        "about_content": """
        **Paper2Code** is an AI agent system that automatically analyzes algorithms
        described in scientific papers and converts them into executable Python code.

        **Key Features:**
        - Automatic PDF parsing and structure analysis
        - Algorithm extraction and pseudocode interpretation
        - Automatic Python code generation
        - Auto-testing and debugging of generated code

        **Tech Stack:**
        - LangGraph-based Multi-Agent System
        - Claude AI (Anthropic)
        - PyMuPDF PDF Parsing
        """,
        "challenge_badge": "2026 AI Co-Scientist Challenge Korea",
    },
    "ko": {
        "page_title": "Paper2Code - AI 논문→코드 변환기",
        "main_header": "Paper2Code",
        "sub_header": "과학 논문을 실행 가능한 Python 코드로 변환하는 AI Agent",
        "config": "설정",
        "api_key_label": "Anthropic API 키",
        "api_key_help": "Claude AI를 사용하기 위한 Anthropic API 키를 입력하세요",
        "api_key_success": "API 키 설정 완료",
        "api_key_warning": "API 키를 입력해주세요",
        "how_it_works": "사용 방법",
        "step_1": "1. **업로드** - 과학 논문 PDF 파일 업로드",
        "step_2": "2. **파싱** - 텍스트 및 구조 추출",
        "step_3": "3. **분석** - 알고리즘 식별 및 분석",
        "step_4": "4. **생성** - Python 코드 생성",
        "step_5": "5. **실행** - 코드 테스트",
        "step_6": "6. **다운로드** - 생성된 코드 받기!",
        "links": "링크",
        "github_repo": "GitHub 저장소",
        "upload_label": "과학 논문 업로드 (PDF)",
        "upload_help": "알고리즘이 포함된 PDF 논문 파일을 업로드하세요",
        "uploaded": "업로드됨",
        "generate_btn": "코드 생성하기",
        "api_key_required": "계속하려면 사이드바에서 Anthropic API 키를 입력해주세요.",
        "processing": "논문을 처리 중입니다... 몇 분 정도 소요될 수 있습니다.",
        "error_processing": "논문 처리 중 오류 발생",
        "results": "결과",
        "success_msg": "코드가 성공적으로 생성되고 실행되었습니다!",
        "status_msg": "파이프라인 완료 상태",
        "files_generated": "생성된 파일",
        "debug_attempts": "디버그 시도",
        "tokens_used": "사용된 토큰",
        "algorithm": "알고리즘",
        "paper_info": "논문 정보",
        "title": "제목",
        "sections": "섹션 수",
        "equations": "수식 수",
        "algo_analysis": "알고리즘 분석",
        "name": "이름",
        "purpose": "목적",
        "description": "설명",
        "steps": "단계",
        "generated_code": "생성된 코드",
        "download_zip": "코드 다운로드 (ZIP)",
        "exec_output": "실행 결과",
        "errors": "오류",
        "about_title": "Paper2Code란?",
        "about_content": """
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
        """,
        "challenge_badge": "2026 AI Co-Scientist Challenge Korea",
    }
}


def t(key):
    """Get translation for current language."""
    lang = st.session_state.get("lang", "en")
    return TRANSLATIONS[lang].get(key, key)


# Page configuration (must be first Streamlit command)
st.set_page_config(
    page_title="Paper2Code - AI Paper to Code",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
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
    .lang-switcher {
        display: flex;
        justify-content: center;
        gap: 0.5rem;
        margin-bottom: 1rem;
    }
    .lang-btn {
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.85rem;
        font-weight: bold;
        cursor: pointer;
        transition: all 0.2s;
    }
    .lang-btn-active {
        background-color: #1E88E5;
        color: white;
    }
    .lang-btn-inactive {
        background-color: #E0E0E0;
        color: #666;
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
    .status-box {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
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
</style>
""", unsafe_allow_html=True)


def check_api_key():
    """Check if API key is configured."""
    api_key = os.environ.get("ANTHROPIC_API_KEY") or st.session_state.get("api_key")
    return api_key is not None and len(api_key) > 0


def init_session_state():
    """Initialize session state variables."""
    if "processing" not in st.session_state:
        st.session_state.processing = False
    if "result" not in st.session_state:
        st.session_state.result = None
    if "current_step" not in st.session_state:
        st.session_state.current_step = ""
    if "api_key" not in st.session_state:
        st.session_state.api_key = None
    if "lang" not in st.session_state:
        st.session_state.lang = "en"


def process_paper(pdf_file, api_key):
    """Process uploaded PDF and generate code."""
    os.environ["ANTHROPIC_API_KEY"] = api_key

    from src.agents import Paper2CodeOrchestrator

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(pdf_file.getvalue())
        tmp_path = tmp.name

    try:
        output_dir = tempfile.mkdtemp()

        orchestrator = Paper2CodeOrchestrator(
            use_docker=False,
            max_debug_attempts=2,
        )

        result = orchestrator.run(
            paper_path=tmp_path,
            output_dir=output_dir,
            verbose=False,
        )

        return result, output_dir

    finally:
        os.unlink(tmp_path)


def create_zip_download(output_dir, project_name):
    """Create a ZIP file for download."""
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


def render_language_switcher():
    """Render language switcher buttons."""
    col1, col2, col3 = st.columns([2, 1, 2])

    with col2:
        lang_col1, lang_col2 = st.columns(2)

        with lang_col1:
            if st.button("ENG", use_container_width=True,
                        type="primary" if st.session_state.lang == "en" else "secondary"):
                st.session_state.lang = "en"
                st.rerun()

        with lang_col2:
            if st.button("KOR", use_container_width=True,
                        type="primary" if st.session_state.lang == "ko" else "secondary"):
                st.session_state.lang = "ko"
                st.rerun()


def render_sidebar():
    """Render sidebar with configuration."""
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/document.png", width=80)
        st.title("Paper2Code")
        st.markdown(f'<div class="challenge-badge">{t("challenge_badge")}</div>', unsafe_allow_html=True)
        st.markdown("---")

        # API Key input
        st.subheader(t("config"))

        api_key = st.text_input(
            t("api_key_label"),
            type="password",
            value=st.session_state.get("api_key", ""),
            help=t("api_key_help"),
        )

        if api_key:
            st.session_state.api_key = api_key
            os.environ["ANTHROPIC_API_KEY"] = api_key

        if check_api_key():
            st.success(t("api_key_success"))
        else:
            st.warning(t("api_key_warning"))

        st.markdown("---")

        # How it works
        st.subheader(t("how_it_works"))
        st.markdown(f"""
        {t("step_1")}
        {t("step_2")}
        {t("step_3")}
        {t("step_4")}
        {t("step_5")}
        {t("step_6")}
        """)

        st.markdown("---")

        # Links
        st.subheader(t("links"))
        st.markdown(f"""
        - [{t("github_repo")}](https://github.com/yonghwan1106/paper2code)
        """)

        st.markdown("---")
        st.caption("Paper2Code MVP v0.1.0")
        st.caption("Powered by Claude AI (Anthropic)")


def render_main():
    """Render main content area."""
    # Language Switcher
    render_language_switcher()

    # Header
    st.markdown(f'<p class="main-header">{t("main_header")}</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="sub-header">{t("sub_header")}</p>', unsafe_allow_html=True)

    # About section
    with st.expander(t("about_title"), expanded=False):
        st.markdown(t("about_content"))

    # File upload section
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        uploaded_file = st.file_uploader(
            t("upload_label"),
            type=["pdf"],
            help=t("upload_help"),
        )

        if uploaded_file:
            st.info(f"{t('uploaded')}: **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} KB)")

    # Process button
    col1, col2, col3 = st.columns([1, 1, 1])

    with col2:
        process_btn = st.button(
            t("generate_btn"),
            type="primary",
            disabled=not (uploaded_file and check_api_key()),
            use_container_width=True,
        )

    if not check_api_key():
        st.warning(t("api_key_required"))
        return

    # Processing
    if process_btn and uploaded_file:
        with st.spinner(t("processing")):
            try:
                result, output_dir = process_paper(
                    uploaded_file,
                    st.session_state.api_key,
                )

                st.session_state.result = result
                st.session_state.output_dir = output_dir

            except Exception as e:
                st.error(f"{t('error_processing')}: {str(e)}")
                return

    # Display results
    if st.session_state.result:
        render_results(st.session_state.result, st.session_state.get("output_dir"))


def render_results(result, output_dir):
    """Render processing results."""
    st.markdown("---")
    st.subheader(t("results"))

    status = result.get("status", "unknown")

    if status == "success":
        st.success(t("success_msg"))
    else:
        st.error(f"{t('status_msg')}: {status}")
        if result.get("error_message"):
            st.error(result["error_message"])

    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    final_output = result.get("final_output", {})

    with col1:
        st.metric(t("files_generated"), final_output.get("file_count", 0))

    with col2:
        st.metric(t("debug_attempts"), final_output.get("debug_attempts", 0))

    with col3:
        st.metric(t("tokens_used"), f"{final_output.get('total_tokens', 0):,}")

    with col4:
        algo_name = (result.get("main_algorithm") or {}).get("name", "N/A")
        st.metric(t("algorithm"), algo_name[:15] + "..." if len(algo_name) > 15 else algo_name)

    # Paper info
    if result.get("paper_summary"):
        with st.expander(t("paper_info"), expanded=False):
            summary = result["paper_summary"]
            st.write(f"**{t('title')}:** {summary.get('title', 'N/A')}")
            st.write(f"**{t('sections')}:** {summary.get('section_count', 0)}")
            st.write(f"**{t('equations')}:** {summary.get('equation_count', 0)}")

    # Algorithm info
    if result.get("main_algorithm"):
        with st.expander(t("algo_analysis"), expanded=False):
            algo = result["main_algorithm"]
            st.write(f"**{t('name')}:** {algo.get('name', 'N/A')}")
            st.write(f"**{t('purpose')}:** {algo.get('purpose', 'N/A')}")
            st.write(f"**{t('description')}:** {algo.get('description', 'N/A')}")

            if algo.get("steps"):
                st.write(f"**{t('steps')}:**")
                for i, step in enumerate(algo["steps"], 1):
                    st.write(f"{i}. {step}")

    # Generated code
    if result.get("code_project"):
        st.subheader(t("generated_code"))

        code_project = result["code_project"]
        files = code_project.get("files", [])

        if files:
            tab_names = [f["filename"] for f in files]
            tabs = st.tabs(tab_names)

            for tab, file_info in zip(tabs, files):
                with tab:
                    st.code(file_info["content"], language="python")

        project_name = code_project.get("name", "generated_code")

        if output_dir:
            zip_buffer = create_zip_download(output_dir, project_name)

            st.download_button(
                label=t("download_zip"),
                data=zip_buffer,
                file_name=f"{project_name}.zip",
                mime="application/zip",
                type="primary",
            )

    # Execution output
    if result.get("execution_result"):
        exec_result = result["execution_result"]

        with st.expander(t("exec_output"), expanded=True):
            if exec_result.get("stdout"):
                st.code(exec_result["stdout"], language="text")

            if exec_result.get("stderr") and status != "success":
                st.error(f"{t('errors')}:")
                st.code(exec_result["stderr"], language="text")


def main():
    """Main application entry point."""
    init_session_state()
    render_sidebar()
    render_main()


if __name__ == "__main__":
    main()
