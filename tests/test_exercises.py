import json

import pytest

from database.exercises import (Exercise, ExerciseError, exercise_for_user,
                                generate_exercise, parse_exercise, verify_exercise)
from database.tracker import Finding, MistakeTracker

GOOD = {
    "function_name": "last_item",
    "prompt": "Write last_item(xs) returning the last element, or None if empty.",
    "reference_solution": "def last_item(xs):\n    return xs[-1] if xs else None\n",
    "tests": ("from solution import last_item\n"
              "def test_basic():\n    assert last_item([1, 2, 3]) == 3\n"
              "def test_empty():\n    assert last_item([]) is None\n"),
}
BROKEN = dict(GOOD, reference_solution="def last_item(xs):\n    return xs[len(xs)]\n")
HANGS = dict(GOOD, reference_solution="def last_item(xs):\n    while True:\n        pass\n")


def fake_llm(*replies):
    it = iter(replies)
    return lambda prompt: next(it)


def test_parse_tolerates_markdown_fences():
    ex = parse_exercise("```json\n" + json.dumps(GOOD) + "\n```", "edge_case")
    assert ex.function_name == "last_item"


@pytest.mark.parametrize("bad", ["no json here", "{not json}", json.dumps({"prompt": "x"})])
def test_parse_rejects_bad_replies(bad):
    with pytest.raises(ExerciseError):
        parse_exercise(bad, "logic")


def test_verify_accepts_correct_and_rejects_wrong_solution():
    assert verify_exercise(parse_exercise(json.dumps(GOOD), "logic"))[0]
    assert not verify_exercise(parse_exercise(json.dumps(BROKEN), "logic"))[0]


def test_verify_times_out_on_infinite_loop():
    ok, out = verify_exercise(parse_exercise(json.dumps(HANGS), "logic"), timeout=2)
    assert not ok and out == "timed out"


def test_generate_retries_until_verified():
    llm = fake_llm("garbage", json.dumps(BROKEN), json.dumps(GOOD))
    assert generate_exercise(llm, "edge_case").function_name == "last_item"


def test_generate_gives_up_after_max_attempts():
    with pytest.raises(ExerciseError):
        generate_exercise(fake_llm(*[json.dumps(BROKEN)] * 3), "logic")


def test_exercise_targets_users_top_mistake_and_is_stored():
    t = MistakeTracker()
    for i in range(2):
        t.submit_attempt(t.start_session("u1"), "u1", "x",
                         [Finding("index_bounds", "IndexError", symbol=f"a{i}")])
    t.submit_attempt(t.start_session("u1"), "u1", "x", [Finding("type", "TypeError")])
    seen = []
    def llm(prompt):
        seen.append(prompt)
        return json.dumps(GOOD)
    ex = exercise_for_user(t, llm, "u1")
    assert "off-by-one" in seen[0]          # prompt aimed at index_bounds
    assert ex.category == "index_bounds"
    stored = t.repo.user_exercises("u1")
    assert len(stored) == 1 and stored[0]["verified"] == 1
