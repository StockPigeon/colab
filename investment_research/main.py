"""Main entry point for investment research analysis."""

import argparse
import json
import sys
from datetime import datetime

from .crew import InvestmentResearchCrew
from .helpers import load_and_validate_env, clear_cache, get_cache_stats
from .pdf import generate_equity_research_pdf, generate_hedge_fund_memo_pdf
from .tools import (
    fmp_news_tool,
    investment_data_tool,
    price_sentiment_data_tool,
    governance_data_tool,
    business_profile_tool,
)


# Tool registry for CLI access
TOOLS = {
    "fmp_news": fmp_news_tool,
    "investment_data": investment_data_tool,
    "price_sentiment": price_sentiment_data_tool,
    "governance_data": governance_data_tool,
    "business_profile": business_profile_tool,
}

# Section names for report output
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
    "INVESTMENT SCORECARD",
]


def run_tool(tool_name: str, ticker: str):
    """Run a single tool and print its output."""
    if tool_name not in TOOLS:
        print(f"Unknown tool: {tool_name}")
        print(f"Available tools: {list(TOOLS.keys())}")
        sys.exit(1)

    # Clear cache for fresh tool test
    clear_cache()

    tool = TOOLS[tool_name]
    print(f"\n### Running tool: {tool_name} for {ticker} ###\n")

    result = tool._run(ticker)

    # Pretty print JSON
    try:
        data = json.loads(result)
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except json.JSONDecodeError:
        print(result)

    # Print cache stats
    stats = get_cache_stats()
    print(f"\n[Cache] Hits: {stats['hits']}, Misses: {stats['misses']}, Hit Rate: {stats['hit_rate_pct']}%")


def run_task(task_name: str, ticker: str):
    """Run a single task and print its output."""
    # Clear cache for fresh task test
    clear_cache()

    crew = InvestmentResearchCrew()

    available_tasks = [
        "task_price_sentiment",
        "task_business_phase",
        "task_key_metrics",
        "task_business_profile",
        "task_business_moat",
        "task_execution_risk",
        "task_growth_drivers",
        "task_management_risk",
        "task_quant_valuation",
        "task_investment_scorecard",
    ]

    if task_name not in available_tasks:
        print(f"Unknown task: {task_name}")
        print(f"Available tasks: {available_tasks}")
        sys.exit(1)

    print(f"\n### Running task: {task_name} for {ticker} ###\n")
    result = crew.run_single_task(task_name, ticker)

    print("\n" + "=" * 60)
    print("TASK OUTPUT")
    print("=" * 60 + "\n")

    if hasattr(result, 'tasks_output') and result.tasks_output:
        print(result.tasks_output[0].raw)
    else:
        print(result)

    # Print cache stats
    stats = get_cache_stats()
    print(f"\n[Cache] Hits: {stats['hits']}, Misses: {stats['misses']}, Hit Rate: {stats['hit_rate_pct']}%")


def run_agent(agent_name: str, ticker: str):
    """Test a single agent with a default prompt."""
    # Clear cache for fresh agent test
    clear_cache()

    crew = InvestmentResearchCrew()

    available_agents = [
        "phase_classifier",
        "sentiment_analyst",
        "strategist",
        "governance_expert",
        "quant_auditor",
        "business_profile_analyst",
        "scorecard_analyst",
    ]

    if agent_name not in available_agents:
        print(f"Unknown agent: {agent_name}")
        print(f"Available agents: {available_agents}")
        sys.exit(1)

    print(f"\n### Testing agent: {agent_name} for {ticker} ###\n")
    result = crew.run_single_agent(agent_name, ticker)

    print("\n" + "=" * 60)
    print("AGENT OUTPUT")
    print("=" * 60 + "\n")

    if hasattr(result, 'tasks_output') and result.tasks_output:
        print(result.tasks_output[0].raw)
    else:
        print(result)

    # Print cache stats
    stats = get_cache_stats()
    print(f"\n[Cache] Hits: {stats['hits']}, Misses: {stats['misses']}, Hit Rate: {stats['hit_rate_pct']}%")


