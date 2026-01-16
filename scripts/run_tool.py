#!/usr/bin/env python3
"""
Run individual tools for testing.

Usage:
    python scripts/run_tool.py <tool_name> <ticker>

Examples:
    python scripts/run_tool.py investment_data AAPL
    python scripts/run_tool.py fmp_news MSFT
    python scripts/run_tool.py price_sentiment GOOGL
    python scripts/run_tool.py governance_data META
    python scripts/run_tool.py business_profile NVDA
"""

import sys
import json
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from investment_research.helpers import load_and_validate_env
from investment_research.tools import (
    fmp_news_tool,
    investment_data_tool,
    price_sentiment_data_tool,
    governance_data_tool,
    business_profile_tool,
)


TOOLS = {
    "fmp_news": fmp_news_tool,
    "investment_data": investment_data_tool,
    "price_sentiment": price_sentiment_data_tool,
    "governance_data": governance_data_tool,
    "business_profile": business_profile_tool,
}


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        print(f"\nAvailable tools: {list(TOOLS.keys())}")
        sys.exit(1)

    tool_name = sys.argv[1]
    ticker = sys.argv[2].upper()

    if tool_name not in TOOLS:
        print(f"Unknown tool: {tool_name}")
        print(f"Available tools: {list(TOOLS.keys())}")
        sys.exit(1)

    # Load environment
    load_and_validate_env()

    tool = TOOLS[tool_name]
    print(f"\n### Running {tool_name} for {ticker} ###\n")

    result = tool._run(ticker)

    # Pretty print JSON
    try:
        data = json.loads(result)
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except json.JSONDecodeError:
        print(result)


if __name__ == "__main__":
    main()
