"""
Paper2Code - Streamlit Web Application (Enhanced Version)
AI를 활용하여 과학 논문을 실행 가능한 Python 코드로 변환합니다.

Enhanced Features:
- Modern UI with animations
- Real-time progress tracking
- Token estimation
- Copy code functionality
- Improved result visualization
"""

import io
import os
import tempfile
import zipfile
import time
from pathlib import Path

import streamlit as st

# =============================================================================
# Sample Papers / 샘플 논문
# =============================================================================
SAMPLE_PAPERS = {
    "simplest_sort": {
        "file": "samples/simplest_sort.pdf",
        "arxiv": "2110.01111",
        "estimated_tokens": 30000,
        "en": {
            "title": "Is this the simplest sorting algorithm ever?",
            "description": "A surprisingly simple 3-line sorting algorithm. Perfect for testing!",
            "difficulty": "Easy",
            "algorithm": "ICan'tBelieveItCanSort",
            "time": "~2 min",
        },
        "ko": {
            "title": "가장 간단한 정렬 알고리즘?",
            "description": "놀랍도록 간단한 3줄짜리 정렬 알고리즘. 테스트에 최적!",
            "difficulty": "쉬움",
            "algorithm": "ICan'tBelieveItCanSort",
            "time": "~2분",
        },
    },
    "classix_clustering": {
        "file": "samples/classix_clustering.pdf",
        "arxiv": "2202.01456",
        "estimated_tokens": 80000,
        "en": {
            "title": "CLASSIX: Fast and Explainable Clustering",
            "description": "A fast clustering algorithm based on sorting. Includes clear pseudocode.",
            "difficulty": "Medium",
            "algorithm": "CLASSIX Clustering",
            "time": "~5 min",
        },
        "ko": {
            "title": "CLASSIX: 빠르고 설명 가능한 클러스터링",
            "description": "정렬 기반의 빠른 클러스터링 알고리즘. 명확한 의사코드 포함.",
            "difficulty": "보통",
            "algorithm": "CLASSIX 클러스터링",
            "time": "~5분",
        },
    },
    "formal_transformers": {
        "file": "samples/formal_transformers.pdf",
        "arxiv": "2207.09238",
        "estimated_tokens": 150000,
        "en": {
            "title": "Formal Algorithms for Transformers",
            "description": "Complete pseudocode for Transformer components including Attention and GPT-2.",
            "difficulty": "Hard",
            "algorithm": "Transformer/Attention",
            "time": "~10 min",
        },
        "ko": {
            "title": "트랜스포머를 위한 공식 알고리즘",
            "description": "Attention, GPT-2 등 트랜스포머 구성요소의 완전한 의사코드.",
            "difficulty": "어려움",
            "algorithm": "Transformer/Attention",
            "time": "~10분",
        },
    },
}

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
        "step_1": "Upload",
        "step_2": "Parse",
        "step_3": "Analyze",
        "step_4": "Generate",
        "step_5": "Execute",
        "step_6": "Download",
        "links": "Links",
        "github_repo": "GitHub Repository",
        "upload_label": "Upload a Scientific Paper (PDF)",
        "upload_help": "Upload a PDF file containing algorithm descriptions",
        "uploaded": "Uploaded",
        "generate_btn": "Generate Code",
        "api_key_required": "Please enter your Anthropic API key in the sidebar to continue.",
        "processing": "Processing paper...",
        "error_processing": "Error processing paper",
        "results": "Results",
        "success_msg": "Code generated successfully!",
        "status_msg": "Pipeline completed with status",
        "files_generated": "Files",
        "debug_attempts": "Debug",
        "tokens_used": "Tokens",
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
        "download_zip": "Download All (ZIP)",
        "download_file": "Download",
        "copy_code": "Copy",
        "exec_output": "Execution Output",
        "errors": "Errors",
        "about_title": "What is Paper2Code?",
        "about_content": """
**Paper2Code** is an AI agent that automatically analyzes algorithms from scientific papers and converts them into executable Python code.

**Features:** PDF parsing • Algorithm extraction • Code generation • Auto-testing
        """,
        "challenge_badge": "2026 AI Co-Scientist Challenge Korea",
        "sample_papers": "Try Sample Papers",
        "sample_papers_desc": "Test Paper2Code with real arXiv papers",
        "select_sample": "Selected",
        "difficulty": "Difficulty",
        "test_sample_btn": "Test",
        "or_upload": "Or upload your own paper",
        "view_arxiv": "arXiv",
        "estimated_tokens": "Est. tokens",
        "estimated_cost": "Est. cost",
        "estimated_time": "Est. time",
        "processing_step_1": "Parsing PDF...",
        "processing_step_2": "Analyzing algorithms...",
        "processing_step_3": "Generating code...",
        "processing_step_4": "Testing code...",
        "rate_limit_warning": "Rate limit may apply. Wait 1-2 min if error occurs.",
        "copied": "Copied!",
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
        "how_it_works": "작동 방식",
        "step_1": "업로드",
        "step_2": "파싱",
        "step_3": "분석",
        "step_4": "생성",
        "step_5": "실행",
        "step_6": "다운로드",
        "links": "링크",
        "github_repo": "GitHub 저장소",
        "upload_label": "과학 논문 업로드 (PDF)",
        "upload_help": "알고리즘이 포함된 PDF 논문 파일을 업로드하세요",
        "uploaded": "업로드됨",
        "generate_btn": "코드 생성하기",
        "api_key_required": "계속하려면 사이드바에서 Anthropic API 키를 입력해주세요.",
        "processing": "논문 처리 중...",
        "error_processing": "처리 중 오류 발생",
        "results": "결과",
        "success_msg": "코드가 성공적으로 생성되었습니다!",
        "status_msg": "파이프라인 완료 상태",
        "files_generated": "파일",
        "debug_attempts": "디버그",
        "tokens_used": "토큰",
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
        "download_zip": "전체 다운로드 (ZIP)",
        "download_file": "다운로드",
        "copy_code": "복사",
        "exec_output": "실행 결과",
        "errors": "오류",
        "about_title": "Paper2Code란?",
        "about_content": """
**Paper2Code**는 과학 논문의 알고리즘을 분석하고 실행 가능한 Python 코드로 변환하는 AI 에이전트입니다.

**기능:** PDF 파싱 • 알고리즘 추출 • 코드 생성 • 자동 테스트
        """,
        "challenge_badge": "2026 AI Co-Scientist Challenge Korea",
        "sample_papers": "샘플 논문 테스트",
        "sample_papers_desc": "실제 arXiv 논문으로 테스트해보세요",
        "select_sample": "선택됨",
        "difficulty": "난이도",
        "test_sample_btn": "테스트",
        "or_upload": "또는 직접 업로드",
        "view_arxiv": "arXiv",
        "estimated_tokens": "예상 토큰",
        "estimated_cost": "예상 비용",
        "estimated_time": "예상 시간",
        "processing_step_1": "PDF 파싱 중...",
        "processing_step_2": "알고리즘 분석 중...",
        "processing_step_3": "코드 생성 중...",
        "processing_step_4": "코드 테스트 중...",
        "rate_limit_warning": "Rate limit 주의. 오류 시 1-2분 대기 후 재시도하세요.",
        "copied": "복사됨!",
    }
}


