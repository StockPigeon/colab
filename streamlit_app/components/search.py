"""Stock search component."""

import streamlit as st
from ..services.stock_search import search_stocks, validate_ticker


def render_search():
    """Render the stock search interface."""

    st.subheader("Search for a Stock")

    # Search input
    search_query = st.text_input(
        "Enter company name or ticker symbol",
        placeholder="e.g., Apple, AAPL, Microsoft, MSFT",
        key="search_input",
        help="Search by company name (like 'Apple') or ticker symbol (like 'AAPL')"
    )

    # Search results
    if search_query and len(search_query) >= 2:
        with st.spinner("Searching..."):
            results = search_stocks(search_query, limit=8)

        if results:
            st.write("**Select a stock:**")

            for result in results:
                symbol = result.get("symbol", "")
                name = result.get("name", "Unknown")
                exchange = result.get("exchange", "")

                col1, col2, col3 = st.columns([1, 3, 1])

                with col1:
                    st.markdown(f"**{symbol}**")

                with col2:
                    st.write(f"{name}")
                    if exchange:
                        st.caption(exchange)

                with col3:
                    if st.button("Select", key=f"select_{symbol}", type="secondary"):
                        st.session_state.selected_ticker = symbol
                        st.session_state.selected_company = name
                        st.rerun()

        elif search_query:
            st.info("No results found. Try a different search term or enter a ticker symbol directly.")

            # Allow direct ticker input
            st.write("**Or enter a ticker directly:**")
            direct_ticker = st.text_input(
                "Ticker symbol",
                placeholder="e.g., AAPL",
                key="direct_ticker_input"
            )

            if direct_ticker:
                if st.button("Use this ticker", type="secondary"):
                    ticker = direct_ticker.strip().upper()
                    validation = validate_ticker(ticker)
                    if validation.get("valid"):
                        st.session_state.selected_ticker = validation.get("symbol")
                        st.session_state.selected_company = validation.get("name", ticker)
                        st.rerun()
                    else:
                        st.error(f"Could not validate ticker: {validation.get('error', 'Unknown error')}")


def render_selected_stock():
    """Render the selected stock card with generate button."""

    ticker = st.session_state.get("selected_ticker")
    company = st.session_state.get("selected_company", "")

    if not ticker:
        return False

    st.divider()

    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown(f"### Selected: **{ticker}**")
        if company:
            st.write(company)

    with col2:
        if st.button("Change", type="secondary"):
            st.session_state.selected_ticker = None
            st.session_state.selected_company = None
            st.rerun()

    st.divider()

    # Generate button
    if st.button(
        "Generate Research Report",
        type="primary",
        use_container_width=True,
        help="This will take 5-10 minutes. Keep this page open."
    ):
        st.session_state.start_analysis = True
        st.rerun()

    st.caption("Analysis typically takes 5-10 minutes. Please keep this page open.")

    return True
