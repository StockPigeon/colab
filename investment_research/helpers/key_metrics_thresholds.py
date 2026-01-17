"""Key metrics thresholds by business phase."""

from typing import Literal

# Metric categories
CATEGORIES = ["revenue", "profitability", "cash_balance", "vs_expectations", "capital_efficiency"]

# Phase names for display
PHASE_NAMES = {
    1: "STARTUP",
    2: "HYPERGROWTH",
    3: "SELF FUNDING",
    4: "OPERATING LEVERAGE",
    5: "CAPITAL RETURN",
    6: "DECLINE",
}

# Threshold definitions by phase
# Each metric has: name, thresholds (good/bad), inverse flag, format string
PHASE_THRESHOLDS = {
    1: {  # STARTUP
        "revenue": {
            "name": "Revenue",
            "key": "revenue",
            "good": 10_000_000,
            "bad": 1_000_000,
            "inverse": False,
            "format": "${:,.0f}",
            "format_suffix": "",
        },
        "profitability": {
            "name": "Gross Margin",
            "key": "gross_margin_pct",
            "good": 50,
            "bad": 20,
            "inverse": False,
            "format": "{:.1f}",
            "format_suffix": "%",
        },
        "cash_balance": {
            "name": "Cash Runway",
            "key": "cash_runway_months",
            "good": 18,
            "bad": 12,
            "inverse": False,
            "format": "{:.0f}",
            "format_suffix": " months",
        },
        "vs_expectations": {
            "name": "Revenue vs Estimate",
            "key": "revenue_surprise_pct",
            "good": 5,
            "bad": -5,
            "inverse": False,
            "format": "{:+.1f}",
            "format_suffix": "%",
        },
        "capital_efficiency": {
            "name": "Shares Outstanding YoY",
            "key": "shares_yoy_pct",
            "good": 10,
            "bad": 25,
            "inverse": True,  # Lower is better
            "format": "{:+.1f}",
            "format_suffix": "%",
        },
    },
    2: {  # HYPERGROWTH
        "revenue": {
            "name": "Revenue 3Y CAGR",
            "key": "revenue_cagr_3y",
            "good": 40,
            "bad": 20,
            "inverse": False,
            "format": "{:.1f}",
            "format_suffix": "%",
        },
        "profitability": {
            "name": "Gross Margin Direction",
            "key": "gross_margin_direction",
            "good": "Improving",
            "bad": "Declining",
            "inverse": False,
            "format": "{}",
            "format_suffix": "",
            "is_direction": True,
        },
        "cash_balance": {
            "name": "Cash Runway",
            "key": "cash_runway_months",
            "good": 18,
            "bad": 12,
            "inverse": False,
            "format": "{:.0f}",
            "format_suffix": " months",
        },
        "vs_expectations": {
            "name": "Revenue vs Estimate",
            "key": "revenue_surprise_pct",
            "good": 5,
            "bad": -5,
            "inverse": False,
            "format": "{:+.1f}",
            "format_suffix": "%",
        },
        "capital_efficiency": {
            "name": "Shares 3Y CAGR",
            "key": "shares_cagr_3y",
            "good": 5,
            "bad": 15,
            "inverse": True,
            "format": "{:+.1f}",
            "format_suffix": "%",
        },
    },
    3: {  # SELF FUNDING
        "revenue": {
            "name": "Revenue 3Y CAGR",
            "key": "revenue_cagr_3y",
            "good": 25,
            "bad": 10,
            "inverse": False,
            "format": "{:.1f}",
            "format_suffix": "%",
        },
        "profitability": {
            "name": "Gross Margin Direction",
            "key": "gross_margin_direction",
            "good": "Improving",
            "bad": "Declining",
            "inverse": False,
            "format": "{}",
            "format_suffix": "",
            "is_direction": True,
        },
        "cash_balance": {
            "name": "Operating Margin",
            "key": "operating_margin_pct",
            "good": 0,
            "bad": -5,
            "inverse": False,
            "format": "{:.1f}",
            "format_suffix": "%",
        },
        "vs_expectations": {
            "name": "Free Cash Flow",
            "key": "fcf",
            "good": 0,
            "bad": -1,  # Any negative is bad
            "inverse": False,
            "format": "${:,.0f}",
            "format_suffix": "",
            "is_fcf": True,
        },
        "capital_efficiency": {
            "name": "Shares 3Y CAGR",
            "key": "shares_cagr_3y",
            "good": 5,
            "bad": 10,
            "inverse": True,
            "format": "{:+.1f}",
            "format_suffix": "%",
        },
    },
    4: {  # OPERATING LEVERAGE
        "revenue": {
            "name": "Revenue 3Y CAGR",
            "key": "revenue_cagr_3y",
            "good": 15,
            "bad": 5,
            "inverse": False,
            "format": "{:.1f}",
            "format_suffix": "%",
        },
        "profitability": {
            "name": "Operating Margin",
            "key": "operating_margin_pct",
            "good": 20,
            "bad": 10,
            "inverse": False,
            "format": "{:.1f}",
            "format_suffix": "%",
        },
        "cash_balance": {
            "name": "FCF Margin",
            "key": "fcf_margin_pct",
            "good": 15,
            "bad": 5,
            "inverse": False,
            "format": "{:.1f}",
            "format_suffix": "%",
        },
        "vs_expectations": {
            "name": "EPS vs Estimate",
            "key": "eps_surprise_pct",
            "good": 5,
            "bad": -5,
            "inverse": False,
            "format": "{:+.1f}",
            "format_suffix": "%",
        },
        "capital_efficiency": {
            "name": "ROIC",
            "key": "roic_pct",
            "good": 15,
            "bad": 10,
            "inverse": False,
            "format": "{:.1f}",
            "format_suffix": "%",
        },
    },
    5: {  # CAPITAL RETURN
        "revenue": {
            "name": "Revenue 3Y CAGR",
            "key": "revenue_cagr_3y",
            "good": 5,
            "bad": 0,
            "inverse": False,
            "format": "{:.1f}",
            "format_suffix": "%",
        },
        "profitability": {
            "name": "FCF / Net Income",
            "key": "fcf_to_net_income_pct",
            "good": 80,
            "bad": 50,
            "inverse": False,
            "format": "{:.0f}",
            "format_suffix": "%",
        },
        "cash_balance": {
            "name": "Interest Coverage",
            "key": "interest_coverage",
            "good": 10,
            "bad": 5,
            "inverse": False,
            "format": "{:.1f}",
            "format_suffix": "x",
        },
        "vs_expectations": {
            "name": "ROIC",
            "key": "roic_pct",
            "good": 12,
            "bad": 8,
            "inverse": False,
            "format": "{:.1f}",
            "format_suffix": "%",
        },
        "capital_efficiency": {
            "name": "Capital Return Yield",
            "key": "capital_return_yield_pct",
            "good": 4,
            "bad": 2,
            "inverse": False,
            "format": "{:.1f}",
            "format_suffix": "%",
        },
    },
    6: {  # DECLINE - no metrics
        "revenue": None,
        "profitability": None,
        "cash_balance": None,
        "vs_expectations": None,
        "capital_efficiency": None,
    },
}


