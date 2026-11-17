from copy import deepcopy
from pprint import pprint

from ai.code_mentor_pipeline import analyze_code
from ai.llm_feedback import generate_feedback, validate_feedback

sample_code = """
import math
import os

print(unknown_variable)
"""

results = analyze_code(sample_code)
pprint("------static analysis findings------")
pprint(results)
pprint("------------------------------------")

feedback = generate_feedback(sample_code, results)
pprint("------llm analysis findings------")
pprint(feedback)
pprint("---------------------------------")

"""
for reference: what the llm feedback could look like

feedback = {
    "feedback": [
        {
            "explanation": "You imported the `math` module into your "
            "program, but you haven't actually used any "
            "functions or constants from it.",
            "hint": "If you aren't doing any mathematical calculations that "
            "require the `math` library, you can safely remove the "
            "`import math` line.",
            "rule": "F401",
        },
        {
            "explanation": "You imported the `os` module, but it is not "
            "being used anywhere in your code.",
            "hint": "If your program doesn't need to interact with the "
            "operating system, you can remove the `import os` line "
            "to keep your code clean.",
            "rule": "F401",
        },
        {
            "explanation": "You are telling Python to print "
            "`unknown_variable`, but Python doesn't know "
            "what that is because it hasn't been created or "
            "assigned a value yet.",
            "hint": "Before using a variable in a `print()` statement, make "
            "sure to define it first by assigning a value to it "
            "(for example: `unknown_variable = ...`).",
            "rule": "F821",
        },
    ]
}
"""

feedback2 = deepcopy(feedback)
feedback2["feedback"][0].pop("hint")

feedback3 = deepcopy(feedback)
feedback3["feedback"][0]["rule"] = "F999"

feedback4 = deepcopy(feedback)
feedback4["feedback"].append(deepcopy(feedback4["feedback"][0]))

feedback5 = deepcopy(feedback)
feedback5["feedback"][0].update(explanation="")

pprint("-------feedback validation-------")
pprint(f"Correct Feedback Validation: {validate_feedback(results, feedback)}")
pprint(f"Missing 'hint': {validate_feedback(results, feedback2)}")
pprint(f"Incorrect rule code: {validate_feedback(results, feedback3)}")
pprint(f"Duplicate Feedback entry: {validate_feedback(results, feedback4)}")
pprint(f"Empty explanation: {validate_feedback(results, feedback5)}")
