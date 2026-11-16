"""SQLite storage backend: local development and tests, no setup needed."""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone

_SCHEMA = """
create table if not exists sessions (
    id text primary key, user_id text not null, title text,
    started_at text not null, closed_at text);
create table if not exists attempts (
    id text primary key, session_id text not null, user_id text not null,
    attempt_no int not null, code text not null, created_at text not null,
    unique (session_id, attempt_no));
create table if not exists issues (
    id text primary key, session_id text not null, user_id text not null,
    category text not null, rule_key text not null, fingerprint text not null,
    message text, first_attempt int not null, last_attempt int not null,
    attempts_seen int not null default 1, hint_level int not null default 0,
    status text not null default 'open', resolved_at text,
    created_at text not null default '',
    unique (session_id, fingerprint));
create table if not exists exercises (
    id text primary key, user_id text not null, category text not null,
    prompt text not null, reference_solution text not null, tests text not null,
    verified int not null default 0, created_at text not null);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SqliteRepo:
    def __init__(self, path: str = ":memory:"):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(_SCHEMA)

    def add_session(self, user_id: str, title: str) -> str:
        sid = str(uuid.uuid4())
        self.db.execute(
            "insert into sessions (id, user_id, title, started_at) values (?,?,?,?)",
            (sid, user_id, title, _now()),
        )
        self.db.commit()
        return sid

    def session_owner(self, session_id: str) -> str | None:
        row = self.db.execute(
            "select user_id from sessions where id=?", (session_id,)
        ).fetchone()
        return row["user_id"] if row else None

    def add_attempt(self, session_id: str, user_id: str, code: str) -> int:
        n = self.db.execute(
            "select coalesce(max(attempt_no),0)+1 from attempts where session_id=?",
            (session_id,),
        ).fetchone()[0]
        self.db.execute(
            "insert into attempts (id, session_id, user_id, attempt_no, code, created_at)"
            " values (?,?,?,?,?,?)",
            (str(uuid.uuid4()), session_id, user_id, n, code, _now()),
        )
        self.db.commit()
        return n

    def find_issue(self, session_id: str, fingerprint: str) -> dict | None:
        row = self.db.execute(
            "select * from issues where session_id=? and fingerprint=?",
            (session_id, fingerprint),
        ).fetchone()
        return dict(row) if row else None

    def add_issue(self, session_id, user_id, category, rule_key, fingerprint,
                  message, attempt_no) -> str:
        iid = str(uuid.uuid4())
        self.db.execute(
            "insert into issues (id, session_id, user_id, category, rule_key,"
            " fingerprint, message, first_attempt, last_attempt, created_at)"
            " values (?,?,?,?,?,?,?,?,?,?)",
            (iid, session_id, user_id, category, rule_key, fingerprint, message,
             attempt_no, attempt_no, _now()),
        )
        self.db.commit()
        return iid

    def reopen_issue(self, issue_id: str, attempt_no: int) -> None:
        self.db.execute(
            "update issues set attempts_seen=attempts_seen+1, last_attempt=?,"
            " status='open', resolved_at=null where id=?",
            (attempt_no, issue_id),
        )
        self.db.commit()

    def open_issues(self, session_id: str) -> list[dict]:
        rows = self.db.execute(
            "select id, fingerprint from issues where session_id=? and status='open'",
            (session_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def resolve_issue(self, issue_id: str) -> None:
        self.db.execute(
            "update issues set status='resolved', resolved_at=? where id=?",
            (_now(), issue_id),
        )
        self.db.commit()

    def bump_hint(self, issue_id: str, max_level: int) -> int:
        self.db.execute(
            "update issues set hint_level=min(hint_level+1, ?) where id=?",
            (max_level, issue_id),
        )
        self.db.commit()
        return self.db.execute(
            "select hint_level from issues where id=?", (issue_id,)
        ).fetchone()[0]

    def user_issues(self, user_id: str) -> list[dict]:
        rows = self.db.execute(
            "select category, attempts_seen, hint_level, status, created_at, resolved_at"
            " from issues where user_id=?", (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def add_exercise(self, user_id: str, ex, verified: bool) -> str:
        eid = str(uuid.uuid4())
        self.db.execute(
            "insert into exercises (id, user_id, category, prompt, reference_solution,"
            " tests, verified, created_at) values (?,?,?,?,?,?,?,?)",
            (eid, user_id, ex.category, ex.prompt, ex.reference_solution, ex.tests,
             int(verified), _now()),
        )
        self.db.commit()
        return eid

    def user_exercises(self, user_id: str) -> list[dict]:
        rows = self.db.execute(
            "select * from exercises where user_id=? order by created_at", (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]
