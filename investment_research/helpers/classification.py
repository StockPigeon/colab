"""Industry-based classification heuristics."""


def get_purchase_frequency_hint(sector: str, industry: str) -> str:
    """
    Provide purchase frequency classification hint based on sector/industry.

    Args:
        sector: Company sector
        industry: Company industry

    Returns:
        Classification hint string
    """
    recurring_keywords = ["software", "saas", "subscription", "insurance", "utility",
                          "telecom", "communication", "internet", "cloud", "streaming"]
    yearly_keywords = ["apparel", "retail", "restaurant", "entertainment", "media"]
    infrequent_keywords = ["auto", "automobile", "housing", "real estate", "furniture",
                           "appliance", "aerospace", "machinery", "construction"]

    combined = f"{sector} {industry}".lower()

    for kw in recurring_keywords:
        if kw in combined:
            return "Likely RECURRING - subscription/service based business model"
    for kw in infrequent_keywords:
        if kw in combined:
            return "Likely EVERY FEW YEARS - durable goods or major purchases"
    for kw in yearly_keywords:
        if kw in combined:
            return "Likely YEARLY - regular but not subscription purchases"

    return "Analyze business model to determine purchase frequency"


def get_recession_sensitivity_hint(sector: str, industry: str) -> str:
    """
    Provide recession sensitivity hint based on sector/industry.

    Args:
        sector: Company sector
        industry: Company industry

    Returns:
        Recession sensitivity hint string
    """
    recession_proof = ["healthcare", "pharmaceutical", "biotech", "utility", "utilities",
                       "consumer staples", "food", "beverage", "household", "discount"]
    highly_cyclical = ["consumer discretionary", "luxury", "travel", "leisure", "hotel",
                       "airline", "auto", "automobile", "real estate", "construction",
                       "materials", "mining", "casino", "gambling"]

    combined = f"{sector} {industry}".lower()

    for kw in recession_proof:
        if kw in combined:
            return "Likely RECESSION-PROOF - essential goods/services"
    for kw in highly_cyclical:
        if kw in combined:
            return "Likely HIGHLY CYCLICAL - discretionary spending dependent"

    return "Likely NORMAL - moderate economic sensitivity"
