"""Personalized practice exercises, targeted at a student's top recurring mistake.

Flow: pick the user's top mistake category -> ask an LLM for an exercise as JSON
(prompt, reference solution, pytest tests) -> VERIFY the reference solution
passes its own tests -> store it. Unverified exercises are never shown.

The LLM is any callable `llm(prompt: str) -> str`, so the AI layer can plug in
whichever (cheap) model it uses, and tests use a fake one.

NOTE: verification runs LLM-written code in a subprocess with a timeout and a
temp directory. That stops runaways but is not a hardened sandbox; for anything
public-facing, run it in Docker.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .taxonomy import CATEGORIES

LLM = Callable[[str], str]

CATEGORY_FOCUS = {
    "syntax": "writing syntactically valid Python (colons, brackets, quotes)",
    "indentation": "correct indentation of blocks",
    "name": "defining and spelling variable and function names correctly",
    "type": "handling types correctly (str vs int, None, conversions)",
    "index_bounds": "loop bounds and indexing (off-by-one, index out of range)",
    "logic": "correct conditions and control flow",
    "edge_case": "edge cases (empty input, zero, negatives, single element)",
    "style": "clean, readable Python",
    "other": "general beginner Python",
}


@dataclass
class Exercise:
    category: str
    prompt: str
    reference_solution: str
    tests: str
    function_name: str = ""


class ExerciseError(Exception):
    pass


def build_prompt(category: str, context: str = "") -> str:
    focus = CATEGORY_FOCUS.get(category, CATEGORY_FOCUS["other"])
    return (
        "You write short Python practice exercises for beginners.\n"
        f"Target skill: {focus}.\n"
        f"{context}\n"
        "Return ONLY a JSON object with keys:\n"
        '  "function_name": name of the function the student must write,\n'
        '  "prompt": the exercise description (do not include the solution),\n'
        '  "reference_solution": complete Python code defining that function,\n'
        '  "tests": pytest code that does `from solution import <function_name>` '
        "and has 3-5 test functions, including at least one edge case.\n"
        "Keep it solvable in under 10 lines. Standard library only."
    )


def parse_exercise(text: str, category: str) -> Exercise:
    """Extract and validate the JSON object from an LLM reply."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ExerciseError("no JSON object in LLM reply")
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as e:
        raise ExerciseError(f"invalid JSON: {e}") from e
    for key in ("function_name", "prompt", "reference_solution", "tests"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise ExerciseError(f"missing or empty field: {key}")
    return Exercise(category, data["prompt"], data["reference_solution"],
                    data["tests"], data["function_name"])


def verify_exercise(ex: Exercise, timeout: float = 10.0) -> tuple[bool, str]:
    """Run the reference solution against its own tests. Returns (passed, output)."""
    with tempfile.TemporaryDirectory() as d:
        Path(d, "solution.py").write_text(ex.reference_solution, encoding="utf-8")
        Path(d, "test_solution.py").write_text(ex.tests, encoding="utf-8")
        try:
            proc = subprocess.run(
                [sys.executable, "-I", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                 "test_solution.py"],
                cwd=d, capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return False, "timed out"
        return proc.returncode == 0, (proc.stdout + proc.stderr)[-2000:]


def generate_exercise(llm: LLM, category: str, context: str = "",
                      max_attempts: int = 3) -> Exercise:
    """Ask the LLM until it returns an exercise whose solution passes its tests."""
    if category not in CATEGORIES:
        raise ValueError(f"unknown category {category!r}")
    last = "no attempts made"
    for _ in range(max_attempts):
        try:
            ex = parse_exercise(llm(build_prompt(category, context)), category)
        except ExerciseError as e:
            last = str(e)
            continue
        ok, out = verify_exercise(ex)
        if ok:
            return ex
        last = f"reference solution failed its tests: {out[-300:]}"
    raise ExerciseError(f"could not produce a verified exercise: {last}")


def exercise_for_user(tracker, llm: LLM, user_id: str) -> Exercise:
    """Generate and store a verified exercise for the user's top recurring mistake."""
    top = tracker.top_mistakes(user_id, 1)
    category = top[0]["category"] if top else "logic"
    ex = generate_exercise(llm, category, tracker.llm_context(user_id))
    tracker.repo.add_exercise(user_id, ex, verified=True)
    return ex
