from ai.progressive_hints import find_feedback, select_hint

feedback = {
    "rule": "F821",
    "explanation": "The variable score has not been defined.",
    "hints": {
        "1": "Check whether score exists.",
        "2": "Look for a variable assignment before the print statement.",
        "3": "Define score before trying to print its value.",
    },
}

for level in (1, 2, 3):
    print(f"Level {level}: {select_hint(feedback, level)}")

assert select_hint(feedback, 1) == "Check whether score exists."
assert (
    select_hint(feedback, 2)
    == "Look for a variable assignment before the print statement."
)
assert select_hint(feedback, 3) == "Define score before trying to print its value."

try:
    select_hint(feedback, 4)
except ValueError:
    print("PASS: Invalid hint level was rejected.")
else:
    raise AssertionError("Invalid hint level was accepted.")

try:
    select_hint(feedback, 0)
except ValueError:
    print("PASS: Invalid hint level was rejected.")
else:
    raise AssertionError("Invalid hint level was accepted.")


# Mock Gemini response for testing progressive hints without API calls.
response = {
    "feedback": [
        {
            "rule": "F401",
            "symbol": "math",
            "explanation": "The math module was imported but never used.",
            "hints": {
                "1": "Look at the imports at the top of your code.",
                "2": "Check whether you use the math module anywhere.",
                "3": "Remove the unused import if it isn't needed.",
            },
        },
        {
            "rule": "F821",
            "symbol": "score",
            "explanation": "The variable score has not been defined.",
            "hints": {
                "1": "Look carefully at the variable you're trying to print.",
                "2": "Check whether score was defined before the print statement.",
                "3": "Find where score is used and define it before that line.",
            },
        },
        {
            "rule": "F821",
            "symbol": "total",
            "explanation": "The variable total has not been defined.",
            "hints": {
                "1": "Check the variable names used in your code.",
                "2": "Look for a variable named total and check its spelling.",
                "3": "Make sure total is assigned a value before you use it.",
            },
        },
    ]
}

# Correct feedback lookup
assert find_feedback(response, "F821", "score")["symbol"] == "score"
assert find_feedback(response, "F821", "total")["symbol"] == "total"
assert find_feedback(response, "F401", "math")["symbol"] == "math"

# Missing feedback
assert find_feedback(response, "F821", "unknown") is None
assert find_feedback(response, "F821", "math") is None

# Correct progressive hints
score_entry = find_feedback(response, "F821", "score")
total_entry = find_feedback(response, "F821", "total")

assert select_hint(score_entry, 2) == score_entry["hints"]["2"]
assert select_hint(total_entry, 3) == total_entry["hints"]["3"]

print("PASS: All progressive hint tests completed.")
