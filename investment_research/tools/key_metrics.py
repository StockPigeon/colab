"""Key Metrics Tool - Phase-specific financial metrics with scoring."""

import os
import json
from crewai.tools import tool

from ..helpers.http_client import get_json
from ..helpers.business_phase import compute_business_phase
from ..helpers.key_metrics_thresholds import (
    CATEGORIES,
    PHASE_THRESHOLDS,
    score_metric,
    format_metric_value,
    get_phase_name,
)


def _safe_div(numerator, denominator, default=None):
    """Safe division that handles None and zero."""
    if numerator is None or denominator is None or denominator == 0:
        return default
    return numerator / denominator


def _calculate_cagr(end_value, start_value, years):
    """Calculate compound annual growth rate."""
    if end_value is None or start_value is None or start_value <= 0 or years <= 0:
        return None
    try:
        return ((end_value / start_value) ** (1 / years) - 1) * 100
    except (ValueError, ZeroDivisionError):
        return None


def _get_direction(current, prior):
    """Determine if a metric is improving, stable, or declining."""
    if current is None or prior is None:
        return None
    if current > prior * 1.01:  # >1% improvement
        return "Improving"
    elif current < prior * 0.99:  # >1% decline
        return "Declining"
    return "Stable"


def _fetch_financial_data(symbol: str, api_key: str) -> dict:
    """Fetch all required financial data from FMP."""
    base_v3 = "https://financialmodelingprep.com/api/v3"

    # Profile for company name and market cap
    profile_resp = get_json(f"{base_v3}/profile/{symbol}", {"apikey": api_key})
    profile_data = profile_resp.get("data", []) if profile_resp.get("ok") else []
    profile = profile_data[0] if profile_data else {}

    # Income statement (5 years for CAGR)
    inc_resp = get_json(
        f"{base_v3}/income-statement/{symbol}",
        {"period": "annual", "limit": 5, "apikey": api_key},
    )
    income_data = inc_resp.get("data", []) if inc_resp.get("ok") else []

    # Cash flow statement (3 years)
    cf_resp = get_json(
        f"{base_v3}/cash-flow-statement/{symbol}",
        {"period": "annual", "limit": 3, "apikey": api_key},
    )
    cashflow_data = cf_resp.get("data", []) if cf_resp.get("ok") else []

    # Balance sheet (5 years for share dilution)
    bs_resp = get_json(
        f"{base_v3}/balance-sheet-statement/{symbol}",
        {"period": "annual", "limit": 5, "apikey": api_key},
    )
    balance_data = bs_resp.get("data", []) if bs_resp.get("ok") else []

    # Key metrics TTM (for ROIC)
    metrics_resp = get_json(f"{base_v3}/key-metrics-ttm/{symbol}", {"apikey": api_key})
    metrics_data = metrics_resp.get("data", []) if metrics_resp.get("ok") else []
    metrics_ttm = metrics_data[0] if metrics_data else {}

    # Analyst estimates
    estimates_resp = get_json(
        f"{base_v3}/analyst-estimates/{symbol}",
        {"limit": 1, "apikey": api_key},
    )
    estimates_data = estimates_resp.get("data", []) if estimates_resp.get("ok") else []
    estimates = estimates_data[0] if estimates_data else {}

    # Quote for current price
    quote_resp = get_json(f"{base_v3}/quote/{symbol}", {"apikey": api_key})
    quote_data = quote_resp.get("data", []) if quote_resp.get("ok") else []
    quote = quote_data[0] if quote_data else {}

    return {
        "profile": profile,
        "income": income_data,
        "cashflow": cashflow_data,
        "balance": balance_data,
        "metrics_ttm": metrics_ttm,
        "estimates": estimates,
        "quote": quote,
    }


