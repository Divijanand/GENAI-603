from ai.llm_feedback import validate_feedback

analysis_results = {
    "issues": [
        {
            "source": "Ruff",
            "type": "F821",
            "category": "name",
            "line": 1,
            "message": "Undefined name `score`",
        }
    ]
}

valid_feedback = {
    "feedback": [
        {
            "rule": "F821",
            "symbol": "score",
            "explanation": "The variable score has not been defined.",
            "hints": {
                "1": "Check the variable being printed.",
                "2": "Check whether score was defined earlier.",
                "3": "Find where score is used and define it first.",
            },
        }
    ]
}

assert validate_feedback(analysis_results, valid_feedback) is True

invalid1 = {
    "feedback": [
        {
            "rule": "F821",
            "symbol": "score",
            "explanation": "The variable score has not been defined.",
        }
    ]
}
assert validate_feedback(analysis_results, invalid1) is False

invalid2 = {
    "feedback": [
        {
            "rule": "F821",
            "symbol": "score",
            "explanation": "The variable score has not been defined.",
            "hints": {
                "1": "Check the variable being printed.",
                "2": "Check whether score was defined earlier.",
            },
        }
    ]
}
assert validate_feedback(analysis_results, invalid2) is False

invalid3 = {
    "feedback": [
        {
            "rule": "F821",
            "symbol": "score",
            "explanation": "The variable score has not been defined.",
            "hints": {
                "1": "Check the variable being printed.",
                "2": "      ",
                "3": "Find where score is used and define it first.",
            },
        }
    ]
}
assert validate_feedback(analysis_results, invalid3) is False

invalid4 = {
    "feedback": [
        {
            "rule": "F821",
            "symbol": "score",
            "explanation": "The variable score has not been defined.",
            "hints": {
                "1": 123456789,
                "2": "Check whether score was defined earlier.",
                "3": "Find where score is used and define it first.",
            },
        }
    ]
}
assert validate_feedback(analysis_results, invalid4) is False

invalid5 = {
    "feedback": [
        {
            "rule": "F401",
            "symbol": "score",
            "explanation": "The variable score has not been defined.",
            "hints": {
                "1": "Check the variable being printed.",
                "2": "Check whether score was defined earlier.",
                "3": "Find where score is used and define it first.",
            },
        }
    ]
}
assert validate_feedback(analysis_results, invalid5) is False


invalid6 = {
    "feedback": [
        {
            "rule": "F821",
            "symbol": "",
            "explanation": "The variable score has not been defined.",
            "hints": {
                "1": "Check the variable being printed.",
                "2": "Check whether score was defined earlier.",
                "3": "Find where score is used and define it first.",
            },
        }
    ]
}
assert validate_feedback(analysis_results, invalid6) is True

invalid7 = {
    "feedback": [
        {
            "rule": "F821",
            "symbol": "score",
            "explanation": "The variable score has not been defined.",
            "hints": {
                "1": "Check the variable being printed.",
                "2": "Check whether score was defined earlier.",
                "3": "Find where score is used and define it first.",
                "4": "Give solution to user.",
            },
        }
    ]
}
assert validate_feedback(analysis_results, invalid7) is False

invalid8 = {
    "feedback": [
        {
            "rule": "F821",
            "symbol": "score",
            "hints": {
                "1": "Check the variable being printed.",
                "2": "Check whether score was defined earlier.",
                "3": "Find where score is used and define it first.",
            },
        }
    ]
}
assert validate_feedback(analysis_results, invalid8) is False
