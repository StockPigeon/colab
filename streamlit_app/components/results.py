"""Results display component."""

import streamlit as st
from pathlib import Path
import base64


def render_results(ticker: str, company_name: str = ""):
    """Render the analysis results with tabs for different outputs."""

    st.header(f"Research Results: {ticker}")
    if company_name and company_name != ticker:
        st.write(company_name)

    # Define output paths
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
            st.session_state.selected_ticker = None
            st.session_state.selected_company = None
            st.session_state.analysis_complete = False
            st.session_state.start_analysis = False
            st.rerun()

    with col2:
        if st.button("Re-run Analysis", type="secondary"):
            st.session_state.analysis_complete = False
            st.session_state.start_analysis = True
            st.rerun()


def _render_markdown_report(report_path: Path):
    """Render the markdown report."""

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
    """Display PDF with download button and preview."""

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
    """Display generated charts."""

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
    """Check if results files exist for a ticker."""
    report_md = Path(f"{ticker}_report.md")
    return report_md.exists()
