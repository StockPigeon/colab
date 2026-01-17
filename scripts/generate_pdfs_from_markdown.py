#!/usr/bin/env python3
"""Generate PDFs from existing markdown reports."""

import argparse
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from investment_research.pdf.base import check_pdf_dependencies
import subprocess


def markdown_to_pdf_pandoc(md_path: str, pdf_path: str) -> str:
    """Convert markdown to PDF using pandoc."""
    check_pdf_dependencies()
    
    if not os.path.exists(md_path):
        raise FileNotFoundError(f"Markdown file not found: {md_path}")
    
    cmd = [
        "pandoc", md_path,
        "-o", pdf_path,
        "--pdf-engine=xelatex",
        "-V", "documentclass=article",
        "-V", "colorlinks=true",
    ]
    
    try:
        subprocess.run(cmd, check=True)
        return pdf_path
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Pandoc conversion failed: {e}")


def generate_equity_pdf(ticker: str) -> None:
    """Generate equity research PDF from temp markdown."""
    temp_md = f"{ticker}_equity_research_equity_temp.md"
    output_pdf = f"{ticker}_equity_research.pdf"
    
    if not os.path.exists(temp_md):
        print(f"Error: {temp_md} not found")
        return
    
    try:
        result = markdown_to_pdf_pandoc(temp_md, output_pdf)
        print(f"✓ Saved Equity Research PDF to: {result}")
    except Exception as e:
        print(f"✗ Equity Research PDF generation failed: {e}")


def generate_memo_pdf(ticker: str) -> None:
    """Generate investment memo PDF from temp markdown."""
    temp_md = f"{ticker}_investment_memo_memo_temp.md"
    output_pdf = f"{ticker}_investment_memo.pdf"
    
    if not os.path.exists(temp_md):
        print(f"Error: {temp_md} not found")
        return
    
    try:
        result = markdown_to_pdf_pandoc(temp_md, output_pdf)
        print(f"✓ Saved Investment Memo PDF to: {result}")
    except Exception as e:
        print(f"✗ Investment Memo PDF generation failed: {e}")


def main():
    parser = argparse.ArgumentParser(description="Generate PDFs from existing markdown reports")
    parser.add_argument("ticker", help="Stock ticker symbol")
    parser.add_argument("--equity", action="store_true", default=True, help="Generate equity research PDF (default)")
    parser.add_argument("--memo", action="store_true", default=True, help="Generate investment memo PDF (default)")
    
    args = parser.parse_args()
    
    if args.equity:
        generate_equity_pdf(args.ticker)
    if args.memo:
        generate_memo_pdf(args.ticker)


if __name__ == "__main__":
    main()
