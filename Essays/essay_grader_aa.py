#!/usr/bin/env python3
"""
Canvas New Quizzes: Essay Grader with OpenAI - PART AA (Model Testing)

Tests different OpenAI models by grading only the first 10 student submissions.
Uses hardcoded grading instructions and saves minimal results for comparison.
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
from anthropic import Anthropic
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

# Available models for testing (OpenAI and Anthropic)
AVAILABLE_MODELS = [
    "gpt-4o",
    "gpt-4o-2024-05-13",
    "gpt-4o-mini",
    "gpt-4.1",
    "gpt-4.1-mini",
    "gpt-4.1-nano",
    "gpt-5",
    "gpt-5-mini",
    "gpt-5-nano",
    "gpt-5-pro",
    "claude-sonnet-4-5"
]

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


def get_claude_api_key():
    """Retrieve Claude API key from macOS Keychain"""
    result = subprocess.run(
        ["security", "find-generic-password", "-a", "claude", "-s", "claude_api_key", "-w"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True
    )
    key = result.stdout.strip()
    if not key:
        print("⚠️  WARNING: Could not retrieve Claude API key from Keychain")
        print("   Set it using: security add-generic-password -a claude -s claude_api_key -w 'your_key'")
    return key


def select_model() -> str:
    """Display available models and let user select one"""
    print("\n" + "=" * 80)
    print("SELECT OPENAI MODEL FOR TESTING")
    print("=" * 80)

    print(f"\nAvailable models:")
    print("-" * 80)

    for i, model in enumerate(AVAILABLE_MODELS, 1):
        print(f"{i:2d}. {model}")

    print("-" * 80)

    while True:
        try:
            choice = input(f"\nSelect model (1-{len(AVAILABLE_MODELS)}): ").strip()
            choice_num = int(choice)
            if 1 <= choice_num <= len(AVAILABLE_MODELS):
                selected_model = AVAILABLE_MODELS[choice_num - 1]
                print(f"\n✅ Selected model: {selected_model}")
                return selected_model
            else:
                print(f"Please enter a number between 1 and {len(AVAILABLE_MODELS)}")
        except ValueError:
            print("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print("\n\n👋 Cancelled by user")
            sys.exit(0)


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
    """Represents AI grading results for a student (model testing version)"""
    student_id: int
    student_name: str
    essay_text: str
    ai_grade: float
    ai_feedback: str
    model_used: str


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


class EssayGrader:
    """Handles essay grading using OpenAI or Anthropic API"""

    def __init__(self, selected_model: str):
        """Initialize appropriate API client based on selected model"""
        self.selected_model = selected_model

        # Auto-detect API provider based on model name
        if selected_model.startswith('claude-'):
            # Use Anthropic API
            api_key = get_claude_api_key()
            if not api_key:
                print("❌ ERROR: Claude API key required for this model")
                sys.exit(1)
            self.client = Anthropic(api_key=api_key)
            self.api_provider = 'anthropic'
        else:
            # Use OpenAI API
            api_key = get_openai_api_key()
            if not api_key:
                print("❌ ERROR: OpenAI API key required for this model")
                sys.exit(1)
            self.client = OpenAI(api_key=api_key)
            self.api_provider = 'openai'

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

    def grade_essay(self, essay_text: str, grading_guidelines: str,
                   points_possible: float) -> Tuple[float, str]:
        """
        Grade an essay using OpenAI API

        Returns: (grade, feedback)
        """
        prompt = f"""You are grading an essay question. Here are the details:

GRADING INSTRUCTIONS:
{grading_guidelines}

POINTS POSSIBLE: {points_possible}

STUDENT ESSAY:
\"\"\"
{essay_text}
\"\"\"

Please grade this essay and provide detailed feedback. Your response must be a valid JSON object with exactly two fields:
{{
  "grade": <numeric grade between 0 and {points_possible}>,
  "feedback": "<detailed feedback explaining the grade>"
}}

