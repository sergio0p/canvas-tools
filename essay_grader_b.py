#!/usr/bin/env python3
"""
Canvas New Quizzes: Essay Grader with OpenAI - PART B

Reviews AI-graded essays and uploads approved grades to Canvas.
Loads grading results from JSON files created by Part A.
"""

import sys
import os
import json
import glob
import shutil
import keyring
import requests
from typing import List, Optional, Dict
from dataclasses import dataclass
from openai import OpenAI
from bs4 import BeautifulSoup

# Configuration
CANVAS_SERVICE_NAME = 'canvas'
CANVAS_USERNAME = 'access-token'
HOST = 'https://uncch.instructure.com'
API_V1 = f"{HOST}/api/v1"
API_QUIZ = f"{HOST}/api/quiz/v1"


@dataclass
class Course:
    """Represents a Canvas course"""
    id: int
    name: str
    workflow_state: str


@dataclass
class Assignment:
    """Represents a Canvas assignment (New Quiz)"""
    id: int
    name: str
    points_possible: float
    due_at: Optional[str]


@dataclass
class EssayQuestion:
    """Represents an essay question"""
    item_id: str
    title: str
    points_possible: float
    prompt: str


@dataclass
class StudentSubmission:
    """Represents a student's essay submission"""
    student_id: int
    student_name: str
    essay_text: str
    old_question_grade: float
    old_total_grade: float


@dataclass
class GradingResult:
    """Represents AI grading results for a student"""
    student_id: int
    student_name: str
    essay_text: str
    ai_grade: float
    ai_feedback: str
    old_question_grade: float
    new_question_grade: float
    old_total_grade: float
    new_total_grade: float
    approved: Optional[bool] = None


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

    def update_grade(self, course_id: int, assignment_id: int, user_id: int,
                    grade: float, comment: str) -> bool:
        """Update student's quiz grade and add feedback comment"""
        url = f"{API_V1}/courses/{course_id}/assignments/{assignment_id}/submissions/{user_id}"

        data = {
            'submission[posted_grade]': str(grade),
            'comment[text_comment]': comment
        }

        response = self.session.put(url, data=data)

        if response.status_code == 200:
            return True
        else:
            print(f"  ❌ Failed to update grade for user {user_id}: {response.status_code}")
            return False


def display_submission_for_review(result: GradingResult, index: int, total: int) -> None:
    """Display a single submission for review"""
    print("\n" + "=" * 100)
    print(f"SUBMISSION {index}/{total}: {result.student_name} (ID: {result.student_id})")
    print("=" * 100)
    
    print("\n📝 STUDENT ESSAY:")
    print("-" * 100)
    # Show first 500 characters of essay
    essay_preview = result.essay_text[:500]
    if len(result.essay_text) > 500:
        essay_preview += f"\n... ({len(result.essay_text) - 500} more characters)"
    print(essay_preview)
    
    print("\n🤖 AI GRADING:")
    print("-" * 100)
    print(f"Grade: {result.ai_grade:.1f} / {result.new_question_grade:.1f}")
    print(f"\nFeedback:\n{result.ai_feedback}")
    
    print("\n📊 GRADE IMPACT:")
    print("-" * 100)
    print(f"Old question grade: {result.old_question_grade:.1f}")
    print(f"New question grade: {result.new_question_grade:.1f}")
    print(f"Old total grade:    {result.old_total_grade:.1f}")
    print(f"New total grade:    {result.new_total_grade:.1f}")
    print(f"Change:             {result.new_total_grade - result.old_total_grade:+.1f}")


def get_user_choice(prompt: str, max_value: int) -> int:
    """Get user selection from menu"""
    while True:
        try:
            choice = input(f"\n{prompt} (1-{max_value}, or 'q' to quit): ").strip()
            if choice.lower() == 'q':
                print("\nExiting...")
                sys.exit(0)

            value = int(choice)
            if 1 <= value <= max_value:
                return value - 1
            else:
                print(f"Please enter a number between 1 and {max_value}")
        except ValueError:
            print("Invalid input. Please enter a number.")


def clear_screen():
    """Clear the terminal screen (like cls in BASIC)"""
    os.system('clear' if os.name == 'posix' else 'cls')


