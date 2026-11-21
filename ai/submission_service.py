"""
Filename: submission_service.py
Author: Ayra Babar
Date: 2026-11-20
Version: 1.0

Description:
    Coordinates static analysis, finding conversion, and mistake tracking for
    student code submissions.

"""

from ai.code_mentor_pipeline import analyze_code
from ai.finding_adapter import convert_to_findings
from ai.progressive_hints import select_hint


def process_submission(user_id, session_id, user_code, tracker):
    """
    Analyze submitted Python code and record its findings.

    Args:
        user_id (str): The student submitting code.
        session_id (str): The student's existing coding session.
        user_code (str): The submitted Python code.
        tracker (MistakeTracker): The tracker instance to use.

    Returns:
        dict: Analysis results, findings, and submission outcome.
    """

    user_issues = analyze_code(user_code)
    findings = convert_to_findings(user_issues)
    result = tracker.submit_attempt(session_id, user_id, user_code, findings)

    submission_details = {
        "analysis": user_issues,
        "findings": findings,
        "submission": result,
    }

    return submission_details


def request_hint(tracker, issue_id, feedback):
    """
    Advance the hint level for a tracked issue and return its hint.

    Args:
        tracker (MistakeTracker): Database mistake tracker.
        issue_id (str): ID of the mistake requesting help.
        feedback (dict): One validated Gemini feedback entry.

    Returns:
        str: The hint corresponding to the updated level.
    """
    hint_level = tracker.next_hint_level(issue_id)
    return select_hint(feedback, hint_level)
