"""
Filename: code_mentor_pipeline.py
Author: Ayra Babar
Date: 2026-11-15
Version: 1.0

Description:
    Core static analysis pipeline for CodeMentor AI.
    Analyzes user-submitted Python code using AST and Ruff,
    collects syntax and linting issues, and returns
    structured findings for further processing.
"""

import ast  # import the built-in module for parsing python abstract syntax trees
import json
import subprocess
import sys

# from database.taxonomy import categorize


def ast_analysis(user_code):
    """
    Analyzes user-submitted Python code for syntax errors using AST.

    Args:
        user_code (str): Python source code submitted through the UI.

    Returns:
        list[dict]: A list of detected syntax errors containing
        the source, type, line number, and error message.
        Returns an empty list if no syntax errors are detected.

    Raises:
        TypeError: If user_code is not a string.
    """

    # reject non-string input before attempting to parse Python source code.
    if not isinstance(user_code, str):
        raise TypeError("user python code needs to be sent as string value")

    ast_errors = []

    try:
        ast.parse(user_code)  # parse the source code without executing it.

    except IndentationError as error:
        ast_errors.append(  # convert Python's IndentationError into a structured finding.
            {
                "source": "AST",
                "type": "indentation",
                "category": "indentation",
                "line": error.lineno,
                "message": error.msg,
            }
        )

    except SyntaxError as error:
        ast_errors.append(  # convert Python's SyntaxError into a structured finding.
            {
                "source": "AST",
                "type": "syntax",
                "category": "syntax",
                "line": error.lineno,
                "message": error.msg,
            }
        )

    return ast_errors


def ruff_analysis(user_code):
    """
    Analyzes user-submitted Python code using Ruff's linting rules.

    Args:
        user_code (str): Python source code submitted through the UI.

    Returns:
        list[dict]: A list of detected linting issues containing
        the source, rule code, line number, and error message.
        Returns an empty list if no linting issues are detected.

    Raises:
        TypeError: If user_code is not a string.
        subprocess.CalledProcessError: If Ruff exits abnormally.
        OSError: If the Ruff subprocess cannot be started.
        json.JSONDecodeError: If Ruff returns invalid JSON.
    """
    if not isinstance(user_code, str):
        raise TypeError("user python code needs to be sent as string value")

    ruff_errors = []

    # run Ruff as a subprocess and send the submitted code through stdin.
    # this avoids creating a temporary Python file for each submission.
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "-", "--output-format", "json"],
        check=False,
        input=user_code,
        capture_output=True,
        text=True,
    )

    # ruff exit codes 0 and 1 indicate normal completion.
    # other exit codes indicate an operational failure.
    if result.returncode not in (0, 1):
        raise subprocess.CalledProcessError(
            result.returncode, result.args, output=result.stdout, stderr=result.stderr
        )

    # deserialize Ruff's JSON output into Python dictionaries.
    issue_data = json.loads(result.stdout)

    # convert each Ruff diagnostic into the same format used by AST.
    for issue in issue_data:
        ruff_errors.append(
            {
                "source": "Ruff",
                "type": issue["code"],
                # "category": categorize(issue["code"]),
                "line": issue["location"]["row"],
                "message": issue["message"],
            }
        )

    return ruff_errors


def combine_errors(ast_errors, ruff_errors):
    """
    Combines AST and Ruff findings into a single dictionary.

    Args:
        ast_errors (list[dict]): Syntax errors detected by AST.
        ruff_errors (list[dict]): Linting issues detected by Ruff.

    Returns:
        dict: A dictionary containing an "issues" key whose value
        is a list of all AST and Ruff findings.
    """

    # merge both lists under one key for consistent downstream processing.
    code_errors = {}
    code_errors["issues"] = ast_errors + ruff_errors
    return code_errors


def analyze_code(user_code):
    """
    Coordinates the complete AST and Ruff static analysis pipeline.

    Calls both analysis functions, combines their findings,
    and returns the results in a consistent format.

    Args:
        user_code (str): Python source code submitted through the UI.

    Returns:
        dict: A dictionary containing all detected syntax
        and linting issues under the "issues" key.
    """

    # run both static analyzers on the submitted source code.
    ast_errors = ast_analysis(user_code)
    ruff_errors = ruff_analysis(user_code)

    # combine their findings into a single result for the application.
    code_errors = combine_errors(ast_errors, ruff_errors)
    return code_errors
