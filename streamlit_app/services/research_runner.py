"""Research runner with file-based progress tracking for Streamlit."""

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Any


# Progress file location
PROGRESS_FILE = Path("/tmp/investment_research_progress.json")


@dataclass
class TaskProgress:
    """Progress info for a single task."""
    task_id: str
    display_name: str
    agent_name: str
    status: str = "pending"  # pending, in_progress, completed, error

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "display_name": self.display_name,
            "agent_name": self.agent_name,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            task_id=data["task_id"],
            display_name=data["display_name"],
            agent_name=data["agent_name"],
            status=data.get("status", "pending"),
        )


@dataclass
class ProgressState:
    """Overall progress state for an analysis run."""
    ticker: str
    company_name: str = ""
    tasks: List[TaskProgress] = field(default_factory=list)
    is_running: bool = False
    is_complete: bool = False
    error: Optional[str] = None
    current_task_index: int = 0

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

    def to_dict(self):
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "tasks": [t.to_dict() for t in self.tasks],
            "is_running": self.is_running,
            "is_complete": self.is_complete,
            "error": self.error,
            "current_task_index": self.current_task_index,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            ticker=data["ticker"],
            company_name=data.get("company_name", ""),
            tasks=[TaskProgress.from_dict(t) for t in data.get("tasks", [])],
            is_running=data.get("is_running", False),
            is_complete=data.get("is_complete", False),
            error=data.get("error"),
            current_task_index=data.get("current_task_index", 0),
        )


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


def save_progress(progress: ProgressState) -> None:
    """Save progress state to file."""
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress.to_dict(), f)


def load_progress() -> Optional[ProgressState]:
    """Load progress state from file."""
    if not PROGRESS_FILE.exists():
        return None
    try:
        with open(PROGRESS_FILE, "r") as f:
            data = json.load(f)
        return ProgressState.from_dict(data)
    except Exception:
        return None


def clear_progress() -> None:
    """Clear the progress file."""
    if PROGRESS_FILE.exists():
        PROGRESS_FILE.unlink()


def update_task_progress(task_index: int, status: str) -> None:
    """Update a specific task's progress."""
    progress = load_progress()
    if progress and task_index < len(progress.tasks):
        progress.tasks[task_index].status = status
        if status == "in_progress":
            progress.current_task_index = task_index
            # Mark previous tasks as completed
            for i in range(task_index):
                if progress.tasks[i].status != "completed":
                    progress.tasks[i].status = "completed"
        save_progress(progress)


def is_analysis_running() -> bool:
    """Check if an analysis is currently running."""
    progress = load_progress()
    return progress is not None and progress.is_running and not progress.is_complete


def start_analysis(ticker: str) -> bool:
    """
    Start the analysis in a background process.
    Returns True if started successfully.
    """
    if is_analysis_running():
        return False

    # Create initial progress
    progress = create_initial_progress(ticker)
    progress.is_running = True
    progress.tasks[0].status = "in_progress"
    save_progress(progress)

    # Get the path to the runner script
    runner_script = Path(__file__).parent / "run_analysis.py"

    # Start the analysis in a subprocess
    env = os.environ.copy()
    subprocess.Popen(
        [sys.executable, str(runner_script), ticker],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    return True


def get_progress() -> Optional[ProgressState]:
    """Get current progress state."""
    return load_progress()


# Keep these for backwards compatibility with existing code
class ResearchRunner:
    """Wrapper class for compatibility."""

    @property
    def is_running(self) -> bool:
        return is_analysis_running()

    @property
    def is_complete(self) -> bool:
        progress = load_progress()
        return progress is not None and progress.is_complete

    def start(self, ticker: str) -> None:
        start_analysis(ticker)

    def get_progress(self) -> Optional[ProgressState]:
        return load_progress()

    def reset(self) -> None:
        clear_progress()


_runner_instance: Optional[ResearchRunner] = None


def get_runner() -> ResearchRunner:
    """Get or create the runner instance."""
    global _runner_instance
    if _runner_instance is None:
        _runner_instance = ResearchRunner()
    return _runner_instance
