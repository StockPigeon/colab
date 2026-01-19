"""Research runner with progress tracking."""

import threading
import queue
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Callable, Any
from pathlib import Path


@dataclass
class TaskProgress:
    """Progress info for a single task."""
    task_id: str
    display_name: str
    agent_name: str
    status: str = "pending"  # pending, in_progress, completed, error
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class ProgressState:
    """Overall progress state for an analysis run."""
    ticker: str
    company_name: str = ""
    tasks: List[TaskProgress] = field(default_factory=list)
    is_running: bool = False
    is_complete: bool = False
    error: Optional[str] = None
    result: Any = None

    @property
    def total_tasks(self) -> int:
        return len(self.tasks)

    @property
    def completed_count(self) -> int:
        return sum(1 for t in self.tasks if t.status == "completed")

    @property
    def progress_percent(self) -> float:
        if self.total_tasks == 0:
            return 0
        return (self.completed_count / self.total_tasks) * 100

    @property
    def current_task(self) -> Optional[TaskProgress]:
        for t in self.tasks:
            if t.status == "in_progress":
                return t
        return None


# Task definitions with display names
TASK_INFO = [
    ("task_price_sentiment", "Analyzing Price & Sentiment", "sentiment_analyst"),
    ("task_business_phase", "Classifying Business Phase", "phase_classifier"),
    ("task_key_metrics", "Evaluating Key Metrics", "quant_auditor"),
    ("task_business_profile", "Analyzing Business Profile", "business_profile_analyst"),
    ("task_business_moat", "Identifying Competitive Moat", "strategist"),
    ("task_execution_risk", "Assessing Execution Risk", "governance_expert"),
    ("task_growth_drivers", "Finding Growth Drivers", "strategist"),
    ("task_management_risk", "Evaluating Management", "governance_expert"),
    ("task_visual_valuation", "Creating Valuation Charts", "valuation_analyst"),
    ("task_quant_valuation", "Calculating Valuation", "quant_auditor"),
    ("task_investment_scorecard", "Generating Scorecard", "scorecard_analyst"),
]


def create_initial_progress(ticker: str) -> ProgressState:
    """Create initial progress state with all tasks pending."""
    tasks = [
        TaskProgress(task_id=task_id, display_name=display_name, agent_name=agent)
        for task_id, display_name, agent in TASK_INFO
    ]
    return ProgressState(ticker=ticker, tasks=tasks)


class ResearchRunner:
    """
    Manages background execution of research analysis with progress tracking.

    Usage:
        runner = ResearchRunner()
        runner.start("AAPL")

        while not runner.is_complete:
            progress = runner.get_progress()
            # Update UI with progress
            time.sleep(1)

        result = runner.get_result()
    """

    def __init__(self):
        self.progress_state: Optional[ProgressState] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self.progress_state is not None and self.progress_state.is_running

    @property
    def is_complete(self) -> bool:
        with self._lock:
            return self.progress_state is not None and self.progress_state.is_complete

    def start(self, ticker: str) -> None:
        """Start analysis in a background thread."""
        if self.is_running:
            return

        # Initialize progress state
        with self._lock:
            self.progress_state = create_initial_progress(ticker)
            self.progress_state.is_running = True

        # Start background thread
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_analysis,
            args=(ticker,),
            daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        """Request stop of running analysis."""
        self._stop_event.set()

    def get_progress(self) -> Optional[ProgressState]:
        """Get current progress state (thread-safe copy)."""
        with self._lock:
            if self.progress_state is None:
                return None
            # Return a shallow copy to avoid race conditions
            return ProgressState(
                ticker=self.progress_state.ticker,
                company_name=self.progress_state.company_name,
                tasks=list(self.progress_state.tasks),
                is_running=self.progress_state.is_running,
                is_complete=self.progress_state.is_complete,
                error=self.progress_state.error,
                result=self.progress_state.result,
            )

    def get_result(self) -> Any:
        """Get the analysis result (after completion)."""
        with self._lock:
            if self.progress_state and self.progress_state.is_complete:
                return self.progress_state.result
        return None

    def _update_task_status(self, task_index: int, status: str) -> None:
        """Update a task's status (thread-safe)."""
        with self._lock:
            if self.progress_state and task_index < len(self.progress_state.tasks):
                task = self.progress_state.tasks[task_index]
                task.status = status
                if status == "in_progress":
                    task.started_at = datetime.now()
                elif status == "completed":
                    task.completed_at = datetime.now()

    def _run_analysis(self, ticker: str) -> None:
        """Run the actual analysis (in background thread)."""
        import sys
        import os

        # Add parent directory to path for imports
        parent_dir = str(Path(__file__).parent.parent.parent)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)

        try:
            # Import here to avoid circular imports
            from investment_research.crew import InvestmentResearchCrew
            from investment_research.helpers import load_and_validate_env, clear_cache
            from investment_research.pdf import (
                generate_equity_research_pdf,
                generate_hedge_fund_memo_pdf,
            )
            from investment_research.main import generate_revenue_charts, SECTION_NAMES

            # Load environment
            load_and_validate_env()
            clear_cache()

            # Create crew with callbacks
            crew_instance = InvestmentResearchCrew()

            # Mark first task as in progress
            self._update_task_status(0, "in_progress")

            # Run the crew - we'll track progress by intercepting task outputs
            crew = crew_instance.crew()

            # Unfortunately CrewAI doesn't expose easy task-level callbacks,
            # so we'll run the crew and track progress based on task completion
            result = crew.kickoff(inputs={"ticker": ticker})

            # Mark all tasks as completed
            for i in range(len(TASK_INFO)):
                self._update_task_status(i, "completed")

            # Extract company name from results
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

            with self._lock:
                if self.progress_state:
                    self.progress_state.company_name = company_name

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
            generate_revenue_charts(ticker, company_name)

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

            # Store result
            with self._lock:
                if self.progress_state:
                    self.progress_state.result = result
                    self.progress_state.is_complete = True
                    self.progress_state.is_running = False

        except Exception as e:
            with self._lock:
                if self.progress_state:
                    self.progress_state.error = str(e)
                    self.progress_state.is_complete = True
                    self.progress_state.is_running = False


# Singleton instance for Streamlit session
_runner_instance: Optional[ResearchRunner] = None


def get_runner() -> ResearchRunner:
    """Get or create the singleton runner instance."""
    global _runner_instance
    if _runner_instance is None:
        _runner_instance = ResearchRunner()
    return _runner_instance
