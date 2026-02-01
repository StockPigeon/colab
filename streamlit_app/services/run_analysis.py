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


def run_analysis(ticker: str, use_parallel: bool = True):
    """Run the full analysis with progress updates.

    Args:
        ticker: Stock ticker symbol
        use_parallel: If True, use Red/Blue team parallel analysis (recommended)
    """
    from dotenv import load_dotenv
    load_dotenv()

    from investment_research.helpers import load_and_validate_env, clear_cache
    from investment_research.main import generate_revenue_charts

    # Load environment
    load_and_validate_env()
    clear_cache()

    if use_parallel:
        # Use Red/Blue team parallel analysis
        from investment_research.crew_parallel import ParallelInvestmentResearchCrew
        from investment_research.pdf.unified_report import UnifiedReportGenerator

        # Create parallel crew
        crew_instance = ParallelInvestmentResearchCrew()

        # Note: Task 0 is already marked as in_progress by research_runner.py
        # Progress updates are now handled by CrewAI task callbacks in crew.py

        # Run the crew (Red/Blue + CIO)
        results = crew_instance.run_full_analysis(ticker)

        # results contains: blue, red, cio
        result = results['blue']  # For backward compatibility with company name extraction
        cio_synthesis = results['cio']
        red_output = results['red']
        blue_output = results['blue']
    else:
        # Use standard sequential analysis
        from investment_research.crew import InvestmentResearchCrew
        crew_instance = InvestmentResearchCrew()
        crew = crew_instance.crew()

        # Run the crew
        result = crew.kickoff(inputs={"ticker": ticker})
        cio_synthesis = None
        red_output = None
        blue_output = None

    # Extract company name from task outputs
    company_name = ticker
    if hasattr(result, 'tasks_output') and result.tasks_output:
        # Search all task outputs for company name (parallel mode may have different ordering)
        for task_output in result.tasks_output:
            if not hasattr(task_output, 'raw'):
                continue
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
        if hasattr(result, 'tasks_output') and result.tasks_output:
            for i, task_output in enumerate(result.tasks_output):
                name = SECTION_NAMES[i] if i < len(SECTION_NAMES) else f"Section {i+1}"
                if hasattr(task_output, 'raw'):
                    f.write(f"## {name}\n\n")
                    f.write(task_output.raw.strip() + "\n\n")

    # Generate charts
    try:
        generate_revenue_charts(ticker, company_name)
    except Exception:
        pass

    # Generate report(s)
    if use_parallel and cio_synthesis:
        # Generate single unified report
        from investment_research.pdf.unified_report import UnifiedReportGenerator

        unified_pdf = f"{ticker}_Investment_Research_Report.pdf"

        try:
            report_gen = UnifiedReportGenerator()
            report_gen.generate_report(
                ticker=ticker,
                company_name=company_name,
                blue_output=blue_output,
                red_output=red_output,
                cio_synthesis=cio_synthesis,
                output_path=unified_pdf
            )
        except Exception as e:
            print(f"Warning: Unified report generation failed: {e}")
            # Log the warning to progress file so users can see it
            data = load_progress()
            if data:
                data["pdf_warning"] = f"PDF generation failed: {e}"
                save_progress(data)

        # Upload unified report to cloud storage
        try:
            from streamlit_app.services.storage import get_storage_service
            import glob

            storage = get_storage_service()
            if storage:
                # Find chart files for this ticker
                chart_files = [Path(p) for p in glob.glob(f"reports/charts/{ticker}*.png")]

                # Upload unified report
                storage.upload_report(
                    ticker=ticker,
                    company_name=company_name,
                    markdown_path=Path(report_md) if Path(report_md).exists() else None,
                    equity_pdf_path=Path(unified_pdf) if Path(unified_pdf).exists() else None,
                    memo_pdf_path=None,  # No memo PDF in parallel mode
                    chart_paths=chart_files,
                )
        except Exception as e:
            # Cloud storage upload is optional - don't fail the analysis
            print(f"Note: Could not upload to cloud storage: {e}")

    else:
        # Generate old-style reports for backward compatibility
        from investment_research.pdf import (
            generate_equity_research_pdf,
            generate_hedge_fund_memo_pdf,
        )

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
        except Exception as e:
            print(f"Warning: Equity research PDF generation failed: {e}")
            data = load_progress()
            if data:
                data["pdf_warning"] = f"Equity PDF generation failed: {e}"
                save_progress(data)

        try:
            generate_hedge_fund_memo_pdf(
                ticker=ticker,
                company_name=company_name,
                task_outputs=result.tasks_output,
                section_names=SECTION_NAMES,
                output_path=memo_pdf
            )
        except Exception as e:
            print(f"Warning: Investment memo PDF generation failed: {e}")
            data = load_progress()
            if data:
                data["pdf_warning"] = f"Memo PDF generation failed: {e}"
                save_progress(data)

        # Upload reports to cloud storage (if configured)
        try:
            from streamlit_app.services.storage import get_storage_service
            import glob

            storage = get_storage_service()
            if storage:
                # Find chart files for this ticker
                chart_files = [Path(p) for p in glob.glob(f"reports/charts/{ticker}*.png")]

                storage.upload_report(
                    ticker=ticker,
                    company_name=company_name,
                    markdown_path=Path(report_md) if Path(report_md).exists() else None,
                    equity_pdf_path=Path(equity_pdf) if Path(equity_pdf).exists() else None,
                    memo_pdf_path=Path(memo_pdf) if Path(memo_pdf).exists() else None,
                    chart_paths=chart_files,
                )
        except Exception as e:
            # Cloud storage upload is optional - don't fail the analysis
            print(f"Note: Could not upload to cloud storage: {e}")

    return company_name


def main():
    if len(sys.argv) < 2:
        print("Usage: run_analysis.py <TICKER> [--sequential]")
        sys.exit(1)

    ticker = sys.argv[1].strip().upper()

    # Check for --sequential flag
    use_parallel = "--sequential" not in sys.argv

    try:
        print(f"Running {'Red/Blue Parallel' if use_parallel else 'Sequential'} analysis for {ticker}")
        company_name = run_analysis(ticker, use_parallel=use_parallel)
        mark_complete(company_name=company_name)
    except Exception as e:
        import traceback
        traceback.print_exc()
        mark_complete(error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
