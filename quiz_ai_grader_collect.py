#!/usr/bin/env python3
"""
Canvas Quiz AI Grader - Collection Script

Collects student submissions, grades with OpenAI, and saves results to JSON.
Does NOT post grades to Canvas - use quiz_ai_grader_validate.py for validation and posting.
"""

import sys
import json
import time
import subprocess
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import requests
import keyring
from openai import OpenAI

try:
    from tqdm import tqdm
except ImportError:
    print("⚠️  tqdm not installed. Progress bars will not be displayed.")
    print("Install with: pip install tqdm")
    tqdm = None


# === CONFIGURATION ===
CANVAS_SERVICE_NAME = 'canvas'
CANVAS_USERNAME = 'access-token'
CANVAS_API_BASE = "https://uncch.instructure.com/api/v1"

OPENAI_SERVICE = 'openai'
OPENAI_ACCOUNT = 'openai'

DEFAULT_GRADING_GUIDELINES = """Grade based on clarity, accuracy, use of examples, and writing quality.
Provide constructive feedback in 2-3 sentences."""


# === API KEY RETRIEVAL ===

def get_openai_api_key() -> str:
    """Retrieve OpenAI API key from macOS keychain using security command."""
    try:
        result = subprocess.run(
            ['security', 'find-generic-password', '-s', OPENAI_SERVICE,
             '-a', OPENAI_ACCOUNT, '-w'],
            capture_output=True,
            text=True,
            check=True
        )
        api_key = result.stdout.strip()
        if not api_key:
            raise ValueError("Empty API key returned from keychain")
        return api_key
    except subprocess.CalledProcessError:
        print(f"❌ ERROR: No OpenAI API key found in keychain.")
        print(f"Add one using:")
        print(f'  security add-generic-password -s "{OPENAI_SERVICE}" -a "{OPENAI_ACCOUNT}" -w "your_api_key"')
        sys.exit(1)
    except Exception as e:
        print(f"❌ ERROR: Failed to retrieve OpenAI API key: {e}")
        sys.exit(1)


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

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                print(f"⏳ Rate limited. Waiting {retry_after} seconds...")
                time.sleep(retry_after)
                return self.canvas_request(method, endpoint, **kwargs)

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
            sys.exit(1)
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error: {e}")
            sys.exit(1)

    def get_favorite_courses(self) -> List[Dict]:
        """Fetch user's favorited courses."""
        courses = []
        url = "users/self/favorites/courses"
        params = {'per_page': 100}

        response = self.canvas_request('GET', url, params=params)
        courses.extend(response.json())

        # Handle pagination
        while 'next' in response.links:
            response = self.canvas_request('GET', response.links['next']['url'])
            courses.extend(response.json())

        return courses

    def get_quiz_assignments(self, course_id: int) -> List[Dict]:
        """Fetch all quiz assignments for a course."""
        assignments = []
        url = f"courses/{course_id}/assignments"
        params = {'per_page': 100}

        response = self.canvas_request('GET', url, params=params)
        all_assignments = response.json()

        # Handle pagination
        while 'next' in response.links:
            response = self.canvas_request('GET', response.links['next']['url'])
            all_assignments.extend(response.json())

        # Filter for quiz assignments
        assignments = [a for a in all_assignments if a.get('is_quiz_assignment') or a.get('quiz_id')]

        return assignments

    def get_essay_questions(self, course_id: int, quiz_id: int) -> List[Dict]:
        """Fetch all essay questions for a quiz."""
        url = f"courses/{course_id}/quizzes/{quiz_id}/questions"
        params = {'per_page': 100}

        response = self.canvas_request('GET', url, params=params)
        all_questions = response.json()

        # Handle pagination
        while 'next' in response.links:
            response = self.canvas_request('GET', response.links['next']['url'])
            all_questions.extend(response.json())

        # Filter for essay questions
        essay_questions = [q for q in all_questions if q.get('question_type') == 'essay_question']

        return essay_questions

    def hide_quiz_results(self, course_id: int, quiz_id: int) -> bool:
        """Hide quiz results from students."""
        url = f"courses/{course_id}/quizzes/{quiz_id}"
        data = {'quiz[hide_results]': 'always'}

        try:
            self.canvas_request('PUT', url, data=data)
            return True
        except Exception as e:
            print(f"⚠️  Warning: Could not hide quiz results: {e}")
            return False

    def get_quiz_submissions(self, course_id: int, quiz_id: int) -> List[Dict]:
        """Fetch all completed quiz submissions."""
        url = f"courses/{course_id}/quizzes/{quiz_id}/submissions"
        params = {
            'include[]': 'user',
            'per_page': 100
        }

        response = self.canvas_request('GET', url, params=params)
        data = response.json()
        all_submissions = data.get('quiz_submissions', [])

        # Handle pagination
        while 'next' in response.links:
            response = self.canvas_request('GET', response.links['next']['url'])
            data = response.json()
            all_submissions.extend(data.get('quiz_submissions', []))

        # Filter for complete submissions
        completed = [s for s in all_submissions if s.get('workflow_state') == 'complete']

        return completed

    def get_submission_answers(self, quiz_submission_id: int) -> List[Dict]:
        """Get answers for a specific quiz submission."""
        url = f"quiz_submissions/{quiz_submission_id}/questions"

        response = self.canvas_request('GET', url)
        data = response.json()
        return data.get('quiz_submission_questions', [])