def t(key):
    """Get translation for current language."""
    lang = st.session_state.get("lang", "en")
    return TRANSLATIONS[lang].get(key, key)


def get_sample_info(sample_key):
    """Get sample paper info in current language."""
    lang = st.session_state.get("lang", "en")
    sample = SAMPLE_PAPERS[sample_key]
    return {
        **sample[lang],
        "file": sample["file"],
        "arxiv": sample["arxiv"],
        "estimated_tokens": sample["estimated_tokens"],
    }


# Page configuration
st.set_page_config(
    page_title="Paper2Code - AI Paper to Code",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# Enhanced CSS Styles
# =============================================================================
st.markdown("""
<style>
    /* Import Google Font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* Global Styles */
    .stApp {
        font-family: 'Inter', sans-serif;
    }

    /* Header Styles */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        font-weight: 700;
        text-align: center;
        margin-bottom: 0.5rem;
        animation: fadeIn 0.8s ease-out;
    }

    .sub-header {
        font-size: 1.1rem;
        color: #6b7280;
        text-align: center;
        margin-bottom: 2rem;
        animation: fadeIn 1s ease-out;
    }

    /* Challenge Badge */
    .challenge-badge {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.6rem 1.2rem;
        border-radius: 2rem;
        font-size: 0.75rem;
        font-weight: 600;
        text-align: center;
        margin-bottom: 1rem;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }

    /* Sample Paper Cards */
    .sample-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 1rem;
        padding: 1.5rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        height: 100%;
        position: relative;
        overflow: hidden;
    }

    .sample-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, #667eea, #764ba2);
        transform: scaleX(0);
        transition: transform 0.3s ease;
    }

    .sample-card:hover {
        border-color: #667eea;
        box-shadow: 0 10px 40px rgba(102, 126, 234, 0.15);
        transform: translateY(-4px);
    }

    .sample-card:hover::before {
        transform: scaleX(1);
    }

    .sample-card h4 {
        margin: 0.75rem 0;
        font-weight: 600;
        color: #1f2937;
        font-size: 1.1rem;
    }

    .sample-card p {
        color: #6b7280;
        font-size: 0.875rem;
        line-height: 1.5;
    }

    /* Difficulty Badges */
    .difficulty-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.025em;
    }

    .difficulty-easy {
        background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
        color: #065f46;
    }

    .difficulty-medium {
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        color: #92400e;
    }

    .difficulty-hard {
        background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
        color: #991b1b;
    }

    /* Stats Card */
    .stat-card {
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        border-radius: 1rem;
        padding: 1.25rem;
        text-align: center;
        border: 1px solid #e2e8f0;
    }

    .stat-value {
        font-size: 2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .stat-label {
        font-size: 0.875rem;
        color: #64748b;
        margin-top: 0.25rem;
    }

    /* Success/Error Messages */
    .success-banner {
        background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
        border: 1px solid #34d399;
        border-radius: 1rem;
        padding: 1rem 1.5rem;
        color: #065f46;
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }

    .error-banner {
        background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
        border: 1px solid #f87171;
        border-radius: 1rem;
        padding: 1rem 1.5rem;
        color: #991b1b;
        font-weight: 500;
    }

    /* Code Block Enhancement */
    .code-header {
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        color: #e2e8f0;
        padding: 0.75rem 1rem;
        border-radius: 0.75rem 0.75rem 0 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-family: 'Inter', sans-serif;
        font-size: 0.875rem;
    }

    .code-actions {
        display: flex;
        gap: 0.5rem;
    }

    /* Progress Steps */
    .progress-container {
        display: flex;
        justify-content: space-between;
        margin: 2rem 0;
        position: relative;
    }

    .progress-step {
        display: flex;
        flex-direction: column;
        align-items: center;
        position: relative;
        z-index: 1;
    }

    .step-circle {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        font-size: 0.875rem;
        transition: all 0.3s ease;
    }

    .step-inactive {
        background: #e5e7eb;
        color: #9ca3af;
    }

    .step-active {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        animation: pulse 2s infinite;
    }

    .step-complete {
        background: #10b981;
        color: white;
    }

    .step-label {
        margin-top: 0.5rem;
        font-size: 0.75rem;
        color: #6b7280;
    }

    /* Divider */
    .divider-text {
        display: flex;
        align-items: center;
        text-align: center;
        color: #9ca3af;
        margin: 2rem 0;
        font-size: 0.875rem;
    }

    .divider-text::before,
    .divider-text::after {
        content: '';
        flex: 1;
        border-bottom: 1px solid #e5e7eb;
    }

    .divider-text::before { margin-right: 1rem; }
    .divider-text::after { margin-left: 1rem; }

    /* Animations */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.05); }
    }

    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }

    .spinner {
        display: inline-block;
        width: 20px;
        height: 20px;
        border: 2px solid #e5e7eb;
        border-top-color: #667eea;
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }

    /* Info Box */
    .info-box {
        background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
        border: 1px solid #93c5fd;
        border-radius: 0.75rem;
        padding: 1rem;
        color: #1e40af;
        font-size: 0.875rem;
    }

    /* Token Estimation */
    .token-estimate {
        background: #f8fafc;
        border-radius: 0.5rem;
        padding: 0.5rem 0.75rem;
        font-size: 0.75rem;
        color: #64748b;
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Button Enhancement */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border: none;
        font-weight: 600;
        transition: all 0.3s ease;
    }

    .stButton > button[kind="primary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
</style>
""", unsafe_allow_html=True)


def get_api_key():
    """Get API key from session state only (user must enter in sidebar)."""
    return st.session_state.get("api_key")


def check_api_key():
    """Check if API key is configured."""
    api_key = get_api_key()
    return api_key is not None and len(api_key) > 0


def init_session_state():
    """Initialize session state variables."""
    defaults = {
        "processing": False,
        "result": None,
        "current_step": "",
        "api_key": None,
        "lang": "en",
        "selected_sample": None,
        "processing_stage": 0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def process_paper_from_path(paper_path, api_key):
    """Process a PDF file from path and generate code."""
    os.environ["ANTHROPIC_API_KEY"] = api_key
    from src.agents import Paper2CodeOrchestrator

    output_dir = tempfile.mkdtemp()
    orchestrator = Paper2CodeOrchestrator(use_docker=False, max_debug_attempts=2)
    result = orchestrator.run(paper_path=paper_path, output_dir=output_dir, verbose=False)
    return result, output_dir


def process_paper(pdf_file, api_key):
    """Process uploaded PDF and generate code."""
    os.environ["ANTHROPIC_API_KEY"] = api_key
    from src.agents import Paper2CodeOrchestrator

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(pdf_file.getvalue())
        tmp_path = tmp.name

    try:
        output_dir = tempfile.mkdtemp()
        orchestrator = Paper2CodeOrchestrator(use_docker=False, max_debug_attempts=2)
        result = orchestrator.run(paper_path=tmp_path, output_dir=output_dir, verbose=False)
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
            if st.button("🇺🇸 ENG", use_container_width=True,
                        type="primary" if st.session_state.lang == "en" else "secondary"):
                st.session_state.lang = "en"
                st.rerun()
        with lang_col2:
            if st.button("🇰🇷 한국어", use_container_width=True,
                        type="primary" if st.session_state.lang == "ko" else "secondary"):
                st.session_state.lang = "ko"
                st.rerun()


def render_sidebar():
    """Render sidebar with configuration."""
    with st.sidebar:
        # Logo and Title
        st.markdown("""
        <div style="text-align: center; padding: 1rem 0;">
            <span style="font-size: 3rem;">🔬</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<h1 style='text-align: center; font-size: 1.5rem;'>Paper2Code</h1>", unsafe_allow_html=True)
        st.markdown(f'<div class="challenge-badge">{t("challenge_badge")}</div>', unsafe_allow_html=True)

        st.markdown("---")

        # API Key Section
        st.markdown(f"### ⚙️ {t('config')}")

        api_key = st.text_input(
            t("api_key_label"),
            type="password",
            value=st.session_state.get("api_key", ""),
            help=t("api_key_help"),
            placeholder="sk-ant-api03-..."
        )

        if api_key:
            st.session_state.api_key = api_key
            os.environ["ANTHROPIC_API_KEY"] = api_key

        if check_api_key():
            st.success(f"✅ {t('api_key_success')}")
        else:
            st.warning(f"⚠️ {t('api_key_warning')}")

        st.markdown("---")

        # How it works - Visual Steps
        st.markdown(f"### 🔄 {t('how_it_works')}")

        steps = [
            ("📄", t("step_1")),
            ("🔍", t("step_2")),
            ("🧠", t("step_3")),
            ("💻", t("step_4")),
            ("▶️", t("step_5")),
            ("📥", t("step_6")),
        ]

        step_html = '<div style="display: flex; flex-wrap: wrap; gap: 0.5rem;">'
        for emoji, label in steps:
            step_html += f'''
            <div style="background: #f1f5f9; padding: 0.5rem 0.75rem; border-radius: 0.5rem; font-size: 0.8rem;">
                {emoji} {label}
            </div>
            '''
        step_html += '</div>'
        st.markdown(step_html, unsafe_allow_html=True)

        st.markdown("---")

        # Rate Limit Warning
        st.markdown(f"""
        <div class="info-box">
            ⚡ {t('rate_limit_warning')}
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # Links
        st.markdown(f"### 🔗 {t('links')}")
        st.markdown(f"[📚 {t('github_repo')}](https://github.com/yonghwan1106/paper2code)")

        st.markdown("---")
        st.caption("Paper2Code v0.2.0")
        st.caption("Powered by Claude AI")


def get_difficulty_class(difficulty):
    """Get CSS class for difficulty level."""
    d = difficulty.lower()
    if d in ["easy", "쉬움"]:
        return "difficulty-easy"
    elif d in ["medium", "보통"]:
        return "difficulty-medium"
    return "difficulty-hard"


def estimate_cost(tokens):
    """Estimate cost based on token count (Claude Sonnet 4.5 pricing)."""
    # $3 per 1M input, $15 per 1M output (roughly 50/50 split estimated)
    input_cost = (tokens * 0.5 / 1_000_000) * 3
    output_cost = (tokens * 0.5 / 1_000_000) * 15
    return input_cost + output_cost


def render_sample_papers():
    """Render sample papers selection section."""
    st.markdown(f"### 📚 {t('sample_papers')}")
    st.caption(t("sample_papers_desc"))

    cols = st.columns(3)

    for idx, (key, _) in enumerate(SAMPLE_PAPERS.items()):
        info = get_sample_info(key)
        difficulty_class = get_difficulty_class(info["difficulty"])
        est_cost = estimate_cost(info["estimated_tokens"])

        with cols[idx]:
            st.markdown(f"""
            <div class="sample-card">
                <span class="difficulty-badge {difficulty_class}">{info["difficulty"]}</span>
                <h4>{info["title"]}</h4>
                <p>{info["description"]}</p>
                <p style="font-size: 0.75rem; color: #9ca3af; margin-top: 0.75rem;">
                    🤖 {info["algorithm"]}<br>
                    ⏱️ {info["time"]} • 🪙 ~${est_cost:.2f}
                </p>
            </div>
            """, unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"🚀 {t('test_sample_btn')}", key=f"test_{key}", use_container_width=True, type="primary"):
                    st.session_state.selected_sample = key
                    st.rerun()
            with col2:
                st.link_button(f"📄 {t('view_arxiv')}", f"https://arxiv.org/abs/{info['arxiv']}", use_container_width=True)

    # Process selected sample
    if st.session_state.selected_sample and check_api_key():
        sample_key = st.session_state.selected_sample
        info = get_sample_info(sample_key)

        st.markdown("---")
        st.markdown(f"""
        <div class="info-box">
            ✅ <strong>{t('select_sample')}:</strong> {info['title']}<br>
            <span style="font-size: 0.8rem;">🪙 {t('estimated_tokens')}: ~{info['estimated_tokens']:,} • 💰 {t('estimated_cost')}: ~${estimate_cost(info['estimated_tokens']):.2f}</span>
        </div>
        """, unsafe_allow_html=True)

        # Progress indicator
        progress_placeholder = st.empty()
        status_placeholder = st.empty()

        with st.spinner(t("processing")):
            try:
                base_dir = Path(__file__).parent
                sample_path = base_dir / info["file"]

                if not sample_path.exists():
                    st.error(f"Sample file not found: {info['file']}")
                    st.session_state.selected_sample = None
                    return

                result, output_dir = process_paper_from_path(str(sample_path), get_api_key())

                st.session_state.result = result
                st.session_state.output_dir = output_dir
                st.session_state.selected_sample = None
                st.rerun()

            except Exception as e:
                st.error(f"❌ {t('error_processing')}: {str(e)}")
                st.session_state.selected_sample = None


def render_sample_papers_preview():
    """Render sample papers preview (when API key not configured)."""
    st.markdown(f"### 📚 {t('sample_papers')}")
    st.caption(t("sample_papers_desc"))

    cols = st.columns(3)

    for idx, (key, _) in enumerate(SAMPLE_PAPERS.items()):
        info = get_sample_info(key)
        difficulty_class = get_difficulty_class(info["difficulty"])

        with cols[idx]:
            st.markdown(f"""
            <div class="sample-card" style="opacity: 0.6;">
                <span class="difficulty-badge {difficulty_class}">{info["difficulty"]}</span>
                <h4>{info["title"]}</h4>
                <p>{info["description"]}</p>
            </div>
            """, unsafe_allow_html=True)
            st.link_button(f"📄 {t('view_arxiv')}", f"https://arxiv.org/abs/{info['arxiv']}", use_container_width=True)


def render_results(result, output_dir):
    """Render processing results."""
    st.markdown("---")
    st.markdown(f"## 📊 {t('results')}")

    status = result.get("status", "unknown")

    # Status Banner
    if status == "success":
        st.markdown(f"""
        <div class="success-banner">
            <span style="font-size: 1.5rem;">✅</span>
            <span>{t('success_msg')}</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="error-banner">
            <span style="font-size: 1.25rem;">❌</span>
            {t('status_msg')}: {status}
        </div>
        """, unsafe_allow_html=True)
        if result.get("error_message"):
            st.error(result["error_message"])

    st.markdown("<br>", unsafe_allow_html=True)

    # Stats Cards
    final_output = result.get("final_output", {})
    col1, col2, col3, col4 = st.columns(4)

    stats = [
        (col1, t("files_generated"), final_output.get("file_count", 0), "📁"),
        (col2, t("debug_attempts"), final_output.get("debug_attempts", 0), "🔧"),
        (col3, t("tokens_used"), f"{final_output.get('total_tokens', 0):,}", "🪙"),
        (col4, t("algorithm"), (result.get("main_algorithm") or {}).get("name", "N/A")[:12], "🧠"),
    ]

    for col, label, value, emoji in stats:
        with col:
            st.markdown(f"""
            <div class="stat-card">
                <div style="font-size: 1.5rem;">{emoji}</div>
                <div class="stat-value">{value}</div>
                <div class="stat-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Paper and Algorithm Info
    col1, col2 = st.columns(2)

    with col1:
        if result.get("paper_summary"):
            with st.expander(f"📄 {t('paper_info')}", expanded=False):
                summary = result["paper_summary"]
                st.write(f"**{t('title')}:** {summary.get('title', 'N/A')}")
                st.write(f"**{t('sections')}:** {summary.get('section_count', 0)}")
                st.write(f"**{t('equations')}:** {summary.get('equation_count', 0)}")

    with col2:
        if result.get("main_algorithm"):
            with st.expander(f"🧠 {t('algo_analysis')}", expanded=False):
                algo = result["main_algorithm"]
                st.write(f"**{t('name')}:** {algo.get('name', 'N/A')}")
                st.write(f"**{t('purpose')}:** {algo.get('purpose', 'N/A')}")
                if algo.get("steps"):
                    st.write(f"**{t('steps')}:**")
                    for i, step in enumerate(algo["steps"], 1):
                        st.write(f"{i}. {step}")

    # Generated Code Section
    if result.get("code_project"):
        st.markdown(f"### 💻 {t('generated_code')}")

        code_project = result["code_project"]
        files = code_project.get("files", [])

        if files:
            # Create tabs for each file
            tab_names = [f"📄 {f['filename']}" for f in files]
            tabs = st.tabs(tab_names)

            for tab, file_info in zip(tabs, files):
                with tab:
                    # Code header with actions
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.caption(f"📝 {file_info.get('description', '')}")
                    with col2:
                        # Copy button (using st.code's built-in copy)
                        pass
                    with col3:
                        # Individual file download
                        st.download_button(
                            f"📥 {t('download_file')}",
                            file_info["content"],
                            file_name=file_info["filename"],
                            mime="text/plain",
                            use_container_width=True,
                        )

                    st.code(file_info["content"], language="python")

        # ZIP Download
        project_name = code_project.get("name", "generated_code")
        if output_dir:
            st.markdown("<br>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                zip_buffer = create_zip_download(output_dir, project_name)
                st.download_button(
                    label=f"📦 {t('download_zip')}",
                    data=zip_buffer,
                    file_name=f"{project_name}.zip",
                    mime="application/zip",
                    type="primary",
                    use_container_width=True,
                )

    # Execution Output
    if result.get("execution_result"):
        exec_result = result["execution_result"]
        with st.expander(f"▶️ {t('exec_output')}", expanded=True):
            if exec_result.get("stdout"):
                st.code(exec_result["stdout"], language="text")
            if exec_result.get("stderr") and status != "success":
                st.error(f"❌ {t('errors')}:")
                st.code(exec_result["stderr"], language="text")


def render_main():
    """Render main content area."""
    render_language_switcher()

    # Header
    st.markdown(f'<p class="main-header">{t("main_header")}</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="sub-header">{t("sub_header")}</p>', unsafe_allow_html=True)

    # About
    with st.expander(f"ℹ️ {t('about_title')}", expanded=False):
        st.markdown(t("about_content"))

    # API Key Check
    if not check_api_key():
        st.warning(f"🔑 {t('api_key_required')}")
        st.markdown("---")
        render_sample_papers_preview()
        return

    # Sample Papers
    st.markdown("---")
    render_sample_papers()

    # Divider
    st.markdown(f'<div class="divider-text">{t("or_upload")}</div>', unsafe_allow_html=True)

    # File Upload
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        uploaded_file = st.file_uploader(
            t("upload_label"),
            type=["pdf"],
            help=t("upload_help"),
        )

        if uploaded_file:
            st.info(f"📄 {t('uploaded')}: **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} KB)")

    # Process Button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        process_btn = st.button(
            f"🚀 {t('generate_btn')}",
            type="primary",
            disabled=not (uploaded_file and check_api_key()),
            use_container_width=True,
        )

    # Processing
    if process_btn and uploaded_file:
        with st.spinner(t("processing")):
            try:
                result, output_dir = process_paper(uploaded_file, get_api_key())
                st.session_state.result = result
                st.session_state.output_dir = output_dir
            except Exception as e:
                st.error(f"❌ {t('error_processing')}: {str(e)}")
                return

    # Results
    if st.session_state.result:
        render_results(st.session_state.result, st.session_state.get("output_dir"))


def main():
    """Main application entry point."""
    init_session_state()
    render_sidebar()
    render_main()


if __name__ == "__main__":
    main()
