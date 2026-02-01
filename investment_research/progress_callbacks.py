"""Progress callbacks for CrewAI task execution.

This module provides callbacks that update the progress file
as each CrewAI task completes, enabling real-time progress tracking
in the Streamlit UI.
"""

import json
from pathlib import Path
from typing import Callable, Optional


# Progress file path (must match research_runner.py)
PROGRESS_FILE = Path("/tmp/investment_research_progress.json")

# Task order - must match TASK_INFO in research_runner.py
TASK_ORDER = [
    "task_price_sentiment",
    "task_business_phase",
    "task_key_metrics",
    "task_business_profile",
    "task_business_moat",
    "task_execution_risk",
    "task_growth_drivers",
    "task_management_risk",
    "task_visual_valuation",
    "task_quant_valuation",
    "task_investment_scorecard",
]


def load_progress() -> Optional[dict]:
    """Load progress data from file."""
    if not PROGRESS_FILE.exists():
        return None
    try:
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def save_progress(data: dict) -> None:
    """Save progress data to file."""
    try:
        with open(PROGRESS_FILE, "w") as f:
            json.dump(data, f)
    except IOError:
        pass  # Fail silently - progress tracking is non-critical


def update_task_status(task_index: int, status: str) -> None:
    """
    Update a task's status in the progress file.

    Args:
        task_index: Index of the task (0-10)
        status: New status ('pending', 'in_progress', 'completed')
    """
    data = load_progress()
    if not data:
        return

    tasks = data.get("tasks", [])
    if task_index >= len(tasks):
        return

    tasks[task_index]["status"] = status
    data["current_task_index"] = task_index

    # When marking a task in_progress, ensure all previous tasks are completed
    if status == "in_progress":
        for i in range(task_index):
            if tasks[i]["status"] != "completed":
                tasks[i]["status"] = "completed"

    save_progress(data)


def create_task_callback(task_name: str) -> Callable:
    """
    Create a callback function for a specific CrewAI task.

    The callback is invoked when the task completes. It updates
    the progress file to mark this task as completed and the
    next task as in_progress.

    Args:
        task_name: Name of the task (e.g., 'task_price_sentiment' or 'blue_price_sentiment')

    Returns:
        Callback function compatible with CrewAI Task.callback
    """
    # Normalize task name - strip team prefix (blue_/red_) and add task_ prefix if needed
    normalized_name = task_name
    for prefix in ("blue_", "red_"):
        if task_name.startswith(prefix):
            normalized_name = "task_" + task_name[len(prefix):]
            break

    # If no team prefix, ensure task_ prefix exists
    if not normalized_name.startswith("task_"):
        normalized_name = "task_" + normalized_name

    try:
        task_index = TASK_ORDER.index(normalized_name)
    except ValueError:
        # Unknown task - return no-op callback
        return lambda output: None

    def callback(output):
        """Called when task completes."""
        # Mark current task as completed
        update_task_status(task_index, "completed")

        # Mark next task as in_progress (if there is one)
        next_index = task_index + 1
        if next_index < len(TASK_ORDER):
            update_task_status(next_index, "in_progress")

    return callback