def score_metric(value, threshold_config: dict) -> Literal["🟢", "🟡", "🔴", "N/A"]:
    """
    Score a metric value against thresholds.

    Args:
        value: The metric value (can be numeric or string for direction metrics)
        threshold_config: Dict with 'good', 'bad', 'inverse', and optionally 'is_direction'

    Returns:
        Emoji score: 🟢 Good, 🟡 Neutral, 🔴 Bad, or N/A
    """
    if value is None or threshold_config is None:
        return "N/A"

    # Handle direction metrics (Improving/Stable/Declining)
    if threshold_config.get("is_direction"):
        if value == threshold_config["good"]:
            return "🟢"
        elif value == threshold_config["bad"]:
            return "🔴"
        return "🟡"

    # Handle FCF special case (positive = good, negative = bad)
    if threshold_config.get("is_fcf"):
        if value > 0:
            return "🟢"
        elif value < 0:
            return "🔴"
        return "🟡"

    good = threshold_config["good"]
    bad = threshold_config["bad"]
    inverse = threshold_config.get("inverse", False)

    if inverse:
        # Lower is better (e.g., share dilution)
        if value <= good:
            return "🟢"
        elif value >= bad:
            return "🔴"
        return "🟡"
    else:
        # Higher is better (most metrics)
        if value >= good:
            return "🟢"
        elif value <= bad:
            return "🔴"
        return "🟡"


def format_metric_value(value, threshold_config: dict) -> str:
    """Format a metric value for display."""
    if value is None or threshold_config is None:
        return "N/A"

    # Handle infinity for cash runway
    if isinstance(value, float) and value == float("inf"):
        return "∞"

    try:
        fmt = threshold_config.get("format", "{}")
        suffix = threshold_config.get("format_suffix", "")
        return fmt.format(value) + suffix
    except (ValueError, TypeError):
        return str(value)


def get_phase_metrics(phase: int) -> dict:
    """Get the threshold configuration for a specific phase."""
    return PHASE_THRESHOLDS.get(phase, PHASE_THRESHOLDS[6])


def get_phase_name(phase: int) -> str:
    """Get the display name for a phase."""
    return PHASE_NAMES.get(phase, "UNKNOWN")
