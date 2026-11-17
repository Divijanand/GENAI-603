"""CodeMentor AI

Beginners paste Python here. The code goes through the AST + Ruff analysis, each
mistake is tracked per student (repeats are not counted as new mistakes), and
the student can ask for hints that escalate from a nudge to a fix.
From the project root:

    streamlit run app/main.py
"""

import sys
from pathlib import Path
from types import SimpleNamespace

# Streamlit puts app/ on the path, not the project root. Add the root so the
# ai/ and database/ packages import.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from app.service import LEVEL_NAMES, ReviewService  # noqa: E402
from database.repo_sqlite import SqliteRepo  # noqa: E402
from database.tracker import MistakeTracker  # noqa: E402

DB_PATH = ROOT / "codementor.db"  # local history; ignored by git


def explain_syntax_error(error):
    """Say what the syntax error means in plain language."""
    message = (error.msg or "").lower()

    # The wording shifts between Python versions
    if "string" in message:
        return (
            "A string was started with a quote but never closed. "
            "Check that every opening quote has a matching closing quote."
        )
    if "unexpected eof" in message or "never closed" in message:
        return (
            "The code looks unfinished. A parenthesis, bracket, brace, or quote "
            "may be missing its closing partner."
        )
    if "indent" in message:
        return (
            "The indentation does not line up. Python uses spaces at the start of a line "
            "to group code, so lines in the same block should start at the same position."
        )
    if "expected ':'" in message or "expected an indented block" in message:
        return (
            "A line such as if, for, while, or def needs a colon at the end, "
            "and the following line should be indented."
        )
    if "unmatched" in message:
        return "A closing parenthesis, bracket, or brace does not have a matching opening one."

    return (
        "Python could not understand this line. Look for a typo, a missing colon, "
        "or a symbol that is in the wrong place."
    )


@st.cache_resource
def get_service():
    """One service per server process, backed by a local SQLite file."""
    tracker = MistakeTracker(SqliteRepo(str(DB_PATH)))
    return ReviewService(
        tracker, explain_fn=lambda msg: explain_syntax_error(SimpleNamespace(msg=msg))
    )


def show_outcome(key, outcome):
    """List each mistake with a hint button that escalates one level per click."""
    service = get_service()
    st.caption(
        f"Attempt {outcome.attempt_no}: {outcome.n_new} new, "
        f"{outcome.n_repeated} still open, {outcome.n_resolved} fixed."
    )
    if not outcome.issues:
        st.success("No issues found.")
        return

    hints = st.session_state.setdefault("hints", {})
    for issue in outcome.issues:
        where = f"line {issue.line}" if issue.line else "no line"
        tag = "new" if issue.status == "new" else "still open"
        st.error(f"{issue.category} ({issue.rule}), {where}: {issue.message}  [{tag}]")
        shown = hints.setdefault(issue.issue_id, [])
        for level, text in shown:
            st.info(f"{LEVEL_NAMES[level]}: {text}")
        if len(shown) < 3 and st.button(
            "Get a hint" if not shown else "Get another hint",
            key=f"{key}-{issue.issue_id}-{len(shown)}",
        ):
            shown.append(service.hint(issue.issue_id))
            st.rerun()


def show_sidebar():
    stats = get_service().sidebar_stats()
    st.sidebar.header("Your mistakes")
    if not stats["top"]:
        st.sidebar.write("Nothing tracked yet.")
        return
    for row in stats["top"]:
        st.sidebar.write(f"{row['category']}: {row['mistakes']} mistake(s)")
    st.sidebar.caption(
        f"Fixed so far: {stats['resolve_rate']:.0%}. "
        f"Average hint level: {stats['avg_hint_level']:.1f} of 3."
    )


st.set_page_config(page_title="CodeMentor AI")
st.title("CodeMentor AI")
st.write(
    "CodeMentor AI helps beginner Python programmers review and debug their code. "
    "Paste a program in the box below, then click Review Code to submit it."
)

# Local variables vanish on the next click. Keep the reviews here or the
# first result disappears as soon as someone hits Resubmit
if "original_review" not in st.session_state:
    st.session_state.original_review = None
if "corrected_review" not in st.session_state:
    st.session_state.corrected_review = None

service = get_service()

code = st.text_area(
    "Enter your Python code below:",
    height=300,
    placeholder="Paste your Python code here",
)

if st.button("Review Code"):
    if not code.strip():
        st.warning("Please enter some Python code before requesting a review.")
    else:
        # A new first submission starts a new debugging session.
        service.new_session(title=code.strip().splitlines()[0][:60])
        st.session_state.hints = {}
        st.session_state.original_code = code
        st.session_state.original_review = service.submit(code)
        # Old correction belonged to the previous submission.
        st.session_state.corrected_review = None

if st.session_state.original_review is not None:
    st.subheader("Review")
    show_outcome("orig", st.session_state.original_review)
    st.caption("Submitted code:")
    st.code(st.session_state.original_code, language="python")

    # Don't ask for a fix until we've actually reviewed something
    corrected_code = st.text_area(
        "Submit corrected code:",
        height=300,
        placeholder="Paste your corrected Python code here",
    )

    if st.button("Resubmit Corrected Code"):
        if not corrected_code.strip():
            st.warning("Please enter your corrected Python code before resubmitting.")
        else:
            # Same session, so repeated mistakes are not counted as new ones.
            st.session_state.corrected_code = corrected_code
            st.session_state.corrected_review = service.submit(corrected_code)

    if st.session_state.corrected_review is not None:
        st.subheader("Review of corrected code")
        show_outcome("corr", st.session_state.corrected_review)
        st.code(st.session_state.corrected_code, language="python")

show_sidebar()
