"""Main entry point for investment research analysis."""

import argparse
import json
import sys
from datetime import datetime

from .crew import InvestmentResearchCrew
from .crew_parallel import ParallelInvestmentResearchCrew
from .helpers import load_and_validate_env, clear_cache, get_cache_stats
from .pdf import generate_equity_research_pdf, generate_hedge_fund_memo_pdf
from .pdf.unified_report import UnifiedReportGenerator
from .charts import generate_product_segment_chart, generate_geographic_segment_chart
from .tools import (
    investment_data_tool,
    price_sentiment_data_tool,
    governance_data_tool,
    business_profile_tool,
)


# Tool registry for CLI access
TOOLS = {
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


def generate_revenue_charts(ticker: str, company_name: str) -> dict:
    """
    Generate revenue breakdown charts using business profile data.

    Args:
        ticker: Stock ticker symbol
        company_name: Company name for chart titles

    Returns:
        Dictionary with paths to generated charts
    """
    charts = {"product_segments": None, "geographic_segments": None}

    try:
        # Fetch business profile data
        profile_json = business_profile_tool._run(ticker)
        profile_data = json.loads(profile_json)

        # Generate product segment chart
        product_segments = profile_data.get("product_segments", [])
        if product_segments:
            chart_path = generate_product_segment_chart(
                symbol=ticker,
                company_name=company_name,
                product_segments=product_segments,
                output_dir="reports/charts"
            )
            if chart_path:
                charts["product_segments"] = chart_path
                print(f"  Generated product segment chart: {chart_path}")

        # Generate geographic segment chart
        geo_segments = profile_data.get("geographic_segments", [])
        if geo_segments:
            chart_path = generate_geographic_segment_chart(
                symbol=ticker,
                company_name=company_name,
                geo_segments=geo_segments,
                output_dir="reports/charts"
            )
            if chart_path:
                charts["geographic_segments"] = chart_path
                print(f"  Generated geographic segment chart: {chart_path}")

    except Exception as e:
        print(f"  Warning: Could not generate revenue charts: {e}")

    return charts


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

    # Generate revenue breakdown charts
    print("\nGenerating revenue breakdown charts...")
    revenue_charts = generate_revenue_charts(ticker, company_name)

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


def run_parallel_red_blue_analysis(ticker: str, no_pdf: bool = False):
    """Run Red/Blue team parallel analysis with CIO synthesis."""
    print(f"\n### Starting Red/Blue Team Parallel Analysis for {ticker} ###\n")
    print("This will run TWO complete analyses simultaneously:")
    print("  - BLUE TEAM (Optimistic/Bull Case)")
    print("  - RED TEAM (Skeptical/Bear Case)")
    print("Then synthesize with a CIO for independent recommendation.\n")

    # Clear cache for fresh analysis
    clear_cache()

    # Initialize parallel crew
    crew = ParallelInvestmentResearchCrew()

    # Run Red/Blue analysis
    results = crew.run_full_analysis(ticker)

    print("\n\n" + "=" * 60)
    print(f"ANALYSIS COMPLETE: {ticker}")
    print("=" * 60 + "\n")

    # Extract company name (try to get from one of the outputs)
    company_name = ticker
    if results['blue'] and hasattr(results['blue'], 'tasks_output'):
        for task_output in results['blue'].tasks_output:
            if 'Analysis:' in str(task_output.raw):
                try:
                    lines = str(task_output.raw).split('\n')
                    for line in lines:
                        if 'Analysis:' in line and '(' in line:
                            name_part = line.split('Analysis:')[1].strip()
                            if '(' in name_part:
                                company_name = name_part.split('(')[0].strip()
                                break
                except Exception:
                    pass
            if company_name != ticker:
                break

    # Generate unified report
    if not no_pdf:
        print("\nGenerating unified investment research report...")
        try:
            report_gen = UnifiedReportGenerator()
            pdf_path = report_gen.generate_report(
                ticker=ticker,
                company_name=company_name,
                blue_output=results['blue'],
                red_output=results['red'],
                cio_synthesis=results['cio']
            )
            print(f"✅ Unified Report saved: {pdf_path}")
        except Exception as e:
            print(f"❌ Report generation failed: {e}")
            import traceback
            traceback.print_exc()

    # Save outputs to JSON for debugging
    debug_file = f"{ticker}_debug_outputs.json"
    try:
        with open(debug_file, "w", encoding="utf-8") as f:
            json.dump({
                "ticker": ticker,
                "company_name": company_name,
                "cio_synthesis": results['cio'],
                "blue_sections": len(results['blue'].tasks_output) if hasattr(results['blue'], 'tasks_output') else 0,
                "red_sections": len(results['red'].tasks_output) if hasattr(results['red'], 'tasks_output') else 0,
                "timestamp": datetime.utcnow().isoformat()
            }, f, indent=2)
        print(f"✅ Debug outputs saved: {debug_file}")
    except Exception as e:
        print(f"⚠️  Could not save debug outputs: {e}")

    # Print cache stats
    stats = get_cache_stats()
    print(f"\n[Cache] Hits: {stats['hits']}, Misses: {stats['misses']}, Hit Rate: {stats['hit_rate_pct']}%")

    return results


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
  # Red/Blue team parallel analysis (RECOMMENDED - faster and less biased)
  python -m investment_research.main --ticker AAPL --parallel

  # Standard sequential analysis
  python -m investment_research.main --ticker AAPL

  # Skip PDF generation
  python -m investment_research.main --ticker AAPL --parallel --no-pdf

  # Test individual tool
  python -m investment_research.main --tool investment_data --ticker AAPL

  # Test individual task
  python -m investment_research.main --task task_business_moat --ticker AAPL

  # Test individual agent
  python -m investment_research.main --agent strategist --ticker AAPL

Available tools: investment_data, price_sentiment, governance_data, business_profile

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
    parser.add_argument("--parallel", action="store_true", help="Use Red/Blue team parallel analysis (recommended)")
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
    elif args.parallel:
        print("\n🚀 Using Red/Blue Team Parallel Analysis (Enhanced Mode)")
        run_parallel_red_blue_analysis(ticker, args.no_pdf)
    else:
        print("\n📊 Using Standard Sequential Analysis")
        print("💡 Tip: Use --parallel for faster Red/Blue team analysis\n")
        run_full_analysis(ticker, args.no_pdf)


if __name__ == "__main__":
    main()
