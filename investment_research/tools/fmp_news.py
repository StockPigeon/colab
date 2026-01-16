"""FMP News Tool - Fetches stock news and press releases."""

import os
import json
from crewai.tools import tool

from ..helpers.http_client import get_json


@tool("fmp_news_tool")
def fmp_news_tool(symbol: str) -> str:
    """
    Fetches stock news and press releases for a ticker from FMP API.
    Use this to find recent news, earnings reactions, analyst coverage, and company announcements.

    Args:
        symbol: The stock ticker symbol (e.g., "AAPL", "MSFT")

    Returns:
        JSON string with news articles and press releases including titles, dates, and links.
    """
    api_key = os.environ.get("FMP_API_KEY")
    if not api_key:
        return json.dumps({"error": "Missing FMP_API_KEY env var"}, indent=2)

    symbol = (symbol or "").strip().upper()
    if not symbol:
        return json.dumps({"error": "No symbol provided"}, indent=2)

    base_v3 = "https://financialmodelingprep.com/api/v3"

    # Fetch stock-specific news
    news_resp = get_json(
        f"{base_v3}/stock_news",
        {"tickers": symbol, "limit": 30, "apikey": api_key}
    )
    stock_news = []
    if news_resp.get("ok"):
        news_data = news_resp.get("data")
        if isinstance(news_data, list):
            for item in news_data[:20]:
                stock_news.append({
                    "title": item.get("title"),
                    "text": (item.get("text") or "")[:500],
                    "url": item.get("url"),
                    "site": item.get("site"),
                    "publishedDate": item.get("publishedDate"),
                })

    # Fetch press releases
    press_resp = get_json(
        f"{base_v3}/press-releases/{symbol}",
        {"limit": 15, "apikey": api_key}
    )
    press_releases = []
    if press_resp.get("ok"):
        press_data = press_resp.get("data")
        if isinstance(press_data, list):
            for item in press_data[:10]:
                press_releases.append({
                    "title": item.get("title"),
                    "text": (item.get("text") or "")[:500],
                    "date": item.get("date"),
                })

    out = {
        "symbol": symbol,
        "stock_news": stock_news,
        "press_releases": press_releases,
        "total_news": len(stock_news),
        "total_press_releases": len(press_releases),
        "debug": {
            "news_url": news_resp.get("url"),
            "press_url": press_resp.get("url"),
        }
    }
    return json.dumps(out, ensure_ascii=False, indent=2)
