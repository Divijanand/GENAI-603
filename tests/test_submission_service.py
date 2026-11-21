from ai.submission_service import process_submission, request_hint
from database.repo_sqlite import SqliteRepo
from database.tracker import MistakeTracker

# create temporary database in memory
repo = SqliteRepo()

# create a mistake tracker instance for the specified temporary database
tracker = MistakeTracker(repo)

# create test student to work with & create a session belonging to them
user_id = "test_student"
session_id = tracker.start_session(user_id, "Python Debugging Test")

# test 1: first submission:
code1 = "print(score)"
result1 = process_submission(user_id, session_id, code1, tracker)
submission1 = result1["submission"]

print("attempt: ", submission1.attempt_no)
print("new: ", submission1.new)
print("repeated: ", submission1.repeated)
print("resolved: ", submission1.resolved)

assert submission1.attempt_no == 1
assert len(submission1.new) == 1
assert len(submission1.repeated) == 0
assert len(submission1.resolved) == 0
print()


# test 2: resubmission with same incorrect code:
result2 = process_submission(user_id, session_id, code1, tracker)
submission2 = result2["submission"]

print("attempt: ", submission2.attempt_no)
print("new: ", submission2.new)
print("repeated: ", submission2.repeated)
print("resolved: ", submission2.resolved)

assert submission2.attempt_no == 2
assert len(submission2.new) == 0
assert len(submission2.repeated) == 1
assert len(submission2.resolved) == 0
# confirms the tracker isn't creating a new mistake everytime the student submits the same error
assert submission2.repeated[0] == submission1.new[0]
print()


# test 3: resubmission with corrected code:
code3 = "score = 95\nprint(score)"
result3 = process_submission(user_id, session_id, code3, tracker)
submission3 = result3["submission"]

print("attempt: ", submission3.attempt_no)
print("new: ", submission3.new)
print("repeated: ", submission3.repeated)
print("resolved: ", submission3.resolved)

assert submission3.attempt_no == 3
assert len(submission3.new) == 0
assert len(submission3.repeated) == 0
assert len(submission3.resolved) == 1
assert submission3.resolved[0] == submission1.new[0]
print()

issue_id = submission1.new[0]
stored_issue = repo.find_issue(session_id, result1["findings"][0].fingerprint)
print(stored_issue["status"])
print(stored_issue["attempts_seen"])
assert stored_issue["status"] == "resolved"
assert stored_issue["attempts_seen"] == 2


# test 4: connect progressive hints to tracker
hint_repo = SqliteRepo()
hint_tracker = MistakeTracker(hint_repo)

hint_user = "hint_test_user"
hint_session = hint_tracker.start_session(hint_user, "Hint Progression Test")

hint_result = process_submission(hint_user, hint_session, "print(score)", hint_tracker)
hint_issue_id = hint_result["submission"].new[0]

# confirms that simply submitting code doesn't reveal a hint
initial_issue = hint_repo.find_issue(
    hint_session, hint_result["findings"][0].fingerprint
)

assert initial_issue["hint_level"] == 0

mock_feedback = {
    "rule": "F821",
    "symbol": "score",
    "explanation": "The variable score has not been defined.",
    "hints": {
        "1": "Check whether score exists.",
        "2": "Look for where score should be defined.",
        "3": "Find the print statement and define score before using it.",
    },
}

assert (
    request_hint(hint_tracker, hint_issue_id, mock_feedback)
    == "Check whether score exists."
)
assert (
    request_hint(hint_tracker, hint_issue_id, mock_feedback)
    == "Look for where score should be defined."
)
assert (
    request_hint(hint_tracker, hint_issue_id, mock_feedback)
    == "Find the print statement and define score before using it."
)
assert (
    request_hint(hint_tracker, hint_issue_id, mock_feedback)
    == "Find the print statement and define score before using it."
)

stored_hint_issue = hint_repo.find_issue(
    hint_session, hint_result["findings"][0].fingerprint
)

assert stored_hint_issue["hint_level"] == 3
