#!/usr/bin/env python
"""
Background script to run investment research analysis.
Updates progress file as tasks complete.
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent directories to path
script_dir = Path(__file__).parent
app_dir = script_dir.parent
repo_dir = app_dir.parent
sys.path.insert(0, str(repo_dir))
sys.path.insert(0, str(app_dir))

# Progress file (must match research_runner.py)
PROGRESS_FILE = Path("/tmp/investment_research_progress.json")

# Section names matching main.py
SECTION_NAMES = [
    "PRICE & SENTIMENT",
    "BUSINESS PHASE",
    "KEY METRICS",
    "BUSINESS PROFILE",
    "BUSINESS & MOAT",
    "EXECUTION RISK",
    "GROWTH DRIVERS",
    "MANAGEMENT QUALITY",
    "VALUATION",
    "QUANT VALUATION",
    "INVESTMENT SCORECARD",
]


def load_progress():
    """Load progress from file."""
    if not PROGRESS_FILE.exists():
        return None
    with open(PROGRESS_FILE, "r") as f:
        return json.load(f)


def save_progress(data):
    """Save progress to file."""
    with open(PROGRESS_FILE, "w") as f:
        json.dump(data, f)


def update_task(task_index: int, status: str):
    """Update a task's status."""
    data = load_progress()
    if data and task_index < len(data.get("tasks", [])):
        data["tasks"][task_index]["status"] = status
        data["current_task_index"] = task_index
        # Mark previous as completed
        for i in range(task_index):
            data["tasks"][i]["status"] = "completed"
        save_progress(data)


def mark_complete(company_name: str = "", error: str = None):
    """Mark analysis as complete."""
    data = load_progress()
    if data:
        data["is_complete"] = True
        data["is_running"] = False
        if company_name:
            data["company_name"] = company_name
        if error:
            data["error"] = error
        # Mark all tasks completed if no error
        if not error:
            for task in data.get("tasks", []):
                task["status"] = "completed"
        save_progress(data)


def run_analysis(ticker: str):
    """Run the full analysis with progress updates."""
    from dotenv import load_dotenv
    load_dotenv()

    from investment_research.crew import InvestmentResearchCrew
    from investment_research.helpers import load_and_validate_env, clear_cache
    from investment_research.pdf import (
        generate_equity_research_pdf,
        generate_hedge_fund_memo_pdf,
    )
    from investment_research.main import generate_revenue_charts

    # Load environment
    load_and_validate_env()
    clear_cache()

    # Create crew
    crew_instance = InvestmentResearchCrew()
    crew = crew_instance.crew()

    # We can't easily hook into CrewAI's task execution,
    # but we can simulate progress based on time estimates
    # For now, mark task 0 as in progress and run
    update_task(0, "in_progress")

    # Run the crew
    result = crew.kickoff(inputs={"ticker": ticker})

    # Extract company name
    company_name = ticker
    for i, task_output in enumerate(result.tasks_output):
        section_name = SECTION_NAMES[i] if i < len(SECTION_NAMES) else ""
        if section_name in ("BUSINESS PROFILE", "BUSINESS PHASE"):
            lines = task_output.raw.split('\n')
            for line in lines:
                if 'Analysis:' in line and '(' in line:
                    try:
                        name_part = line.split('Analysis:')[1].strip()
                        if '(' in name_part:
                            company_name = name_part.split('(')[0].strip()
                            break
                    except Exception:
                        pass
            if company_name != ticker:
                break

    # Save markdown report
    report_md = f"{ticker}_report.md"
    with open(report_md, "w", encoding="utf-8") as f:
        f.write(f"# Investment Analysis Report: {ticker}\n\n")
        f.write(f"_Generated via CrewAI + FMP + Web Research tools._\n\n")
        f.write(f"_Run time (UTC): {datetime.utcnow().isoformat(timespec='seconds')}_\n\n")
        for i, task_output in enumerate(result.tasks_output):
            name = SECTION_NAMES[i] if i < len(SECTION_NAMES) else f"Section {i+1}"
            f.write(f"## {name}\n\n")
            f.write(task_output.raw.strip() + "\n\n")

    # Generate charts
    try:
        generate_revenue_charts(ticker, company_name)
    except Exception:
        pass

    # Generate PDFs
    equity_pdf = f"{ticker}_equity_research.pdf"
    memo_pdf = f"{ticker}_investment_memo.pdf"

    try:
        generate_equity_research_pdf(
            ticker=ticker,
            company_name=company_name,
            task_outputs=result.tasks_output,
            section_names=SECTION_NAMES,
            output_path=equity_pdf
        )
    except Exception:
        pass

    try:
        generate_hedge_fund_memo_pdf(
            ticker=ticker,
            company_name=company_name,
            task_outputs=result.tasks_output,
            section_names=SECTION_NAMES,
            output_path=memo_pdf
        )
    except Exception:
        pass

    return company_name


def main():
    if len(sys.argv) < 2:
        print("Usage: run_analysis.py <TICKER>")
        sys.exit(1)

    ticker = sys.argv[1].strip().upper()

    try:
        company_name = run_analysis(ticker)
        mark_complete(company_name=company_name)
    except Exception as e:
        mark_complete(error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
