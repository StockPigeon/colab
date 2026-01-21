"""Results display component.

Displays analysis results from either local files or cloud storage (Supabase).
"""

import streamlit as st
from pathlib import Path
import base64
from typing import Optional

import requests

from streamlit_app.services.storage import get_storage_service, ReportMetadata


def render_results(ticker: str, company_name: str = "", report_id: Optional[str] = None):
    """
    Render the analysis results with tabs for different outputs.

    Args:
        ticker: Stock ticker symbol
        company_name: Company name for display
        report_id: Optional report ID to load from cloud storage
    """
    st.header(f"Research Results: {ticker}")
    if company_name and company_name != ticker:
        st.write(company_name)

    # Check if we're loading from cloud storage
    report_metadata = None
    if report_id is None:
        # Check session state for report_id
        report_id = st.session_state.get("view_report_id")

    if report_id:
        storage = get_storage_service()
        if storage:
            try:
                report_metadata = storage.get_report_by_id(report_id)
            except Exception:
                pass

    # Define local output paths as fallback
    report_md = Path(f"{ticker}_report.md")
    equity_pdf = Path(f"{ticker}_equity_research.pdf")
    memo_pdf = Path(f"{ticker}_investment_memo.pdf")
    charts_dir = Path("reports/charts")

    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "Report",
        "Equity Research PDF",
        "Investment Memo PDF",
        "Charts"
    ])

    if report_metadata:
        # Load from cloud storage
        with tab1:
            _render_markdown_from_url(report_metadata.markdown_url, ticker)

        with tab2:
            _render_pdf_from_url(report_metadata.equity_pdf_url, "equity_research")

        with tab3:
            _render_pdf_from_url(report_metadata.memo_pdf_url, "investment_memo")

        with tab4:
            _render_charts_from_storage(ticker, report_metadata.storage_path)
    else:
        # Load from local files
        with tab1:
            _render_markdown_report(report_md)

        with tab2:
            _render_pdf(equity_pdf, "equity_research")

        with tab3:
            _render_pdf(memo_pdf, "investment_memo")

        with tab4:
            _render_charts(ticker, charts_dir)

    # Action buttons
    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Analyze Another Stock", type="primary"):
            _clear_session_state()
            st.rerun()

    with col2:
        if st.button("Re-run Analysis", type="secondary"):
            st.session_state.analysis_complete = False
            st.session_state.start_analysis = True
            st.session_state.pop("view_report_id", None)
            st.rerun()


def _clear_session_state():
    """Clear session state for a fresh start."""
    st.session_state.selected_ticker = None
    st.session_state.selected_company = None
    st.session_state.analysis_complete = False
    st.session_state.start_analysis = False
    st.session_state.pop("view_report_id", None)


def _render_markdown_from_url(url: Optional[str], ticker: str):
    """Render markdown content fetched from URL."""
    if not url:
        st.warning("Markdown report not available in cloud storage.")
        # Try local fallback
        local_path = Path(f"{ticker}_report.md")
        if local_path.exists():
            _render_markdown_report(local_path)
        return

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        content = response.text

        # Download button
        st.download_button(
            label="Download Markdown",
            data=content,
            file_name=f"{ticker}_report.md",
            mime="text/markdown",
        )

        # Display content
        st.markdown(content)

    except Exception as e:
        st.error(f"Could not load report from cloud: {e}")
        # Try local fallback
        local_path = Path(f"{ticker}_report.md")
        if local_path.exists():
            st.info("Loading from local cache...")
            _render_markdown_report(local_path)


