"""Historical Multiples Tool - Fetch 10-20 years of valuation multiples with statistics."""

import os
import json
import statistics
from crewai.tools import tool

from ..helpers.http_client import get_json


def _calculate_percentile(value: float, sorted_values: list) -> float:
    """Calculate what percentile the value falls into within the sorted list."""
    if not sorted_values or value is None:
        return None
    count_below = sum(1 for v in sorted_values if v < value)
    return (count_below / len(sorted_values)) * 100


def _filter_outliers(values: list, max_std_dev: float = 3.0) -> list:
    """Filter extreme outliers beyond max_std_dev standard deviations."""
    if len(values) < 3:
        return values

    mean = statistics.mean(values)
    std_dev = statistics.stdev(values)

    if std_dev == 0:
        return values

    return [v for v in values if abs(v - mean) <= max_std_dev * std_dev]


def _compute_statistics(values: list, current_value: float = None) -> dict:
    """Compute statistics for a list of values."""
    # Filter out None and negative values (invalid for most multiples)
    valid_values = [v for v in values if v is not None and v > 0]

    if not valid_values:
        return {
            "count": 0,
            "max": None,
            "min": None,
            "median": None,
            "mean": None,
            "current": current_value,
            "current_percentile": None,
            "vs_median_pct": None,
        }

    # Filter outliers for statistics calculation
    filtered_values = _filter_outliers(valid_values)
    sorted_values = sorted(filtered_values)

    max_val = max(filtered_values)
    min_val = min(filtered_values)
    median_val = statistics.median(filtered_values)
    mean_val = statistics.mean(filtered_values)

    current_percentile = None
    vs_median_pct = None

    if current_value is not None and current_value > 0:
        current_percentile = _calculate_percentile(current_value, sorted_values)
        if median_val and median_val > 0:
            vs_median_pct = ((current_value - median_val) / median_val) * 100

    return {
        "count": len(filtered_values),
        "max": round(max_val, 2),
        "min": round(min_val, 2),
        "median": round(median_val, 2),
        "mean": round(mean_val, 2),
        "current": round(current_value, 2) if current_value else None,
        "current_percentile": round(current_percentile, 1) if current_percentile is not None else None,
        "vs_median_pct": round(vs_median_pct, 1) if vs_median_pct is not None else None,
    }


def _fetch_historical_metrics(symbol: str, api_key: str, limit: int = 20) -> list:
    """Fetch historical annual key metrics from FMP."""
    base_v3 = "https://financialmodelingprep.com/api/v3"

    response = get_json(
        f"{base_v3}/key-metrics/{symbol}",
        {"period": "annual", "limit": limit, "apikey": api_key}
    )

    if not response.get("ok"):
        return []

    return response.get("data", [])


def _fetch_current_metrics(symbol: str, api_key: str) -> dict:
    """Fetch current TTM metrics."""
    base_v3 = "https://financialmodelingprep.com/api/v3"

    response = get_json(
        f"{base_v3}/key-metrics-ttm/{symbol}",
        {"apikey": api_key}
    )

    if not response.get("ok"):
        return {}

    data = response.get("data", [])
    return data[0] if data else {}


def _fetch_quote(symbol: str, api_key: str) -> dict:
    """Fetch current quote for market cap and price."""
    base_v3 = "https://financialmodelingprep.com/api/v3"

    response = get_json(
        f"{base_v3}/quote/{symbol}",
        {"apikey": api_key}
    )

    if not response.get("ok"):
        return {}

    data = response.get("data", [])
    return data[0] if data else {}


def _fetch_analyst_estimates(symbol: str, api_key: str) -> dict:
    """Fetch analyst estimates for forward multiples calculation."""
    base_v3 = "https://financialmodelingprep.com/api/v3"

    response = get_json(
        f"{base_v3}/analyst-estimates/{symbol}",
        {"limit": 1, "apikey": api_key}
    )

    if not response.get("ok"):
        return {}

    data = response.get("data", [])
    return data[0] if data else {}


