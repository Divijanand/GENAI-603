"""
Filename: progressive_hints.py
Author: Ayra Babar
Date: 2026-11-20
Version: 1.0

Description:
    Provides helper functions to locate feedback for a specific
    Python issue and select one of three progressive hint levels.

"""


def find_feedback(response, rule, symbol):
    """
    Find the feedback entry matching a specific rule and symbol.

    Args:
        response (dict): Structured feedback containing multiple issues.
        rule (str): The error rule code to match.
        symbol (str): The identifier associated with the issue.

    Returns:
        dict | None: The matching feedback entry, or None if not found.
    """

    for entry in response["feedback"]:
        if entry.get("rule") == rule and entry.get("symbol") == symbol:
            return entry

    # if there is no match
    return None


def select_hint(feedback, level):
    """
    Select a progressive hint for a detected Python issue.

    Args:
        feedback (dict): A single feedback entry containing three hints.
        level (int): The hint level to extract from LLM produced hints.

    Returns:
        hint (str): String value of the hint extracted to be sent to UI.

    Raises:
        ValueError: "hint level must be 1, 2, or 3"
    """

    if level not in (1, 2, 3):
        raise ValueError("hint level must be 1, 2, or 3")

    level_value = str(level)
    hint = feedback["hints"][level_value]
    return hint