def _render_pdf_from_url(url: Optional[str], key: str):
    """Display PDF fetched from URL with download button and preview."""
    if not url:
        st.warning("PDF not available in cloud storage.")
        return

    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        pdf_bytes = response.content

        # Extract filename from key
        filename = f"{key}.pdf"

        # Download button
        st.download_button(
            label="Download PDF",
            data=pdf_bytes,
            file_name=filename,
            mime="application/pdf",
            key=f"download_{key}_cloud"
        )

        # Embed PDF preview
        base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
        pdf_display = f'''
        <iframe
            src="data:application/pdf;base64,{base64_pdf}"
            width="100%"
            height="800"
            type="application/pdf"
            style="border: 1px solid #ddd; border-radius: 4px;">
        </iframe>
        '''
        st.markdown(pdf_display, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Could not load PDF from cloud: {e}")


def _render_charts_from_storage(ticker: str, storage_path: str):
    """Display charts from cloud storage."""
    storage = get_storage_service()

    if not storage:
        st.info("Cloud storage not configured.")
        return

    try:
        chart_urls = storage.get_chart_urls(storage_path)

        if not chart_urls:
            st.info(f"No charts found for {ticker} in cloud storage.")
            # Try local fallback
            _render_charts(ticker, Path("reports/charts"))
            return

        st.write(f"**{len(chart_urls)} chart(s):**")

        for url in chart_urls:
            # Extract filename from URL
            filename = url.split("/")[-1]
            caption = filename.replace(".png", "").replace("_", " ").replace(ticker, "").strip()

            st.image(url, caption=caption, use_container_width=True)

            # Download button
            try:
                response = requests.get(url, timeout=30)
                if response.ok:
                    st.download_button(
                        label=f"Download {filename}",
                        data=response.content,
                        file_name=filename,
                        mime="image/png",
                        key=f"download_chart_{filename}"
                    )
            except Exception:
                pass

    except Exception as e:
        st.error(f"Error loading charts: {e}")
        # Try local fallback
        _render_charts(ticker, Path("reports/charts"))


def _render_markdown_report(report_path: Path):
    """Render the markdown report from local file."""
    if not report_path.exists():
        st.warning("Markdown report not found.")
        st.info(f"Expected path: {report_path}")
        return

    content = report_path.read_text(encoding="utf-8")

    # Download button
    st.download_button(
        label="Download Markdown",
        data=content,
        file_name=report_path.name,
        mime="text/markdown",
    )

    # Display content
    st.markdown(content)


def _render_pdf(pdf_path: Path, key: str):
    """Display PDF with download button and preview from local file."""
    if not pdf_path.exists():
        st.warning(f"PDF not found: {pdf_path.name}")
        st.info("PDF generation may have failed. Check the markdown report for the analysis content.")
        return

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    # Download button
    st.download_button(
        label="Download PDF",
        data=pdf_bytes,
        file_name=pdf_path.name,
        mime="application/pdf",
        key=f"download_{key}"
    )

    # Try to embed PDF preview
    try:
        base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
        pdf_display = f'''
        <iframe
            src="data:application/pdf;base64,{base64_pdf}"
            width="100%"
            height="800"
            type="application/pdf"
            style="border: 1px solid #ddd; border-radius: 4px;">
        </iframe>
        '''
        st.markdown(pdf_display, unsafe_allow_html=True)
    except Exception:
        st.info("PDF preview not available. Please download to view.")


def _render_charts(ticker: str, charts_dir: Path):
    """Display generated charts from local files."""
    if not charts_dir.exists():
        st.info("No charts directory found.")
        return

    # Find all charts for this ticker
    chart_patterns = [
        f"{ticker}*.png",
        f"{ticker.lower()}*.png",
    ]

    chart_files = []
    for pattern in chart_patterns:
        chart_files.extend(charts_dir.glob(pattern))

    # Remove duplicates
    chart_files = list(set(chart_files))

    if not chart_files:
        st.info(f"No charts found for {ticker}.")
        st.caption(f"Looked in: {charts_dir}")
        return

    st.write(f"**{len(chart_files)} chart(s) generated:**")

    # Display charts
    for chart_file in sorted(chart_files):
        st.image(
            str(chart_file),
            caption=chart_file.stem.replace("_", " ").replace(ticker, "").strip(),
            use_container_width=True
        )

        # Download button for each chart
        with open(chart_file, "rb") as f:
            st.download_button(
                label=f"Download {chart_file.name}",
                data=f.read(),
                file_name=chart_file.name,
                mime="image/png",
                key=f"download_chart_{chart_file.name}"
            )


def check_results_exist(ticker: str) -> bool:
    """Check if results files exist for a ticker (local or cloud)."""
    # Check local first
    report_md = Path(f"{ticker}_report.md")
    if report_md.exists():
        return True

    # Check cloud storage
    storage = get_storage_service()
    if storage:
        try:
            reports = storage.get_reports_for_ticker(ticker)
            return len(reports) > 0
        except Exception:
            pass

    return False
