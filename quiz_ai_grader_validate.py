#!/usr/bin/env python3
"""
Canvas Quiz AI Grader - Validation Script

Reviews AI-graded submissions, allows manual overrides, and posts grades to Canvas.
Processes one JSON file at a time created by quiz_ai_grader_collect.py.
"""

import sys
import json
import shutil
import subprocess
from typing import Dict, Optional
from pathlib import Path
import requests
import keyring


# === CONFIGURATION ===
CANVAS_SERVICE_NAME = 'canvas'
CANVAS_USERNAME = 'access-token'
CANVAS_API_BASE = "https://uncch.instructure.com/api/v1"


# === API KEY RETRIEVAL ===

def get_canvas_api_key() -> str:
    """Retrieve Canvas API token from keyring."""
    token = keyring.get_password(CANVAS_SERVICE_NAME, CANVAS_USERNAME)
    if not token:
        print(f"❌ ERROR: No Canvas API token found in keychain.")
        print(f"Set one using: keyring.set_password('{CANVAS_SERVICE_NAME}', '{CANVAS_USERNAME}', 'your_token')")
        sys.exit(1)
    return token


# === CANVAS API FUNCTIONS ===

class CanvasAPI:
    """Handles all Canvas API interactions."""

    def __init__(self, api_token: str):
        self.api_token = api_token
        self.headers = {'Authorization': f'Bearer {api_token}'}
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def canvas_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make a Canvas API request with error handling."""
        url = f"{CANVAS_API_BASE}/{endpoint.lstrip('/')}"

        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                print(f"❌ Authentication failed. Check your Canvas API token.")
            elif e.response.status_code == 403:
                print(f"❌ Permission denied. You may not have access to this resource.")
            elif e.response.status_code == 404:
                print(f"❌ Resource not found: {endpoint}")
            else:
                print(f"❌ HTTP Error {e.response.status_code}: {e.response.text}")
            raise
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error: {e}")
            raise

    def post_grade_to_canvas(self, course_id: int, quiz_id: int,
                            submission_id: int, attempt: int,
                            question_id: int, score: float,
                            feedback: str) -> bool:
        """Post grade and feedback to Canvas."""
        url = f"courses/{course_id}/quizzes/{quiz_id}/submissions/{submission_id}"

        payload = {
            "quiz_submissions": [{
                "attempt": attempt,
                "questions": {
                    str(question_id): {
                        "score": score,
                        "comment": feedback
                    }
                }
            }]
        }

        try:
            self.canvas_request('PUT', url, json=payload)
            return True
        except Exception as e:
            print(f"    ❌ Failed to post grade: {e}")
            return False


# === FILE OPERATIONS ===

def load_grading_session(filename: str) -> Optional[Dict]:
    """Load grading session from JSON file."""
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"❌ File not found: {filename}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON file: {e}")
        return None
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return None


def create_backup(filename: str) -> str:
    """Create backup of JSON file and return backup filename."""
    backup_filename = f"{filename}.backup.json"
    shutil.copy(filename, backup_filename)
    return backup_filename


def save_grading_session(filename: str, data: Dict) -> bool:
    """Save updated grading session to JSON file."""
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"❌ Error saving file: {e}")
        return False


# === DISPLAY FUNCTIONS ===

def display_session_summary(data: Dict) -> None:
    """Display summary of grading session."""
    print("\n" + "="*70)
    print("GRADING SESSION SUMMARY")
    print("="*70)
    print(f"Course: {data['course']['name']}")
    print(f"Quiz: {data['quiz']['name']}")
    print(f"Question: {data['question']['question_name']}")
    print(f"Points Possible: {data['question']['points_possible']}")
    print(f"Total Submissions: {len(data['submissions'])}")
    print("="*70)


def display_submission(submission: Dict, index: int, total: int, question_text: str) -> None:
    """Display a single submission for review."""
    print("\n" + "="*70)
    print(f"SUBMISSION {index + 1} of {total}")
    print("="*70)
    print(f"Student: {submission['user_name']}")
    print(f"User ID: {submission['user_id']}")
    print("-"*70)
    print("QUESTION:")
    import re
    # Strip HTML tags from question
    q_text_clean = re.sub('<[^<]+?>', '', question_text)
    print(q_text_clean)
    print("-"*70)
    print("STUDENT ANSWER:")
    print(submission['answer'])
    print("-"*70)
    print(f"AI SCORE: {submission['ai_score']}")
    print("AI FEEDBACK:")
    print(submission['ai_feedback'])
    print("="*70)


def get_validation_choice() -> str:
    """Get user's validation choice."""
    print("\nOptions:")
    print("  (v) Validate - Accept AI grade and post to Canvas")
    print("  (o) Override - Provide manual grade and post to Canvas")
    print("  (s) Skip - Don't post this grade (leave in file)")
    print("  (q) Quit - Exit and save progress")

    while True:
        choice = input("\nYour choice (v/o/s/q): ").strip().lower()
        if choice in ['v', 'o', 's', 'q']:
            return choice
        print("❌ Please enter 'v', 'o', 's', or 'q'")


