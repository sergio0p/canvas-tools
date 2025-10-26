#!/usr/bin/env python3
"""
Canvas Text Entry Assignments: Generic Grader - PART A

Grades text entry submissions in Canvas Assignments using OpenAI API.
Saves results to JSON for later review and upload (Part B).
Loads grading schema and instructions from JSON configuration file.
"""

import sys
import os
import time
import json
import glob
import subprocess
import keyring
import requests
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from openai import OpenAI
from bs4 import BeautifulSoup

# Configuration
CANVAS_SERVICE_NAME = 'canvas'
CANVAS_USERNAME = 'access-token'
HOST = 'https://uncch.instructure.com'
API_V1 = f"{HOST}/api/v1"

MAX_CONCURRENT_REQUESTS = 5  # Maximum parallel OpenAI API requests

# Get OpenAI API key from macOS Keychain
def get_openai_api_key():
    """Retrieve OpenAI API key from macOS Keychain"""
    result = subprocess.run(
        ["security", "find-generic-password", "-a", "openai", "-s", "openai_api_key", "-w"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True
    )
    key = result.stdout.strip()
    if not key:
        print("⚠️  WARNING: Could not retrieve OpenAI API key from Keychain")
        print("   Set it using: security add-generic-password -a openai -s openai_api_key -w 'your_key'")
    return key


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


@dataclass
class StudentSubmission:
    """Represents a student's text submission"""
    student_id: int
    student_name: str
    essay_text: str
    old_assignment_grade: float


@dataclass
class GradingResult:
    """Represents AI grading results for a student"""
    student_id: int
    student_name: str
    essay_text: str
    ai_grade: float
    ai_feedback: str
    old_assignment_grade: float
    new_assignment_grade: float
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
                    a.get('due_at')
                ))

        return text_entry_assignments

    def get_submissions(self, course_id: int, assignment_id: int) -> List[dict]:
        """Fetch all submissions for an assignment"""
        url = f"{API_V1}/courses/{course_id}/assignments/{assignment_id}/submissions"
        
        params = {
            'per_page': 100,
            'include[]': ['user']
        }
        
        response = self.session.get(url, params=params)

        if response.status_code != 200:
            print(f"❌ Failed to fetch submissions: {response.status_code}")
            sys.exit(1)

        return response.json()


def load_grading_config(filename: str) -> Dict:
    """
    Load grading configuration from JSON file.
    
    Expected format:
    {
        "schema": {
            "type": "object",
            "properties": {
                "grade": {"type": "number", "enum": [0, 3, 4]},
                "feedback": {"type": "string", "minLength": 1, "maxLength": 4000}
            },
            "required": ["grade", "feedback"],
            "additionalProperties": false
        },
        "instructions": "Grading instructions text here..."
    }
    """
    try:
        with open(filename, 'r') as f:
            config = json.load(f)
        
        # Validate structure
        if 'schema' not in config:
            print(f"❌ Grading config missing 'schema' field")
            sys.exit(1)
        
        if 'instructions' not in config:
            print(f"❌ Grading config missing 'instructions' field")
            sys.exit(1)
        
        # Validate schema structure
        schema = config['schema']
        if not isinstance(schema, dict):
            print(f"❌ 'schema' must be a JSON object")
            sys.exit(1)
        
        if 'properties' not in schema or 'grade' not in schema['properties']:
            print(f"❌ Schema must include 'properties' with 'grade' field")
            sys.exit(1)
        
        if 'feedback' not in schema['properties']:
            print(f"❌ Schema must include 'properties' with 'feedback' field")
            sys.exit(1)
        
        # Validate instructions
        if not isinstance(config['instructions'], str) or not config['instructions'].strip():
            print(f"❌ 'instructions' must be a non-empty string")
            sys.exit(1)
        
        return config
        
    except FileNotFoundError:
        print(f"❌ Grading config file not found: {filename}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing grading config JSON: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error loading grading config: {e}")
        sys.exit(1)