def _calculate_all_metrics(data: dict) -> dict:
    """Calculate all possible metrics from the fetched data."""
    income = data.get("income", [])
    cashflow = data.get("cashflow", [])
    balance = data.get("balance", [])
    metrics_ttm = data.get("metrics_ttm", {})
    estimates = data.get("estimates", {})
    quote = data.get("quote", {})
    profile = data.get("profile", {})

    metrics = {}

    # Current period data
    inc_current = income[0] if income else {}
    inc_prior = income[1] if len(income) > 1 else {}
    inc_3y_ago = income[3] if len(income) > 3 else {}

    cf_current = cashflow[0] if cashflow else {}
    bs_current = balance[0] if balance else {}
    bs_3y_ago = balance[3] if len(balance) > 3 else {}

    # Revenue metrics
    metrics["revenue"] = inc_current.get("revenue")
    revenue_current = inc_current.get("revenue")
    revenue_3y_ago = inc_3y_ago.get("revenue")
    metrics["revenue_cagr_3y"] = _calculate_cagr(revenue_current, revenue_3y_ago, 3)

    # Gross margin metrics
    gross_profit = inc_current.get("grossProfit")
    gross_profit_prior = inc_prior.get("grossProfit")
    revenue_prior = inc_prior.get("revenue")

    metrics["gross_margin_pct"] = _safe_div(gross_profit, revenue_current, None)
    if metrics["gross_margin_pct"]:
        metrics["gross_margin_pct"] *= 100

    gm_current = _safe_div(gross_profit, revenue_current)
    gm_prior = _safe_div(gross_profit_prior, revenue_prior)
    metrics["gross_margin_direction"] = _get_direction(gm_current, gm_prior)

    # Operating margin
    operating_income = inc_current.get("operatingIncome")
    metrics["operating_margin_pct"] = _safe_div(operating_income, revenue_current, None)
    if metrics["operating_margin_pct"]:
        metrics["operating_margin_pct"] *= 100

    # Free cash flow metrics
    operating_cf = cf_current.get("operatingCashFlow")
    capex = cf_current.get("capitalExpenditure", 0)  # Usually negative
    fcf = None
    if operating_cf is not None:
        # CapEx is typically reported as negative, so we add it
        fcf = operating_cf + (capex if capex else 0)
    metrics["fcf"] = fcf

    metrics["fcf_margin_pct"] = _safe_div(fcf, revenue_current, None)
    if metrics["fcf_margin_pct"]:
        metrics["fcf_margin_pct"] *= 100

    # FCF to Net Income ratio
    net_income = inc_current.get("netIncome")
    if fcf is not None and net_income and net_income > 0:
        metrics["fcf_to_net_income_pct"] = (fcf / net_income) * 100
    else:
        metrics["fcf_to_net_income_pct"] = None

    # Cash runway (for unprofitable companies)
    cash = bs_current.get("cashAndCashEquivalents") or bs_current.get("cashAndShortTermInvestments")
    if operating_cf is not None and operating_cf < 0:
        monthly_burn = abs(operating_cf) / 12
        metrics["cash_runway_months"] = _safe_div(cash, monthly_burn)
    else:
        # Company is cash flow positive
        metrics["cash_runway_months"] = float("inf")

    # Shares outstanding metrics
    shares_current = bs_current.get("commonStockSharesOutstanding") or bs_current.get("weightedAverageShsOut")
    shares_prior = balance[1].get("commonStockSharesOutstanding") if len(balance) > 1 else None
    shares_3y_ago_val = bs_3y_ago.get("commonStockSharesOutstanding") if bs_3y_ago else None

    # YoY share growth
    if shares_current and shares_prior:
        metrics["shares_yoy_pct"] = ((shares_current / shares_prior) - 1) * 100
    else:
        metrics["shares_yoy_pct"] = None

    # 3Y share CAGR
    metrics["shares_cagr_3y"] = _calculate_cagr(shares_current, shares_3y_ago_val, 3)

    # Interest coverage
    ebit = inc_current.get("operatingIncome")  # EBIT ≈ Operating Income
    interest_expense = inc_current.get("interestExpense")
    if ebit and interest_expense and interest_expense > 0:
        metrics["interest_coverage"] = ebit / interest_expense
    elif ebit and (interest_expense == 0 or interest_expense is None):
        metrics["interest_coverage"] = float("inf")  # No debt
    else:
        metrics["interest_coverage"] = None

    # ROIC from FMP or calculate
    roic = metrics_ttm.get("roic")
    if roic:
        metrics["roic_pct"] = roic * 100 if roic < 1 else roic  # Handle decimal vs percentage
    else:
        # Try to calculate: NOPAT / Invested Capital
        tax_rate = 0.25  # Assume 25% if not available
        nopat = operating_income * (1 - tax_rate) if operating_income else None
        total_equity = bs_current.get("totalStockholdersEquity")
        total_debt = bs_current.get("totalDebt", 0)
        invested_capital = (total_equity or 0) + (total_debt or 0) - (cash or 0)
        metrics["roic_pct"] = _safe_div(nopat, invested_capital, None)
        if metrics["roic_pct"]:
            metrics["roic_pct"] *= 100

    # Revenue vs estimate
    estimated_revenue = estimates.get("estimatedRevenueAvg")
    actual_revenue = revenue_current
    if estimated_revenue and actual_revenue:
        metrics["revenue_surprise_pct"] = ((actual_revenue - estimated_revenue) / estimated_revenue) * 100
    else:
        metrics["revenue_surprise_pct"] = None

    # EPS vs estimate
    estimated_eps = estimates.get("estimatedEpsAvg")
    actual_eps = inc_current.get("eps") or inc_current.get("epsdiluted")
    if estimated_eps and actual_eps:
        metrics["eps_surprise_pct"] = ((actual_eps - estimated_eps) / abs(estimated_eps)) * 100 if estimated_eps != 0 else None
    else:
        metrics["eps_surprise_pct"] = None

    # Capital return yield
    dividends_paid = abs(cf_current.get("dividendsPaid", 0) or 0)
    buybacks = abs(cf_current.get("commonStockRepurchased", 0) or 0)
    total_capital_returned = dividends_paid + buybacks
    market_cap = quote.get("marketCap") or profile.get("mktCap")
    if market_cap and market_cap > 0:
        metrics["capital_return_yield_pct"] = (total_capital_returned / market_cap) * 100
    else:
        metrics["capital_return_yield_pct"] = None

    return metrics


