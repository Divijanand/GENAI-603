"""
Filename: finding_adapter.py
Author: Ayra Babar
Date: 2026-11-20
Version: 1.0

Description:
    Converts AST and Ruff analysis results into Finding objects compatible
    with the mistake tracker. Extracts identifiers from error messages and
    filters duplicate syntax/indentation errors reported by both analyzers.
"""

from database.tracker import Finding


def extract_quoted_values(message):
    """
    Extract all complete backtick-enclosed values from a str message.

    Args:
        message (str): The message string from a structured AST or Ruff finding.

    Returns:
        list[str]: Contains all complete backtick-enclosed values, or an empty list.
    """

    quoted_parts = message.split("`")
    values = []

    # extract values enclosed by complete pairs of backticks
    for i in range(1, len(quoted_parts), 2):
        if i < (len(quoted_parts) - 1):
            values.append(quoted_parts[i])

    return values


def extract_symbol(issue):
    """
    Extract the first complete backtick-enclosed value from an issue message.

    Args:
        issue (dict): A structured AST or Ruff finding.

    Returns:
        str: The extracted value, or an empty string if none is found.
    """

    message = issue["message"]
    parts = extract_quoted_values(message)

    if len(parts) > 0:
        symbol = parts[0]
    else:
        symbol = ""

    return symbol


# adapter design pattern
def convert_to_findings(analysis_results):
    """
    Convert AST and Ruff issues into Finding objects for mistake tracking.

    Skips Ruff invalid-syntax findings when AST reports a syntax or
    indentation error on the same line.

    Args:
        analysis_results (dict): Structured output from analyze_code().

    Returns:
        list[Finding]: Findings compatible with MistakeTracker.
    """

    findings = []
    ast_error_lines = set()

    # collect AST syntax/indentation error lines for deduplication
    for issue in analysis_results["issues"]:
        if issue["source"] == "AST" and (issue["type"] in ("syntax", "indentation")):
            ast_error_lines.add(issue["line"])

    # skip Ruff syntax findings already reported by AST on the same line
    for issue in analysis_results["issues"]:
        if (
            issue["source"] == "Ruff"
            and issue["type"] == "invalid-syntax"
            and issue["line"] in ast_error_lines
        ):
            continue

        new_finding = Finding(
            category=issue["category"],
            rule_key=issue["type"],
            message=issue["message"],
            symbol=extract_symbol(issue),
        )

        findings.append(new_finding)

    return findings
