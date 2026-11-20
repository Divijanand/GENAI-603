from ai.finding_adapter import (
    convert_to_findings,
    extract_quoted_values,
    extract_symbol,
)
from database.tracker import Finding

# test 1: verify that structured analysis results are converted into Finding objects
analysis_results = {
    "issues": [
        {
            "source": "Ruff",
            "type": "F821",
            "category": "name",
            "line": 3,
            "message": "Undefined name `score`",
        }
    ]
}
print(convert_to_findings(analysis_results))


# test 2: verify symbol extraction from messages with valid, missing,
# incomplete, and multiple backtick-enclosed values
messages = [
    "Undefined name `score`",
    "`math` imported but unused",
    "Import block is un-sorted or un-formatted",
    "Undefined name `score",
    "Redefinition of `score` from `math`",
]

for message in messages:
    issue = {"message": message}
    print(f"Message: {message}")
    print(f"Extracted symbol: {extract_symbol(issue)!r}")
    print()

# test 3: verify that only complete backtick-enclosed values are extracted
print(extract_quoted_values("Undefined name `score`"))
print(extract_quoted_values("Redefinition of `score` from `math`"))
print(extract_quoted_values("Import block is un-sorted"))
print(extract_quoted_values("Undefined name `score"))


# test 4: create Finding objects to test how symbols affect mistake fingerprints
finding1 = Finding(category="name", rule_key="F821", message="", symbol="first_name")
finding2 = Finding(category="name", rule_key="F821", message="", symbol="last_name")
finding3 = Finding(category="name", rule_key="F821", message="", symbol="")
finding4 = Finding(category="name", rule_key="F821", message="", symbol="")

# display the unique fingerprint generated for each Finding
print(finding1.fingerprint)
print(finding2.fingerprint)
print(finding3.fingerprint)
print(finding4.fingerprint)

# different symbols produce different fingerprints, identifying separate mistakes
print(finding1.fingerprint == finding2.fingerprint)

# identical category, rule, and symbol values produce the same fingerprint
# Findings without symbols may therefore be grouped as one mistake
print(finding3.fingerprint == finding4.fingerprint)


# test 5: verify that Ruff syntax errors are skipped only when AST
# reports a syntax/indentation error on the same line
analysis_results_2 = {
    "issues": [
        {
            "source": "AST",
            "type": "syntax",
            "category": "syntax",
            "line": 1,
            "message": "expected ':'",
        },
        {
            "source": "Ruff",
            "type": "invalid-syntax",
            "category": "other",
            "line": 5,
            "message": "Expected ':'",
        },
        {
            "source": "Ruff",
            "type": "F821",
            "category": "name",
            "line": 3,
            "message": "Undefined name `score`",
        },
    ]
}

analysis_results_3 = {
    "issues": [
        {
            "source": "AST",
            "type": "syntax",
            "category": "syntax",
            "line": 1,
            "message": "expected ':'",
        },
        {
            "source": "Ruff",
            "type": "invalid-syntax",
            "category": "other",
            "line": 1,
            "message": "Expected ':'",
        },
        {
            "source": "Ruff",
            "type": "F821",
            "category": "name",
            "line": 3,
            "message": "Undefined name `score`",
        },
    ]
}

findings_a = convert_to_findings(analysis_results_2)
findings_b = convert_to_findings(analysis_results_3)
assert len(findings_a) == 3
assert len(findings_b) == 2
print(findings_a)
print(findings_b)