def list_and_select_json_file() -> str:
    """List all essays_*.json files and let user select one"""
    json_files = sorted(glob.glob("essays_*.json"), reverse=True)
    
    if not json_files:
        print("❌ No essay grading JSON files found in current directory")
        print("   Make sure you're in the same directory as the JSON files from Part A")
        sys.exit(1)
    
    print("\nAvailable Grading Sessions:")
    print("=" * 80)
    
    # Load metadata from each file for display
    file_metadata = []
    for filename in json_files:
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
                course_name = data.get('selected_course', {}).get('name', 'Unknown Course')
                assignment_name = data.get('selected_assignment', {}).get('name', 'Unknown Assignment')
                question_title = data.get('selected_question', {}).get('title', 'Unknown Question')
                num_students = len(data.get('grading_results', []))
                
                file_metadata.append({
                    'filename': filename,
                    'course': course_name,
                    'assignment': assignment_name,
                    'question': question_title,
                    'count': num_students
                })
        except Exception as e:
            print(f"⚠️  Warning: Could not read {filename}: {e}")
            continue
    
    if not file_metadata:
        print("❌ No valid grading session files found")
        sys.exit(1)
    
    # Display menu
    for i, meta in enumerate(file_metadata, 1):
        print(f"\n{i}. Course: {meta['course']}")
        print(f"   Assignment: {meta['assignment']}")
        print(f"   Question: {meta['question']}")
        print(f"   Students: {meta['count']}")
    
    print("\n" + "=" * 80)
    
    # Get selection
    choice = get_user_choice("Select a grading session", len(file_metadata))
    return file_metadata[choice]['filename']


