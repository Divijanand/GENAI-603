import json

from database.evaluation import evaluate, judge_category
from database.tracker import Finding, MistakeTracker
from tests.test_exercises import GOOD, BROKEN


def test_dashboard_summary():
    t = MistakeTracker()
    s = t.start_session("u1")
    f1 = Finding("index_bounds", "IndexError", symbol="a")
    f2 = Finding("type", "TypeError", symbol="b")
    r = t.submit_attempt(s, "u1", "v1", [f1, f2])
    t.submit_attempt(s, "u1", "v2", [f1])        # f2 fixed, f1 repeated
    t.next_hint_level(r.new[0])
    t.next_hint_level(r.new[0])
    d = t.dashboard("u1")
    assert d["total_mistakes"] == 2
    assert d["resolve_rate"] == 0.5
    assert d["avg_hint_level"] == 1.0
    assert {x["category"] for x in d["timeline"]} == {"index_bounds", "type"}
    assert d["top"][0]["attempts"] in (1, 2)


def test_dashboard_empty_user():
    d = MistakeTracker().dashboard("nobody")
    assert d["total_mistakes"] == 0 and d["resolve_rate"] == 0.0 and d["timeline"] == []


def test_judge_parses_and_falls_back():
    assert judge_category(lambda p: "Edge_case.", "x") == "edge_case"
    assert judge_category(lambda p: "banana", "x") == "other"


def test_evaluate_reports_validity_and_targeting():
    replies = iter([json.dumps(GOOD)] + [json.dumps(BROKEN)] * 3)
    gen = lambda p: next(replies)
    judge = lambda p: "edge_case"
    out = evaluate(gen, judge, ["edge_case", "logic"], per_category=1)
    assert out["requested"] == 2 and out["verified"] == 1
    assert out["validity"] == 0.5 and out["targeting"] == 1.0
    assert out["failures"][0]["category"] == "logic"