IMPORTANT:
- Respond ONLY with valid JSON. Do not include any text outside the JSON structure.
- Do not include markdown code blocks or backticks.
- The grade must be a number between 0 and {points_possible}.
- The feedback should be constructive and specific.
"""

        try:
            if self.api_provider == 'anthropic':
                # Use Anthropic API
                response = self.client.messages.create(
                    model=self.selected_model,
                    max_tokens=2048,
                    temperature=1.0,
                    messages=[
                        {"role": "user", "content": f"You are a helpful teaching assistant that grades essays fairly and provides constructive feedback. You always respond with valid JSON only.\n\n{prompt}"}
                    ]
                )
                response_text = response.content[0].text.strip()

            else:
                # Use OpenAI API
                # Determine model capabilities
                model_lower = self.selected_model.lower()
                # Only gpt-5-pro, o1, and o3 use the legacy completions endpoint
                uses_completions_endpoint = any(x in model_lower for x in ['gpt-5-pro', 'o1', 'o3'])
                # gpt-5 (but not gpt-5-pro) supports temperature, gpt-5-pro/o1/o3 do not
                supports_temperature = not uses_completions_endpoint

                # Combine system instructions into user message for all cases
                combined_prompt = "You are a helpful teaching assistant that grades essays fairly and provides constructive feedback. You always respond with valid JSON only.\n\n" + prompt

                # Build API call parameters
                if uses_completions_endpoint:
                    # Models like gpt-5-pro, o1, o3 use completions endpoint (v1/responses)
                    # They don't support temperature or system messages
                    response = self.client.completions.create(
                        model=self.selected_model,
                        prompt=combined_prompt,
                        max_tokens=2048
                    )
                    response_text = response.choices[0].text.strip()
                else:
                    # Standard models (gpt-4, gpt-4o, gpt-5, etc.) use chat completions endpoint
                    api_params = {
                        "model": self.selected_model,
                        "messages": [
                            {"role": "system", "content": "You are a helpful teaching assistant that grades essays fairly and provides constructive feedback. You always respond with valid JSON only."},
                            {"role": "user", "content": prompt}
                        ]
                    }

                    # Add temperature for models that support it
                    if supports_temperature:
                        api_params["temperature"] = 1.0

                    response = self.client.chat.completions.create(**api_params)
                    response_text = response.choices[0].message.content.strip()

            # Clean up response (remove markdown code blocks if present)
            response_text = response_text.replace('```json', '').replace('```', '').strip()

            # Parse JSON response
            result = json.loads(response_text)

            grade = float(result.get('grade', 0))
            feedback = result.get('feedback', 'No feedback provided')

            # Validate grade range
            grade = max(0.0, min(grade, points_possible))

            return grade, feedback

        except json.JSONDecodeError as e:
            print(f"  ⚠️  Warning: Failed to parse AI response as JSON: {e}")
            print(f"  Response was: {response_text[:200]}")
            return 0.0, "Error: Could not parse AI response"
        except Exception as e:
            print(f"  ⚠️  Warning: AI API error ({self.api_provider}): {e}")
            return 0.0, f"Error: {str(e)}"

    def grade_essay_batch(self, submissions: List[Tuple[int, str, str, float, float]],
                         grading_guidelines: str, points_possible: float) -> List[GradingResult]:
        """
        Grade multiple essays in parallel using ThreadPoolExecutor

        Args:
            submissions: List of tuples (student_id, student_name, essay_text,
                        old_question_grade, old_total_grade)
            grading_guidelines: Grading instructions (includes question and criteria)
            points_possible: Maximum points for the question

        Returns:
            List of GradingResult objects
        """
        results = []

        def grade_single(submission_data):
            """Helper function to grade a single submission"""
            student_id, student_name, essay_text, old_question_grade, old_total_grade = submission_data

            try:
                ai_grade, ai_feedback = self.grade_essay(
                    essay_text,
                    grading_guidelines,
                    points_possible
                )

                return GradingResult(
                    student_id=student_id,
                    student_name=student_name,
                    essay_text=essay_text,
                    ai_grade=ai_grade,
                    ai_feedback=ai_feedback,
                    model_used=self.selected_model
                )
            except Exception as e:
                print(f"  ⚠️  Error grading {student_name}: {e}")
                return None

        # Use ThreadPoolExecutor for parallel grading
        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_REQUESTS) as executor:
            # Submit all grading tasks
            futures = []
            for i, submission in enumerate(submissions, 1):
                future = executor.submit(grade_single, submission)
                futures.append((i, submission[1], future))  # (index, student_name, future)

            # Collect results as they complete
            for i, student_name, future in futures:
                print(f"  [{i}/{len(submissions)}] Completed grading for {student_name}")
                result = future.result()
                if result:
                    results.append(result)

        return results


def display_courses(courses: List[Course]) -> None:
    """Display list of courses"""
    print("\nAvailable Courses:")
    print("-" * 60)
    for i, course in enumerate(courses, 1):
        print(f"{i}. {course.name} (ID: {course.id})")


def display_assignments(assignments: List[Assignment]) -> None:
    """Display list of New Quizzes"""
    print("\nNew Quizzes:")
    print("-" * 80)
    for i, assignment in enumerate(assignments, 1):
        due_str = assignment.due_at[:10] if assignment.due_at else "No due date"
        print(f"{i}. {assignment.name} (ID: {assignment.id}) - {assignment.points_possible} pts - Due: {due_str}")


def display_questions(questions: List[EssayQuestion]) -> None:
    """Display list of essay questions"""
    print("\nEssay Questions:")
    print("-" * 80)
    for i, q in enumerate(questions, 1):
        prompt_preview = q.prompt[:60] + "..." if len(q.prompt) > 60 else q.prompt
        print(f"{i}. {q.title} (ID: {q.item_id}) - {q.points_possible} pts")
        print(f"   Prompt: {prompt_preview}")


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


def main():
    """Main program flow"""
    # Clear screen at startup
    clear_screen()

    print("=" * 80)
    print("   CANVAS NEW QUIZZES - ESSAY GRADER WITH OPENAI - PART AA (MODEL TESTING)")
    print("=" * 80)

    # Select model for testing FIRST
    selected_model = select_model()

    # Initialize clients
    print("\n🔐 Authenticating...")
    canvas_client = CanvasAPIClient()
    essay_grader = EssayGrader(selected_model)

    # Load hardcoded grading instructions
    GRADING_INSTRUCTIONS_FILE = "openai_grading_instructions.md"

    print(f"\n📄 Loading grading instructions from: {GRADING_INSTRUCTIONS_FILE}")

    try:
        with open(GRADING_INSTRUCTIONS_FILE, 'r') as f:
            grading_guidelines = f.read()
        print(f"✅ Loaded grading instructions ({len(grading_guidelines)} characters)")

        # Display first 10 lines as preview
        print(f"\n📋 Preview (first 10 lines):")
        print("-" * 80)
        lines = grading_guidelines.split('\n')
        for i, line in enumerate(lines[:10], 1):
            print(f"{i:2d}. {line}")
        print("-" * 80)
    except FileNotFoundError:
        print(f"❌ Grading instructions file not found: {GRADING_INSTRUCTIONS_FILE}")
        print("   Make sure the file exists in the current directory")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error loading grading instructions: {e}")
        sys.exit(1)

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
        q = essay_grader.parse_quiz_item(item)
        if q:
            questions.append(q)

    if not questions:
        print("❌ No essay questions found in this quiz")
        sys.exit(1)

    display_questions(questions)
    question_idx = get_user_choice("Select a question", len(questions))
    selected_question = questions[question_idx]
    print(f"\n✅ Selected: {selected_question.title}")

    # Step 4: Get student submissions - check cache first
    cache_filename = f"student_analysis_{selected_course.id}_{selected_assignment.id}_{selected_question.item_id}.json"

    if os.path.exists(cache_filename):
        print(f"\n📂 Found cached student analysis report: {cache_filename}")
        print(f"   Loading from cache (skipping Canvas report generation)...")
        try:
            with open(cache_filename, 'r') as f:
                student_data = json.load(f)
            print(f"✅ Loaded cached report: {len(student_data)} students")
        except Exception as e:
            print(f"⚠️  Error loading cache file: {e}")
            print(f"   Falling back to Canvas report generation...")
            # Fall through to normal report generation
            cache_filename = None
    else:
        cache_filename = None

    # If no cache or cache failed, generate from Canvas
    if cache_filename is None or 'student_data' not in locals():
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

        # Save to cache for future use
        cache_save_filename = f"student_analysis_{selected_course.id}_{selected_assignment.id}_{selected_question.item_id}.json"
        try:
            with open(cache_save_filename, 'w') as f:
                json.dump(student_data, f, indent=2)
            print(f"💾 Cached report saved to: {cache_save_filename}")
        except Exception as e:
            print(f"⚠️  Warning: Could not save cache file: {e}")

    # Step 5: Find correct item_id from student_analysis
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

    # Step 6: Prepare submissions - LIMIT TO FIRST 10 STUDENTS
    print(f"\n🤖 Preparing submissions for AI grading...")

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

    # Limit to first 10 students for testing
    MAX_STUDENTS = 10
    test_submissions = submissions_to_grade[:MAX_STUDENTS]

    print(f"\n📝 MODEL TESTING MODE: Grading first {len(test_submissions)} of {len(submissions_to_grade)} student(s)")
    print(f"   (Limited to {MAX_STUDENTS} students to conserve tokens)")

    # Grade submissions in parallel
    print(f"\n🚀 Grading {len(test_submissions)} submissions in parallel (max {MAX_CONCURRENT_REQUESTS} concurrent)...")
    print("   This will be much faster than sequential grading!")

    grading_results = essay_grader.grade_essay_batch(
        test_submissions,
        grading_guidelines,
        selected_question.points_possible
    )

    if not grading_results:
        print("❌ No submissions were successfully graded")
        sys.exit(1)

    # Save results to JSON with model name in filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_safe_name = selected_model.replace('/', '_').replace(':', '_').replace('.', '_')
    output_filename = f"model_test_{model_safe_name}_{timestamp}.json"

    print(f"\n💾 Results will be saved to: {output_filename}")

    # Create simplified output structure
    output_data = {
        "model_used": selected_model,
        "timestamp": datetime.now().isoformat(),
        "total_graded": len(grading_results),
        "grading_results": [
            {
                "student_id": r.student_id,
                "student_name": r.student_name,
                "essay_text": r.essay_text,
                "ai_grade": r.ai_grade,
                "ai_feedback": r.ai_feedback,
                "model_used": r.model_used
            }
            for r in grading_results
        ]
    }

    with open(output_filename, 'w') as f:
        json.dump(output_data, f, indent=2)

    # Final summary
    print("\n" + "=" * 100)
    print("MODEL TESTING COMPLETE")
    print("=" * 100)
    print(f"✅ Model tested:        {selected_model}")
    print(f"📝 Students graded:     {len(grading_results)}/{len(submissions_to_grade)}")
    print(f"💾 Results saved to:    {output_filename}")
    print(f"\n💡 To test another model, run this script again")
    print(f"💡 Compare results by reviewing the JSON files")


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
