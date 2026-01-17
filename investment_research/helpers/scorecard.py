"""Scorecard scoring logic for investment research reports."""

import re
from typing import Optional


# Scoring criteria for each section
SCORING_RULES = {
    "price_sentiment": {
        "outlook_scores": {
            "bullish": 5,
            "neutral": 3,
            "bearish": 1,
        },
        "description": "Based on 12-month outlook and sentiment consensus",
    },
    "business_phase": {
        "confidence_scores": {
            "high": 5,
            "medium": 3,
            "low": 1,
        },
        "description": "Based on phase classification confidence",
    },
    "key_metrics": {
        "green_weight": 1,
        "yellow_weight": 0.5,
        "red_weight": 0,
        "max_score": 5,
        "description": "Based on count of green/yellow/red metrics",
    },
    "business_profile": {
        "pricing_power": {
            "can increase prices": 2,
            "would lose customers": 1,
            "price taker": 0,
        },
        "recession_sensitivity": {
            "recession-proof": 2,
            "normal": 1,
            "highly cyclical": 0,
        },
        "purchase_frequency": {
            "recurring": 1,
            "yearly": 0.5,
            "every few years": 0,
        },
        "description": "Based on business characteristics favorability",
    },
    "business_moat": {
        "moat_size": {
            "wide": 4,
            "narrow": 2,
            "none": 0,
        },
        "moat_direction": {
            "widening": 1,
            "stable": 0,
            "narrowing": -1,
        },
        "description": "Based on moat size and direction",
    },
    "execution_risk": {
        "green_value": 1.25,  # 4 greens = 5 points
        "yellow_value": 0.75,
        "red_value": 0.25,
        "description": "Based on 4-factor risk assessment (inverted)",
    },
    "growth_drivers": {
        "strong_value": 1,  # 7 strongs = 7, scaled to 5
        "moderate_value": 0.5,
        "weak_value": 0,
        "scale_factor": 5 / 7,
        "description": "Based on 7 growth driver strengths",
    },
    "management_risk": {
        "alignment_scores": {
            "well-aligned": 5,
            "neutral": 3,
            "misaligned": 1,
        },
        "description": "Based on management alignment and risk severity",
    },
    "valuation": {
        "match_scores": {
            "undervalued": 5,
            "fairly valued": 3,
            "overvalued": 1,
        },
        "description": "Based on story vs numbers match and valuation conclusion",
    },
}

# Grade thresholds (max score = 45)
GRADE_THRESHOLDS = {
    "A": (40, 45, "Strong Buy"),
    "B": (32, 39, "Buy"),
    "C": (23, 31, "Hold"),
    "D": (14, 22, "Underweight"),
    "F": (0, 13, "Avoid"),
}


def parse_score_block(text: str) -> Optional[dict]:
    """
    Parse the standardized score block from task output.

    Expected format:
    ---
    ### Section Score
    **Score:** [1-5]/5
    **Confidence:** High/Medium/Low
    **Key Factor:** [description]
    ---

    Args:
        text: Task output text

    Returns:
        Dictionary with score, confidence, and key_factor, or None if not found
    """
    # Look for the score block pattern
    score_pattern = r"\*\*Score:\*\*\s*(\d)/5"
    confidence_pattern = r"\*\*Confidence:\*\*\s*(High|Medium|Low)"
    key_factor_pattern = r"\*\*Key Factor:\*\*\s*(.+?)(?:\n|---)"

    score_match = re.search(score_pattern, text, re.IGNORECASE)
    confidence_match = re.search(confidence_pattern, text, re.IGNORECASE)
    key_factor_match = re.search(key_factor_pattern, text, re.IGNORECASE | re.DOTALL)

    if score_match:
        return {
            "score": int(score_match.group(1)),
            "confidence": confidence_match.group(1) if confidence_match else "Medium",
            "key_factor": key_factor_match.group(1).strip() if key_factor_match else "",
        }
    return None


def count_emoji_scores(text: str) -> dict:
    """
    Count green, yellow, and red emoji indicators in text.

    Args:
        text: Task output text

    Returns:
        Dictionary with counts of each color
    """
    return {
        "green": len(re.findall(r"🟢", text)),
        "yellow": len(re.findall(r"🟡", text)),
        "red": len(re.findall(r"🔴", text)),
    }


def extract_outlook(text: str) -> str:
    """
    Extract outlook assessment from price sentiment output.

    Args:
        text: Task output text

    Returns:
        "bullish", "neutral", or "bearish"
    """
    text_lower = text.lower()
    if "🟢 bullish" in text_lower or "bullish" in text_lower[:500]:
        return "bullish"
    elif "🔴 bearish" in text_lower or "bearish" in text_lower[:500]:
        return "bearish"
    return "neutral"


