"""Investment Data Tool - Comprehensive financial data for analysis."""

import os
import json
from crewai.tools import tool

from ..helpers.http_client import get_json
from ..helpers.fmp_api import pick_latest_filing, get_latest_transcript
from ..helpers.business_phase import compute_business_phase


@tool("investment_data_tool")
def investment_data_tool(symbol: str) -> str:
    """
    Fetches comprehensive data for a ticker from FMP API:
    - Earnings transcript (Qualitative)
    - SEC filing links (10-K, 10-Q, Proxy)
    - Key TTM metrics
    - Financial growth data
    - Income statement + cash flow (for business phase)

    Args:
        symbol: The stock ticker symbol (e.g., "AAPL", "MSFT")

    Returns:
        JSON string with comprehensive investment data including business phase classification.
    """
    api_key = os.environ.get("FMP_API_KEY")
    if not api_key:
        return json.dumps({"error": "Missing FMP_API_KEY env var"}, indent=2)

    symbol = (symbol or "").strip().upper()
    if not symbol:
        return json.dumps({"error": "No symbol provided"}, indent=2)

    base_v3 = "https://financialmodelingprep.com/api/v3"

    transcript_obj = get_latest_transcript(symbol, api_key)

    profile_resp = get_json(f"{base_v3}/profile/{symbol}", {"apikey": api_key})
    profile_data = profile_resp.get("data") if profile_resp.get("ok") else None
    company_name = None
    if isinstance(profile_data, list) and profile_data:
        company_name = profile_data[0].get("companyName")

    filings_resp = get_json(f"{base_v3}/sec_filings/{symbol}", {"limit": 25, "apikey": api_key})
    filings_data = filings_resp.get("data") if filings_resp.get("ok") else None

    sec_links = []
    latest_filing = None
    if isinstance(filings_data, list):
        for f in filings_data[:8]:
            ftype = f.get("type") or f.get("formType") or "Unknown"
            link = f.get("finalLink") or f.get("link") or f.get("url")
            if link:
                sec_links.append(f"{ftype}: {link}")
        latest_filing = pick_latest_filing(filings_data)

    latest_sec_url = None
    latest_sec_label = None
    latest_sec_date = None
    if latest_filing:
        latest_sec_label = latest_filing.get("type") or latest_filing.get("formType")
        latest_sec_date = latest_filing.get("fillingDate") or latest_filing.get("filingDate")
        latest_sec_url = latest_filing.get("finalLink") or latest_filing.get("link") or latest_filing.get("url")

    metrics_resp = get_json(f"{base_v3}/key-metrics-ttm/{symbol}", {"apikey": api_key})
    metrics_data = metrics_resp.get("data") if metrics_resp.get("ok") else None
    metrics = metrics_data[0] if isinstance(metrics_data, list) and metrics_data else None

    growth_resp = get_json(f"{base_v3}/financial-growth/{symbol}", {"limit": 1, "apikey": api_key})
    growth_data = growth_resp.get("data") if growth_resp.get("ok") else None
    growth = growth_data[0] if isinstance(growth_data, list) and growth_data else None

    inc_resp = get_json(
        f"{base_v3}/income-statement/{symbol}",
        {"period": "annual", "limit": 2, "apikey": api_key},
    )
    inc_data = inc_resp.get("data") if inc_resp.get("ok") else None

    cf_resp = get_json(
        f"{base_v3}/cash-flow-statement/{symbol}",
        {"period": "annual", "limit": 1, "apikey": api_key},
    )
    cf_data = cf_resp.get("data") if cf_resp.get("ok") else None

    revenue_current = revenue_prior = None
    op_income_current = op_income_prior = None

    if isinstance(inc_data, list) and len(inc_data) >= 1:
        revenue_current = inc_data[0].get("revenue")
        op_income_current = inc_data[0].get("operatingIncome")
    if isinstance(inc_data, list) and len(inc_data) >= 2:
        revenue_prior = inc_data[1].get("revenue")
        op_income_prior = inc_data[1].get("operatingIncome")

    dividends_paid = buybacks = None
    if isinstance(cf_data, list) and cf_data:
        dividends_paid = cf_data[0].get("dividendsPaid")
        buybacks = cf_data[0].get("commonStockRepurchased")

    phase_inputs = {
        "revenue_current": revenue_current,
        "revenue_prior": revenue_prior,
        "op_income_current": op_income_current,
        "op_income_prior": op_income_prior,
        "dividends_paid": dividends_paid,
        "buybacks": buybacks,
        "latest_sec_url": latest_sec_url,
        "latest_sec_label": latest_sec_label,
        "latest_sec_date": latest_sec_date,
    }

    phase_classification = compute_business_phase(phase_inputs)

    out = {
        "symbol": symbol,
        "company_name": company_name,
        "business_phase_inputs": phase_inputs,
        "business_phase_classification": phase_classification,
        "transcript": transcript_obj,
        "sec_links": sec_links,
        "metrics": metrics or {"note": "No metrics returned", "debug": metrics_resp if not metrics_resp.get("ok") else None},
        "growth": growth or {"note": "No growth data returned", "debug": growth_resp if not growth_resp.get("ok") else None},
        "debug": {
            "profile_url": profile_resp.get("url"),
            "filings_url": filings_resp.get("url"),
            "metrics_url": metrics_resp.get("url"),
            "growth_url": growth_resp.get("url"),
            "income_statement_url": inc_resp.get("url"),
            "cash_flow_url": cf_resp.get("url"),
        }
    }
    return json.dumps(out, ensure_ascii=False, indent=2)
