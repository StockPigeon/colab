"""SEC EDGAR Filings Tool - Fetches and parses SEC filings."""

import json

from crewai.tools import tool

from ..helpers.sec_edgar import (
    extract_key_sections,
    fetch_filing_content,
    find_recent_filings,
    get_cik_for_ticker,
    get_company_filings,
)


@tool("sec_filings_tool")
def sec_filings_tool(symbol: str) -> str:
    """
    Fetches and parses recent SEC filings (10-K, 10-Q, DEF 14A/Proxy) for a ticker.

    Uses the official SEC EDGAR API to retrieve:
    - Annual reports (10-K): Business description, risk factors, MD&A
    - Quarterly reports (10-Q): Recent financial updates
    - Proxy statements (DEF 14A): Executive compensation, ownership

    Returns extracted text content from filings, not just links.

    Args:
        symbol: The stock ticker symbol (e.g., "AAPL", "MSFT")

    Returns:
        JSON string with filing metadata and extracted content sections.
    """
    symbol = (symbol or "").strip().upper()
    if not symbol:
        return json.dumps({"error": "No symbol provided"}, indent=2)

    # Convert ticker to CIK
    cik = get_cik_for_ticker(symbol)
    if not cik:
        return json.dumps(
            {
                "error": f"Could not find CIK for ticker {symbol}",
                "suggestion": "Verify the ticker symbol is correct and traded on US exchanges",
            },
            indent=2,
        )

    # Fetch company filings metadata
    filings_data = get_company_filings(cik)
    if not filings_data:
        return json.dumps(
            {"error": f"Could not fetch filings for CIK {cik}", "symbol": symbol},
            indent=2,
        )

    # Extract company info
    company_name = filings_data.get("name", symbol)

    # Find recent filings of each type
    form_types = ["10-K", "10-Q", "DEF 14A"]
    recent_filings = find_recent_filings(filings_data, form_types, limit=1)

    # Fetch and parse content for each filing
    filings_with_content = []
    for filing in recent_filings:
        doc_url = filing.get("document_url")
        form_type = filing.get("form_type", "")

        # Fetch document content - need enough to find sections past TOC
        content = fetch_filing_content(doc_url, max_chars=150000)

        filing_result = {
            "form_type": form_type,
            "filing_date": filing.get("filing_date"),
            "document_url": doc_url,
            "content_available": content is not None,
        }

        if content:
            # Extract key sections based on form type
            sections = extract_key_sections(content, form_type)
            filing_result["sections"] = sections

            # Provide a useful excerpt - skip XBRL metadata at start
            # Look for where readable content begins
            excerpt_start = 0
            content_upper = content.upper()
            for marker in ["PART I", "TABLE OF CONTENTS", "FORWARD-LOOKING"]:
                pos = content_upper.find(marker)
                if pos > 0 and pos < 50000:
                    excerpt_start = pos
                    break
            filing_result["full_text_excerpt"] = content[excerpt_start:excerpt_start + 8000]

        filings_with_content.append(filing_result)

    out = {
        "symbol": symbol,
        "cik": cik,
        "company_name": company_name,
        "filings": filings_with_content,
        "filing_count": len(filings_with_content),
        "form_types_searched": form_types,
    }

    return json.dumps(out, ensure_ascii=False, indent=2)
