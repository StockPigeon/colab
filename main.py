#!/usr/bin/env python3
"""
Investment Research Analyzer - Entry Point

This is a backward-compatible wrapper that imports from the new modular package.

Usage:
    python main.py --ticker AAPL
    python main.py --ticker AAPL --no-pdf
    python main.py --tool investment_data --ticker AAPL
    python main.py --task task_business_moat --ticker AAPL
    python main.py --agent strategist --ticker AAPL

For more options, run:
    python main.py --help
"""

from investment_research.main import main

if __name__ == "__main__":
    main()