def load_grading_data(json_filename: str) -> Dict:
    """Load grading data from JSON file"""
    try:
        with open(json_filename, 'r') as f:
            data = json.load(f)
        
        print(f"\n✅ Loaded grading data from: {json_filename}")
        return data
    except FileNotFoundError:
        print(f"❌ File not found: {json_filename}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        sys.exit(1)


def create_backup(json_filename: str) -> str:
    """Create backup of JSON file"""
    backup_filename = json_filename.replace('.json', '.bak.json')
    try:
        shutil.copy2(json_filename, backup_filename)
        print(f"💾 Backup created: {backup_filename}")
        return backup_filename
    except Exception as e:
        print(f"⚠️  Warning: Could not create backup: {e}")
        return None


def save_grading_data(data: Dict, json_filename: str) -> None:
    """Save updated grading data back to JSON file"""
    try:
        with open(json_filename, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"⚠️  Warning: Could not save updated JSON: {e}")


def get_validation_action() -> str:
    """Get user's validation choice"""
    while True:
        choice = input("\n(v)alidate / (o)verride / (s)kip / (q)uit: ").strip().lower()
        if choice in ['v', 'validate']:
            return 'validate'
        elif choice in ['o', 'override']:
            return 'override'
        elif choice in ['s', 'skip']:
            return 'skip'
        elif choice in ['q', 'quit']:
            return 'quit'
        else:
            print("Invalid choice. Please enter 'v', 'o', 's', or 'q'")


def get_override_grade(points_possible: float) -> float:
    """Get override grade from user"""
    while True:
        try:
            grade_str = input(f"\nEnter new grade (0-{points_possible}): ").strip()
            grade = float(grade_str)
            if 0 <= grade <= points_possible:
                return grade
            else:
                print(f"Grade must be between 0 and {points_possible}")
        except ValueError:
            print("Invalid input. Please enter a number.")


def get_override_feedback() -> str:
    """Get override feedback from user"""
    print("\nEnter new feedback (enter a blank line when done):")
    lines = []
    while True:
        line = input()
        if line.strip() == "":
            break
        lines.append(line)
    return "\n".join(lines)


def main():
    """Main program flow"""
    # Clear screen at startup
    clear_screen()

    print("=" * 80)
    print("   CANVAS NEW QUIZZES - ESSAY GRADER WITH OPENAI - PART B")
    print("=" * 80)

    # Initialize Canvas client
    print("\n🔐 Authenticating...")
    canvas_client = CanvasAPIClient()

    # Step 1: Select JSON file to process
    json_filename = list_and_select_json_file()

    # Step 2: Create backup
    print(f"\n📋 Creating backup...")
    backup_filename = create_backup(json_filename)

    # Step 3: Load grading data
    print(f"\n📂 Loading grading data...")
    data = load_grading_data(json_filename)

    # Step 4: Extract data (using EXACT same names as original script)
    grading_results = [GradingResult(**r) for r in data.get('grading_results', [])]
    skipped = data.get('skipped', [])
    selected_course = data.get('selected_course', {})
    selected_assignment = data.get('selected_assignment', {})
    selected_question = data.get('selected_question', {})

    if not grading_results:
        print("❌ No grading results found in file")
        sys.exit(1)

    print(f"\n✅ Loaded {len(grading_results)} student submission(s)")
    if skipped:
        print(f"   ({len(skipped)} were skipped during grading)")

    # Step 5: Individual validation loop with new behavior
    print("\n" + "=" * 100)
    print("INDIVIDUAL SUBMISSION REVIEW")
    print("=" * 100)
    print("Review each submission:")
    print("  (v)alidate - Upload AI grade/feedback immediately")
    print("  (o)verride - Enter new grade/feedback and upload immediately")
    print("  (s)kip     - Move to next student (keeps in queue)")
    print("  (q)uit     - Exit (remaining students stay in queue)")

    uploaded_count = 0
    skipped_count = 0
    i = 0

    while i < len(grading_results):
        result = grading_results[i]
        
        display_submission_for_review(result, i + 1, len(grading_results))
        
        action = get_validation_action()
        
        if action == 'validate':
            # Upload AI grade and feedback
            feedback = (
                f"AI-Graded Essay: {selected_question['title']}\n"
                f"Old score: {result.old_question_grade:.1f}\n"
                f"New score: {result.new_question_grade:.1f}\n\n"
                f"Feedback:\n{result.ai_feedback}"
            )
            
            print(f"\n📤 Uploading AI grade to Canvas...")
            success = canvas_client.update_grade(
                selected_course['id'],
                selected_assignment['id'],
                result.student_id,
                result.new_total_grade,
                feedback
            )
            
            if success:
                print(f"  ✅ Uploaded grade for {result.student_name}")
                uploaded_count += 1
                # Remove from grading_results and update JSON
                grading_results.pop(i)
                data['grading_results'] = [r.__dict__ if hasattr(r, '__dict__') else r for r in grading_results]
                save_grading_data(data, json_filename)
                # Don't increment i since we removed an item
            else:
                print(f"  ❌ Failed to upload - keeping in queue")
                i += 1
        
        elif action == 'override':
            # Get new grade and feedback from user
            new_grade = get_override_grade(selected_question['points_possible'])
            new_feedback = get_override_feedback()
            
            # Calculate new total grade
            new_total_grade = result.old_total_grade - result.old_question_grade + new_grade
            
            # Build feedback comment (using override values, NOT AI values)
            feedback = (
                f"Manually Graded Essay: {selected_question['title']}\n"
                f"Old score: {result.old_question_grade:.1f}\n"
                f"New score: {new_grade:.1f}\n\n"
                f"Feedback:\n{new_feedback}"
            )
            
            print(f"\n📤 Uploading override grade to Canvas...")
            success = canvas_client.update_grade(
                selected_course['id'],
                selected_assignment['id'],
                result.student_id,
                new_total_grade,
                feedback
            )
            
            if success:
                print(f"  ✅ Uploaded override grade for {result.student_name}")
                uploaded_count += 1
                # Remove from grading_results and update JSON
                grading_results.pop(i)
                data['grading_results'] = [r.__dict__ if hasattr(r, '__dict__') else r for r in grading_results]
                save_grading_data(data, json_filename)
                # Don't increment i since we removed an item
            else:
                print(f"  ❌ Failed to upload - keeping in queue")
                i += 1
        
        elif action == 'skip':
            print(f"  ⏭️  Skipped {result.student_name}")
            skipped_count += 1
            i += 1
        
        elif action == 'quit':
            print(f"\n👋 Exiting validation...")
            break

    # Step 6: Final summary
    print("\n" + "=" * 100)
    print("VALIDATION SUMMARY")
    print("=" * 100)
    print(f"✅ Uploaded to Canvas:      {uploaded_count} grade(s)")
    print(f"⏭️  Skipped (still in queue): {skipped_count} student(s)")
    print(f"📋 Remaining in queue:      {len(grading_results)} student(s)")
    
    if len(grading_results) > 0:
        print(f"\n💾 Progress saved to: {json_filename}")
        print(f"   Run Part B again to continue validation")
    else:
        print(f"\n🎉 All submissions processed!")
        print(f"   You can delete: {json_filename}")
        if backup_filename:
            print(f"   Backup available at: {backup_filename}")


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
