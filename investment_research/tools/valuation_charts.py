"""Valuation Charts Tool - CrewAI tool for generating valuation charts."""

import os
import json
from crewai.tools import tool

from ..helpers.http_client import get_json
from ..charts.valuation_charts import (
    generate_historical_multiple_chart,
    generate_peer_comparison_chart,
    generate_individual_peer_charts,
)


# Map phase to appropriate multiples
PHASE_MULTIPLES = {
    1: [("priceToSalesRatio", "P/S Ratio")],  # Startup - Forward P/S (use trailing as proxy)
    2: [("priceToSalesRatio", "P/S Ratio")],  # Hypergrowth - Forward P/S
    3: [("priceToSalesRatio", "P/S Ratio")],  # Self Funding - Trailing P/S
    4: [("peRatio", "P/E Ratio"), ("pfcfRatio", "P/FCF Ratio")],  # Operating Leverage
    5: [("peRatio", "P/E Ratio"), ("pfcfRatio", "P/FCF Ratio")],  # Capital Return
    6: [("pbRatio", "P/B Ratio")],  # Decline
}


def _fetch_historical_data(symbol: str, api_key: str) -> tuple:
    """Fetch historical metrics and current TTM data."""
    base_v3 = "https://financialmodelingprep.com/api/v3"

    # Historical annual metrics
    hist_response = get_json(
        f"{base_v3}/key-metrics/{symbol}",
        {"period": "annual", "limit": 20, "apikey": api_key}
    )
    historical = hist_response.get("data", []) if hist_response.get("ok") else []

    # Current TTM metrics
    ttm_response = get_json(
        f"{base_v3}/key-metrics-ttm/{symbol}",
        {"apikey": api_key}
    )
    ttm_data = ttm_response.get("data", []) if ttm_response.get("ok") else []
    ttm = ttm_data[0] if ttm_data else {}

    # Profile for company name
    profile_response = get_json(
        f"{base_v3}/profile/{symbol}",
        {"apikey": api_key}
    )
    profile_data = profile_response.get("data", []) if profile_response.get("ok") else []
    profile = profile_data[0] if profile_data else {}

    return historical, ttm, profile


def _fetch_peer_data(symbol: str, api_key: str) -> tuple:
    """Fetch peer list and their metrics."""
    base_v3 = "https://financialmodelingprep.com/api/v3"
    base_v4 = "https://financialmodelingprep.com/api/v4"

    # Get peer list
    peers_response = get_json(
        f"{base_v4}/stock_peers",
        {"symbol": symbol, "apikey": api_key}
    )

    peer_tickers = []
    if peers_response.get("ok"):
        data = peers_response.get("data", [])
        if data and isinstance(data, list) and len(data) > 0:
            peer_tickers = data[0].get("peersList", [])[:8]

    # Fetch metrics for each peer
    peers = []
    for ticker in peer_tickers:
        # Get TTM metrics
        metrics_response = get_json(
            f"{base_v3}/key-metrics-ttm/{ticker}",
            {"apikey": api_key}
        )
        metrics = {}
        if metrics_response.get("ok"):
            metrics_data = metrics_response.get("data", [])
            if metrics_data:
                metrics = metrics_data[0]

        # Get profile
        profile_response = get_json(
            f"{base_v3}/profile/{ticker}",
            {"apikey": api_key}
        )
        name = ticker
        if profile_response.get("ok"):
            profile_data = profile_response.get("data", [])
            if profile_data:
                name = profile_data[0].get("companyName", ticker)

        peers.append({
            "symbol": ticker,
            "name": name,
            "peRatio": metrics.get("peRatioTTM"),
            "pfcfRatio": metrics.get("pfcfRatioTTM"),
            "priceToSalesRatio": metrics.get("priceToSalesRatioTTM"),
            "pbRatio": metrics.get("pbRatioTTM"),
            "evToEbitda": metrics.get("enterpriseValueOverEBITDATTM"),
        })

    return peer_tickers, peers


def _compute_stats(values: list) -> dict:
    """Compute basic statistics for a list of values."""
    valid = [v for v in values if v is not None and v > 0]
    if not valid:
        return {"max": None, "min": None, "median": None}

    import statistics
    return {
        "max": round(max(valid), 2),
        "min": round(min(valid), 2),
        "median": round(statistics.median(valid), 2),
    }


