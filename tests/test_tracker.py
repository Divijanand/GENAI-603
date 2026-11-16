import pytest

from database.taxonomy import categorize
from database.tracker import Finding, MistakeTracker

OFF_BY_ONE = Finding("index_bounds", "IndexError", "loop goes past the end", symbol="nums")
NAME_ERR = Finding("name", "F821", "undefined name 'totl'", symbol="totl")


@pytest.fixture
def t():
    return MistakeTracker()


def test_repeated_attempts_do_not_create_new_mistakes(t):
    s = t.start_session("u1")
    r1 = t.submit_attempt(s, "u1", "v1", [OFF_BY_ONE])
    r2 = t.submit_attempt(s, "u1", "v2", [OFF_BY_ONE])
    r3 = t.submit_attempt(s, "u1", "v3", [OFF_BY_ONE])
    assert len(r1.new) == 1 and r2.new == [] and r3.new == []
    assert r2.repeated == r1.new
    top = t.top_mistakes("u1")
    assert top == [{"category": "index_bounds", "mistakes": 1, "attempts": 3}]


def test_fixed_issue_is_resolved(t):
    s = t.start_session("u1")
    r1 = t.submit_attempt(s, "u1", "v1", [OFF_BY_ONE, NAME_ERR])
    r2 = t.submit_attempt(s, "u1", "v2", [OFF_BY_ONE])
    assert r2.resolved == [r1.new[1]]
    r3 = t.submit_attempt(s, "u1", "v3", [])
    assert r3.resolved == [r1.new[0]]


def test_same_mistake_in_new_session_counts_again(t):
    t.submit_attempt(t.start_session("u1"), "u1", "a", [OFF_BY_ONE])
    t.submit_attempt(t.start_session("u1"), "u1", "b", [OFF_BY_ONE])
    assert t.top_mistakes("u1")[0]["mistakes"] == 2


def test_duplicate_finding_in_one_submission_counted_once(t):
    s = t.start_session("u1")
    r = t.submit_attempt(s, "u1", "v1", [NAME_ERR, NAME_ERR])
    assert len(r.new) == 1


def test_users_are_isolated(t):
    t.submit_attempt(t.start_session("u1"), "u1", "a", [OFF_BY_ONE])
    assert t.top_mistakes("u2") == []
    assert "No prior mistakes" in t.llm_context("u2")


def test_cannot_submit_to_another_users_session(t):
    s = t.start_session("u1")
    with pytest.raises(PermissionError):
        t.submit_attempt(s, "u2", "x", [])


def test_hints_escalate_and_cap(t):
    s = t.start_session("u1")
    iid = t.submit_attempt(s, "u1", "v1", [NAME_ERR]).new[0]
    assert [t.next_hint_level(iid) for _ in range(5)] == [1, 2, 3, 3, 3]


def test_llm_context_is_bounded(t):
    for cat in ["syntax", "type", "logic", "name", "style"]:
        t.submit_attempt(t.start_session("u1"), "u1", "x", [Finding(cat, "r", symbol=cat)])
    assert t.llm_context("u1", max_categories=3).count("x)") == 3


def test_unknown_category_rejected(t):
    s = t.start_session("u1")
    with pytest.raises(ValueError):
        t.submit_attempt(s, "u1", "x", [Finding("bogus", "r")])


def test_categorize_prefix_and_exact():
    assert categorize("E999") == "syntax"
    assert categorize("E101") == "indentation"
    assert categorize("E501") == "style"
    assert categorize("ZZZ") == "other"
