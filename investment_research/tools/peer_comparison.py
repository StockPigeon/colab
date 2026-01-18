"""Peer Comparison Tool - Fetch peer tickers and compare valuation multiples."""

import os
import json
import statistics
from crewai.tools import tool

from ..helpers.http_client import get_json


def _fetch_peer_list(symbol: str, api_key: str) -> list:
    """Fetch peer tickers from FMP stock_peers endpoint."""
    base_v4 = "https://financialmodelingprep.com/api/v4"

    response = get_json(
        f"{base_v4}/stock_peers",
        {"symbol": symbol, "apikey": api_key}
    )

    if not response.get("ok"):
        return []

    data = response.get("data", [])
    if data and isinstance(data, list) and len(data) > 0:
        return data[0].get("peersList", [])

    return []


def _fetch_peer_metrics(symbol: str, api_key: str) -> dict:
    """Fetch TTM metrics for a single peer."""
    base_v3 = "https://financialmodelingprep.com/api/v3"

    # Fetch key metrics TTM
    metrics_response = get_json(
        f"{base_v3}/key-metrics-ttm/{symbol}",
        {"apikey": api_key}
    )

    metrics = {}
    if metrics_response.get("ok"):
        data = metrics_response.get("data", [])
        if data:
            metrics = data[0]

    # Fetch profile for company name
    profile_response = get_json(
        f"{base_v3}/profile/{symbol}",
        {"apikey": api_key}
    )

    company_name = symbol
    market_cap = None
    if profile_response.get("ok"):
        data = profile_response.get("data", [])
        if data:
            company_name = data[0].get("companyName", symbol)
            market_cap = data[0].get("mktCap")

    return {
        "symbol": symbol,
        "company_name": company_name,
        "market_cap": market_cap,
        "peRatioTTM": metrics.get("peRatioTTM"),
        "pfcfRatioTTM": metrics.get("pfcfRatioTTM"),
        "priceToSalesRatioTTM": metrics.get("priceToSalesRatioTTM"),
        "pbRatioTTM": metrics.get("pbRatioTTM"),
        "evToEbitdaTTM": metrics.get("enterpriseValueOverEBITDATTM"),
    }


def _calculate_peer_statistics(peer_data: list, metric_key: str) -> dict:
    """Calculate peer group statistics for a specific metric."""
    values = [p.get(metric_key) for p in peer_data if p.get(metric_key) is not None and p.get(metric_key) > 0]

    if not values:
        return {"average": None, "median": None, "min": None, "max": None, "count": 0}

    return {
        "average": round(statistics.mean(values), 2),
        "median": round(statistics.median(values), 2),
        "min": round(min(values), 2),
        "max": round(max(values), 2),
        "count": len(values),
    }


@tool("peer_comparison_tool")
def peer_comparison_tool(symbol: str) -> str:
    """
    Fetches peer company tickers and their current valuation multiples for comparison.

    Uses FMP's stock_peers endpoint to get comparable companies (same exchange,
    sector, and similar market cap), then fetches TTM multiples for each peer.

    Returns peer group statistics (average, median, min, max) and comparison
    of the target company vs peers.

    Args:
        symbol: The stock ticker symbol (e.g., "AAPL", "MSFT")

    Returns:
        JSON string with peer list, peer multiples, and comparative statistics.
    """
    api_key = os.environ.get("FMP_API_KEY")
    if not api_key:
        return json.dumps({"error": "Missing FMP_API_KEY env var"}, indent=2)

    symbol = (symbol or "").strip().upper()
    if not symbol:
        return json.dumps({"error": "No symbol provided"}, indent=2)

    # Fetch peer list
    peer_tickers = _fetch_peer_list(symbol, api_key)

    # Limit to 8 peers to avoid too many API calls
    peer_tickers = peer_tickers[:8]

    if not peer_tickers:
        return json.dumps({
            "symbol": symbol,
            "error": "No peers found for this company",
            "peers": [],
        }, indent=2)

    # Fetch target company metrics
    target_metrics = _fetch_peer_metrics(symbol, api_key)

    # Fetch metrics for each peer
    peer_data = []
    for peer_ticker in peer_tickers:
        peer_metrics = _fetch_peer_metrics(peer_ticker, api_key)
        peer_data.append(peer_metrics)

    # Calculate peer group statistics for each multiple
    multiples_config = [
        {"key": "peRatioTTM", "name": "P/E Ratio"},
        {"key": "pfcfRatioTTM", "name": "P/FCF Ratio"},
        {"key": "priceToSalesRatioTTM", "name": "P/S Ratio"},
        {"key": "pbRatioTTM", "name": "P/B Ratio"},
        {"key": "evToEbitdaTTM", "name": "EV/EBITDA"},
    ]

    comparisons = {}
    for config in multiples_config:
        key = config["key"]
        name = config["name"]

        peer_stats = _calculate_peer_statistics(peer_data, key)
        target_value = target_metrics.get(key)

        # Calculate premium/discount to peer average
        premium_to_avg = None
        premium_to_median = None
        if target_value and target_value > 0:
            if peer_stats["average"] and peer_stats["average"] > 0:
                premium_to_avg = ((target_value - peer_stats["average"]) / peer_stats["average"]) * 100
            if peer_stats["median"] and peer_stats["median"] > 0:
                premium_to_median = ((target_value - peer_stats["median"]) / peer_stats["median"]) * 100

        comparisons[key] = {
            "name": name,
            "target_value": round(target_value, 2) if target_value else None,
            "peer_average": peer_stats["average"],
            "peer_median": peer_stats["median"],
            "peer_min": peer_stats["min"],
            "peer_max": peer_stats["max"],
            "peer_count": peer_stats["count"],
            "premium_to_avg_pct": round(premium_to_avg, 1) if premium_to_avg is not None else None,
            "premium_to_median_pct": round(premium_to_median, 1) if premium_to_median is not None else None,
        }

    output = {
        "symbol": symbol,
        "target_company": {
            "name": target_metrics.get("company_name", symbol),
            "market_cap": target_metrics.get("market_cap"),
            "multiples": {
                "peRatio": target_metrics.get("peRatioTTM"),
                "pfcfRatio": target_metrics.get("pfcfRatioTTM"),
                "priceToSalesRatio": target_metrics.get("priceToSalesRatioTTM"),
                "pbRatio": target_metrics.get("pbRatioTTM"),
                "evToEbitda": target_metrics.get("evToEbitdaTTM"),
            }
        },
        "peers": [
            {
                "symbol": p["symbol"],
                "name": p["company_name"],
                "market_cap": p["market_cap"],
                "peRatio": round(p["peRatioTTM"], 2) if p.get("peRatioTTM") else None,
                "pfcfRatio": round(p["pfcfRatioTTM"], 2) if p.get("pfcfRatioTTM") else None,
                "priceToSalesRatio": round(p["priceToSalesRatioTTM"], 2) if p.get("priceToSalesRatioTTM") else None,
                "pbRatio": round(p["pbRatioTTM"], 2) if p.get("pbRatioTTM") else None,
                "evToEbitda": round(p["evToEbitdaTTM"], 2) if p.get("evToEbitdaTTM") else None,
            }
            for p in peer_data
        ],
        "comparisons": comparisons,
        "peer_count": len(peer_data),
    }

    return json.dumps(output, ensure_ascii=False, indent=2, default=str)
