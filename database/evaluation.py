"""Measure the exercise generator for the report: validity and targeting.

validity  = share of generation requests that end in a verified exercise
            (proposal target: >= 90%).
targeting = share of verified exercises whose practiced skill matches the
            student's mistake category, as judged by a second LLM call.

Both take plain `llm(prompt) -> str` callables, so you can use a cheap model for
generation and any model for judging, and tests can use fakes.
"""
from __future__ import annotations

from .exercises import ExerciseError, generate_exercise
from .taxonomy import CATEGORIES

JUDGE_PROMPT = (
    "Which ONE mistake category does this Python exercise mainly practice?\n"
    "Categories: {cats}\n\nExercise:\n{prompt}\n\n"
    "Answer with just the category name."
)


def judge_category(judge, prompt: str) -> str:
    reply = judge(JUDGE_PROMPT.format(cats=", ".join(CATEGORIES), prompt=prompt))
    words = reply.strip().lower().replace(".", "").split()
    return words[0] if words and words[0] in CATEGORIES else "other"


def evaluate(generator_llm, judge_llm, categories: list[str], per_category: int = 5) -> dict:
    requested = verified = on_target = 0
    failures = []
    for cat in categories:
        for _ in range(per_category):
            requested += 1
            try:
                ex = generate_exercise(generator_llm, cat)
            except ExerciseError as e:
                failures.append({"category": cat, "error": str(e)[:200]})
                continue
            verified += 1
            if judge_category(judge_llm, ex.prompt) == cat:
                on_target += 1
    return {
        "requested": requested,
        "verified": verified,
        "validity": verified / requested if requested else 0.0,
        "targeting": on_target / verified if verified else 0.0,
        "failures": failures,
    }