@tool("valuation_chart_tool")
def valuation_chart_tool(symbol: str, phase: int = 5) -> str:
    """
    Generates valuation charts for a company based on its lifecycle phase.

    Creates:
    1. Historical multiple time series charts with max/median/min bands
    2. Combined peer comparison bar chart
    3. Individual peer vs target comparison charts

    The multiples analyzed depend on the business phase:
    - Phase 1-3 (Early stage): P/S Ratio
    - Phase 4-5 (Mature): P/E Ratio, P/FCF Ratio
    - Phase 6 (Decline): P/B Ratio

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL", "MSFT")
        phase: Business lifecycle phase (1-6). Default is 5.

    Returns:
        JSON string with paths to generated charts and summary statistics.
    """
    api_key = os.environ.get("FMP_API_KEY")
    if not api_key:
        return json.dumps({"error": "Missing FMP_API_KEY env var"}, indent=2)

    symbol = (symbol or "").strip().upper()
    if not symbol:
        return json.dumps({"error": "No symbol provided"}, indent=2)

    # Ensure phase is valid
    phase = max(1, min(6, int(phase)))

    # Get multiples to analyze based on phase
    multiples_to_analyze = PHASE_MULTIPLES.get(phase, PHASE_MULTIPLES[5])

    # Fetch data
    historical, ttm, profile = _fetch_historical_data(symbol, api_key)
    peer_tickers, peers = _fetch_peer_data(symbol, api_key)

    company_name = profile.get("companyName", symbol)
    output_dir = "reports/charts"

    charts_generated = {
        "historical": [],
        "peer_comparison": [],
        "individual_peers": [],
    }
    statistics_summary = {}

    for multiple_key, multiple_name in multiples_to_analyze:
        # Extract historical data
        years = []
        values = []
        for record in historical:
            date = record.get("date", "")
            year = date[:4] if date else None
            value = record.get(multiple_key)
            if year and value is not None:
                years.append(year)
                values.append(value)

        # Reverse to chronological order (oldest first)
        years = years[::-1]
        values = values[::-1]

        # Get current TTM value
        ttm_key = f"{multiple_key}TTM"
        current_value = ttm.get(ttm_key) or ttm.get(multiple_key)

        # Compute statistics
        stats = _compute_stats(values)
        statistics_summary[multiple_key] = {
            "name": multiple_name,
            "current": round(current_value, 2) if current_value else None,
            **stats,
            "years_of_data": len([v for v in values if v and v > 0]),
        }

        # Generate historical chart
        if years and values:
            hist_chart_path = generate_historical_multiple_chart(
                symbol=symbol,
                multiple_name=multiple_name,
                years=years,
                values=values,
                current_value=current_value,
                stats=stats,
                output_dir=output_dir,
            )
            if hist_chart_path:
                charts_generated["historical"].append({
                    "multiple": multiple_name,
                    "path": hist_chart_path,
                })

        # Generate peer comparison chart
        target_value = current_value
        if target_value and peers:
            peer_chart_path = generate_peer_comparison_chart(
                target_symbol=symbol,
                target_name=company_name,
                target_value=target_value,
                peers=peers,
                multiple_name=multiple_name,
                multiple_key=multiple_key,
                output_dir=output_dir,
            )
            if peer_chart_path:
                charts_generated["peer_comparison"].append({
                    "multiple": multiple_name,
                    "path": peer_chart_path,
                })

            # Generate individual peer charts
            individual_paths = generate_individual_peer_charts(
                target_symbol=symbol,
                target_value=target_value,
                peers=peers,
                multiple_name=multiple_name,
                multiple_key=multiple_key,
                output_dir=output_dir,
            )
            for path in individual_paths:
                charts_generated["individual_peers"].append({
                    "multiple": multiple_name,
                    "path": path,
                })

    # Calculate peer averages for summary
    peer_summary = []
    for peer in peers:
        peer_summary.append({
            "symbol": peer["symbol"],
            "name": peer["name"],
        })

    output = {
        "symbol": symbol,
        "company_name": company_name,
        "phase": phase,
        "multiples_analyzed": [m[1] for m in multiples_to_analyze],
        "statistics": statistics_summary,
        "peers_analyzed": peer_summary,
        "peer_count": len(peers),
        "charts": charts_generated,
        "chart_count": {
            "historical": len(charts_generated["historical"]),
            "peer_comparison": len(charts_generated["peer_comparison"]),
            "individual_peers": len(charts_generated["individual_peers"]),
        },
    }

    return json.dumps(output, ensure_ascii=False, indent=2, default=str)
