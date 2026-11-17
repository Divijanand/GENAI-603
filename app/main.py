"""CodeMentor AI

Beginners paste Python here. We check it for syntax errors.
From the project root:

    streamlit run app/main.py
"""

import ast

import streamlit as st


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


def check_syntax(code):
    """Parse the code. Don't run it.

    Streamlit reruns this file on every click, so hand back a dict we can
    save and show again later.
    """
    try:
        # parse() only checks the grammar. Bad syntax raises SyntaxError.
        ast.parse(code)
    except SyntaxError as error:
        return {
            "code": code,
            "valid": False,
            "line": error.lineno,
            "message": error.msg,
            "explanation": explain_syntax_error(error),
        }

    return {
        "code": code,
        "valid": True,
        "line": None,
        "message": None,
        "explanation": None,
    }


def show_syntax_error(result):
    """Show the error, the line number if we have one, and what to look for."""
    if result["line"]:
        st.error(f"Syntax error on line {result['line']}: {result['message']}")
    else:
        st.error(f"Syntax error: {result['message']}")
    st.write(result["explanation"])


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


code = st.text_area(
    "Enter your Python code below:",
    height=300,
    placeholder="Paste your Python code here",
)


# Empty box first, then a syntax check. AI feedback comes later
if st.button("Review Code"):
    if not code.strip():
        st.warning("Please enter some Python code before requesting a review.")
    else:
        st.session_state.original_review = check_syntax(code)
        # Old correction belonged to the previous submission.
        st.session_state.corrected_review = None

        # TODO: send this code to the AI review and show what comes back


if st.session_state.original_review is not None:
    original = st.session_state.original_review

    if original["valid"]:
        st.success("Your code passed the basic syntax check.")
    else:
        show_syntax_error(original)

    st.caption("Submitted code:")
    st.code(original["code"], language="python")

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
            # Same check as the first box
            st.session_state.corrected_review = check_syntax(corrected_code)

    if st.session_state.corrected_review is not None:
        corrected = st.session_state.corrected_review

        if corrected["valid"]:
            st.success("Your corrected code passed the syntax check!")
            st.code(corrected["code"], language="python")
        else:
            show_syntax_error(corrected)