def _determine_phase(data: dict) -> dict:
    """Determine business phase from financial data."""
    income = data.get("income", [])
    cashflow = data.get("cashflow", [])

    inc_current = income[0] if income else {}
    inc_prior = income[1] if len(income) > 1 else {}
    cf_current = cashflow[0] if cashflow else {}

    phase_inputs = {
        "revenue_current": inc_current.get("revenue"),
        "revenue_prior": inc_prior.get("revenue"),
        "op_income_current": inc_current.get("operatingIncome"),
        "op_income_prior": inc_prior.get("operatingIncome"),
        "dividends_paid": cf_current.get("dividendsPaid"),
        "buybacks": cf_current.get("commonStockRepurchased"),
    }

    return compute_business_phase(phase_inputs)


def _score_metrics_for_phase(metrics: dict, phase: int) -> list:
    """Score metrics based on phase-specific thresholds."""
    thresholds = PHASE_THRESHOLDS.get(phase, {})
    results = []

    for category in CATEGORIES:
        config = thresholds.get(category)
        if config is None:
            results.append({
                "category": category.replace("_", " ").title(),
                "metric_name": "N/A",
                "value": None,
                "formatted_value": "N/A",
                "score": "N/A",
            })
            continue

        metric_key = config["key"]
        value = metrics.get(metric_key)
        score = score_metric(value, config)
        formatted = format_metric_value(value, config)

        results.append({
            "category": category.replace("_", " ").title(),
            "metric_name": config["name"],
            "value": value,
            "formatted_value": formatted,
            "score": score,
        })

    return results


@tool("key_metrics_tool")
def key_metrics_tool(symbol: str) -> str:
    """
    Fetches and scores key financial metrics based on the company's business phase.

    Different metrics are evaluated depending on whether the company is in:
    - Phase 1 (Startup): Revenue, Gross Margin, Cash Runway, Revenue vs Estimate, Share Dilution
    - Phase 2 (Hypergrowth): Revenue CAGR, Gross Margin Direction, Cash Runway, Revenue vs Estimate, Share Dilution
    - Phase 3 (Self Funding): Revenue CAGR, Gross Margin Direction, Operating Margin, FCF, Share Dilution
    - Phase 4 (Operating Leverage): Revenue CAGR, Operating Margin, FCF Margin, EPS vs Estimate, ROIC
    - Phase 5 (Capital Return): Revenue CAGR, FCF/Net Income, Interest Coverage, ROIC, Capital Return Yield
    - Phase 6 (Decline): No metrics tracked

    Each metric is scored: 🟢 Good, 🟡 Neutral, 🔴 Bad

    Args:
        symbol: The stock ticker symbol (e.g., "AAPL", "MSFT")

    Returns:
        JSON string with phase-specific metrics and scores.
    """
    api_key = os.environ.get("FMP_API_KEY")
    if not api_key:
        return json.dumps({"error": "Missing FMP_API_KEY env var"}, indent=2)

    symbol = (symbol or "").strip().upper()
    if not symbol:
        return json.dumps({"error": "No symbol provided"}, indent=2)

    # Fetch all data
    data = _fetch_financial_data(symbol, api_key)

    # Get company info
    company_name = data.get("profile", {}).get("companyName", symbol)

    # Determine business phase
    phase_result = _determine_phase(data)
    phase = phase_result.get("phase", 6)
    phase_name = get_phase_name(phase)

    # Calculate all metrics
    all_metrics = _calculate_all_metrics(data)

    # Score metrics for this phase
    scored_metrics = _score_metrics_for_phase(all_metrics, phase)

    # Count scores
    green_count = sum(1 for m in scored_metrics if m["score"] == "🟢")
    yellow_count = sum(1 for m in scored_metrics if m["score"] == "🟡")
    red_count = sum(1 for m in scored_metrics if m["score"] == "🔴")
    total_scored = green_count + yellow_count + red_count

    output = {
        "symbol": symbol,
        "company_name": company_name,
        "business_phase": {
            "phase": phase,
            "phase_name": phase_name,
            "emoji": phase_result.get("emoji", ""),
            "rationale": phase_result.get("rationale", ""),
        },
        "metrics": scored_metrics,
        "summary": {
            "green_count": green_count,
            "yellow_count": yellow_count,
            "red_count": red_count,
            "total_scored": total_scored,
            "score_display": f"{green_count}/{total_scored} Green" if total_scored > 0 else "N/A",
        },
        "all_calculated_metrics": all_metrics,  # For debugging/transparency
    }

    return json.dumps(output, ensure_ascii=False, indent=2, default=str)
