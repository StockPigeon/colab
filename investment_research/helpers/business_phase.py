"""Business phase classification logic."""


def compute_business_phase(phase_inputs: dict) -> dict:
    """
    Decision tree for business lifecycle phase classification.

    Phases:
    - Phase 1: STARTUP - Losses expanding
    - Phase 2: HYPERGROWTH - Losses improving
    - Phase 3: SELF FUNDING - Near breakeven
    - Phase 4: OPERATING LEVERAGE - Profitable with growing revenue
    - Phase 5: CAPITAL RETURN - Dividends or buybacks present
    - Phase 6: DECLINE - Revenue declining with positive operating income

    Args:
        phase_inputs: Dictionary with financial metrics:
            - revenue_current: Current period revenue
            - revenue_prior: Prior period revenue
            - op_income_current: Current operating income
            - op_income_prior: Prior operating income
            - dividends_paid: Dividends paid (usually negative)
            - buybacks: Stock repurchases (usually negative)

    Returns:
        Dictionary with phase classification and supporting data
    """
    rev_now = phase_inputs.get("revenue_current")
    rev_prev = phase_inputs.get("revenue_prior")
    op_now = phase_inputs.get("op_income_current")
    op_prev = phase_inputs.get("op_income_prior")
    dividends_paid = phase_inputs.get("dividends_paid")
    buybacks = phase_inputs.get("buybacks")

    # Capital returns flag
    capital_returns = False
    capital_details = []
    # Cash flow fields are often negative when paid out
    if isinstance(dividends_paid, (int, float)) and dividends_paid != 0:
        capital_returns = True
        capital_details.append(f"DividendsPaid={dividends_paid:,.0f}")
    if isinstance(buybacks, (int, float)) and buybacks != 0:
        capital_returns = True
        capital_details.append(f"CommonStockRepurchased={buybacks:,.0f}")

    # Revenue growth
    rev_growth = None
    if isinstance(rev_now, (int, float)) and isinstance(rev_prev, (int, float)) and rev_prev != 0:
        rev_growth = (rev_now - rev_prev) / abs(rev_prev)

    # Operating margin for breakeven detection
    op_margin = None
    if isinstance(op_now, (int, float)) and isinstance(rev_now, (int, float)) and rev_now != 0:
        op_margin = op_now / rev_now  # e.g., 0.10 = 10%

    have_core = (rev_now is not None and rev_prev is not None and op_now is not None and op_prev is not None)
    have_capital = (dividends_paid is not None or buybacks is not None)

    if capital_returns:
        phase = 5
        name = "CAPITAL RETURN"
        emoji = "💰"
        rationale = "Returning capital (dividends or buybacks)."
    else:
        if not have_core:
            phase = None
            name = "UNKNOWN"
            emoji = "❓"
            rationale = "Insufficient data to classify reliably."
        else:
            near_breakeven = (op_margin is not None and abs(op_margin) <= 0.03)

            if op_now < 0:
                if near_breakeven:
                    phase = 3
                    name = "SELF FUNDING"
                    emoji = "🧩"
                    rationale = "Near breakeven operating income (self-funding zone)."
                else:
                    if op_prev is not None and op_now < op_prev:
                        phase = 1
                        name = "STARTUP"
                        emoji = "🚀"
                        rationale = "Losses expanding."
                    else:
                        phase = 2
                        name = "HYPERGROWTH"
                        emoji = "⚡"
                        rationale = "Losses improving."
            else:
                if rev_growth is not None and rev_growth < 0:
                    phase = 6
                    name = "DECLINE"
                    emoji = "📉"
                    rationale = "Revenue declining."
                else:
                    if near_breakeven:
                        phase = 3
                        name = "SELF FUNDING"
                        emoji = "🧩"
                        rationale = "Near breakeven operating income (self-funding zone)."
                    else:
                        phase = 4
                        name = "OPERATING LEVERAGE"
                        emoji = "📈"
                        rationale = "Profitable with stable/growing revenue."

    if phase is None:
        confidence = "❌ Low"
    else:
        if have_core and have_capital:
            confidence = "✅ High"
        elif have_core:
            confidence = "⚠️ Medium"
        else:
            confidence = "❌ Low"

    return {
        "phase": phase,
        "phase_name": name,
        "emoji": emoji,
        "confidence": confidence,
        "rationale": rationale,
        "capital_returns": {
            "yes": capital_returns,
            "details": capital_details
        },
        "computed": {
            "revenue_growth_yoy": rev_growth,
            "operating_margin": op_margin
        }
    }
