"""Historical reports browser component.

Displays a list of previously generated reports from cloud storage,
allowing users to browse and view reports created by colleagues.
"""

import streamlit as st
from datetime import datetime
from typing import List, Dict

from streamlit_app.services.storage import (
    get_storage_service,
    is_storage_configured,
    ReportMetadata,
)


def render_report_history() -> None:
    """
    Render the historical reports browser in the sidebar.

    Shows recent reports grouped by ticker with the ability to
    click and view any previous report.
    """
    storage = get_storage_service()

    if not storage:
        return

    st.subheader("Previous Reports")

    try:
        reports = storage.get_recent_reports(limit=20)

        if not reports:
            st.caption("No previous reports found.")
            return

        # Group reports by ticker
        by_ticker: Dict[str, List[ReportMetadata]] = {}
        for report in reports:
            if report.ticker not in by_ticker:
                by_ticker[report.ticker] = []
            by_ticker[report.ticker].append(report)

        # Display grouped by ticker
        for ticker, ticker_reports in by_ticker.items():
            with st.expander(f"{ticker} ({len(ticker_reports)})", expanded=False):
                for report in ticker_reports:
                    _render_report_item(report)

    except Exception as e:
        st.caption(f"Could not load history: {str(e)[:50]}")


def _render_report_item(report: ReportMetadata) -> None:
    """Render a single report item with view button."""
    col1, col2 = st.columns([3, 1])

    with col1:
        # Format date nicely
        date_str = report.created_at.strftime("%b %d, %Y")
        time_str = report.created_at.strftime("%H:%M")

        company_display = report.company_name or report.ticker
        if len(company_display) > 20:
            company_display = company_display[:17] + "..."

        st.caption(f"{company_display}")
        st.caption(f"{date_str} {time_str}")

    with col2:
        if st.button("View", key=f"view_{report.id}", use_container_width=True):
            # Set session state to view this report
            st.session_state.view_report_id = report.id
            st.session_state.selected_ticker = report.ticker
            st.session_state.selected_company = report.company_name or report.ticker
            st.session_state.analysis_complete = True
            st.session_state.start_analysis = False
            st.rerun()


def render_report_history_main() -> None:
    """
    Render a full-page historical reports browser.

    Alternative to sidebar view for browsing all reports.
    """
    st.header("Report History")

    storage = get_storage_service()

    if not storage:
        st.warning("Cloud storage is not configured.")
        st.info(
            "To enable report history, set the following environment variables:\n\n"
            "- `SUPABASE_URL`: Your Supabase project URL\n"
            "- `SUPABASE_KEY`: Your Supabase anon/public key"
        )
        return

    # Search/filter options
    col1, col2 = st.columns([2, 1])
    with col1:
        ticker_filter = st.text_input(
            "Filter by ticker",
            placeholder="e.g., AAPL",
            key="history_ticker_filter"
        ).strip().upper()
    with col2:
        limit = st.selectbox("Show", [10, 20, 50], index=1, key="history_limit")

    try:
        if ticker_filter:
            reports = storage.get_reports_for_ticker(ticker_filter)
        else:
            reports = storage.get_recent_reports(limit=limit)

        if not reports:
            if ticker_filter:
                st.info(f"No reports found for {ticker_filter}")
            else:
                st.info("No reports found. Generate your first report!")
            return

        # Display as a table-like list
        for report in reports:
            with st.container():
                col1, col2, col3, col4 = st.columns([2, 3, 2, 1])

                with col1:
                    st.write(f"**{report.ticker}**")

                with col2:
                    company = report.company_name or "-"
                    if len(company) > 30:
                        company = company[:27] + "..."
                    st.write(company)

                with col3:
                    st.write(report.created_at.strftime("%Y-%m-%d %H:%M"))

                with col4:
                    if st.button("View", key=f"main_view_{report.id}"):
                        st.session_state.view_report_id = report.id
                        st.session_state.selected_ticker = report.ticker
                        st.session_state.selected_company = report.company_name
                        st.session_state.analysis_complete = True
                        st.session_state.start_analysis = False
                        st.rerun()

                st.divider()

    except Exception as e:
        st.error(f"Error loading reports: {e}")
