"""Financial Modeling Prep API helper functions."""

from .http_client import get_json


def pick_latest_filing(filings: list) -> dict | None:
    """
    Pick the latest 10-Q if available, else latest 10-K, else latest any.
    Works best if filingDate/fillingDate present.

    Args:
        filings: List of filing dictionaries from FMP API

    Returns:
        The most relevant recent filing or None
    """
    if not isinstance(filings, list) or not filings:
        return None

    def _date_key(f):
        # FMP often uses 'fillingDate' (note spelling), sometimes 'filingDate'
        return f.get("fillingDate") or f.get("filingDate") or ""

    tens_q = [f for f in filings if (f.get("type") or f.get("formType") or "").upper() in ("10-Q", "10Q")]
    tens_k = [f for f in filings if (f.get("type") or f.get("formType") or "").upper() in ("10-K", "10K")]

    if tens_q:
        return sorted(tens_q, key=_date_key, reverse=True)[0]
    if tens_k:
        return sorted(tens_k, key=_date_key, reverse=True)[0]
    return sorted(filings, key=_date_key, reverse=True)[0]


def get_latest_transcript(symbol: str, api_key: str) -> dict:
    """
    Find newest available transcript via stable endpoints:
      1) /stable/earning-call-transcript-dates
      2) /stable/earning-call-transcript?year=&quarter=

    Args:
        symbol: Stock ticker symbol
        api_key: FMP API key

    Returns:
        Dictionary with transcript data or unavailability info
    """
    STABLE = "https://financialmodelingprep.com/stable"

    dates_resp = get_json(
        f"{STABLE}/earning-call-transcript-dates",
        {"symbol": symbol, "apikey": api_key},
    )
    if not dates_resp.get("ok"):
        return {"available": False, "note": "Failed to fetch transcript dates.", "debug": dates_resp}

    dates = dates_resp.get("data")
    if not isinstance(dates, list) or not dates:
        return {"available": False, "note": "No transcript dates returned for this symbol.", "debug_url": dates_resp.get("url")}

    latest = max(
        dates,
        key=lambda d: (
            int(d.get("fiscalYear") or d.get("year") or 0),
            int(d.get("quarter") or 0)
        )
    )

    year = latest.get("fiscalYear") or latest.get("year")
    quarter = latest.get("quarter")

    if year is None or quarter is None:
        return {"available": False, "note": "Transcript dates missing year/quarter.", "latest_row": latest, "debug_url": dates_resp.get("url")}

    t_resp = get_json(
        f"{STABLE}/earning-call-transcript",
        {"symbol": symbol, "year": year, "quarter": quarter, "apikey": api_key},
    )
    if not t_resp.get("ok"):
        return {"available": False, "note": "Failed to fetch transcript.", "year": year, "quarter": quarter, "debug": t_resp}

    t_data = t_resp.get("data")
    if not isinstance(t_data, list) or not t_data:
        return {"available": False, "note": "Transcript returned no rows.", "year": year, "quarter": quarter, "debug_url": t_resp.get("url")}

    content = (t_data[0].get("content") or "").strip()
    if not content:
        return {"available": False, "note": "Transcript content empty.", "year": year, "quarter": quarter, "debug_url": t_resp.get("url")}

    return {"available": True, "year": year, "quarter": quarter, "date": t_data[0].get("date"), "excerpt": content[:8000], "debug_url": t_resp.get("url")}
