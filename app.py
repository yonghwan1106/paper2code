"""
Paper2Code - Streamlit Web Application

Convert scientific papers to executable Python code using AI.
"""

import io
import os
import tempfile
import zipfile
from pathlib import Path

import streamlit as st

# Page configuration
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


def process_paper(pdf_file, api_key):
    """Process uploaded PDF and generate code."""
    # Set API key
    os.environ["ANTHROPIC_API_KEY"] = api_key

    # Import here to avoid loading before API key is set
    from src.agents import Paper2CodeOrchestrator

    # Save uploaded file to temp location
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(pdf_file.getvalue())
        tmp_path = tmp.name

    try:
        # Create output directory
        output_dir = tempfile.mkdtemp()

        # Initialize orchestrator (no Docker for Streamlit Cloud)
        orchestrator = Paper2CodeOrchestrator(
            use_docker=False,
            max_debug_attempts=2,
        )

        # Run pipeline
        result = orchestrator.run(
            paper_path=tmp_path,
            output_dir=output_dir,
            verbose=False,
        )

        return result, output_dir

    finally:
        # Cleanup temp PDF
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


def render_sidebar():
    """Render sidebar with configuration."""
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/document.png", width=80)
        st.title("Paper2Code")
        st.markdown("---")

        # API Key input
        st.subheader("Configuration")

        api_key = st.text_input(
            "Anthropic API Key",
            type="password",
            value=st.session_state.get("api_key", ""),
            help="Enter your Anthropic API key to use Claude for code generation",
        )

        if api_key:
            st.session_state.api_key = api_key
            os.environ["ANTHROPIC_API_KEY"] = api_key

        if check_api_key():
            st.success("API Key configured")
        else:
            st.warning("Please enter your API key")

        st.markdown("---")

        # Info section
        st.subheader("How it works")
        st.markdown("""
        1. **Upload** a scientific paper (PDF)
        2. **Parse** - Extract text and structure
        3. **Analyze** - Identify algorithms
        4. **Generate** - Create Python code
        5. **Execute** - Test the code
        6. **Download** - Get your code!
        """)

        st.markdown("---")

        # Links
        st.subheader("Links")
        st.markdown("""
        - [GitHub Repository](https://github.com/yourusername/paper2code)
        - [Documentation](https://github.com/yourusername/paper2code#readme)
        """)

        st.markdown("---")
        st.caption("Paper2Code MVP v0.1.0")
        st.caption("Powered by Claude AI")


def render_main():
    """Render main content area."""
    # Header
    st.markdown('<p class="main-header">Paper2Code</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Transform Scientific Papers into Executable Python Code</p>', unsafe_allow_html=True)

    # File upload section
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        uploaded_file = st.file_uploader(
            "Upload a Scientific Paper (PDF)",
            type=["pdf"],
            help="Upload a PDF file containing algorithm descriptions",
        )

        if uploaded_file:
            st.info(f"Uploaded: **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} KB)")

    # Process button
    col1, col2, col3 = st.columns([1, 1, 1])

    with col2:
        process_btn = st.button(
            "Generate Code",
            type="primary",
            disabled=not (uploaded_file and check_api_key()),
            use_container_width=True,
        )

    if not check_api_key():
        st.warning("Please enter your Anthropic API key in the sidebar to continue.")
        return

    # Processing
    if process_btn and uploaded_file:
        with st.spinner("Processing paper... This may take a few minutes."):
            # Progress display
            progress_container = st.empty()

            try:
                # Process the paper
                result, output_dir = process_paper(
                    uploaded_file,
                    st.session_state.api_key,
                )

                st.session_state.result = result
                st.session_state.output_dir = output_dir

            except Exception as e:
                st.error(f"Error processing paper: {str(e)}")
                return

    # Display results
    if st.session_state.result:
        render_results(st.session_state.result, st.session_state.get("output_dir"))


def render_results(result, output_dir):
    """Render processing results."""
    st.markdown("---")
    st.subheader("Results")

    # Status
    status = result.get("status", "unknown")

    if status == "success":
        st.success("Code generated and executed successfully!")
    else:
        st.error(f"Pipeline completed with status: {status}")
        if result.get("error_message"):
            st.error(result["error_message"])

    # Metrics
    col1, col2, col3, col4 = st.columns(4)

    final_output = result.get("final_output", {})

    with col1:
        st.metric("Files Generated", final_output.get("file_count", 0))

    with col2:
        st.metric("Debug Attempts", final_output.get("debug_attempts", 0))

    with col3:
        st.metric("Tokens Used", f"{final_output.get('total_tokens', 0):,}")

    with col4:
        algo_name = (result.get("main_algorithm") or {}).get("name", "N/A")
        st.metric("Algorithm", algo_name[:20] + "..." if len(algo_name) > 20 else algo_name)

    # Paper info
    if result.get("paper_summary"):
        with st.expander("Paper Information", expanded=False):
            summary = result["paper_summary"]
            st.write(f"**Title:** {summary.get('title', 'N/A')}")
            st.write(f"**Sections:** {summary.get('section_count', 0)}")
            st.write(f"**Equations:** {summary.get('equation_count', 0)}")

    # Algorithm info
    if result.get("main_algorithm"):
        with st.expander("Algorithm Analysis", expanded=False):
            algo = result["main_algorithm"]
            st.write(f"**Name:** {algo.get('name', 'N/A')}")
            st.write(f"**Purpose:** {algo.get('purpose', 'N/A')}")
            st.write(f"**Description:** {algo.get('description', 'N/A')}")

            if algo.get("steps"):
                st.write("**Steps:**")
                for i, step in enumerate(algo["steps"], 1):
                    st.write(f"{i}. {step}")

    # Generated code
    if result.get("code_project"):
        st.subheader("Generated Code")

        code_project = result["code_project"]
        files = code_project.get("files", [])

        # Create tabs for each file
        if files:
            tab_names = [f["filename"] for f in files]
            tabs = st.tabs(tab_names)

            for tab, file_info in zip(tabs, files):
                with tab:
                    st.code(file_info["content"], language="python")

        # Download button
        project_name = code_project.get("name", "generated_code")

        if output_dir:
            zip_buffer = create_zip_download(output_dir, project_name)

            st.download_button(
                label="Download Code (ZIP)",
                data=zip_buffer,
                file_name=f"{project_name}.zip",
                mime="application/zip",
                type="primary",
            )

    # Execution output
    if result.get("execution_result"):
        exec_result = result["execution_result"]

        with st.expander("Execution Output", expanded=True):
            if exec_result.get("stdout"):
                st.code(exec_result["stdout"], language="text")

            if exec_result.get("stderr") and status != "success":
                st.error("Errors:")
                st.code(exec_result["stderr"], language="text")


def main():
    """Main application entry point."""
    init_session_state()
    render_sidebar()
    render_main()


if __name__ == "__main__":
    main()
