"""End-to-end check against a real Supabase project. Run after docs/supabase_setup.md."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.repo_supabase import SupabaseRepo, make_client
from database.tracker import Finding, MistakeTracker

client = make_client()
email = f"smoke{int(time.time())}@example.com"
auth = client.auth.sign_up({"email": email, "password": "Smoke-test-pw-123!"})
if auth.session is None:
    sys.exit("Sign-up returned no session: turn off 'Confirm email' in Supabase Auth.")
uid = auth.user.id

t = MistakeTracker(SupabaseRepo(client))
f = Finding("index_bounds", "IndexError", "loop runs past the end", symbol="nums")
s = t.start_session(uid, "smoke test")
r1 = t.submit_attempt(s, uid, "v1", [f])
r2 = t.submit_attempt(s, uid, "v2", [f])
assert len(r1.new) == 1 and r2.new == [], "repeat was counted as a new mistake"
top = t.top_mistakes(uid)
assert top == [{"category": "index_bounds", "mistakes": 1, "attempts": 2}], top
print("OK: auth, RLS-scoped inserts, and de-duplication work on Supabase.")
print(t.llm_context(uid))

# Exercises: store a verified exercise under RLS and read it back.
from database.exercises import Exercise
ex = Exercise("index_bounds", "Write last_item(xs).", "def last_item(xs): return xs[-1]",
              "from solution import last_item\ndef test_a(): assert last_item([1,2])==2\n")
t.repo.add_exercise(uid, ex, verified=True)
rows = t.repo.user_exercises(uid)
assert len(rows) == 1 and rows[0]["verified"] is True, rows
print("OK: exercises stored and read back under RLS.")
