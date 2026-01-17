"""SEC EDGAR API helper functions for fetching and parsing SEC filings."""

import re
import time
from typing import Optional

from .http_client import session

# SEC requires a specific User-Agent format
SEC_USER_AGENT = "InvestmentResearch research@example.com"

# Cache for ticker to CIK mapping (populated on first use)
_ticker_cik_cache: dict[str, str] = {}


def _get_sec_headers() -> dict:
    """Get headers required for SEC EDGAR API."""
    return {
        "User-Agent": SEC_USER_AGENT,
        "Accept-Encoding": "gzip, deflate",
    }


def get_cik_for_ticker(ticker: str) -> Optional[str]:
    """
    Convert ticker symbol to 10-digit zero-padded CIK.

    Args:
        ticker: Stock ticker symbol (e.g., "AAPL")

    Returns:
        10-digit CIK string or None if not found
    """
    global _ticker_cik_cache

    ticker = ticker.upper().strip()

    # Check cache first
    if ticker in _ticker_cik_cache:
        return _ticker_cik_cache[ticker]

    # Fetch company tickers mapping
    url = "https://www.sec.gov/files/company_tickers.json"
    try:
        resp = session.get(url, headers=_get_sec_headers(), timeout=30)
        if resp.status_code != 200:
            return None

        data = resp.json()

        # Build cache from response
        for entry in data.values():
            t = entry.get("ticker", "").upper()
            cik = entry.get("cik_str")
            if t and cik:
                _ticker_cik_cache[t] = str(cik).zfill(10)

        return _ticker_cik_cache.get(ticker)
    except Exception:
        return None


def get_company_filings(cik: str) -> Optional[dict]:
    """
    Fetch company filings metadata from SEC EDGAR.

    Args:
        cik: 10-digit CIK number

    Returns:
        Dictionary with filing metadata or None on error
    """
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"

    try:
        resp = session.get(url, headers=_get_sec_headers(), timeout=30)
        if resp.status_code != 200:
            return None
        return resp.json()
    except Exception:
        return None


def find_recent_filings(
    filings_data: dict, form_types: list[str], limit: int = 1
) -> list[dict]:
    """
    Extract recent filings of specified types from SEC response.

    Args:
        filings_data: Full SEC filings response
        form_types: List of form types to find (e.g., ["10-K", "10-Q", "DEF 14A"])
        limit: Maximum number of each type to return

    Returns:
        List of filing metadata dictionaries
    """
    recent = filings_data.get("filings", {}).get("recent", {})

    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])

    results = []
    counts = {ft.upper(): 0 for ft in form_types}

    cik = str(filings_data.get("cik", "")).lstrip("0")

    for i in range(len(forms)):
        form = forms[i] if i < len(forms) else ""
        form_upper = form.upper().strip()

        # Check if this form type is one we want
        matched_type = None
        for ft in form_types:
            ft_upper = ft.upper()
            # Exact match or form contains our type (handles 10-K/A, DEF 14A, etc.)
            if form_upper == ft_upper or ft_upper in form_upper:
                matched_type = ft_upper
                break

        if matched_type and counts.get(matched_type, 0) < limit:
            accession = accessions[i] if i < len(accessions) else ""
            accession_no_dashes = accession.replace("-", "")
            primary_doc = primary_docs[i] if i < len(primary_docs) else ""

            results.append(
                {
                    "form_type": form,
                    "filing_date": dates[i] if i < len(dates) else "",
                    "accession_number": accession,
                    "document_url": f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_no_dashes}/{primary_doc}",
                }
            )
            counts[matched_type] = counts.get(matched_type, 0) + 1

        # Stop if we have enough of each
        if all(c >= limit for c in counts.values()):
            break

    return results