@tool("historical_multiples_tool")
def historical_multiples_tool(symbol: str) -> str:
    """
    Fetches 10-20 years of historical valuation multiples for a company and calculates
    statistics including max, min, median, mean, and current percentile.

    Multiples returned:
    - P/E Ratio (peRatio)
    - P/FCF Ratio (pfcfRatio)
    - P/S Ratio (priceToSalesRatio)
    - P/B Ratio (pbRatio)
    - EV/EBITDA (enterpriseValueOverEBITDA)

    Also calculates forward multiples:
    - Forward P/S = Market Cap / Estimated Revenue
    - Forward P/E = Price / Estimated EPS

    Args:
        symbol: The stock ticker symbol (e.g., "AAPL", "MSFT")

    Returns:
        JSON string with historical multiples data, statistics, and forward multiples.
    """
    api_key = os.environ.get("FMP_API_KEY")
    if not api_key:
        return json.dumps({"error": "Missing FMP_API_KEY env var"}, indent=2)

    symbol = (symbol or "").strip().upper()
    if not symbol:
        return json.dumps({"error": "No symbol provided"}, indent=2)

    # Fetch all required data
    historical_data = _fetch_historical_metrics(symbol, api_key, limit=20)
    current_ttm = _fetch_current_metrics(symbol, api_key)
    quote = _fetch_quote(symbol, api_key)
    estimates = _fetch_analyst_estimates(symbol, api_key)

    # Extract historical values by multiple type
    multiples_config = {
        "peRatio": {"name": "P/E Ratio", "field": "peRatio"},
        "pfcfRatio": {"name": "P/FCF Ratio", "field": "pfcfRatio"},
        "priceToSalesRatio": {"name": "P/S Ratio", "field": "priceToSalesRatio"},
        "pbRatio": {"name": "P/B Ratio", "field": "pbRatio"},
        "evToEbitda": {"name": "EV/EBITDA", "field": "enterpriseValueOverEBITDA"},
    }

    # Build historical time series and statistics for each multiple
    multiples_analysis = {}

    for key, config in multiples_config.items():
        field = config["field"]
        name = config["name"]

        # Extract historical values with dates
        historical_series = []
        historical_values = []

        for record in historical_data:
            value = record.get(field)
            date = record.get("date", "")
            year = date[:4] if date else None

            if value is not None and value > 0:
                historical_series.append({
                    "year": year,
                    "date": date,
                    "value": round(value, 2)
                })
                historical_values.append(value)

        # Get current TTM value
        current_value = current_ttm.get(f"{field}TTM") or current_ttm.get(field)

        # Calculate statistics
        stats = _compute_statistics(historical_values, current_value)

        multiples_analysis[key] = {
            "name": name,
            "historical_series": historical_series,
            "statistics": stats,
            "years_of_data": len(historical_series),
        }

    # Calculate forward multiples
    market_cap = quote.get("marketCap")
    price = quote.get("price")
    estimated_revenue = estimates.get("estimatedRevenueAvg")
    estimated_eps = estimates.get("estimatedEpsAvg")

    forward_multiples = {}

    # Forward P/S
    if market_cap and estimated_revenue and estimated_revenue > 0:
        forward_ps = market_cap / estimated_revenue
        forward_multiples["forwardPS"] = {
            "name": "Forward P/S",
            "value": round(forward_ps, 2),
            "market_cap": market_cap,
            "estimated_revenue": estimated_revenue,
        }

    # Forward P/E
    if price and estimated_eps and estimated_eps > 0:
        forward_pe = price / estimated_eps
        forward_multiples["forwardPE"] = {
            "name": "Forward P/E",
            "value": round(forward_pe, 2),
            "price": price,
            "estimated_eps": round(estimated_eps, 2),
        }

    output = {
        "symbol": symbol,
        "company_name": quote.get("name", symbol),
        "current_price": quote.get("price"),
        "market_cap": market_cap,
        "multiples": multiples_analysis,
        "forward_multiples": forward_multiples,
        "data_summary": {
            "years_available": len(historical_data),
            "has_analyst_estimates": bool(estimates),
        }
    }

    return json.dumps(output, ensure_ascii=False, indent=2, default=str)
