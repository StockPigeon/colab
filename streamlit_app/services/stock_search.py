"""Stock search service using FMP API."""

import os
from typing import List, Dict, Optional
import requests


def get_api_key() -> str:
    """Get FMP API key from environment or Streamlit secrets."""
    try:
        import streamlit as st
        if "FMP_API_KEY" in st.secrets:
            return st.secrets["FMP_API_KEY"]
    except Exception:
        pass
    return os.environ.get("FMP_API_KEY", "")


def search_stocks(query: str, limit: int = 10) -> List[Dict]:
    """
    Search for stocks by company name or symbol.

    Uses FMP's search-name endpoint for name searches,
    and search endpoint for symbol searches.

    Args:
        query: Search term (company name or partial symbol)
        limit: Maximum results to return

    Returns:
        List of dicts with: symbol, name, exchange
    """
    api_key = get_api_key()
    if not api_key:
        return []

    query = query.strip()
    if not query:
        return []

    results = []

    # Try symbol search first (if query looks like a ticker)
    if query.isupper() and len(query) <= 5:
        try:
            url = "https://financialmodelingprep.com/api/v3/search"
            params = {
                "query": query,
                "limit": limit,
                "apikey": api_key,
            }
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    results = [
                        {
                            "symbol": item.get("symbol", ""),
                            "name": item.get("name", ""),
                            "exchange": item.get("exchangeShortName", ""),
                        }
                        for item in data
                    ]
        except Exception:
            pass

    # Also try name search (fetch more to allow filtering)
    try:
        url = "https://financialmodelingprep.com/api/v3/search-name"
        params = {
            "query": query,
            "limit": limit * 3,  # Fetch more to allow filtering
            "apikey": api_key,
        }
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list):
                name_results = [
                    {
                        "symbol": item.get("symbol", ""),
                        "name": item.get("name", ""),
                        "exchange": item.get("exchangeShortName", ""),
                    }
                    for item in data
                ]
                # Merge results, avoiding duplicates
                seen_symbols = {r["symbol"] for r in results}
                for r in name_results:
                    if r["symbol"] not in seen_symbols:
                        results.append(r)
                        seen_symbols.add(r["symbol"])
    except Exception:
        pass

    # Filter to only stocks with valid symbols on major exchanges
    # Include most common exchanges worldwide
    major_exchanges = {
        # US
        "NYSE", "NASDAQ", "AMEX", "NYSE ARCA", "NYSE MKT", "BATS",
        # International
        "ASX", "LSE", "TSX", "HKSE", "SSE", "SZSE", "TSE", "NSE", "BSE",
        # European
        "XETRA", "EURONEXT", "FSX", "SIX", "BME",
        # Other
        "NEO", "JPX",
    }
    filtered = [
        r for r in results
        if r["symbol"] and r["exchange"] in major_exchanges
    ]

    # If we filtered everything out, return unfiltered but prioritize known exchanges
    if not filtered and results:
        # Sort: major exchanges first, then others
        results.sort(key=lambda r: 0 if r["exchange"] in major_exchanges else 1)
        return results[:limit]

    return filtered[:limit]


def validate_ticker(symbol: str) -> Dict:
    """
    Validate a ticker symbol and return company info.

    Args:
        symbol: Stock ticker symbol

    Returns:
        Dict with company name and validation status
    """
    api_key = get_api_key()
    if not api_key:
        return {"valid": False, "error": "Missing API key"}

    symbol = symbol.strip().upper()

    try:
        url = f"https://financialmodelingprep.com/api/v3/profile/{symbol}"
        resp = requests.get(url, params={"apikey": api_key}, timeout=10)

        if resp.status_code == 200:
            data = resp.json()
            if data and isinstance(data, list) and len(data) > 0:
                profile = data[0]
                return {
                    "valid": True,
                    "symbol": profile.get("symbol"),
                    "name": profile.get("companyName"),
                    "exchange": profile.get("exchangeShortName"),
                    "sector": profile.get("sector"),
                    "industry": profile.get("industry"),
                }
    except Exception as e:
        return {"valid": False, "error": str(e)}

    return {"valid": False, "error": "Symbol not found"}