class EssayGrader:
    """Handles essay grading using OpenAI API"""

    def __init__(self, grading_config: Dict):
        """Initialize OpenAI client with grading configuration"""
        api_key = get_openai_api_key()
        if not api_key:
            print("❌ ERROR: OpenAI API key required for essay grading")
            sys.exit(1)
        self.client = OpenAI(api_key=api_key)
        self.schema = grading_config['schema']
        self.instructions = grading_config['instructions']

    @staticmethod
    def extract_essay_text(answer_html: str) -> str:
        """Extract plain text from HTML essay answer"""
        if not answer_html:
            return ""
        soup = BeautifulSoup(answer_html, 'html.parser')
        return soup.get_text(separator='\n', strip=True)

    def grade_essay(self, submission_content: str, points_possible: float, is_structured: bool = False) -> Tuple[float, str]:
        """
        Grade a submission using OpenAI API with configured schema and instructions
        
        Args:
            submission_content: Either plain text or JSON string of structured content
            points_possible: Maximum points for the assignment
            is_structured: If True, submission_content is structured JSON; if False, plain text
        
        Returns: (grade, feedback)
        """
        # Build the prompt based on submission type
        if is_structured:
            submission_section = f"""STUDENT SUBMISSION (Structured JSON):
\"\"\"
{submission_content}
\"\"\"

NOTE: The submission is in structured JSON format with "content" array containing text sections and tables.
Tables have "blue_entries" showing which relations the student marked in blue."""
        else:
            submission_section = f"""STUDENT SUBMISSION:
\"\"\"
{submission_content}
\"\"\""""
        
        prompt = f"""You are grading a student submission. Here are the details:

GRADING INSTRUCTIONS:
{self.instructions}

POINTS POSSIBLE: {points_possible}

{submission_section}

Please grade this submission according to the grading instructions. Your response must be a valid JSON object with exactly two fields:
{{
  "grade": <numeric grade>,
  "feedback": "<feedback text>"
}}

IMPORTANT:
- Respond ONLY with valid JSON. Do not include any text outside the JSON structure.
- Do not include markdown code blocks or backticks.
- Follow the grading schema exactly.
- The feedback should be constructive and follow the guidelines in the grading instructions.
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "grading_schema",
                        "schema": self.schema
                    }
                },
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a strict grader that follows the rubric exactly and returns ONLY the "
                            "structured result. Do not include any extra text."
                        )
                    },
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = response.choices[0].message.content.strip()
            
            # Clean up response (remove markdown code blocks if present)
            response_text = response_text.replace('```json', '').replace('```', '').strip()
            
            # Parse JSON response
            result = json.loads(response_text)
            
            grade = float(result.get('grade', 0))
            feedback = result.get('feedback', 'No feedback provided')
            
            # Validate grade is in allowed enum if specified
            if 'enum' in self.schema.get('properties', {}).get('grade', {}):
                allowed_grades = self.schema['properties']['grade']['enum']
                if grade not in allowed_grades:
                    print(f"  ⚠️  Warning: AI returned grade {grade} not in allowed values {allowed_grades}")
                    # Find closest allowed grade
                    grade = min(allowed_grades, key=lambda x: abs(x - grade))
                    print(f"  ℹ️  Adjusted to closest allowed grade: {grade}")
            
            return grade, feedback

        except json.JSONDecodeError as e:
            print(f"  ❌ Failed to parse AI response as JSON: {e}")
            print(f"  Response was: {response_text[:200]}")
            return 0.0, "Error: Could not parse AI response"
        except Exception as e:
            print(f"  ❌ Error calling OpenAI API: {e}")
            return 0.0, f"Error: {str(e)}"

    def grade_essay_batch(self, submissions: List[Tuple], points_possible: float) -> List[GradingResult]:
        """
        Grade multiple essays in parallel using ThreadPoolExecutor
        
        Args:
            submissions: List of (student_id, student_name, content, old_assignment_grade, is_structured)
                        where content is either plain text or JSON string
            points_possible: Maximum points for the assignment
            
        Returns:
            List of GradingResult objects
        """
        def grade_single(submission_data):
            student_id, student_name, content, old_assignment_grade, is_structured = submission_data
            
            print(f"  🤖 Grading {student_name}...")
            ai_grade, ai_feedback = self.grade_essay(content, points_possible, is_structured)
            
            new_assignment_grade = ai_grade
            
            print(f"  ✅ {student_name}: {ai_grade}/{points_possible}")
            
            return GradingResult(
                student_id=student_id,
                student_name=student_name,
                essay_text=content,  # Store the content (plain or structured)
                ai_grade=ai_grade,
                ai_feedback=ai_feedback,
                old_assignment_grade=old_assignment_grade,
                new_assignment_grade=new_assignment_grade
            )
        
        # Use ThreadPoolExecutor for parallel grading
        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_REQUESTS) as executor:
            results = list(executor.map(grade_single, submissions))
        
        return results


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
    print("TEXT ENTRY ASSIGNMENTS")
    print("=" * 100)
    for i, assignment in enumerate(assignments, 1):
        due = assignment.due_at or "No due date"
        print(f"{i}. {assignment.name} (Points: {assignment.points_possible}, Due: {due})")
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


def select_grading_config() -> str:
    """Let user select a grading configuration JSON file"""
    import glob
    
    json_files = glob.glob("grading_config_*.json")
    
    if not json_files:
        print("❌ No grading configuration files found (grading_config_*.json)")
        sys.exit(1)
    
    # Sort alphabetically
    json_files.sort()
    
    print("\n" + "=" * 100)
    print("SELECT GRADING CONFIGURATION FILE")
    print("=" * 100)
    print("This file contains the grading schema and instructions for the AI.")
    print("=" * 100)
    
    for i, filename in enumerate(json_files, 1):
        print(f"{i}. {filename}")
    
    print("=" * 100)
    
    while True:
        try:
            choice = input(f"\nSelect file (1-{len(json_files)}): ").strip()
            choice_num = int(choice)
            if 1 <= choice_num <= len(json_files):
                return json_files[choice_num - 1]
            else:
                print(f"Please enter a number between 1 and {len(json_files)}")
        except ValueError:
            print("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print("\n\n👋 Cancelled by user")
            sys.exit(0)


def save_grading_results(results: List[GradingResult], skipped: List[str], filename: str,
                        course_id: int, course_name: str, assignment_id: int, assignment_name: str,
                        assignment_points: float, grading_config_filename: str) -> None:
    """Save grading results to JSON file"""
    data = {
        "grading_results": [asdict(r) for r in results],
        "skipped": skipped,
        "json_filename": filename,
        "selected_course": {
            "id": course_id,
            "name": course_name
        },
        "selected_assignment": {
            "id": assignment_id,
            "name": assignment_name,
            "points_possible": assignment_points
        },
        "grading_config_filename": grading_config_filename
    }
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"\n💾 Grading results saved to: {filename}")


def clear_screen():
    """Clear the terminal screen (like cls in BASIC)"""
    os.system('clear' if os.name == 'posix' else 'cls')


def main():
    """Main program flow"""
    # Clear screen at startup
    clear_screen()

    print("=" * 100)
    print("   CANVAS TEXT ENTRY ASSIGNMENTS - Generic Grader - PART A")
    print("   This grader works with Canvas Assignments that accept online text entry")
    print("=" * 100)

    # Ask if user wants to load from preprocessed file or fetch from Canvas
    print("\n📂 SUBMISSION SOURCE")
    print("=" * 100)
    print("Load submissions from:")
    print("  1. Fetch from Canvas API (standard)")
    print("  2. Load from preprocessed JSON file (for structured submissions)")
    
    while True:
        try:
            choice = input("\nEnter choice (1-2): ").strip()
            if choice in ['1', '2']:
                break
            print("Please enter 1 or 2")
        except KeyboardInterrupt:
            print("\n\n👋 Cancelled by user")
            sys.exit(0)
    
    use_preprocessed = (choice == '2')
    
    if use_preprocessed:
        # Load from preprocessed JSON file
        print("\n📂 Looking for preprocessed JSON files...")
        json_files = glob.glob("*_processed.json")
        
        if not json_files:
            print("❌ No *_processed.json files found in current directory")
            print("   Run html_to_json_converter.py first to create preprocessed files")
            sys.exit(1)
        
        print("\n" + "=" * 100)
        print("AVAILABLE PREPROCESSED FILES")
        print("=" * 100)
        for i, f in enumerate(json_files, 1):
            print(f"{i}. {f}")
        print("=" * 100)
        
        while True:
            try:
                file_choice = input(f"\nSelect file (1-{len(json_files)}): ").strip()
                file_idx = int(file_choice) - 1
                if 0 <= file_idx < len(json_files):
                    break
                print(f"Please enter a number between 1 and {len(json_files)}")
            except ValueError:
                print("Invalid input. Please enter a number.")
            except KeyboardInterrupt:
                print("\n\n👋 Cancelled by user")
                sys.exit(0)
        
        preprocessed_file = json_files[file_idx]
        print(f"\n✅ Selected: {preprocessed_file}")
        
        # Load the preprocessed file
        print(f"\n📂 Loading preprocessed submissions...")
        try:
            with open(preprocessed_file, 'r') as f:
                preprocessed_data = json.load(f)
        except Exception as e:
            print(f"❌ Failed to load file: {e}")
            sys.exit(1)
        
        submissions_data = preprocessed_data.get('submissions', [])
        selected_course_name = preprocessed_data.get('course', 'Unknown Course')
        selected_assignment_name = preprocessed_data.get('assignment', 'Unknown Assignment')
        
        # We need course_id and assignment_id for saving results
        # Try to extract from filename: text_submissions_COURSEID_ASSIGNMENTID_processed.json
        import re
        match = re.search(r'text_submissions_(\d+)_(\d+)_processed\.json', preprocessed_file)
        if match:
            selected_course_id = int(match.group(1))
            selected_assignment_id = int(match.group(2))
        else:
            print("⚠️  Warning: Could not extract course/assignment IDs from filename")
            selected_course_id = 0
            selected_assignment_id = 0
        
        # Estimate points_possible - will be confirmed when loading grading config
        selected_assignment_points = 0.0  # Will be set from grading config
        
        print(f"✅ Loaded {len(submissions_data)} submission(s)")
        print(f"   Course: {selected_course_name}")
        print(f"   Assignment: {selected_assignment_name}")
        
    else:
        # Original workflow: Fetch from Canvas
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
        print(f"\n📋 Fetching text entry assignments for {selected_course.name}...")
        assignments = canvas_client.get_text_entry_assignments(selected_course.id)

        if not assignments:
            print("❌ No text entry assignments found in this course")
            sys.exit(1)

        display_assignments(assignments)
        assignment_idx = get_user_choice("Select an assignment", len(assignments))
        selected_assignment = assignments[assignment_idx]
        print(f"\n✅ Selected: {selected_assignment.name}")
        
        selected_course_name = selected_course.name
        selected_course_id = selected_course.id
        selected_assignment_name = selected_assignment.name
        selected_assignment_id = selected_assignment.id
        selected_assignment_points = selected_assignment.points_possible
        
        # Fetch submissions from Canvas
        print(f"\n⬇️  Fetching submissions from Canvas...")
        submissions_data = canvas_client.get_submissions(
            selected_course.id,
            selected_assignment.id
        )

        print(f"✅ Fetched {len(submissions_data)} submission(s)")
    
    # Step 3: Select grading configuration
    grading_config_filename = select_grading_config()
    print(f"\n✅ Selected: {grading_config_filename}")

    print(f"\n📋 Loading grading configuration...")
    grading_config = load_grading_config(grading_config_filename)
    print(f"✅ Grading configuration loaded")
    print(f"   Allowed grades: {grading_config['schema']['properties']['grade'].get('enum', 'any numeric value')}")
    
    # If we loaded from preprocessed file, get points_possible from grading config
    if use_preprocessed:
        # Estimate from max value in grade enum
        grade_enum = grading_config['schema']['properties']['grade'].get('enum', [])
        if grade_enum:
            selected_assignment_points = max(grade_enum)
            print(f"   Points possible (from config): {selected_assignment_points}")
        else:
            print("   ⚠️  Warning: Could not determine points_possible from grading config")
            selected_assignment_points = 100.0  # Default fallback

    # Initialize essay grader with configuration
    print("\n🔐 Initializing OpenAI grader...")
    essay_grader = EssayGrader(grading_config)

    # Step 5: Prepare submissions and grade with AI in parallel
    print(f"\n🤖 Preparing submissions for AI grading...")

    submissions_to_grade = []
    skipped = []

    for submission in submissions_data:
        student_id = submission['user_id']
        student_name = submission.get('user', {}).get('name', 'Unknown Student')
        
        # Only process text entry submissions with content
        if submission.get('submission_type') != 'online_text_entry':
            continue
        
        # Check if submission has structured content (from preprocessor)
        if 'structured_content' in submission and submission['structured_content']:
            # Case 1: Structured submission (tables, formatted content)
            structured_content = submission['structured_content']
            content_str = json.dumps(structured_content, indent=2)
            is_structured = True
            print(f"  📊 {student_name}: Structured submission detected")
        else:
            # Case 2: Regular text submission
            essay_html = submission.get('body', '')
            
            if not essay_html or essay_html.strip() == '':
                skipped.append(f"{student_name}: Empty submission")
                continue
            
            content_str = essay_grader.extract_essay_text(essay_html)
            is_structured = False
        
        old_assignment_grade = submission.get('score', 0.0) or 0.0

        submissions_to_grade.append((
            student_id,
            student_name,
            content_str,
            old_assignment_grade,
            is_structured
        ))

    if not submissions_to_grade:
        print("❌ No text submissions to grade")
        if skipped:
            print("\nSkipped students:")
            for msg in skipped:
                print(f"  - {msg}")
        sys.exit(1)

    # Grade all submissions in parallel
    print(f"\n🚀 Grading {len(submissions_to_grade)} submission(s) in parallel (max {MAX_CONCURRENT_REQUESTS} concurrent)...")
    print("   This will be much faster than sequential grading!")

    grading_results = essay_grader.grade_essay_batch(
        submissions_to_grade,
        selected_assignment_points
    )

    if not grading_results:
        print("❌ No submissions were successfully graded")
        if skipped:
            print("\nSkipped students:")
            for msg in skipped:
                print(f"  - {msg}")
        sys.exit(1)

    # Save results to JSON
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_filename = f"text_entries_{selected_course_id}_{timestamp}.json"
    save_grading_results(
        grading_results,
        skipped,
        json_filename,
        selected_course_id,
        selected_course_name,
        selected_assignment_id,
        selected_assignment_name,
        selected_assignment_points,
        grading_config_filename
    )

    # Final summary
    print("\n" + "=" * 100)
    print("GRADING COMPLETE - PART A")
    print("=" * 100)
    print(f"✅ Successfully graded:     {len(grading_results)} submission(s)")
    if skipped:
        print(f"⚠️  Skipped (no answer):     {len(skipped)} student(s)")
        print("\nSkipped students:")
        for msg in skipped:
            print(f"  - {msg}")
    print(f"\n💾 Results saved to: {json_filename}")
    print("\n📝 Next step: Run Part B to review and upload grades to Canvas")


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
