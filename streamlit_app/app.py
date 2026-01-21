"""
Investment Research Streamlit App

A web interface for generating AI-powered equity research reports.
"""

import os
import streamlit as st
import sys
import time
from pathlib import Path

# Add directories to path for imports
app_dir = str(Path(__file__).parent)
parent_dir = str(Path(__file__).parent.parent)
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Load environment BEFORE other imports
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from streamlit_app.components.search import render_search, render_selected_stock
from streamlit_app.components.progress import render_progress, render_analysis_running
from streamlit_app.components.results import render_results, check_results_exist
from streamlit_app.components.report_history import render_report_history
from streamlit_app.services.research_runner import get_runner, get_progress, clear_progress
from streamlit_app.services.storage import is_storage_configured

# Page configuration
st.set_page_config(
    page_title="Investment Research",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
    initial_sidebar_state="expanded"
)


def init_session_state():
    """Initialize session state variables."""
    defaults = {
        "selected_ticker": None,
        "selected_company": None,
        "start_analysis": False,
        "analysis_complete": False,
        "view_report_id": None,  # For viewing historical reports from cloud
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def load_environment():
    """Load environment variables, preferring Streamlit secrets."""
    # Try to load from Streamlit secrets first
    try:
        if hasattr(st, 'secrets'):
            if "FMP_API_KEY" in st.secrets:
                os.environ["FMP_API_KEY"] = st.secrets["FMP_API_KEY"]
            if "OPENAI_API_KEY" in st.secrets:
                os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
    except Exception:
        pass

    # Validate required keys
    missing = []
    if not os.environ.get("FMP_API_KEY"):
        missing.append("FMP_API_KEY")
    if not os.environ.get("OPENAI_API_KEY"):
        missing.append("OPENAI_API_KEY")

    return missing


def render_sidebar():
    """Render the sidebar."""
    with st.sidebar:
        st.header("About")
        st.markdown("""
        This tool generates comprehensive investment research
        using a **Red/Blue Team** approach:

        🔵 **Blue Team**: Optimistic analysis (Bull Case)
        🔴 **Red Team**: Skeptical analysis (Bear Case)
        💼 **CIO**: Independent synthesis & recommendation

        **Analysis covers:**
        - Price trends & sentiment
        - Business model & phase
        - Financial metrics & valuation
        - Competitive moat
        - Management quality & risks
        - Growth drivers

        ⚡ **Parallel execution** - Faster and less biased!

        **Note:** Analysis takes 10-15 minutes.
        """)

        st.divider()

        # Quick actions
        if st.session_state.get("selected_ticker"):
            if st.button("Clear Selection", use_container_width=True):
                clear_progress()
                st.session_state.selected_ticker = None
                st.session_state.selected_company = None
                st.session_state.analysis_complete = False
                st.session_state.start_analysis = False
                st.session_state.pop("view_report_id", None)
                st.rerun()

        st.divider()

        # Report history (if cloud storage is configured)
        if is_storage_configured():
            render_report_history()
            st.divider()

        # Info
        st.caption("Powered by CrewAI + Financial Modeling Prep")


def main():
    """Main application entry point."""
    init_session_state()

    # Check environment
    missing_keys = load_environment()

    # Header
    st.title(":chart_with_upwards_trend: Investment Research")
    st.markdown("*AI-powered equity research reports*")

    # Show error if missing API keys
    if missing_keys:
        st.error(f"Missing required API keys: {', '.join(missing_keys)}")
        st.info(
            "Please configure your API keys:\n\n"
            "**For local development:** Create a `.env` file with:\n"
            "```\n"
            "FMP_API_KEY=your_fmp_key\n"
            "OPENAI_API_KEY=your_openai_key\n"
            "```\n\n"
            "**For Streamlit Cloud:** Add secrets in the app settings."
        )
        return

    render_sidebar()

    st.divider()

    # Check if there's an ongoing analysis from the progress file
    progress = get_progress()

    # Sync session state with progress file
    if progress:
        if progress.is_running and not progress.is_complete:
            # Analysis is running
            st.session_state.selected_ticker = progress.ticker
            st.session_state.start_analysis = True
            st.session_state.analysis_complete = False
        elif progress.is_complete and not progress.error:
            # Analysis completed successfully
            st.session_state.selected_ticker = progress.ticker
            st.session_state.selected_company = progress.company_name or progress.ticker
            st.session_state.analysis_complete = True
            st.session_state.start_analysis = False

    # Main content - state machine
    ticker = st.session_state.get("selected_ticker")
    start_analysis = st.session_state.get("start_analysis", False)
    analysis_complete = st.session_state.get("analysis_complete", False)

    # State: Analysis complete - show results
    if analysis_complete and ticker:
        company = st.session_state.get("selected_company", "")
        render_results(ticker, company)

    # State: Analysis running
    elif start_analysis and ticker:
        run_analysis(ticker)

    # State: Stock selected but not started
    elif ticker:
        render_selected_stock()

    # State: No stock selected - show search
    else:
        render_search()


def run_analysis(ticker: str):
    """Run the analysis with progress tracking."""
    runner = get_runner()

    # Start the analysis if not already running
    if not runner.is_running and not runner.is_complete:
        runner.start(ticker)
        time.sleep(1)  # Give subprocess time to start

    # Get current progress
    progress = runner.get_progress()

    if progress is None:
        st.warning("Could not get progress state. Starting analysis...")
        runner.start(ticker)
        time.sleep(2)
        st.rerun()
        return

    # Check for completion
    if progress.is_complete:
        if progress.error:
            st.error(f"Analysis failed: {progress.error}")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Try Again", type="primary"):
                    clear_progress()
                    st.session_state.start_analysis = True
                    st.rerun()
            with col2:
                if st.button("Choose Different Stock"):
                    clear_progress()
                    st.session_state.selected_ticker = None
                    st.session_state.start_analysis = False
                    st.rerun()
            return
        else:
            # Success!
            st.session_state.analysis_complete = True
            st.session_state.start_analysis = False
            st.session_state.selected_company = progress.company_name or ticker
            st.rerun()
            return

    # Show progress
    render_progress(progress)

    # Auto-refresh every few seconds
    time.sleep(3)
    st.rerun()


if __name__ == "__main__":
    main()