def run_full_analysis(ticker: str, no_pdf: bool = False):
    """Run the full investment research analysis."""
    # Clear cache for fresh analysis
    clear_cache()

    print(f"\n### Starting Full Analysis for {ticker} ###\n")

    crew = InvestmentResearchCrew()
    result = crew.crew().kickoff(inputs={"ticker": ticker})

    print("\n\n" + "=" * 60)
    print(f"FINAL CONSOLIDATED REPORT: {ticker}")
    print("=" * 60 + "\n")

    for i, task_output in enumerate(result.tasks_output):
        name = SECTION_NAMES[i] if i < len(SECTION_NAMES) else f"SECTION {i+1}"
        print(f"### {name} ###\n")
        print(task_output.raw)
        print("\n" + "-" * 40 + "\n")

    # Save markdown report
    report_md = f"{ticker}_report.md"
    equity_pdf = f"{ticker}_equity_research.pdf"
    memo_pdf = f"{ticker}_investment_memo.pdf"

    # Extract company name from the business profile section if available
    company_name = ticker
    for i, task_output in enumerate(result.tasks_output):
        if SECTION_NAMES[i] in ("BUSINESS PROFILE", "BUSINESS PHASE"):
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

    with open(report_md, "w", encoding="utf-8") as f:
        f.write(f"# Investment Analysis Report: {ticker}\n\n")
        f.write(f"_Generated via CrewAI + FMP + Web Research tools._\n\n")
        f.write(f"_Run time (UTC): {datetime.utcnow().isoformat(timespec='seconds')}_\n\n")

        for i, task_output in enumerate(result.tasks_output):
            name = SECTION_NAMES[i] if i < len(SECTION_NAMES) else f"Section {i+1}"
            f.write(f"## {name}\n\n")
            f.write(task_output.raw.strip() + "\n\n")

    print(f"Saved markdown to: {report_md}")

    if not no_pdf:
        # Generate Equity Research Style PDF
        try:
            generate_equity_research_pdf(
                ticker=ticker,
                company_name=company_name,
                task_outputs=result.tasks_output,
                section_names=SECTION_NAMES,
                output_path=equity_pdf
            )
            print(f"Saved Equity Research PDF to: {equity_pdf}")
        except Exception as e:
            print(f"Equity Research PDF generation failed: {e}")

        # Generate Hedge Fund Memo Style PDF
        try:
            generate_hedge_fund_memo_pdf(
                ticker=ticker,
                company_name=company_name,
                task_outputs=result.tasks_output,
                section_names=SECTION_NAMES,
                output_path=memo_pdf
            )
            print(f"Saved Investment Memo PDF to: {memo_pdf}")
        except Exception as e:
            print(f"Investment Memo PDF generation failed: {e}")

    # Print cache stats
    stats = get_cache_stats()
    print(f"\n[Cache] Hits: {stats['hits']}, Misses: {stats['misses']}, Hit Rate: {stats['hit_rate_pct']}%")

    return result


def main():
    """Main CLI entry point."""
    load_and_validate_env()

    import os
    print("OPENAI_API_KEY loaded:", bool(os.getenv("OPENAI_API_KEY")))
    print("FMP_API_KEY loaded:", bool(os.getenv("FMP_API_KEY")))

    parser = argparse.ArgumentParser(
        description="CrewAI Investment Analyzer - Modular stock research tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full analysis
  python -m investment_research.main --ticker AAPL

  # Skip PDF generation
  python -m investment_research.main --ticker AAPL --no-pdf

  # Test individual tool
  python -m investment_research.main --tool investment_data --ticker AAPL

  # Test individual task
  python -m investment_research.main --task task_business_moat --ticker AAPL

  # Test individual agent
  python -m investment_research.main --agent strategist --ticker AAPL

Available tools: fmp_news, investment_data, price_sentiment, governance_data, business_profile

Available tasks: task_price_sentiment, task_business_phase, task_key_metrics,
                 task_business_profile, task_business_moat, task_execution_risk,
                 task_growth_drivers, task_management_risk, task_quant_valuation,
                 task_investment_scorecard

Available agents: phase_classifier, sentiment_analyst, strategist,
                  governance_expert, quant_auditor, business_profile_analyst,
                  scorecard_analyst
        """
    )

    parser.add_argument("--ticker", type=str, default=None, help="Ticker symbol (e.g., AAPL)")
    parser.add_argument("--no-pdf", action="store_true", help="Skip PDF generation")
    parser.add_argument("--tool", type=str, help="Run a specific tool only")
    parser.add_argument("--task", type=str, help="Run a specific task only")
    parser.add_argument("--agent", type=str, help="Test a specific agent")

    args = parser.parse_args()

    # Get ticker - required for all operations
    ticker = args.ticker
    if not ticker:
        ticker = input("Enter a ticker symbol: ").strip().upper()
    else:
        ticker = ticker.strip().upper()

    if not ticker:
        print("Error: Ticker symbol is required")
        sys.exit(1)

    # Dispatch to appropriate handler
    if args.tool:
        run_tool(args.tool, ticker)
    elif args.task:
        run_task(args.task, ticker)
    elif args.agent:
        run_agent(args.agent, ticker)
    else:
        run_full_analysis(ticker, args.no_pdf)


if __name__ == "__main__":
    main()
