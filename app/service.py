"""Glue between the interface, the AI analysis pipeline and the mistake tracker.

    code -> ai.code_mentor_pipeline (AST + Ruff) -> Finding -> MistakeTracker
                                                  -> tiered hints for the UI

Gemini feedback is optional. If GEMINI_API_KEY is not set (or the call fails),
the service falls back to the analyzer's own messages, so the app still works.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from ai.code_mentor_pipeline import analyze_code
from database.taxonomy import categorize
from database.tracker import Finding, MistakeTracker

LEVEL_NAMES = {1: "Nudge", 2: "Guided explanation", 3: "Fix"}


def to_findings(analysis: dict) -> list[Finding]:
    """Convert the AI pipeline's {"issues": [...]} into tracker findings."""
    findings = []
    for issue in analysis["issues"]:
        rule = issue["type"]
        category = issue.get("category") or categorize(rule)
        # Ruff wraps the offending name in backticks, e.g. "Undefined name `x`".
        # Using it as the symbol keeps the fingerprint stable across line moves.
        m = re.search(r"`([^`]+)`", issue["message"])
        findings.append(Finding(category, rule, issue["message"], m.group(1) if m else ""))
    return findings


def llm_feedback(code: str, analysis: dict) -> dict:
    """Per-rule explanation and hint from Gemini, or {} if unavailable."""
    from dotenv import load_dotenv

    load_dotenv()
    if not os.environ.get("GEMINI_API_KEY") or not analysis["issues"]:
        return {}
    try:
        from ai.llm_feedback import generate_feedback  # needs the API key at import

        out = generate_feedback(code, analysis)
        return {row["rule"]: row for row in out["feedback"]}
    except Exception:
        return {}


@dataclass
class IssueView:
    issue_id: str
    category: str
    rule: str
    line: int | None
    message: str
    status: str  # "new" | "repeated"
    hint_level: int = 0


@dataclass
class Outcome:
    attempt_no: int
    issues: list[IssueView] = field(default_factory=list)
    n_new: int = 0
    n_repeated: int = 0
    n_resolved: int = 0


class ReviewService:
    def __init__(self, tracker: MistakeTracker, user_id: str = "local-user",
                 feedback_fn=llm_feedback, explain_fn=None):
        self.tracker = tracker
        self.user_id = user_id
        self.feedback_fn = feedback_fn
        self.explain_fn = explain_fn  # optional plain-language explainer for syntax errors
        self.session_id: str | None = None
        self._feedback: dict = {}
        self._analysis_by_issue: dict[str, dict] = {}

    def new_session(self, title: str = "") -> None:
        self.session_id = self.tracker.start_session(self.user_id, title)
        self._feedback, self._analysis_by_issue = {}, {}

    def submit(self, code: str) -> Outcome:
        if self.session_id is None:
            self.new_session()
        analysis = analyze_code(code)
        findings = to_findings(analysis)
        result = self.tracker.submit_attempt(self.session_id, self.user_id, code, findings)
        self._feedback = self.feedback_fn(code, analysis) if findings else {}

        outcome = Outcome(result.attempt_no, n_new=len(result.new),
                          n_repeated=len(result.repeated), n_resolved=len(result.resolved))
        raw = {(i["type"], i["message"]): i for i in analysis["issues"]}
        for f in findings:
            row = self.tracker.repo.find_issue(self.session_id, f.fingerprint)
            issue_id = row["id"]
            line = raw.get((f.rule_key, f.message), {}).get("line")
            self._analysis_by_issue[issue_id] = {"line": line, "finding": f}
            outcome.issues.append(IssueView(
                issue_id, f.category, f.rule_key, line, f.message,
                "new" if issue_id in result.new else "repeated", row["hint_level"]))
        return outcome

    def hint(self, issue_id: str) -> tuple[int, str]:
        """Escalate this issue one level (nudge, guided explanation, fix)."""
        level = self.tracker.next_hint_level(issue_id)
        info = self._analysis_by_issue[issue_id]
        f: Finding = info["finding"]
        where = f"line {info['line']}" if info["line"] else "your code"
        llm = self._feedback.get(f.rule_key, {})
        if level == 1:
            return level, f"Take another look at {where}. This is a {f.category} issue."
        if level == 2:
            text = llm.get("explanation")
            if not text and self.explain_fn and f.category in ("syntax", "indentation"):
                text = self.explain_fn(f.message)
            return level, text or f.message
        text = llm.get("hint")
        if text:
            return level, text
        return level, (f"{f.message} (Set GEMINI_API_KEY to get a written fix suggestion "
                       "here; for now this is the analyzer's own message.)")

    def sidebar_stats(self) -> dict:
        return self.tracker.dashboard(self.user_id)