def extract_confidence_level(text: str) -> str:
    """
    Extract confidence level from business phase output.

    Args:
        text: Task output text

    Returns:
        "high", "medium", or "low"
    """
    text_lower = text.lower()
    if "✅ high" in text_lower or "confidence level** | ✅ high" in text_lower:
        return "high"
    elif "❌ low" in text_lower or "confidence level** | ❌ low" in text_lower:
        return "low"
    return "medium"


def extract_moat_assessment(text: str) -> tuple[str, str]:
    """
    Extract moat size and direction from moat analysis output.

    Args:
        text: Task output text

    Returns:
        Tuple of (moat_size, moat_direction)
    """
    text_lower = text.lower()

    # Moat size
    if "wide" in text_lower and "🛡️" in text:
        moat_size = "wide"
    elif "narrow" in text_lower and "🥈" in text:
        moat_size = "narrow"
    else:
        moat_size = "none"

    # Moat direction
    if "widening" in text_lower and "↗️" in text:
        direction = "widening"
    elif "narrowing" in text_lower and "↘️" in text:
        direction = "narrowing"
    else:
        direction = "stable"

    return moat_size, direction


def extract_valuation_conclusion(text: str) -> str:
    """
    Extract valuation conclusion from valuation output.

    Args:
        text: Task output text

    Returns:
        "undervalued", "fairly valued", or "overvalued"
    """
    text_lower = text.lower()
    if "undervalued" in text_lower:
        return "undervalued"
    elif "overvalued" in text_lower:
        return "overvalued"
    return "fairly valued"


def extract_alignment(text: str) -> str:
    """
    Extract management alignment from management risk output.

    Args:
        text: Task output text

    Returns:
        "well-aligned", "neutral", or "misaligned"
    """
    text_lower = text.lower()
    if "🟢 well-aligned" in text_lower or "well-aligned" in text_lower[:1000]:
        return "well-aligned"
    elif "🔴 misaligned" in text_lower or "misaligned" in text_lower[:1000]:
        return "misaligned"
    return "neutral"


def calculate_section_score(section_name: str, task_output: str) -> dict:
    """
    Calculate score for a section based on its output.

    Args:
        section_name: Name of the section (e.g., "price_sentiment")
        task_output: Raw task output text

    Returns:
        Dictionary with score (1-5), confidence, and key_factor
    """
    # First try to parse embedded score block
    parsed = parse_score_block(task_output)
    if parsed:
        return parsed

    # Otherwise, calculate based on section-specific logic
    rules = SCORING_RULES.get(section_name, {})
    score = 3  # Default neutral
    confidence = "Medium"
    key_factor = ""

    if section_name == "price_sentiment":
        outlook = extract_outlook(task_output)
        score = rules.get("outlook_scores", {}).get(outlook, 3)
        key_factor = f"12-month outlook: {outlook}"

    elif section_name == "business_phase":
        conf = extract_confidence_level(task_output)
        score = rules.get("confidence_scores", {}).get(conf, 3)
        key_factor = f"Phase confidence: {conf}"

    elif section_name == "key_metrics":
        counts = count_emoji_scores(task_output)
        raw_score = (
            counts["green"] * rules.get("green_weight", 1)
            + counts["yellow"] * rules.get("yellow_weight", 0.5)
            + counts["red"] * rules.get("red_weight", 0)
        )
        # Normalize to 1-5 scale (assuming 5 metrics max)
        score = min(5, max(1, round(raw_score)))
        key_factor = f"{counts['green']} green, {counts['yellow']} yellow, {counts['red']} red"

    elif section_name == "business_profile":
        # This needs manual scoring based on characteristics
        score = 3  # Default, will be overridden by embedded score
        key_factor = "Business characteristics assessment"

    elif section_name == "business_moat":
        moat_size, direction = extract_moat_assessment(task_output)
        base_score = rules.get("moat_size", {}).get(moat_size, 2)
        direction_adj = rules.get("moat_direction", {}).get(direction, 0)
        score = min(5, max(1, base_score + direction_adj))
        key_factor = f"Moat: {moat_size}, Direction: {direction}"

    elif section_name == "execution_risk":
        counts = count_emoji_scores(task_output)
        # Invert: more greens = higher score
        raw_score = (
            counts["green"] * rules.get("green_value", 1.25)
            + counts["yellow"] * rules.get("yellow_value", 0.75)
            + counts["red"] * rules.get("red_value", 0.25)
        )
        score = min(5, max(1, round(raw_score)))
        key_factor = f"Risk factors: {counts['green']}🟢 {counts['yellow']}🟡 {counts['red']}🔴"

    elif section_name == "growth_drivers":
        counts = count_emoji_scores(task_output)
        raw_score = (
            counts["green"] * rules.get("strong_value", 1)
            + counts["yellow"] * rules.get("moderate_value", 0.5)
            + counts["red"] * rules.get("weak_value", 0)
        )
        score = min(5, max(1, round(raw_score * rules.get("scale_factor", 5 / 7))))
        key_factor = f"Growth drivers: {counts['green']} strong, {counts['yellow']} moderate"

    elif section_name == "management_risk":
        alignment = extract_alignment(task_output)
        score = rules.get("alignment_scores", {}).get(alignment, 3)
        key_factor = f"Management alignment: {alignment}"

    elif section_name == "valuation":
        conclusion = extract_valuation_conclusion(task_output)
        score = rules.get("match_scores", {}).get(conclusion, 3)
        key_factor = f"Valuation: {conclusion}"

    return {
        "score": score,
        "confidence": confidence,
        "key_factor": key_factor,
    }


