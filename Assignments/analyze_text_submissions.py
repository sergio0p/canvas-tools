#!/usr/bin/env python3
"""
Canvas Text Entry Submissions Downloader

Downloads ALL submissions from assignments that accept online text entries.
Saves complete submission data including user info, body HTML, scores, etc.
"""

import sys
import json
import keyring
import requests
from typing import List, Optional
from dataclasses import dataclass

# Configuration
CANVAS_SERVICE_NAME = 'canvas'
CANVAS_USERNAME = 'access-token'
HOST = 'https://uncch.instructure.com'
API_V1 = f"{HOST}/api/v1"


@dataclass
class Course:
    """Represents a Canvas course"""
    id: int
    name: str
    workflow_state: str


@dataclass
class Assignment:
    """Represents a Canvas assignment"""
    id: int
    name: str
    points_possible: float
    due_at: Optional[str]
    submission_types: List[str]


class CanvasAPIClient:
    """Handles all Canvas API interactions"""

    def __init__(self):
        """Initialize API client with authentication"""
        self.token = self._get_token()
        self.session = requests.Session()
        self.session.headers.update({'Authorization': f'Bearer {self.token}'})

    def _get_token(self) -> str:
        """Retrieve API token from keychain"""
        token = keyring.get_password(CANVAS_SERVICE_NAME, CANVAS_USERNAME)
        if not token:
            print(f"❌ ERROR: No Canvas API token found in keychain.")
            print(f"Set one using: keyring.set_password('{CANVAS_SERVICE_NAME}', '{CANVAS_USERNAME}', 'your_token')")
            sys.exit(1)
        return token

    def get_favorite_courses(self) -> List[Course]:
        """Fetch user's favorite courses, filtered for published only"""
        url = f"{API_V1}/users/self/favorites/courses"
        response = self.session.get(url)

        if response.status_code != 200:
            print(f"❌ Failed to fetch courses: {response.status_code}")
            sys.exit(1)

        courses = response.json()
        published = [
            Course(c['id'], c['name'], c['workflow_state'])
            for c in courses
            if c.get('workflow_state') == 'available'
        ]

        return published

    def get_text_entry_assignments(self, course_id: int) -> List[Assignment]:
        """Fetch assignments that accept online text entry submissions"""
        url = f"{API_V1}/courses/{course_id}/assignments"
        response = self.session.get(url, params={'per_page': 100})

        if response.status_code != 200:
            print(f"❌ Failed to fetch assignments: {response.status_code}")
            sys.exit(1)

        assignments = response.json()
        
        # Filter for assignments with online_text_entry in submission_types
        text_entry_assignments = []
        for a in assignments:
            submission_types = a.get('submission_types', [])
            if 'online_text_entry' in submission_types:
                text_entry_assignments.append(Assignment(
                    a['id'],
                    a['name'],
                    a.get('points_possible', 0.0),
                    a.get('due_at'),
                    submission_types
                ))

        return text_entry_assignments

    def get_submissions(self, course_id: int, assignment_id: int, limit: Optional[int] = None) -> List[dict]:
        """
        Fetch submissions for an assignment
        
        Args:
            course_id: Canvas course ID
            assignment_id: Canvas assignment ID
            limit: Maximum number of submissions to return (None = all)
        
        Returns:
            List of submission dictionaries with full data
        """
        url = f"{API_V1}/courses/{course_id}/assignments/{assignment_id}/submissions"
        
        # Request all submissions with extended data
        # Include all available fields for complete submission information
        params = {
            'per_page': 100,
            'include[]': [
                'user',                    # User information (name, ID, etc.)
                'submission_comments',     # Comments on submission
                'rubric_assessment',       # Rubric grading if applicable
                'assignment',              # Assignment details
                'course',                  # Course details
                'group',                   # Group info if group assignment
                'read_status'              # Whether submission has been read
            ]
        }
        
        response = self.session.get(url, params=params)

        if response.status_code != 200:
            print(f"❌ Failed to fetch submissions: {response.status_code}")
            sys.exit(1)

        all_submissions = response.json()
        
        # Filter for non-empty text submissions
        text_submissions = []
        for submission in all_submissions:
            # Check if submission type is online_text_entry and has content
            if (submission.get('submission_type') == 'online_text_entry' and 
                submission.get('body') and 
                submission.get('body').strip()):
                text_submissions.append(submission)
                
                # Apply limit if specified
                if limit is not None and len(text_submissions) >= limit:
                    break
        
        return text_submissions


def display_courses(courses: List[Course]) -> None:
    """Display courses in a numbered list"""
    print("\n" + "=" * 100)
    print("FAVORITE COURSES")
    print("=" * 100)
    for i, course in enumerate(courses, 1):
        print(f"{i}. {course.name}")
    print("=" * 100)


