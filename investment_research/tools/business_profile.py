"""Business Profile Tool - Business model analysis data."""

import os
import json
from crewai.tools import tool

from ..helpers.http_client import get_json
from ..helpers.fmp_api import get_latest_transcript
from ..helpers.classification import get_purchase_frequency_hint, get_recession_sensitivity_hint


@tool("business_profile_tool")
def business_profile_tool(symbol: str) -> str:
    """
    Fetches business profile data for completing a business analysis table:
    - Company description and business model
    - Product/service segments and revenue breakdown
    - Geographic revenue segmentation
    - Industry/sector classification for recession sensitivity
    - Margin data for pricing power analysis

    Args:
        symbol: The stock ticker symbol (e.g., "AAPL", "MSFT")

    Returns:
        JSON string with business profile data including segments and classification hints.
    """
    api_key = os.environ.get("FMP_API_KEY")
    if not api_key:
        return json.dumps({"error": "Missing FMP_API_KEY env var"}, indent=2)

    symbol = (symbol or "").strip().upper()
    if not symbol:
        return json.dumps({"error": "No symbol provided"}, indent=2)

    base_v3 = "https://financialmodelingprep.com/api/v3"
    base_v4 = "https://financialmodelingprep.com/api/v4"

    # Get company profile (description, sector, industry, country, business summary)
    profile_resp = get_json(f"{base_v3}/profile/{symbol}", {"apikey": api_key})
    profile_data = profile_resp.get("data") if profile_resp.get("ok") else None
    profile_info = {}
    if isinstance(profile_data, list) and profile_data:
        p = profile_data[0]
        profile_info = {
            "companyName": p.get("companyName"),
            "description": p.get("description"),
            "sector": p.get("sector"),
            "industry": p.get("industry"),
            "country": p.get("country"),
            "website": p.get("website"),
            "fullTimeEmployees": p.get("fullTimeEmployees"),
            "ipoDate": p.get("ipoDate"),
        }

    # Get revenue by product/service segment (premium endpoint)
    product_seg_resp = get_json(
        f"{base_v4}/revenue-product-segmentation",
        {"symbol": symbol, "structure": "flat", "period": "annual", "apikey": api_key}
    )
    product_segments = []
    if product_seg_resp.get("ok"):
        seg_data = product_seg_resp.get("data")
        if isinstance(seg_data, list) and seg_data:
            # Get most recent period
            latest = seg_data[0] if seg_data else {}
            for key, val in latest.items():
                if key not in ("date", "symbol", "reportedCurrency", "period"):
                    product_segments.append({"segment": key, "revenue": val})

    # Get revenue by geographic segment (premium endpoint)
    geo_seg_resp = get_json(
        f"{base_v4}/revenue-geographic-segmentation",
        {"symbol": symbol, "structure": "flat", "period": "annual", "apikey": api_key}
    )
    geo_segments = []
    if geo_seg_resp.get("ok"):
        seg_data = geo_seg_resp.get("data")
        if isinstance(seg_data, list) and seg_data:
            latest = seg_data[0] if seg_data else {}
            for key, val in latest.items():
                if key not in ("date", "symbol", "reportedCurrency", "period"):
                    geo_segments.append({"region": key, "revenue": val})

    # Get financial ratios for pricing power analysis
    ratios_resp = get_json(f"{base_v3}/ratios-ttm/{symbol}", {"apikey": api_key})
    ratios_data = ratios_resp.get("data") if ratios_resp.get("ok") else None
    pricing_power_metrics = {}
    if isinstance(ratios_data, list) and ratios_data:
        r = ratios_data[0]
        pricing_power_metrics = {
            "grossProfitMarginTTM": r.get("grossProfitMarginTTM"),
            "operatingProfitMarginTTM": r.get("operatingProfitMarginTTM"),
            "netProfitMarginTTM": r.get("netProfitMarginTTM"),
            "returnOnEquityTTM": r.get("returnOnEquityTTM"),
            "returnOnAssetsTTM": r.get("returnOnAssetsTTM"),
        }

    # Get income statement for revenue trends
    inc_resp = get_json(
        f"{base_v3}/income-statement/{symbol}",
        {"period": "annual", "limit": 3, "apikey": api_key}
    )
    inc_data = inc_resp.get("data") if inc_resp.get("ok") else None
    revenue_history = []
    if isinstance(inc_data, list):
        for stmt in inc_data:
            revenue_history.append({
                "year": stmt.get("calendarYear"),
                "revenue": stmt.get("revenue"),
                "grossProfit": stmt.get("grossProfit"),
                "operatingIncome": stmt.get("operatingIncome"),
            })

    # Get earnings transcript for qualitative context
    transcript_obj = get_latest_transcript(symbol, api_key)

    # Sector-based heuristics for classification guidance
    sector = profile_info.get("sector", "").lower()
    industry = profile_info.get("industry", "").lower()

    classification_hints = {
        "purchase_frequency_hint": get_purchase_frequency_hint(sector, industry),
        "recession_sensitivity_hint": get_recession_sensitivity_hint(sector, industry),
    }

    out = {
        "symbol": symbol,
        "profile": profile_info,
        "product_segments": product_segments,
        "geographic_segments": geo_segments,
        "pricing_power_metrics": pricing_power_metrics,
        "revenue_history": revenue_history,
        "transcript_excerpt": transcript_obj.get("excerpt", "")[:4000] if transcript_obj.get("available") else None,
        "classification_hints": classification_hints,
        "debug": {
            "profile_url": profile_resp.get("url"),
            "product_seg_url": product_seg_resp.get("url"),
            "geo_seg_url": geo_seg_resp.get("url"),
            "ratios_url": ratios_resp.get("url"),
        }
    }
    return json.dumps(out, ensure_ascii=False, indent=2)
