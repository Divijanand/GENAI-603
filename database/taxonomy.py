"""Fixed mistake taxonomy shared by the AI feedback layer and the database."""

CATEGORIES = (
    "syntax",
    "indentation",
    "name",         # undefined / misspelled variables
    "type",
    "index_bounds",  # off-by-one, index out of range
    "logic",
    "edge_case",
    "style",
    "other",
)

# Rough mapping from Ruff / pyflakes rule prefixes and Python exception names
# to a category, so static-analysis findings classify without an LLM call.
RULE_TO_CATEGORY = {
    "E999": "syntax",
    "invalid-syntax": "syntax",
    "SyntaxError": "syntax",
    "IndentationError": "indentation",
    "E1": "indentation",
    "F821": "name",
    "NameError": "name",
    "TypeError": "type",
    "IndexError": "index_bounds",
    "F401": "style",  # unused import
    "F841": "style",  # unused variable
    "I": "style",     # import sorting
    "B": "logic",
    "E": "style",
    "W": "style",
}


def categorize(rule_key: str) -> str:
    """Map a rule code / exception name to a taxonomy category."""
    if rule_key in RULE_TO_CATEGORY:
        return RULE_TO_CATEGORY[rule_key]
    # Longest matching prefix wins (e.g. "E1" beats "E").
    for prefix in sorted(RULE_TO_CATEGORY, key=len, reverse=True):
        if rule_key.startswith(prefix):
            return RULE_TO_CATEGORY[prefix]
    return "other"


def validate(category: str) -> str:
    if category not in CATEGORIES:
        raise ValueError(f"unknown category {category!r}; expected one of {CATEGORIES}")
    return category
