from app.service import ReviewService, to_findings
from database.taxonomy import categorize
from database.tracker import MistakeTracker

BAD = "import os\nx = 10\nprint(unknown_variable)\n"
FIXED_IMPORT = "x = 10\nprint(unknown_variable)\n"


def make(feedback=None):
    return ReviewService(MistakeTracker(), feedback_fn=feedback or (lambda code, a: {}))


def test_ruff_rules_map_to_taxonomy():
    assert categorize("F401") == "style"
    assert categorize("I001") == "style"
    assert categorize("F821") == "name"
    assert categorize("invalid-syntax") == "syntax"


def test_findings_use_symbol_from_message():
    analysis = {"issues": [
        {"source": "Ruff", "type": "F821", "line": 3, "message": "Undefined name `foo`"},
        {"source": "AST", "type": "syntax", "category": "syntax", "line": 1, "message": "invalid syntax"},
    ]}
    f = to_findings(analysis)
    assert (f[0].category, f[0].symbol) == ("name", "foo")
    assert (f[1].category, f[1].symbol) == ("syntax", "")


def test_resubmitting_does_not_recount_and_marks_fixed():
    s = make()
    first = s.submit(BAD)
    assert first.n_new == 3 and first.n_repeated == 0
    second = s.submit(FIXED_IMPORT)
    assert second.n_new == 0
    assert second.n_repeated == 1  # undefined name still there
    assert second.n_resolved == 2  # unused import and import order fixed
    assert s.sidebar_stats()["top"][0]["category"] == "style"


def test_hints_escalate_and_use_llm_text_when_available():
    feedback = lambda code, a: {"F821": {"rule": "F821", "explanation": "You never defined it.",
                                         "hint": "Assign it before printing."}}
    s = make(feedback)
    out = s.submit("print(unknown_variable)\n")
    issue = out.issues[0]
    l1, t1 = s.hint(issue.issue_id)
    l2, t2 = s.hint(issue.issue_id)
    l3, t3 = s.hint(issue.issue_id)
    l4, _ = s.hint(issue.issue_id)
    assert (l1, l2, l3, l4) == (1, 2, 3, 3)  # capped at 3
    assert "line 1" in t1
    assert t2 == "You never defined it."
    assert t3 == "Assign it before printing."


def test_hints_fall_back_without_llm():
    s = make()
    out = s.submit("print(unknown_variable)\n")
    s.hint(out.issues[0].issue_id)
    _, explanation = s.hint(out.issues[0].issue_id)
    assert "Undefined name" in explanation
    _, fix = s.hint(out.issues[0].issue_id)
    assert "GEMINI_API_KEY" in fix


def test_clean_code_has_no_issues():
    s = make()
    out = s.submit("print('hi')\n")
    assert out.issues == [] and out.n_new == 0
