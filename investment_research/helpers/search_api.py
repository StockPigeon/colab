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


def search_duckduckgo(query: str) -> dict:
    """
    Search using DuckDuckGo Instant Answer API (free, no key).

    Note: This is limited - returns instant answers, not full search results.

    Args:
        query: Search query string

    Returns:
        Dictionary with search results or error
    """
    url = "https://api.duckduckgo.com/"

    try:
        resp = session.get(
            url,
            params={"q": query, "format": "json", "no_redirect": "1"},
            timeout=10,
        )

        if resp.status_code != 200:
            return {"error": f"DuckDuckGo API error: {resp.status_code}"}

        data = resp.json()

        # Extract useful information
        results = []

        # Abstract (main answer)
        if data.get("Abstract"):
            results.append(
                {
                    "title": data.get("Heading", ""),
                    "snippet": data.get("Abstract"),
                    "url": data.get("AbstractURL"),
                    "source": data.get("AbstractSource"),
                }
            )

        # Related topics
        for topic in data.get("RelatedTopics", [])[:5]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append(
                    {
                        "title": topic.get("Text", "")[:100],
                        "snippet": topic.get("Text"),
                        "url": topic.get("FirstURL"),
                    }
                )

        return {"ok": True, "data": {"results": results}, "source": "duckduckgo"}
    except Exception as e:
        return {"error": str(e)}


def search_combined(query: str, include_news: bool = True) -> dict:
    """
    Perform search using available APIs with fallback.

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

    # Try Serper first for web results
    serper_web = search_serper(query, "search")
    if serper_web.get("ok"):
        results["sources_used"].append("serper-web")
        organic = serper_web.get("data", {}).get("organic", [])
        for item in organic[:8]:
            results["web_results"].append(
                {
                    "title": item.get("title"),
                    "snippet": item.get("snippet"),
                    "url": item.get("link"),
                    "date": item.get("date"),
                }
            )
    elif serper_web.get("error"):
        results["errors"].append(f"Serper web: {serper_web.get('error')}")

    # Try Serper news if requested
    if include_news:
        serper_news = search_serper(query, "news")
        if serper_news.get("ok"):
            results["sources_used"].append("serper-news")
            news = serper_news.get("data", {}).get("news", [])
            for item in news[:8]:
                results["news_results"].append(
                    {
                        "title": item.get("title"),
                        "snippet": item.get("snippet"),
                        "url": item.get("link"),
                        "date": item.get("date"),
                        "source": item.get("source"),
                    }
                )
        elif serper_news.get("error") and "Missing SERPER_API_KEY" not in str(serper_news.get("error")):
            results["errors"].append(f"Serper news: {serper_news.get('error')}")

    # Fallback to DuckDuckGo if no results from Serper
    if not results["web_results"] and not results["news_results"]:
        ddg = search_duckduckgo(query)
        if ddg.get("ok"):
            results["sources_used"].append("duckduckgo")
            results["web_results"] = ddg.get("data", {}).get("results", [])
        elif ddg.get("error"):
            results["errors"].append(f"DuckDuckGo: {ddg.get('error')}")

    # If still no results, provide guidance
    if not results["web_results"] and not results["news_results"]:
        if "Missing SERPER_API_KEY" in str(results.get("errors", [])):
            results["suggestion"] = "Set SERPER_API_KEY environment variable for search functionality"

    results["total_results"] = len(results["web_results"]) + len(results["news_results"])
    return results
