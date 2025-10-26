#!/usr/bin/env python3
"""
Canvas New Quizzes: Generic Grader - PART A
CANVAS NEW QUIZZES ONLY - NOT for regular assignments

Grades questions in Canvas New Quizzes using OpenAI API.
Saves results to JSON for later review and upload (Part B).
Loads grading schema and instructions from JSON configuration file.
"""

import sys
import os
import time
import json
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
API_QUIZ = f"{HOST}/api/quiz/v1"

POLL_INTERVAL = 2.0
REPORT_TIMEOUT = 900
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

    def get_new_quizzes(self, course_id: int) -> List[Assignment]:
        """Fetch New Quizzes assignments for a course"""
        url = f"{API_V1}/courses/{course_id}/assignments"
        response = self.session.get(url, params={'per_page': 100})

        if response.status_code != 200:
            print(f"❌ Failed to fetch assignments: {response.status_code}")
            sys.exit(1)

        assignments = response.json()
        new_quizzes = [
            Assignment(
                a['id'],
                a['name'],
                a.get('points_possible', 0.0),
                a.get('due_at')
            )
            for a in assignments
            if a.get('is_quiz_lti_assignment')
        ]

        return new_quizzes

    def get_quiz_items(self, course_id: int, assignment_id: int) -> List[dict]:
        """Fetch quiz items/questions"""
        url = f"{API_QUIZ}/courses/{course_id}/quizzes/{assignment_id}/items"
        response = self.session.get(url)

        if response.status_code != 200:
            print(f"❌ Failed to fetch quiz items: {response.status_code}")
            sys.exit(1)

        return response.json()

    def create_student_analysis_report(self, course_id: int, assignment_id: int) -> str:
        """Create a student_analysis report and return progress URL"""
        url = f"{API_QUIZ}/courses/{course_id}/quizzes/{assignment_id}/reports"
        payload = {
            "quiz_report": {
                "report_type": "student_analysis",
                "format": "json"
            }
        }

        response = self.session.post(url, json=payload)

        if response.status_code not in (200, 201, 202):
            print(f"❌ Failed to create report: {response.status_code}")
            sys.exit(1)

        data = response.json()
        progress_url = data.get('progress_url') or (data.get('progress') or {}).get('url')

        if not progress_url and (data.get('progress') or {}).get('id'):
            progress_url = f"/api/v1/progress/{data['progress']['id']}"

        if not progress_url:
            print(f"❌ No progress_url in response")
            sys.exit(1)

        return progress_url

    def poll_progress(self, progress_url: str) -> dict:
        """Poll progress endpoint until completion"""
        url = progress_url if progress_url.startswith("http") else f"{HOST}{progress_url}"
        start = time.time()

        while True:
            response = self.session.get(url)

            if response.status_code != 200:
                print(f"❌ Progress polling failed: {response.status_code}")
                sys.exit(1)

            prog = response.json()
            state = prog.get('workflow_state')

            print(f"  Report status: {state}")

            if state == 'completed':
                return prog
            elif state == 'failed':
                print(f"❌ Report generation failed")
                sys.exit(1)
            elif time.time() - start > REPORT_TIMEOUT:
                print(f"❌ Report generation timed out after {REPORT_TIMEOUT}s")
                sys.exit(1)

            time.sleep(POLL_INTERVAL)

    def resolve_download_url(self, progress_data: dict) -> str:
        """Extract download URL from progress response"""
        results = progress_data.get('results') or {}

        if isinstance(results, dict):
            url = results.get('url')
            if url:
                return url

            att = results.get('attachment') or {}
            if isinstance(att, dict):
                url = att.get('url') or att.get('download_url')
                if url:
                    return url

            file_id = results.get('attachment_id') or results.get('file_id')
            if file_id:
                file_url = f"{API_V1}/files/{file_id}"
                response = self.session.get(file_url)
                if response.status_code == 200:
                    file_data = response.json()
                    return file_data.get('url') or file_data.get('download_url')

        print(f"❌ Could not resolve download URL")
        sys.exit(1)

    def download_report(self, url: str) -> List[dict]:
        """Download and parse student analysis report"""
        response = self.session.get(url, stream=True)

        if response.status_code != 200:
            print(f"❌ Failed to download report: {response.status_code}")
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
    def parse_quiz_item(item: dict) -> Optional[EssayQuestion]:
        """Parse a quiz item to extract essay question details"""
        entry = item.get('entry', {})

        if entry.get('interaction_type_slug') != 'essay':
            return None

        item_id = item['id']
        title = entry.get('title', 'Untitled Question')
        points_possible = item.get('points_possible', 0.0)
        prompt_html = entry.get('item_body', '')

        # Extract plain text from HTML
        soup = BeautifulSoup(prompt_html, 'html.parser')
        prompt = soup.get_text(separator=' ', strip=True)

        return EssayQuestion(
            item_id=item_id,
            title=title,
            points_possible=points_possible,
            prompt=prompt
        )

    @staticmethod
    def extract_essay_text(answer_html: str) -> str:
        """Extract plain text from HTML essay answer"""
        if not answer_html:
            return ""
        soup = BeautifulSoup(answer_html, 'html.parser')
        return soup.get_text(separator='\n', strip=True)

    def grade_essay(self, essay_text: str, points_possible: float) -> Tuple[float, str]:
        """
        Grade an essay using OpenAI API with configured schema and instructions

        Returns: (grade, feedback)
        """
        prompt = f"""You are grading a student submission. Here are the details:

GRADING INSTRUCTIONS:
{self.instructions}

POINTS POSSIBLE: {points_possible}

STUDENT SUBMISSION:
\"\"\"
{essay_text}
\"\"\"

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
            submissions: List of (student_id, student_name, essay_text, old_question_grade, old_total_grade)
            points_possible: Maximum points for the question
            
        Returns:
            List of GradingResult objects
        """
        def grade_single(submission_data):
            student_id, student_name, essay_text, old_question_grade, old_total_grade = submission_data
            
            print(f"  🤖 Grading {student_name}...")
            ai_grade, ai_feedback = self.grade_essay(essay_text, points_possible)
            
            new_question_grade = ai_grade
            new_total_grade = old_total_grade - old_question_grade + new_question_grade
            
            print(f"  ✅ {student_name}: {ai_grade}/{points_possible}")
            
            return GradingResult(
                student_id=student_id,
                student_name=student_name,
                essay_text=essay_text,
                ai_grade=ai_grade,
                ai_feedback=ai_feedback,
                old_question_grade=old_question_grade,
                new_question_grade=new_question_grade,
                old_total_grade=old_total_grade,
                new_total_grade=new_total_grade
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
    print("NEW QUIZZES")
    print("=" * 100)
    for i, assignment in enumerate(assignments, 1):
        due = assignment.due_at or "No due date"
        print(f"{i}. {assignment.name} (Points: {assignment.points_possible}, Due: {due})")
    print("=" * 100)


def display_questions(questions: List[EssayQuestion]) -> None:
    """Display essay questions in a numbered list"""
    print("\n" + "=" * 100)
    print("ESSAY QUESTIONS")
    print("=" * 100)
    for i, question in enumerate(questions, 1):
        prompt_preview = question.prompt[:100] + "..." if len(question.prompt) > 100 else question.prompt
        print(f"{i}. {question.title}")
        print(f"   Points: {question.points_possible}")
        print(f"   Prompt: {prompt_preview}")
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
    """Let user enter grading configuration JSON file path"""
    print("\n" + "=" * 100)
    print("GRADING CONFIGURATION FILE")
    print("=" * 100)
    print("Enter the path to your grading config JSON file.")
    print("You can drag & drop the file into the terminal or type/paste the path.")
    print("=" * 100)

    while True:
        try:
            filepath = input("\nFile path: ").strip()

            if not filepath:
                print("❌ No file path entered")
                continue

            # Remove quotes if user dragged/dropped (some terminals add quotes)
            if filepath.startswith("'") and filepath.endswith("'"):
                filepath = filepath[1:-1]
            if filepath.startswith('"') and filepath.endswith('"'):
                filepath = filepath[1:-1]

            # Check if file exists
            if os.path.isfile(filepath):
                # Verify it's a JSON file
                if filepath.endswith('.json'):
                    return filepath
                else:
                    print(f"⚠️  Warning: File doesn't have .json extension")
                    confirm = input("Use anyway? (y/n): ").strip().lower()
                    if confirm == 'y':
                        return filepath
            else:
                print(f"❌ File not found: {filepath}")
                retry = input("Try again? (y/n): ").strip().lower()
                if retry != 'y':
                    print("❌ Cannot continue without grading configuration")
                    sys.exit(1)
        except KeyboardInterrupt:
            print("\n\n👋 Cancelled by user")
            sys.exit(0)


def save_grading_results(results: List[GradingResult], skipped: List[str], filename: str,
                        course_id: int, course_name: str, assignment_id: int, assignment_name: str,
                        question_title: str, question_points: float, question_item_id: str,
                        grading_config_filename: str) -> None:
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
            "name": assignment_name
        },
        "selected_question": {
            "title": question_title,
            "points_possible": question_points,
            "item_id": question_item_id
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
    print("   CANVAS NEW QUIZZES ONLY - Generic Grader - PART A")
    print("   This grader works ONLY with Canvas New Quizzes,")
    print("   not regular assignments nor Classical Quizzes")
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
    print(f"\n📋 Fetching New Quizzes for {selected_course.name}...")
    assignments = canvas_client.get_new_quizzes(selected_course.id)

    if not assignments:
        print("❌ No New Quizzes found in this course")
        sys.exit(1)

    display_assignments(assignments)
    assignment_idx = get_user_choice("Select a quiz", len(assignments))
    selected_assignment = assignments[assignment_idx]
    print(f"\n✅ Selected: {selected_assignment.name}")

    # Step 3: Select essay question
    print(f"\n❓ Fetching quiz questions...")
    quiz_items = canvas_client.get_quiz_items(selected_course.id, selected_assignment.id)

    questions = []
    for item in quiz_items:
        q = EssayGrader.parse_quiz_item(item)
        if q:
            questions.append(q)

    if not questions:
        print("❌ No essay questions found in this quiz")
        sys.exit(1)

    display_questions(questions)
    question_idx = get_user_choice("Select a question", len(questions))
    selected_question = questions[question_idx]
    print(f"\n✅ Selected: {selected_question.title}")

    # Step 4: Select grading configuration
    grading_config_filename = select_grading_config()
    print(f"\n✅ Selected: {grading_config_filename}")

    print(f"\n📋 Loading grading configuration...")
    grading_config = load_grading_config(grading_config_filename)
    print(f"✅ Grading configuration loaded")
    print(f"   Allowed grades: {grading_config['schema']['properties']['grade'].get('enum', 'any numeric value')}")

    # Initialize essay grader with configuration
    print("\n🔐 Initializing OpenAI grader...")
    essay_grader = EssayGrader(grading_config)

    # Step 5: Get student submissions
    print(f"\n📊 Creating student analysis report...")
    progress_url = canvas_client.create_student_analysis_report(
        selected_course.id,
        selected_assignment.id
    )

    print(f"⏳ Waiting for report generation...")
    progress_data = canvas_client.poll_progress(progress_url)

    print(f"⬇️ Downloading report...")
    download_url = canvas_client.resolve_download_url(progress_data)
    student_data = canvas_client.download_report(download_url)

    print(f"✅ Report downloaded: {len(student_data)} students")

    # Step 6: Find correct item_id from student_analysis
    question_item_id = None
    if student_data:
        first_student_responses = student_data[0].get('item_responses', [])
        essay_questions_found = 0
        for resp in first_student_responses:
            if resp.get('item_type') == 'essay':
                if essay_questions_found == question_idx:
                    question_item_id = resp.get('item_id')
                    break
                essay_questions_found += 1

    if not question_item_id:
        print(f"❌ Could not find item_id in student responses")
        sys.exit(1)

    print(f"  ℹ️  Using item_id from student_analysis: {question_item_id}")

    # Step 7: Prepare submissions and grade with AI in parallel
    print(f"\n🤖 Preparing {len(student_data)} submissions for AI grading...")

    submissions_to_grade = []
    skipped = []

    for student in student_data:
        student_id = student['student_data']['id']
        student_name = student['student_data']['name']

        # Find essay question response
        question_response = None
        for resp in student.get('item_responses', []):
            if resp.get('item_id') == question_item_id:
                question_response = resp
                break

        if not question_response:
            skipped.append(f"{student_name}: No response found")
            continue

        # Extract grades and essay
        old_question_grade = question_response.get('score', 0.0)
        old_total_grade = student.get('summary', {}).get('score', 0.0)
        essay_html = question_response.get('answer', '')

        if not essay_html or essay_html.strip() == '':
            skipped.append(f"{student_name}: Empty submission")
            continue

        essay_text = essay_grader.extract_essay_text(essay_html)

        submissions_to_grade.append((
            student_id,
            student_name,
            essay_text,
            old_question_grade,
            old_total_grade
        ))

    if not submissions_to_grade:
        print("❌ No submissions to grade")
        if skipped:
            print("\nSkipped students:")
            for msg in skipped:
                print(f"  - {msg}")
        sys.exit(1)

    # Grade all submissions in parallel
    print(f"\n🚀 Grading {len(submissions_to_grade)} submissions in parallel (max {MAX_CONCURRENT_REQUESTS} concurrent)...")
    print("   This will be much faster than sequential grading!")

    grading_results = essay_grader.grade_essay_batch(
        submissions_to_grade,
        selected_question.points_possible
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
    json_filename = f"essays_{selected_course.id}_{timestamp}.json"
    save_grading_results(
        grading_results,
        skipped,
        json_filename,
        selected_course.id,
        selected_course.name,
        selected_assignment.id,
        selected_assignment.name,
        selected_question.title,
        selected_question.points_possible,
        question_item_id,
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