def fetch_filing_content(document_url: str, max_chars: int = 80000) -> Optional[str]:
    """
    Fetch and extract text content from a filing document.

    SEC filings are HTML/iXBRL - this extracts readable text.

    Args:
        document_url: URL to the filing document
        max_chars: Maximum characters to return

    Returns:
        Extracted text content or None on error
    """
    try:
        # Rate limiting: SEC allows 10 req/sec
        time.sleep(0.15)

        resp = session.get(document_url, headers=_get_sec_headers(), timeout=60)
        if resp.status_code != 200:
            return None

        html = resp.text

        # Handle iXBRL format - remove ix: namespace tags but keep content
        # This handles inline XBRL documents that mix XBRL with HTML
        text = re.sub(r"<ix:[^>]*>", "", html)
        text = re.sub(r"</ix:[^>]*>", "", text)

        # Remove script and style tags
        text = re.sub(
            r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE
        )
        text = re.sub(
            r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE
        )

        # Remove hidden spans (often used for XBRL context)
        text = re.sub(
            r'<span[^>]*style="[^"]*display:\s*none[^"]*"[^>]*>.*?</span>',
            "",
            text,
            flags=re.DOTALL | re.IGNORECASE,
        )

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", text)

        # Decode HTML entities
        text = text.replace("&nbsp;", " ")
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&quot;", '"')
        text = text.replace("&#8217;", "'")
        text = text.replace("&#8220;", '"')
        text = text.replace("&#8221;", '"')
        text = text.replace("&#8212;", "-")
        text = text.replace("&#160;", " ")

        # Clean up whitespace
        text = re.sub(r"\s+", " ", text)
        text = text.strip()

        return text[:max_chars]
    except Exception:
        return None


def extract_key_sections(text: str, form_type: str) -> dict:
    """
    Extract key sections from filing text based on form type.

    Args:
        text: Full filing text
        form_type: Type of form (10-K, 10-Q, DEF 14A)

    Returns:
        Dictionary with extracted sections
    """
    sections = {}
    text_upper = text.upper()

    # Skip past the table of contents (usually in first ~40K chars of 10-K/10-Q)
    # Look for "PART I" or similar to find where actual content starts
    toc_end = 0
    part_markers = ["PART I ITEM 1", "PART I. ITEM 1", "PART 1 ITEM 1"]
    for marker in part_markers:
        pos = text_upper.find(marker)
        if pos > 0:
            toc_end = pos
            break

    if "10-K" in form_type.upper() or "10-Q" in form_type.upper():
        # Common sections in 10-K/10-Q
        # The actual section headers typically have "ITEM X." followed by section name
        # We look for the actual content section, not TOC entries
        section_patterns = [
            ("business", ["ITEM 1. B", "ITEM 1. BUSINESS", "ITEM 1.BUSINESS"], "ITEM 1A"),
            ("risk_factors", ["ITEM 1A. R", "ITEM 1A. RISK", "ITEM 1A.RISK"], "ITEM 1B"),
            ("mda", ["ITEM 7. M", "ITEM 7. MANAGEMENT", "ITEM 7.MANAGEMENT"], "ITEM 7A"),
            ("financial_condition", ["ITEM 7A. Q", "ITEM 7A. QUANTITATIVE"], "ITEM 8"),
        ]

        for name, start_patterns, end_marker in section_patterns:
            start = -1
            # Try each pattern, looking past TOC
            for pattern in start_patterns:
                # Find occurrences after position 40000 (skip TOC area)
                pos = text_upper.find(pattern, max(toc_end, 40000))
                if pos > 0:
                    start = pos
                    break

            if start == -1:
                continue

            # Find end marker after start
            end = text_upper.find(end_marker, start + 20)
            if end == -1 or end <= start:
                end = start + 15000  # Default section length

            section_text = text[start : min(end, start + 12000)]
            if len(section_text) > 500:  # Only include if substantial
                sections[name] = section_text

    elif "DEF 14A" in form_type.upper() or "14A" in form_type.upper():
        # Proxy statement sections
        section_markers = [
            ("executive_compensation", "EXECUTIVE COMPENSATION", "DIRECTOR COMPENSATION"),
            ("director_compensation", "DIRECTOR COMPENSATION", "SECURITY OWNERSHIP"),
            ("ownership", "SECURITY OWNERSHIP", "CERTAIN RELATIONSHIPS"),
            ("proposals", "PROPOSAL", "EXECUTIVE COMPENSATION"),
        ]

        for name, start_marker, end_marker in section_markers:
            start = text_upper.find(start_marker)
            if start == -1:
                continue

            end = text_upper.find(end_marker, start + len(start_marker))
            if end == -1 or end <= start:
                end = start + 15000

            section_text = text[start : min(end, start + 12000)]
            if len(section_text) > 500:
                sections[name] = section_text

    return sections
