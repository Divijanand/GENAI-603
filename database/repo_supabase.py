"""Supabase (Postgres) storage backend.

Pass a supabase-py client that is signed in as the student (anon key + the
user's session). Row level security in schema.sql then guarantees each user
can only read and write their own rows, even if app code has a bug.

    from database.repo_supabase import SupabaseRepo, make_client
    repo = SupabaseRepo(make_client())
"""
from __future__ import annotations

import os
from datetime import datetime, timezone


def make_client():
    """Build a client from SUPABASE_URL / SUPABASE_ANON_KEY (see .env.example)."""
    from dotenv import load_dotenv
    from supabase import create_client

    load_dotenv()
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_ANON_KEY"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SupabaseRepo:
    def __init__(self, client):
        self.c = client

    def add_session(self, user_id: str, title: str) -> str:
        res = self.c.table("sessions").insert({"user_id": user_id, "title": title}).execute()
        return res.data[0]["id"]

    def session_owner(self, session_id: str) -> str | None:
        res = self.c.table("sessions").select("user_id").eq("id", session_id).execute()
        return res.data[0]["user_id"] if res.data else None

    def add_attempt(self, session_id: str, user_id: str, code: str) -> int:
        res = (self.c.table("attempts").select("attempt_no").eq("session_id", session_id)
               .order("attempt_no", desc=True).limit(1).execute())
        n = (res.data[0]["attempt_no"] if res.data else 0) + 1
        self.c.table("attempts").insert(
            {"session_id": session_id, "user_id": user_id, "attempt_no": n, "code": code}
        ).execute()
        return n

    def find_issue(self, session_id: str, fingerprint: str) -> dict | None:
        res = (self.c.table("issues").select("*").eq("session_id", session_id)
               .eq("fingerprint", fingerprint).execute())
        return res.data[0] if res.data else None

    def add_issue(self, session_id, user_id, category, rule_key, fingerprint,
                  message, attempt_no) -> str:
        res = self.c.table("issues").insert({
            "session_id": session_id, "user_id": user_id, "category": category,
            "rule_key": rule_key, "fingerprint": fingerprint, "message": message,
            "first_attempt": attempt_no, "last_attempt": attempt_no,
        }).execute()
        return res.data[0]["id"]

    def reopen_issue(self, issue_id: str, attempt_no: int) -> None:
        cur = self.c.table("issues").select("attempts_seen").eq("id", issue_id).execute()
        seen = cur.data[0]["attempts_seen"] + 1
        self.c.table("issues").update({
            "attempts_seen": seen, "last_attempt": attempt_no,
            "status": "open", "resolved_at": None,
        }).eq("id", issue_id).execute()

    def open_issues(self, session_id: str) -> list[dict]:
        res = (self.c.table("issues").select("id, fingerprint")
               .eq("session_id", session_id).eq("status", "open").execute())
        return res.data

    def resolve_issue(self, issue_id: str) -> None:
        self.c.table("issues").update(
            {"status": "resolved", "resolved_at": _now()}
        ).eq("id", issue_id).execute()

    def bump_hint(self, issue_id: str, max_level: int) -> int:
        cur = self.c.table("issues").select("hint_level").eq("id", issue_id).execute()
        level = min(cur.data[0]["hint_level"] + 1, max_level)
        self.c.table("issues").update({"hint_level": level}).eq("id", issue_id).execute()
        return level

    def user_issues(self, user_id: str) -> list[dict]:
        res = (self.c.table("issues").select("category, attempts_seen, hint_level, status, created_at, resolved_at")
               .eq("user_id", user_id).execute())
        return res.data

    def add_exercise(self, user_id: str, ex, verified: bool) -> str:
        res = self.c.table("exercises").insert({
            "user_id": user_id, "category": ex.category, "prompt": ex.prompt,
            "reference_solution": ex.reference_solution, "tests": ex.tests,
            "verified": verified,
        }).execute()
        return res.data[0]["id"]

    def user_exercises(self, user_id: str) -> list[dict]:
        res = (self.c.table("exercises").select("*").eq("user_id", user_id)
               .order("created_at").execute())
        return res.data
