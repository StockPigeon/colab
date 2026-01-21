"""Progress display component."""

import streamlit as st
from streamlit_app.services.research_runner import ProgressState


def render_progress(progress: ProgressState):
    """Render the progress indicator."""

    st.subheader(f"Analyzing {progress.ticker}...")

    # Overall progress bar
    progress_pct = progress.progress_percent / 100
    st.progress(progress_pct, text=f"{int(progress.progress_percent)}% Complete")

    # Current task indicator
    current = progress.current_task
    if current:
        st.info(f"**Currently:** {current.display_name}")

    # Error display
    if progress.error:
        st.error(f"Error: {progress.error}")
        return

    # Task checklist
    st.write("**Progress:**")

    for task in progress.tasks:
        if task.status == "completed":
            icon = ":white_check_mark:"
            status_text = "Done"
        elif task.status == "in_progress":
            icon = ":hourglass_flowing_sand:"
            status_text = "Working..."
        elif task.status == "error":
            icon = ":x:"
            status_text = "Error"
        else:
            icon = ":white_circle:"
            status_text = "Pending"

        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(f"{icon} {task.display_name}")
        with col2:
            st.caption(status_text)

    # Estimated time remaining
    if progress.is_running and not progress.is_complete:
        remaining = progress.total_tasks - progress.completed_count
        st.caption(f"Approximately {remaining} {'step' if remaining == 1 else 'steps'} remaining...")


def render_analysis_running():
    """Render a simple 'analysis running' indicator when we can't get detailed progress."""

    st.subheader("Analysis in Progress...")

    # Indeterminate progress (show partial progress bar)
    st.progress(0.1, text="Running AI agents...")

    st.info(
        "The AI agents are analyzing the stock. This typically takes 5-10 minutes.\n\n"
        "**Please keep this page open.**"
    )

    with st.expander("What's happening?"):
        st.write("""
        Our AI agents are performing comprehensive research:

        1. **Sentiment Analysis** - Analyzing price trends and market sentiment
        2. **Business Phase** - Classifying the company's growth stage
        3. **Key Metrics** - Evaluating financial health indicators
        4. **Business Profile** - Understanding the business model
        5. **Moat Analysis** - Identifying competitive advantages
        6. **Risk Assessment** - Evaluating execution and management risks
        7. **Growth Drivers** - Finding catalysts for future growth
        8. **Valuation** - Calculating fair value estimates
        9. **Final Scorecard** - Generating investment recommendation

        Each step involves querying financial databases, reading SEC filings,
        and using AI to synthesize insights.
        """)
