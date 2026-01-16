#!/usr/bin/env python3
"""
Run individual tasks for testing.

Usage:
    python scripts/run_task.py <task_name> <ticker>

Examples:
    python scripts/run_task.py task_price_sentiment AAPL
    python scripts/run_task.py task_business_phase MSFT
    python scripts/run_task.py task_business_profile GOOGL
    python scripts/run_task.py task_business_moat META
    python scripts/run_task.py task_management_risk NVDA
    python scripts/run_task.py task_quant_valuation AMZN

Available tasks:
    - task_price_sentiment
    - task_business_phase
    - task_business_profile
    - task_business_moat
    - task_management_risk
    - task_quant_valuation
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from investment_research.helpers import load_and_validate_env
from investment_research.crew import InvestmentResearchCrew


AVAILABLE_TASKS = [
    "task_price_sentiment",
    "task_business_phase",
    "task_business_profile",
    "task_business_moat",
    "task_management_risk",
    "task_quant_valuation",
]


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    task_name = sys.argv[1]
    ticker = sys.argv[2].upper()

    if task_name not in AVAILABLE_TASKS:
        print(f"Unknown task: {task_name}")
        print(f"Available tasks: {AVAILABLE_TASKS}")
        sys.exit(1)

    # Load environment
    load_and_validate_env()

    print(f"\n### Running {task_name} for {ticker} ###\n")

    crew = InvestmentResearchCrew()
    result = crew.run_single_task(task_name, ticker)

    print("\n" + "=" * 60)
    print("TASK OUTPUT")
    print("=" * 60 + "\n")

    if hasattr(result, 'tasks_output') and result.tasks_output:
        print(result.tasks_output[0].raw)
    else:
        print(result)


if __name__ == "__main__":
    main()