# === OPENAI FUNCTIONS ===

class OpenAIGrader:
    """Handles OpenAI API interactions for grading."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def grade_essay(self, question_text: str, student_answer: str,
                   points_possible: float, grading_guidelines: str) -> Optional[Tuple[float, str]]:
        """Grade an essay using OpenAI and return (score, feedback)."""

        system_prompt = "You are an expert educator grading essays. Return only valid JSON."

        user_prompt = f"""Question: {question_text}
Maximum Points: {points_possible}

Grading Guidelines:
{grading_guidelines}

Student Response:
{student_answer}

Respond with JSON only:
{{"score": <number>, "feedback": "<text>"}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content

            # Parse JSON response
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()

            result = json.loads(content)
            score = float(result.get('score', 0))
            feedback = result.get('feedback', 'No feedback provided.')

            # Validate score
            if score < 0:
                score = 0
            elif score > points_possible:
                score = points_possible

            return (score, feedback)

        except json.JSONDecodeError as e:
            print(f"    ⚠️  Invalid JSON from OpenAI: {e}")
            return None
        except Exception as e:
            print(f"    ⚠️  OpenAI API error: {e}")
            return None


# === USER INPUT FUNCTIONS ===

def display_courses(courses: List[Dict]) -> None:
    """Display numbered list of courses."""
    print("\n" + "="*70)
    print("YOUR COURSES")
    print("="*70)
    for idx, course in enumerate(courses, 1):
        course_code = course.get('course_code', 'N/A')
        course_name = course.get('name', 'Unnamed Course')
        print(f"{idx}. [{course_code}] {course_name}")
    print("="*70)


def select_course(courses: List[Dict]) -> Optional[Dict]:
    """Prompt user to select a course."""
    while True:
        choice = input("\nEnter course number (or 'exit' to quit): ").strip().lower()

        if choice == 'exit':
            return None

        try:
            course_num = int(choice)
            if 1 <= course_num <= len(courses):
                return courses[course_num - 1]
            else:
                print(f"❌ Please enter a number between 1 and {len(courses)}")
        except ValueError:
            print("❌ Please enter a valid number or 'exit'")


def display_quizzes(quizzes: List[Dict]) -> None:
    """Display numbered list of quiz assignments."""
    print("\n" + "="*70)
    print("QUIZ ASSIGNMENTS")
    print("="*70)
    for idx, quiz in enumerate(quizzes, 1):
        quiz_name = quiz.get('name', 'Unnamed Quiz')
        quiz_id = quiz.get('quiz_id', 'N/A')
        print(f"{idx}. {quiz_name} (Quiz ID: {quiz_id})")
    print("="*70)


def select_quiz(quizzes: List[Dict]) -> Optional[Dict]:
    """Prompt user to select a quiz."""
    while True:
        choice = input("\nEnter quiz number (or 'exit' to quit): ").strip().lower()

        if choice == 'exit':
            return None

        try:
            quiz_num = int(choice)
            if 1 <= quiz_num <= len(quizzes):
                return quizzes[quiz_num - 1]
            else:
                print(f"❌ Please enter a number between 1 and {len(quizzes)}")
        except ValueError:
            print("❌ Please enter a valid number or 'exit'")


def display_questions(questions: List[Dict]) -> None:
    """Display numbered list of essay questions."""
    print("\n" + "="*70)
    print("ESSAY QUESTIONS")
    print("="*70)
    for idx, q in enumerate(questions, 1):
        q_name = q.get('question_name', 'Unnamed Question')
        q_text = q.get('question_text', '')
        # Strip HTML tags for display
        import re
        q_text_clean = re.sub('<[^<]+?>', '', q_text)
        q_text_short = q_text_clean[:100] + '...' if len(q_text_clean) > 100 else q_text_clean
        points = q.get('points_possible', 0)
        print(f"{idx}. {q_name} ({points} pts)")
        print(f"    {q_text_short}")
    print("="*70)


def select_question(questions: List[Dict]) -> Optional[Dict]:
    """Prompt user to select an essay question."""
    while True:
        choice = input("\nEnter question number (or 'exit' to quit): ").strip().lower()

        if choice == 'exit':
            return None

        try:
            q_num = int(choice)
            if 1 <= q_num <= len(questions):
                return questions[q_num - 1]
            else:
                print(f"❌ Please enter a number between 1 and {len(questions)}")
        except ValueError:
            print("❌ Please enter a valid number or 'exit'")


def get_multiline_input() -> str:
    """Get multi-line grading guidelines from user."""
    print("\n" + "="*70)
    print("GRADING GUIDELINES")
    print("="*70)
    print("Enter your grading guidelines for OpenAI.")
    print("Press Enter on an empty line when done.")
    print("Leave empty to use default guidelines.")
    print("-"*70)

    lines = []
    while True:
        try:
            line = input()
            if line == "":
                break
            lines.append(line)
        except EOFError:
            break

    guidelines = "\n".join(lines).strip()

    if not guidelines:
        guidelines = DEFAULT_GRADING_GUIDELINES
        print("\n📝 Using default grading guidelines:")
    else:
        print("\n📝 Your grading guidelines:")

    print("-"*70)
    print(guidelines)
    print("-"*70)

    confirm = input("\nUse these guidelines? (y/n): ").strip().lower()
    if confirm != 'y':
        print("❌ Aborted by user.")
        return None

    return guidelines


def show_next_action_menu() -> str:
    """Display menu for next action and return user choice."""
    print("\n" + "="*70)
    print("WHAT WOULD YOU LIKE TO DO NEXT?")
    print("="*70)
    print("1. Grade another question from this quiz")
    print("2. Grade a question from another quiz in this course")
    print("3. Grade a question from a different course")
    print("4. Finish and exit")
    print("="*70)

    while True:
        choice = input("\nEnter your choice (1-4): ").strip()
        if choice in ['1', '2', '3', '4']:
            return choice
        print("❌ Please enter a number between 1 and 4")


# === GRADING AND FILE OPERATIONS ===

def grade_submissions(canvas: CanvasAPI, grader: OpenAIGrader,
                     course_id: int, quiz_id: int, question: Dict,
                     grading_guidelines: str) -> List[Dict]:
    """Grade all submissions and return list of graded submissions."""

    question_id = question['id']
    question_text = question.get('question_text', '')
    points_possible = question.get('points_possible', 0)

    # Get submissions
    print(f"\n📥 Fetching quiz submissions...")
    submissions = canvas.get_quiz_submissions(course_id, quiz_id)

    if not submissions:
        print("❌ No completed submissions found.")
        return []

    print(f"✅ Found {len(submissions)} completed submission(s)")

    graded_submissions = []

    # Process each submission
    iterator = tqdm(submissions, desc="Grading") if tqdm else submissions

    for submission in iterator:
        user_id = submission.get('user_id')
        submission_id = submission.get('id')
        attempt = submission.get('attempt', 1)

        # Get student name
        student_name = f"Student {user_id}"
        if 'user' in submission:
            student_name = submission['user'].get('name', student_name)

        if not tqdm:
            print(f"\n👤 Processing: {student_name}")

        # Get submission answers
        try:
            answers = canvas.get_submission_answers(submission_id)

            # Find the essay answer for this question
            essay_answer = None
            for ans in answers:
                if ans.get('id') == question_id:
                    essay_answer = ans.get('answer', '')
                    break

            if not essay_answer:
                if tqdm:
                    tqdm.write(f"  ⊘ Skipped: {student_name} (no answer)")
                else:
                    print(f"  ⊘ Skipped (no answer)")
                continue

            # Grade with OpenAI
            result = grader.grade_essay(
                question_text=question_text,
                student_answer=essay_answer,
                points_possible=points_possible,
                grading_guidelines=grading_guidelines
            )

            if not result:
                if tqdm:
                    tqdm.write(f"  ✗ Failed: {student_name} (OpenAI error)")
                else:
                    print(f"  ✗ Failed (OpenAI error)")
                continue

            score, feedback = result

            # Store graded submission
            graded_submissions.append({
                'user_id': user_id,
                'user_name': student_name,
                'submission_id': submission_id,
                'attempt': attempt,
                'answer': essay_answer,
                'ai_score': score,
                'ai_feedback': feedback
            })

            if tqdm:
                tqdm.write(f"  ✓ Graded: {student_name} ({score}/{points_possible})")
            else:
                print(f"  ✓ Graded ({score}/{points_possible})")

        except Exception as e:
            if tqdm:
                tqdm.write(f"  ✗ Failed: {student_name} ({str(e)})")
            else:
                print(f"  ✗ Failed ({str(e)})")

    return graded_submissions


def save_grading_session(course: Dict, quiz: Dict, question: Dict,
                         grading_guidelines: str, submissions: List[Dict]) -> str:
    """Save grading session to JSON file and return filename."""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    course_id = course['id']
    quiz_id = quiz.get('quiz_id')
    question_id = question['id']

    filename = f"grading_session_{course_id}_{quiz_id}_{question_id}_{timestamp}.json"

    data = {
        'timestamp': datetime.now().isoformat(),
        'course': {
            'id': course['id'],
            'name': course.get('name'),
            'course_code': course.get('course_code')
        },
        'quiz': {
            'id': quiz.get('id'),
            'quiz_id': quiz_id,
            'name': quiz.get('name')
        },
        'question': {
            'id': question['id'],
            'question_name': question.get('question_name'),
            'question_text': question.get('question_text'),
            'points_possible': question.get('points_possible')
        },
        'grading_guidelines': grading_guidelines,
        'submissions': submissions
    }

    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

    return filename


# === MAIN FUNCTION ===

def main():
    """Main orchestration function."""

    print("="*70)
    print("CANVAS QUIZ AI GRADER - COLLECTION SCRIPT")
    print("="*70)
    print("\nThis script collects submissions and grades them with AI.")
    print("Results are saved to JSON files for validation.")
    print("Use quiz_ai_grader_validate.py to review and post grades.")

    # Get API keys
    print("\n🔑 Retrieving API keys...")
    canvas_token = get_canvas_api_key()
    openai_key = get_openai_api_key()

    # Initialize APIs
    canvas = CanvasAPI(canvas_token)
    grader = OpenAIGrader(openai_key)

    # Main loop - can process multiple questions/quizzes/courses
    current_course = None
    current_quiz = None

    while True:
        # Step 1: Select course (or reuse current)
        if current_course is None:
            print("\n📚 Fetching your favorited courses...")
            courses = canvas.get_favorite_courses()

            if not courses:
                print("❌ No favorited courses found. Star courses in Canvas first.")
                sys.exit(1)

            display_courses(courses)
            current_course = select_course(courses)

            if not current_course:
                print("\n👋 Exiting...")
                sys.exit(0)

            print(f"\n✅ Selected: {current_course['name']}")

        course_id = current_course['id']

        # Step 2: Select quiz (or reuse current)
        if current_quiz is None:
            print(f"\n📝 Fetching quiz assignments...")
            quizzes = canvas.get_quiz_assignments(course_id)

            if not quizzes:
                print("❌ No quiz assignments found in this course.")
                current_course = None
                continue

            display_quizzes(quizzes)
            current_quiz = select_quiz(quizzes)

            if not current_quiz:
                current_course = None
                continue

            print(f"\n✅ Selected: {current_quiz['name']}")

        quiz_id = current_quiz.get('quiz_id')

        # Step 3: Select essay question
        print(f"\n📋 Fetching essay questions...")
        questions = canvas.get_essay_questions(course_id, quiz_id)

        if not questions:
            print("❌ No essay questions found in this quiz.")
            current_quiz = None
            continue

        display_questions(questions)
        selected_question = select_question(questions)

        if not selected_question:
            current_quiz = None
            continue

        print(f"\n✅ Selected: {selected_question.get('question_name')}")

        # Step 4: Get grading guidelines
        grading_guidelines = get_multiline_input()

        if not grading_guidelines:
            continue

        # Step 5: Confirm and proceed
        print("\n" + "="*70)
        print("READY TO GRADE")
        print("="*70)
        print(f"Course: {current_course['name']}")
        print(f"Quiz: {current_quiz['name']}")
        print(f"Question: {selected_question.get('question_name')}")
        print(f"Points: {selected_question.get('points_possible')}")
        print("="*70)

        proceed = input("\nProceed with AI grading? (y/n): ").strip().lower()
        if proceed != 'y':
            print("\n❌ Aborted by user.")
            continue

        # Step 6: Hide quiz results
        print("\n🔒 Hiding quiz results from students...")
        canvas.hide_quiz_results(course_id, quiz_id)

        # Step 7: Grade submissions
        print("\n🤖 Starting AI grading...")
        graded_submissions = grade_submissions(
            canvas=canvas,
            grader=grader,
            course_id=course_id,
            quiz_id=quiz_id,
            question=selected_question,
            grading_guidelines=grading_guidelines
        )

        # Step 8: Save to JSON
        if graded_submissions:
            filename = save_grading_session(
                course=current_course,
                quiz=current_quiz,
                question=selected_question,
                grading_guidelines=grading_guidelines,
                submissions=graded_submissions
            )

            print(f"\n💾 Results saved to: {filename}")
            print(f"   Total submissions graded: {len(graded_submissions)}")
        else:
            print("\n⚠️  No submissions were successfully graded.")

        # Step 9: Ask what to do next
        choice = show_next_action_menu()

        if choice == '1':
            # Grade another question from same quiz
            continue
        elif choice == '2':
            # Grade question from another quiz in same course
            current_quiz = None
            continue
        elif choice == '3':
            # Grade question from different course
            current_course = None
            current_quiz = None
            continue
        elif choice == '4':
            # Exit
            print("\n" + "="*70)
            print("SESSION COMPLETE")
            print("="*70)
            print("\n✅ All grading sessions saved to JSON files.")
            print("\n📝 Next step: Use quiz_ai_grader_validate.py to review and post grades.")
            print("\n👋 Goodbye!")
            sys.exit(0)


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
