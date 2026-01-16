"""Price Sentiment Data Tool - 1-year price performance metrics."""

import os
import json
from datetime import datetime, timedelta
from crewai.tools import tool

from ..helpers.http_client import get_json


@tool("price_sentiment_data_tool")
def price_sentiment_data_tool(symbol: str) -> str:
    """
    Computes 1-year price performance metrics needed for the sentiment template:
    - 1Y % change
    - 52-week range
    - current price
    - vs 50/200-day SMA (approx from latest SMA values)
    - vs S&P 500 (uses ^GSPC if available)

    Args:
        symbol: The stock ticker symbol (e.g., "AAPL", "MSFT")

    Returns:
        JSON string with price performance metrics and S&P 500 comparison.
    """
    api_key = os.environ.get("FMP_API_KEY")
    if not api_key:
        return json.dumps({"error": "Missing FMP_API_KEY"}, indent=2)

    symbol = (symbol or "").strip().upper()
    if not symbol:
        return json.dumps({"error": "No symbol provided"}, indent=2)

    base_v3 = "https://financialmodelingprep.com/api/v3"

    end = datetime.utcnow().date()
    start = end - timedelta(days=365)

    # Current quote
    q = get_json(f"{base_v3}/quote/{symbol}", {"apikey": api_key})
    quote = (q.get("data") or [])
    current_price = quote[0].get("price") if isinstance(quote, list) and quote else None

    # 1Y daily history (line)
    hist = get_json(
        f"{base_v3}/historical-price-full/{symbol}",
        {"from": str(start), "to": str(end), "serietype": "line", "apikey": api_key},
    )
    h = (hist.get("data") or {}).get("historical") if hist.get("ok") and isinstance(hist.get("data"), dict) else None

    one_year_change = None
    low_52w = None
    high_52w = None
    first_close = last_close = None
    if isinstance(h, list) and len(h) >= 2:
        h_sorted = sorted(h, key=lambda r: r.get("date") or "")
        first_close = h_sorted[0].get("close")
        last_close = h_sorted[-1].get("close")
        closes = [r.get("close") for r in h_sorted if isinstance(r.get("close"), (int, float))]
        if closes:
            low_52w = min(closes)
            high_52w = max(closes)
        if isinstance(first_close, (int, float)) and isinstance(last_close, (int, float)) and first_close != 0:
            one_year_change = (last_close - first_close) / abs(first_close)

    def _latest_sma(period: int):
        r = get_json(
            f"{base_v3}/technical_indicator/daily/{symbol}",
            {"type": "sma", "period": period, "apikey": api_key},
        )
        data = r.get("data")
        if r.get("ok") and isinstance(data, list) and data:
            return data[0].get("sma")
        return None

    sma50 = _latest_sma(50)
    sma200 = _latest_sma(200)

    def _vs_ma(px, ma):
        if not isinstance(px, (int, float)) or not isinstance(ma, (int, float)) or ma == 0:
            return None
        if abs(px - ma) / abs(ma) <= 0.005:
            return "At"
        return "Above" if px > ma else "Below"

    vs50 = _vs_ma(current_price, sma50)
    vs200 = _vs_ma(current_price, sma200)

    # S&P 500 compare (best-effort)
    spx_symbol = "^GSPC"
    spx_hist = get_json(
        f"{base_v3}/historical-price-full/{spx_symbol}",
        {"from": str(start), "to": str(end), "serietype": "line", "apikey": api_key},
    )
    spx_h = (spx_hist.get("data") or {}).get("historical") if spx_hist.get("ok") and isinstance(spx_hist.get("data"), dict) else None
    spx_change = None
    if isinstance(spx_h, list) and len(spx_h) >= 2:
        spx_sorted = sorted(spx_h, key=lambda r: r.get("date") or "")
        spx_first = spx_sorted[0].get("close")
        spx_last = spx_sorted[-1].get("close")
        if isinstance(spx_first, (int, float)) and isinstance(spx_last, (int, float)) and spx_first != 0:
            spx_change = (spx_last - spx_first) / abs(spx_first)

    out = {
        "symbol": symbol,
        "window": {"start": str(start), "end": str(end)},
        "current_price": current_price,
        "one_year_change_pct": (one_year_change * 100) if isinstance(one_year_change, (int, float)) else None,
        "range_52w": {"low": low_52w, "high": high_52w},
        "moving_averages": {"sma50": sma50, "sma200": sma200, "vs50": vs50, "vs200": vs200},
        "sp500": {
            "symbol": spx_symbol,
            "one_year_change_pct": (spx_change * 100) if isinstance(spx_change, (int, float)) else None,
        },
        "debug": {
            "quote_url": q.get("url"),
            "hist_url": hist.get("url"),
            "sma50_url": f"{base_v3}/technical_indicator/daily/{symbol}?type=sma&period=50&apikey=***",
            "sma200_url": f"{base_v3}/technical_indicator/daily/{symbol}?type=sma&period=200&apikey=***",
            "spx_hist_url": spx_hist.get("url"),
        },
    }
    return json.dumps(out, ensure_ascii=False, indent=2)
