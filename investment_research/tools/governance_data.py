"""Governance Data Tool - Governance-focused data for management analysis."""

import os
import json
from crewai.tools import tool

from ..helpers.http_client import get_json
from ..helpers.fmp_api import get_latest_transcript


@tool("governance_data_tool")
def governance_data_tool(symbol: str) -> str:
    """
    Fetches governance-focused data for a ticker from FMP API:
    - Company profile (ownership, executives)
    - SEC filing links (10-K, 10-Q, Proxy/DEF 14A)
    - Earnings transcript (for management candor analysis)
    Does NOT include financial metrics, income statements, or cash flow data.

    Args:
        symbol: The stock ticker symbol (e.g., "AAPL", "MSFT")

    Returns:
        JSON string with governance-focused data including SEC filings and transcripts.
    """
    api_key = os.environ.get("FMP_API_KEY")
    if not api_key:
        return json.dumps({"error": "Missing FMP_API_KEY env var"}, indent=2)

    symbol = (symbol or "").strip().upper()
    if not symbol:
        return json.dumps({"error": "No symbol provided"}, indent=2)

    base_v3 = "https://financialmodelingprep.com/api/v3"

    # Get company profile
    profile_resp = get_json(f"{base_v3}/profile/{symbol}", {"apikey": api_key})
    profile_data = profile_resp.get("data") if profile_resp.get("ok") else None
    company_name = None
    profile_info = {}
    if isinstance(profile_data, list) and profile_data:
        p = profile_data[0]
        company_name = p.get("companyName")
        profile_info = {
            "companyName": company_name,
            "ceo": p.get("ceo"),
            "fullTimeEmployees": p.get("fullTimeEmployees"),
            "industry": p.get("industry"),
            "sector": p.get("sector"),
            "website": p.get("website"),
        }

    # Get earnings transcript for candor analysis
    transcript_obj = get_latest_transcript(symbol, api_key)

    # Get SEC filings (focus on governance-relevant filings)
    filings_resp = get_json(f"{base_v3}/sec_filings/{symbol}", {"limit": 50, "apikey": api_key})
    filings_data = filings_resp.get("data") if filings_resp.get("ok") else None

    sec_links = []
    proxy_filing = None
    latest_10k = None
    latest_10q = None

    if isinstance(filings_data, list):
        for f in filings_data:
            ftype = (f.get("type") or f.get("formType") or "").upper()
            link = f.get("finalLink") or f.get("link") or f.get("url")
            filing_date = f.get("fillingDate") or f.get("filingDate")

            # Capture proxy statement (DEF 14A) for compensation data
            if "DEF 14A" in ftype or "PROXY" in ftype:
                if proxy_filing is None and link:
                    proxy_filing = {"type": ftype, "date": filing_date, "url": link}
                    sec_links.append(f"PROXY (DEF 14A): {link}")

            # Capture latest 10-K
            elif ftype in ("10-K", "10K"):
                if latest_10k is None and link:
                    latest_10k = {"type": ftype, "date": filing_date, "url": link}
                    sec_links.append(f"10-K: {link}")

            # Capture latest 10-Q
            elif ftype in ("10-Q", "10Q"):
                if latest_10q is None and link:
                    latest_10q = {"type": ftype, "date": filing_date, "url": link}
                    sec_links.append(f"10-Q: {link}")

            # Stop once we have key filings
            if proxy_filing and latest_10k and latest_10q:
                break

    out = {
        "symbol": symbol,
        "company_name": company_name,
        "profile": profile_info,
        "transcript": transcript_obj,
        "sec_filings": {
            "proxy": proxy_filing,
            "latest_10k": latest_10k,
            "latest_10q": latest_10q,
        },
        "sec_links": sec_links,
        "debug": {
            "profile_url": profile_resp.get("url"),
            "filings_url": filings_resp.get("url"),
        }
    }
    return json.dumps(out, ensure_ascii=False, indent=2)