def calculate_overall_grade(section_scores: dict) -> tuple[str, int, str]:
    """
    Calculate overall letter grade from section scores.

    Args:
        section_scores: Dictionary mapping section names to their scores

    Returns:
        Tuple of (letter_grade, total_score, recommendation)
    """
    total = sum(s.get("score", 0) for s in section_scores.values())

    for grade, (min_score, max_score, recommendation) in GRADE_THRESHOLDS.items():
        if min_score <= total <= max_score:
            return grade, total, recommendation

    return "C", total, "Hold"


def score_to_stars(score: int) -> str:
    """
    Convert numeric score (1-5) to star rating.

    Args:
        score: Score from 1 to 5

    Returns:
        Star string (e.g., "⭐⭐⭐⭐")
    """
    return "⭐" * max(1, min(5, score))


def generate_scorecard_summary(
    ticker: str,
    company_name: str,
    section_scores: dict,
    section_summaries: dict,
) -> str:
    """
    Generate the investment scorecard markdown output.

    Args:
        ticker: Stock ticker
        company_name: Company name
        section_scores: Dictionary of section scores
        section_summaries: Dictionary of 1-line summaries per section

    Returns:
        Formatted markdown scorecard
    """
    grade, total, recommendation = calculate_overall_grade(section_scores)

    # Section display mapping
    section_display = {
        "price_sentiment": ("📈 Market", "Price & Sentiment"),
        "business_phase": ("📊 Stage", "Business Phase"),
        "key_metrics": ("💰 Financials", "Key Metrics"),
        "business_profile": ("🏢 Business", "Business Profile"),
        "business_moat": ("🏰 Moat", "Competitive Position"),
        "execution_risk": ("⚠️ Risk", "Execution Risk"),
        "growth_drivers": ("🚀 Growth", "Growth Drivers"),
        "management_risk": ("👔 Management", "Management & Risk"),
        "valuation": ("💵 Valuation", "Quant & Valuation"),
    }

    # Build table rows
    rows = []
    for section_key, (category, section_name) in section_display.items():
        score_data = section_scores.get(section_key, {"score": 3})
        stars = score_to_stars(score_data.get("score", 3))
        summary = section_summaries.get(section_key, score_data.get("key_factor", ""))
        rows.append(f"| {category} | {section_name} | {stars} | {summary} |")

    table = "\n".join(rows)

    # Sort sections by score for strengths/concerns
    sorted_sections = sorted(
        section_scores.items(),
        key=lambda x: x[1].get("score", 0),
        reverse=True,
    )

    strengths = sorted_sections[:3]
    concerns = sorted_sections[-3:][::-1]  # Reverse to show worst first

    strengths_text = "\n".join(
        f"{i+1}. **{section_display.get(s[0], ('', s[0]))[1]}**: {s[1].get('key_factor', '')}"
        for i, s in enumerate(strengths)
    )

    concerns_text = "\n".join(
        f"{i+1}. **{section_display.get(s[0], ('', s[0]))[1]}**: {s[1].get('key_factor', '')}"
        for i, s in enumerate(concerns)
    )

    return f"""# 📊 Investment Scorecard: {company_name} ({ticker})

## Overall Grade: {grade}
**Recommendation:** {recommendation.upper()}

---

| Category | Section | Rating | Key Finding |
|:---------|:--------|:------:|:------------|
{table}

---

## Investment Thesis
Based on comprehensive analysis across 9 dimensions, {company_name} receives a grade of **{grade}** with a **{recommendation}** recommendation. The total score of {total}/45 reflects {"strong fundamentals" if grade in ["A", "B"] else "mixed signals" if grade == "C" else "significant concerns"}.

## Top Strengths
{strengths_text}

## Key Concerns
{concerns_text}

## What to Watch
- Monitor the weakest scoring areas for improvement
- Track key metrics that drive the overall assessment
"""
