"""Web Search API helper functions for flexible search capabilities."""

import os
from typing import Optional

from .http_client import session


def parse_search_input(input_string: str) -> tuple[str, str]:
    """
    Parse search input string to extract ticker and query.

    Formats supported:
    - "AAPL:antitrust lawsuit" -> ("AAPL", "AAPL antitrust lawsuit")
    - "AAPL" -> ("AAPL", "AAPL company news")
    - "what is NVIDIA doing with AI" -> ("", "what is NVIDIA doing with AI")

    Args:
        input_string: Raw input string

    Returns:
        Tuple of (ticker, search_query)
    """
    input_string = (input_string or "").strip()

    if ":" in input_string:
        parts = input_string.split(":", 1)
        ticker = parts[0].strip().upper()
        query_part = parts[1].strip() if len(parts) > 1 else ""

        # Prepend ticker to query for context
        search_query = f"{ticker} {query_part}".strip()
        return (ticker, search_query)

    # Check if input looks like a ticker (all caps, 1-5 chars, letters only)
    if input_string.isupper() and 1 <= len(input_string) <= 5 and input_string.isalpha():
        return (input_string, f"{input_string} company news stock")

    # Treat as raw query
    return ("", input_string)


def search_duckduckgo_lib(query: str, search_type: str = "text", num_results: int = 8) -> dict:
    """
    Search using duckduckgo-search Python library.

    Args:
        query: Search query string
        search_type: "text" for web, "news" for news
        num_results: Number of results to return

    Returns:
        Dictionary with search results or error
    """
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            return {"error": "ddgs package not installed. Run: pip install ddgs"}

    import time
    import random

    # Add small random delay to avoid rate limiting
    time.sleep(random.uniform(0.5, 1.5))

    try:
        with DDGS() as ddgs:
            if search_type == "news":
                raw_results = list(ddgs.news(query, max_results=num_results))
                results = []
                for item in raw_results:
                    results.append({
                        "title": item.get("title", ""),
                        "snippet": item.get("body", ""),
                        "url": item.get("url", ""),
                        "date": item.get("date", ""),
                        "source": item.get("source", ""),
                    })
            else:
                raw_results = list(ddgs.text(query, max_results=num_results))
                results = []
                for item in raw_results:
                    results.append({
                        "title": item.get("title", ""),
                        "snippet": item.get("body", ""),
                        "url": item.get("href", ""),
                    })

            return {"ok": True, "data": {"results": results}, "source": "duckduckgo"}
    except Exception as e:
        error_msg = str(e)
        # If rate limited, return empty results rather than error
        if "Ratelimit" in error_msg or "202" in error_msg:
            return {"ok": True, "data": {"results": []}, "source": "duckduckgo", "note": "Rate limited, returning empty"}
        return {"error": f"DuckDuckGo search failed: {error_msg}"}


def search_serper(
    query: str, search_type: str = "search", num_results: int = 10
) -> dict:
    """
    Search using Serper.dev API.

    Args:
        query: Search query string
        search_type: "search" for web, "news" for news
        num_results: Number of results to return

    Returns:
        Dictionary with search results or error
    """
    api_key = os.environ.get("SERPER_API_KEY")
    if not api_key:
        return {"error": "Missing SERPER_API_KEY environment variable", "fallback": True}

    url = f"https://google.serper.dev/{search_type}"

    try:
        resp = session.post(
            url,
            json={"q": query, "num": num_results},
            headers={
                "X-API-KEY": api_key,
                "Content-Type": "application/json",
            },
            timeout=15,
        )

        if resp.status_code != 200:
            return {
                "error": f"Serper API error: {resp.status_code}",
                "fallback": True,
            }

        return {"ok": True, "data": resp.json(), "source": "serper"}
    except Exception as e:
        return {"error": str(e), "fallback": True}


def search_combined(query: str, include_news: bool = True) -> dict:
    """
    Perform search using available APIs with fallback.

    Priority:
    1. DuckDuckGo (free, no API key needed)
    2. Serper (if API key available)

    Args:
        query: Search query string
        include_news: Whether to also search for news

    Returns:
        Combined search results
    """
    results = {
        "query": query,
        "web_results": [],
        "news_results": [],
        "sources_used": [],
        "errors": [],
    }

    # Try DuckDuckGo first (free, no API key)
    ddg_web = search_duckduckgo_lib(query, "text")
    if ddg_web.get("ok"):
        results["sources_used"].append("duckduckgo-web")
        results["web_results"] = ddg_web.get("data", {}).get("results", [])[:8]
    elif ddg_web.get("error"):
        results["errors"].append(f"DuckDuckGo web: {ddg_web.get('error')}")

    # Try DuckDuckGo news if requested
    if include_news:
        ddg_news = search_duckduckgo_lib(query, "news")
        if ddg_news.get("ok"):
            results["sources_used"].append("duckduckgo-news")
            results["news_results"] = ddg_news.get("data", {}).get("results", [])[:8]
        elif ddg_news.get("error"):
            results["errors"].append(f"DuckDuckGo news: {ddg_news.get('error')}")

    # Fallback to Serper if DuckDuckGo failed
    if not results["web_results"]:
        serper_web = search_serper(query, "search")
        if serper_web.get("ok"):
            results["sources_used"].append("serper-web")
            organic = serper_web.get("data", {}).get("organic", [])
            for item in organic[:8]:
                results["web_results"].append({
                    "title": item.get("title"),
                    "snippet": item.get("snippet"),
                    "url": item.get("link"),
                    "date": item.get("date"),
                })

    if include_news and not results["news_results"]:
        serper_news = search_serper(query, "news")
        if serper_news.get("ok"):
            results["sources_used"].append("serper-news")
            news = serper_news.get("data", {}).get("news", [])
            for item in news[:8]:
                results["news_results"].append({
                    "title": item.get("title"),
                    "snippet": item.get("snippet"),
                    "url": item.get("link"),
                    "date": item.get("date"),
                    "source": item.get("source"),
                })

    results["total_results"] = len(results["web_results"]) + len(results["news_results"])
    return results
