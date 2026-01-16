#!/usr/bin/env python3
"""
Test individual agents for debugging.

Usage:
    python scripts/run_agent.py <agent_name> <ticker> [custom_prompt]

Examples:
    python scripts/run_agent.py strategist AAPL
    python scripts/run_agent.py phase_classifier MSFT
    python scripts/run_agent.py sentiment_analyst GOOGL "Analyze recent price action"

Available agents:
    - phase_classifier
    - sentiment_analyst
    - strategist
    - governance_expert
    - quant_auditor
    - business_profile_analyst
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from investment_research.helpers import load_and_validate_env
from investment_research.crew import InvestmentResearchCrew


AVAILABLE_AGENTS = [
    "phase_classifier",
    "sentiment_analyst",
    "strategist",
    "governance_expert",
    "quant_auditor",
    "business_profile_analyst",
]


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    agent_name = sys.argv[1]
    ticker = sys.argv[2].upper()
    prompt = sys.argv[3] if len(sys.argv) > 3 else None

    if agent_name not in AVAILABLE_AGENTS:
        print(f"Unknown agent: {agent_name}")
        print(f"Available agents: {AVAILABLE_AGENTS}")
        sys.exit(1)

    # Load environment
    load_and_validate_env()

    print(f"\n### Testing {agent_name} for {ticker} ###\n")
    if prompt:
        print(f"Custom prompt: {prompt}\n")

    crew = InvestmentResearchCrew()
    result = crew.run_single_agent(agent_name, ticker, prompt)

    print("\n" + "=" * 60)
    print("AGENT OUTPUT")
    print("=" * 60 + "\n")

    if hasattr(result, 'tasks_output') and result.tasks_output:
        print(result.tasks_output[0].raw)
    else:
        print(result)


if __name__ == "__main__":
    main()
