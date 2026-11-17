"""Per-user mistake tracking with de-duplication across resubmissions.

The logic lives here; storage is a pluggable repo (SqliteRepo for local dev and
tests, SupabaseRepo for the real app). Both expose the same methods.

Key rule: a mistake is identified by a fingerprint (category + rule + symbol),
NOT by line number. Resubmitting code that still has the same mistake bumps
`attempts_seen` on the existing issue; it never creates a second mistake.
"""
from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass, field

from .repo_sqlite import SqliteRepo
from .taxonomy import validate

MAX_HINT_LEVEL = 3  # 1 nudge, 2 guided explanation, 3 fix


@dataclass(frozen=True)
class Finding:
    """One problem reported by the analysis layer (AST/Ruff/LLM)."""
    category: str
    rule_key: str
    message: str = ""
    symbol: str = ""  # e.g. the variable/function involved; stabilises the fingerprint

    @property
    def fingerprint(self) -> str:
        raw = f"{self.category}|{self.rule_key}|{self.symbol}".lower()
        return hashlib.sha1(raw.encode()).hexdigest()[:16]


@dataclass
class SubmitResult:
    attempt_no: int
    new: list[str] = field(default_factory=list)       # issue ids first seen now
    repeated: list[str] = field(default_factory=list)  # still unresolved, not re-counted
    resolved: list[str] = field(default_factory=list)  # fixed by this submission


class MistakeTracker:
    def __init__(self, repo=None):
        self.repo = repo if repo is not None else SqliteRepo()

    def start_session(self, user_id: str, title: str = "") -> str:
        return self.repo.add_session(user_id, title)

    def submit_attempt(
        self, session_id: str, user_id: str, code: str, findings: list[Finding]
    ) -> SubmitResult:
        if self.repo.session_owner(session_id) != user_id:
            raise PermissionError("session does not belong to this user")
        for f in findings:
            validate(f.category)

        n = self.repo.add_attempt(session_id, user_id, code)
        result = SubmitResult(attempt_no=n)
        seen = set()
        for f in findings:
            fp = f.fingerprint
            if fp in seen:  # same mistake reported twice in one submission
                continue
            seen.add(fp)
            existing = self.repo.find_issue(session_id, fp)
            if existing is None:
                result.new.append(self.repo.add_issue(
                    session_id, user_id, f.category, f.rule_key, fp, f.message, n))
            else:
                # Same mistake again (or it came back after being fixed): reopen
                # and bump the counter, but do not create a new mistake.
                self.repo.reopen_issue(existing["id"], n)
                result.repeated.append(existing["id"])

        # Anything open in this session that was not found this time is fixed.
        for row in self.repo.open_issues(session_id):
            if row["fingerprint"] not in seen:
                self.repo.resolve_issue(row["id"])
                result.resolved.append(row["id"])
        return result

    def next_hint_level(self, issue_id: str) -> int:
        """Escalate nudge -> guided -> fix, one level per request, capped at 3."""
        return self.repo.bump_hint(issue_id, MAX_HINT_LEVEL)

    def top_mistakes(self, user_id: str, n: int = 5) -> list[dict]:
        """Recurring categories. Counts distinct mistakes, not repeated attempts."""
        mistakes: dict[str, int] = defaultdict(int)
        attempts: dict[str, int] = defaultdict(int)
        for row in self.repo.user_issues(user_id):
            mistakes[row["category"]] += 1
            attempts[row["category"]] += row["attempts_seen"]
        ranked = sorted(mistakes, key=lambda c: (-mistakes[c], c))[:n]
        return [{"category": c, "mistakes": mistakes[c], "attempts": attempts[c]}
                for c in ranked]

    def llm_context(self, user_id: str, max_categories: int = 3) -> str:
        """Small, bounded summary of one user's history for the LLM prompt.

        Deliberately capped so context never grows with history length.
        """
        top = self.top_mistakes(user_id, max_categories)
        if not top:
            return "No prior mistakes recorded for this student."
        parts = [f"{t['category']} ({t['mistakes']}x)" for t in top]
        return "Student's most frequent past mistakes: " + ", ".join(parts) + "."

    # -- dashboard -------------------------------------------------------------
    def dashboard(self, user_id: str) -> dict:
        """Everything the mistake dashboard needs, in one call.

        - top: recurring categories (distinct mistakes, not repeated attempts)
        - timeline: new mistakes per day per category, oldest first
        - resolve_rate: share of this user's mistakes that got fixed
        - avg_hint_level: how much help the student needed on average (0-3)
        """
        rows = self.repo.user_issues(user_id)
        timeline: dict[tuple[str, str], int] = defaultdict(int)
        for r in rows:
            timeline[(str(r["created_at"])[:10], r["category"])] += 1
        total = len(rows)
        return {
            "top": self.top_mistakes(user_id),
            "timeline": [
                {"day": day, "category": cat, "mistakes": n}
                for (day, cat), n in sorted(timeline.items())
            ],
            "total_mistakes": total,
            "resolve_rate": (
                sum(r["status"] == "resolved" for r in rows) / total if total else 0.0
            ),
            "avg_hint_level": (
                sum(r["hint_level"] for r in rows) / total if total else 0.0
            ),
        }
