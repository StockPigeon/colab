"""PDF generation module for investment reports."""

from .base import md_to_pdf_pandoc, check_pdf_dependencies
from .equity_research import generate_equity_research_pdf
from .hedge_fund_memo import generate_hedge_fund_memo_pdf

__all__ = [
    "md_to_pdf_pandoc",
    "check_pdf_dependencies",
    "generate_equity_research_pdf",
    "generate_hedge_fund_memo_pdf",
]
