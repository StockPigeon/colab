"""Web Search Tool - Flexible search for investment research."""

import json

from crewai.tools import tool

from ..helpers.search_api import parse_search_input, search_combined


@tool("web_search_tool")
def web_search_tool(query: str) -> str:
    """
    Performs web and news search for investment research topics.

    Supports flexible query formats:
    - "AAPL:antitrust lawsuit" - Search for Apple antitrust news
    - "NVDA:AI chip competition AMD" - Search for NVIDIA AI competition
    - "TSLA" - Default company news search
    - "semiconductor supply chain 2024" - Raw query search

    Returns recent web pages and news articles relevant to the query.
    More flexible than stock-specific news tools.

    Args:
        query: Search query in format "TICKER:search terms" or just search terms

    Returns:
        JSON string with web and news search results including titles, snippets, and URLs.
    """
    query = (query or "").strip()
    if not query:
        return json.dumps({"error": "No search query provided"}, indent=2)

    # Parse input to extract ticker and search query
    ticker, search_query = parse_search_input(query)

    # Perform combined search
    results = search_combined(search_query, include_news=True)

    out = {
        "original_input": query,
        "ticker": ticker if ticker else None,
        "search_query": search_query,
        "web_results": results.get("web_results", []),
        "news_results": results.get("news_results", []),
        "total_results": results.get("total_results", 0),
        "sources_used": results.get("sources_used", []),
    }

    return json.dumps(out, ensure_ascii=False, indent=2)