def display_assignments(assignments: List[Assignment]) -> None:
    """Display assignments in a numbered list"""
    print("\n" + "=" * 100)
    print("ASSIGNMENTS WITH ONLINE TEXT ENTRY")
    print("=" * 100)
    for i, assignment in enumerate(assignments, 1):
        due = assignment.due_at or "No due date"
        types = ", ".join(assignment.submission_types)
        print(f"{i}. {assignment.name}")
        print(f"   Points: {assignment.points_possible} | Due: {due}")
        print(f"   Submission types: {types}")
    print("=" * 100)


def get_user_choice(prompt: str, max_choice: int) -> int:
    """Get a valid numeric choice from user"""
    while True:
        try:
            choice = input(f"\n{prompt} (1-{max_choice}): ").strip()
            choice_num = int(choice)
            if 1 <= choice_num <= max_choice:
                return choice_num - 1  # Return 0-indexed
            else:
                print(f"Please enter a number between 1 and {max_choice}")
        except ValueError:
            print("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print("\n\n👋 Cancelled by user")
            sys.exit(0)


def save_submissions_to_json(submissions: List[dict], filename: str, 
                             course_name: str, assignment_name: str) -> None:
    """Save submissions to JSON file for processing"""
    data = {
        "course": course_name,
        "assignment": assignment_name,
        "total_submissions": len(submissions),
        "submissions": submissions
    }
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\n💾 Submissions saved to: {filename}")


def display_submission_summary(submissions: List[dict]) -> None:
    """Display a summary of the submissions"""
    print("\n" + "=" * 100)
    print("SUBMISSION SUMMARY")
    print("=" * 100)
    
    for i, sub in enumerate(submissions, 1):
        user = sub.get('user', {})
        user_name = user.get('name', 'Unknown User')
        body_length = len(sub.get('body', ''))
        submitted_at = sub.get('submitted_at', 'Not submitted')
        score = sub.get('score', 'Not graded')
        
        print(f"\n{i}. {user_name}")
        print(f"   Submitted: {submitted_at}")
        print(f"   Score: {score}")
        print(f"   Body length: {body_length} characters")
        
        # Show first 200 characters of the body
        body_preview = sub.get('body', '')[:200]
        if len(sub.get('body', '')) > 200:
            body_preview += "..."
        print(f"   Preview: {body_preview}")
    
    print("=" * 100)


def main():
    """Main program flow"""
    print("=" * 100)
    print("   CANVAS TEXT ENTRY SUBMISSIONS DOWNLOADER")
    print("   Download ALL submissions from text entry assignments")
    print("=" * 100)

    # Initialize Canvas client
    print("\n🔐 Authenticating with Canvas...")
    canvas_client = CanvasAPIClient()

    # Step 1: Select course
    print("\n📚 Fetching favorite courses...")
    courses = canvas_client.get_favorite_courses()

    if not courses:
        print("❌ No published courses found in favorites")
        sys.exit(1)

    display_courses(courses)
    course_idx = get_user_choice("Select a course", len(courses))
    selected_course = courses[course_idx]
    print(f"\n✅ Selected: {selected_course.name}")

    # Step 2: Select assignment
    print(f"\n📋 Fetching assignments with online text entry...")
    assignments = canvas_client.get_text_entry_assignments(selected_course.id)

    if not assignments:
        print("❌ No assignments with online text entry found in this course")
        sys.exit(1)

    display_assignments(assignments)
    assignment_idx = get_user_choice("Select an assignment", len(assignments))
    selected_assignment = assignments[assignment_idx]
    print(f"\n✅ Selected: {selected_assignment.name}")

    # Step 3: Download ALL submissions (no limit)
    print(f"\n⬇️  Downloading ALL text submissions...")
    submissions = canvas_client.get_submissions(
        selected_course.id,
        selected_assignment.id,
        limit=None  # Get all submissions
    )

    if not submissions:
        print("❌ No text submissions found for this assignment")
        sys.exit(1)

    print(f"✅ Found {len(submissions)} text submission(s)")

    # Display summary
    display_submission_summary(submissions)

    # Save to JSON
    filename = f"text_submissions_{selected_course.id}_{selected_assignment.id}.json"
    save_submissions_to_json(
        submissions,
        filename,
        selected_course.name,
        selected_assignment.name
    )

    # Final summary
    print("\n" + "=" * 100)
    print("DOWNLOAD COMPLETE")
    print("=" * 100)
    print(f"✅ Downloaded {len(submissions)} submission(s)")
    print(f"💾 Data saved to: {filename}")
    print("\n📊 Submission fields included:")
    print("   - user (name, ID, email, etc.)")
    print("   - body (HTML content)")
    print("   - score, grade, graded_at")
    print("   - submitted_at, attempt")
    print("   - submission_comments")
    print("   - assignment and course details")
    print("\n➡️  Next step: Run html_to_json_converter.py to process the HTML")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Exiting...")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
