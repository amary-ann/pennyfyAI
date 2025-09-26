import re

def extract_price_range(query: str):
    """
    Extract min and/or max price from user query using regex.
    Examples:
        "phones under 500" → (None, 500)
        "laptops above 1000" → (1000, None)
        "between 200 and 600" → (200, 600)
    """
    query = query.lower()
    min_price, max_price = None, None

    between_match = re.search(r'between\s+(\d+)\s+and\s+(\d+)', query)
    if between_match:
        return float(between_match.group(1)), float(between_match.group(2))

    under_match = re.search(r'under\s+(\d+)', query)
    if under_match:
        max_price = float(under_match.group(1))

    below_match = re.search(r'below\s+(\d+)', query)
    if below_match:
        max_price = float(below_match.group(1))

    over_match = re.search(r'over\s+(\d+)', query)
    if over_match:
        min_price = float(over_match.group(1))

    above_match = re.search(r'above\s+(\d+)', query)
    if above_match:
        min_price = float(above_match.group(1))

    return min_price, max_price


def extract_store_names(query: str, available_stores: list[str] | None):
    if not available_stores:
        return []
    query_lower = query.lower()
    matched_stores = [store for store in available_stores if store.lower() in query_lower]

    # If no stores explicitly mentioned, assume "all stores"
    return matched_stores if matched_stores else available_stores