def get_manual_grade(points_possible: float) -> Optional[Dict]:
    """Get manual score and feedback from user."""
    print("\n" + "-"*70)
    print("MANUAL OVERRIDE")
    print("-"*70)

    # Get score
    while True:
        try:
            score_input = input(f"Enter score (0-{points_possible}): ").strip()
            score = float(score_input)
            if 0 <= score <= points_possible:
                break
            else:
                print(f"❌ Score must be between 0 and {points_possible}")
        except ValueError:
            print("❌ Please enter a valid number")

    # Get feedback
    print("\nEnter feedback (press Enter twice when done):")
    lines = []
    empty_count = 0
    while True:
        try:
            line = input()
            if line == "":
                empty_count += 1
                if empty_count >= 2:
                    break
                lines.append("")
            else:
                empty_count = 0
                lines.append(line)
        except EOFError:
            break

    feedback = "\n".join(lines).strip()

    if not feedback:
        print("❌ Feedback cannot be empty")
        return None

    return {'score': score, 'feedback': feedback}


# === MAIN VALIDATION PROCESS ===

def validate_and_post(canvas: CanvasAPI, filename: str) -> None:
    """Main validation and posting process."""

    # Load grading session
    data = load_grading_session(filename)
    if not data:
        sys.exit(1)

    # Check if there are submissions to process
    if not data['submissions']:
        print("\n✅ All submissions have been processed!")
        print("No submissions remaining in this file.")
        sys.exit(0)

    # Create backup
    print(f"\n💾 Creating backup...")
    backup_filename = create_backup(filename)
    print(f"   Backup saved to: {backup_filename}")

    # Display session summary
    display_session_summary(data)

    # Extract metadata
    course_id = data['course']['id']
    quiz_id = data['quiz']['quiz_id']
    question_id = data['question']['id']
    question_text = data['question']['question_text']
    points_possible = data['question']['points_possible']

    # Statistics
    stats = {
        'validated': 0,
        'overridden': 0,
        'skipped': 0,
        'failed': 0
    }

    # Process each submission
    submissions = data['submissions'][:]
    index = 0

    while index < len(submissions):
        submission = submissions[index]

        # Display submission
        display_submission(submission, index, len(submissions), question_text)

        # Get user choice
        choice = get_validation_choice()

        if choice == 'v':
            # Validate - post AI grade
            print(f"\n📤 Posting AI grade to Canvas...")
            success = canvas.post_grade_to_canvas(
                course_id=course_id,
                quiz_id=quiz_id,
                submission_id=submission['submission_id'],
                attempt=submission['attempt'],
                question_id=question_id,
                score=submission['ai_score'],
                feedback=submission['ai_feedback']
            )

            if success:
                print(f"✅ Posted: {submission['user_name']} ({submission['ai_score']}/{points_possible})")
                stats['validated'] += 1
                # Remove from list and update file
                submissions.pop(index)
                data['submissions'] = submissions
                save_grading_session(filename, data)
                # Don't increment index - next submission is now at current index
            else:
                print(f"❌ Failed to post grade")
                stats['failed'] += 1
                index += 1

        elif choice == 'o':
            # Override - get manual grade
            manual = get_manual_grade(points_possible)

            if manual:
                print(f"\n📤 Posting manual grade to Canvas...")
                success = canvas.post_grade_to_canvas(
                    course_id=course_id,
                    quiz_id=quiz_id,
                    submission_id=submission['submission_id'],
                    attempt=submission['attempt'],
                    question_id=question_id,
                    score=manual['score'],
                    feedback=manual['feedback']
                )

                if success:
                    print(f"✅ Posted: {submission['user_name']} ({manual['score']}/{points_possible})")
                    stats['overridden'] += 1
                    # Remove from list and update file
                    submissions.pop(index)
                    data['submissions'] = submissions
                    save_grading_session(filename, data)
                    # Don't increment index
                else:
                    print(f"❌ Failed to post grade")
                    stats['failed'] += 1
                    index += 1
            else:
                print("⚠️  Manual override cancelled")
                index += 1

        elif choice == 's':
            # Skip - leave in file
            print(f"⊘ Skipped: {submission['user_name']}")
            stats['skipped'] += 1
            index += 1

        elif choice == 'q':
            # Quit - save and exit
            print("\n" + "="*70)
            print("EXITING - PROGRESS SAVED")
            print("="*70)
            print(f"\n📊 Session Statistics:")
            print(f"   Validated (AI): {stats['validated']}")
            print(f"   Overridden (Manual): {stats['overridden']}")
            print(f"   Skipped: {stats['skipped']}")
            print(f"   Failed: {stats['failed']}")
            print(f"\n   Remaining submissions: {len(submissions)}")
            print(f"\n💾 Progress saved to: {filename}")
            print(f"   Backup available at: {backup_filename}")
            print("\n📝 Run this script again to resume validation.")
            print("\n👋 Goodbye!")
            sys.exit(0)

    # All submissions processed
    print("\n" + "="*70)
    print("VALIDATION COMPLETE")
    print("="*70)
    print(f"\n📊 Final Statistics:")
    print(f"   Validated (AI): {stats['validated']}")
    print(f"   Overridden (Manual): {stats['overridden']}")
    print(f"   Skipped: {stats['skipped']}")
    print(f"   Failed: {stats['failed']}")

    if stats['skipped'] > 0:
        print(f"\n⚠️  {stats['skipped']} submission(s) were skipped and remain in the file.")
        print(f"   These can be graded manually in SpeedGrader.")

    # SpeedGrader link
    assignment_id = data['quiz']['id']
    speedgrader_url = f"https://uncch.instructure.com/courses/{course_id}/gradebook/speed_grader?assignment_id={assignment_id}"
    print(f"\n🔗 SpeedGrader: {speedgrader_url}")

    print(f"\n💾 Updated file: {filename}")
    print(f"   Backup available at: {backup_filename}")
    print("\n✅ All done!")


# === MAIN FUNCTION ===

def main():
    """Main orchestration function."""

    print("="*70)
    print("CANVAS QUIZ AI GRADER - VALIDATION SCRIPT")
    print("="*70)
    print("\nThis script reviews AI grades and posts them to Canvas.")
    print("You can validate, override, or skip each submission.")

    # Get filename
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        print("\n" + "-"*70)
        filename = input("Enter JSON filename to validate: ").strip()

    if not filename:
        print("❌ No filename provided")
        sys.exit(1)

    # Check if file exists
    if not Path(filename).exists():
        print(f"❌ File not found: {filename}")
        sys.exit(1)

    # Get Canvas API key
    print("\n🔑 Retrieving Canvas API key...")
    canvas_token = get_canvas_api_key()

    # Initialize Canvas API
    canvas = CanvasAPI(canvas_token)

    # Run validation process
    validate_and_post(canvas, filename)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Progress has been saved.")
        print("Run this script again to resume validation.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
