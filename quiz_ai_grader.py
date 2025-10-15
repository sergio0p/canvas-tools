#!/usr/bin/env python3
"""
Canvas Quiz AI Grader

Automatically grades essay questions in Canvas LMS quizzes using OpenAI API.
Allows custom grading guidelines and posts results to Canvas for manual validation.
"""

import sys
import json
import time
import subprocess
from typing import List, Dict, Optional, Tuple
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


# === MAIN GRADING PROCESS ===

def grade_submissions(canvas: CanvasAPI, grader: OpenAIGrader,
                     course_id: int, quiz_id: int, question: Dict,
                     grading_guidelines: str) -> Dict:
    """Main automated grading process."""

    question_id = question['id']
    question_text = question.get('question_text', '')
    points_possible = question.get('points_possible', 0)

    # Get submissions
    print(f"\n📥 Fetching quiz submissions...")
    submissions = canvas.get_quiz_submissions(course_id, quiz_id)

    if not submissions:
        print("❌ No completed submissions found.")
        return {
            'total': 0,
            'posted': 0,
            'skipped': 0,
            'failed': 0,
            'scores': []
        }

    print(f"✅ Found {len(submissions)} completed submission(s)")

    # Statistics
    stats = {
        'total': len(submissions),
        'posted': 0,
        'skipped': 0,
        'failed': 0,
        'scores': []
    }

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
                stats['skipped'] += 1
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
                stats['failed'] += 1
                continue

            score, feedback = result

            # Post to Canvas
            success = canvas.post_grade_to_canvas(
                course_id=course_id,
                quiz_id=quiz_id,
                submission_id=submission_id,
                attempt=attempt,
                question_id=question_id,
                score=score,
                feedback=feedback
            )

            if success:
                if tqdm:
                    tqdm.write(f"  ✓ Posted: {student_name} ({score}/{points_possible})")
                else:
                    print(f"  ✓ Posted ({score}/{points_possible})")
                stats['posted'] += 1
                stats['scores'].append(score)
            else:
                stats['failed'] += 1

        except Exception as e:
            if tqdm:
                tqdm.write(f"  ✗ Failed: {student_name} ({str(e)})")
            else:
                print(f"  ✗ Failed ({str(e)})")
            stats['failed'] += 1

    return stats


def display_summary(course: Dict, quiz: Dict, question: Dict, stats: Dict) -> None:
    """Display final summary and reminders."""

    print("\n" + "="*70)
    print("GRADING COMPLETE")
    print("="*70)

    print(f"\nCourse: {course.get('name')}")
    print(f"Quiz: {quiz.get('name')}")

    import re
    q_text = re.sub('<[^<]+?>', '', question.get('question_text', ''))
    q_text_short = q_text[:80] + '...' if len(q_text) > 80 else q_text
    print(f"Question: {q_text_short}")

    print(f"\n📊 STATISTICS")
    print(f"  Total submissions: {stats['total']}")
    print(f"  Successfully posted: {stats['posted']}")
    print(f"  Skipped (no answer): {stats['skipped']}")
    print(f"  Failed: {stats['failed']}")

    if stats['scores']:
        avg_score = sum(stats['scores']) / len(stats['scores'])
        min_score = min(stats['scores'])
        max_score = max(stats['scores'])
        print(f"\n📈 SCORE DISTRIBUTION")
        print(f"  Average: {avg_score:.2f}")
        print(f"  Min: {min_score:.2f}")
        print(f"  Max: {max_score:.2f}")

    print("\n" + "⚠"*35)
    print("⚠️  QUIZ RESULTS ARE HIDDEN FROM STUDENTS")
    print("⚠"*35)
    print("\nAll AI grades have been posted to Canvas.")
    print("\nBEFORE unhiding results:")
    print("  - Review grades in SpeedGrader")
    print("  - Validate AI grading quality")
    print("  - Adjust scores as needed")
    print("\nTo unhide: Edit quiz settings in Canvas")

    course_id = course['id']
    quiz_id = quiz.get('quiz_id')
    speedgrader_url = f"https://uncch.instructure.com/courses/{course_id}/gradebook/speed_grader?assignment_id={quiz.get('id')}"
    print(f"\n🔗 SpeedGrader: {speedgrader_url}")

    print("="*70)


# === MAIN FUNCTION ===

def main():
    """Main orchestration function."""

    print("="*70)
    print("CANVAS QUIZ AI GRADER")
    print("="*70)

    # Get API keys
    print("\n🔑 Retrieving API keys...")
    canvas_token = get_canvas_api_key()
    openai_key = get_openai_api_key()

    # Initialize APIs
    canvas = CanvasAPI(canvas_token)
    grader = OpenAIGrader(openai_key)

    # Step 1: Select course
    print("\n📚 Fetching your favorited courses...")
    courses = canvas.get_favorite_courses()

    if not courses:
        print("❌ No favorited courses found. Star courses in Canvas first.")
        sys.exit(1)

    display_courses(courses)
    selected_course = select_course(courses)

    if not selected_course:
        print("\n👋 Exiting...")
        sys.exit(0)

    course_id = selected_course['id']
    print(f"\n✅ Selected: {selected_course['name']}")

    # Step 2: Select quiz
    print(f"\n📝 Fetching quiz assignments...")
    quizzes = canvas.get_quiz_assignments(course_id)

    if not quizzes:
        print("❌ No quiz assignments found in this course.")
        sys.exit(1)

    display_quizzes(quizzes)
    selected_quiz = select_quiz(quizzes)

    if not selected_quiz:
        print("\n👋 Exiting...")
        sys.exit(0)

    quiz_id = selected_quiz.get('quiz_id')
    print(f"\n✅ Selected: {selected_quiz['name']}")

    # Step 3: Select essay question
    print(f"\n📋 Fetching essay questions...")
    questions = canvas.get_essay_questions(course_id, quiz_id)

    if not questions:
        print("❌ No essay questions found in this quiz.")
        sys.exit(1)

    display_questions(questions)
    selected_question = select_question(questions)

    if not selected_question:
        print("\n👋 Exiting...")
        sys.exit(0)

    print(f"\n✅ Selected: {selected_question.get('question_name')}")

    # Step 4: Get grading guidelines
    grading_guidelines = get_multiline_input()

    if not grading_guidelines:
        sys.exit(0)

    # Step 5: Confirm and proceed
    print("\n" + "="*70)
    print("READY TO GRADE")
    print("="*70)
    print(f"Course: {selected_course['name']}")
    print(f"Quiz: {selected_quiz['name']}")
    print(f"Question: {selected_question.get('question_name')}")
    print(f"Points: {selected_question.get('points_possible')}")
    print("="*70)

    proceed = input("\nProceed with automated grading? (y/n): ").strip().lower()
    if proceed != 'y':
        print("\n❌ Aborted by user.")
        sys.exit(0)

    # Step 6: Hide quiz results
    print("\n🔒 Hiding quiz results from students...")
    canvas.hide_quiz_results(course_id, quiz_id)

    # Step 7: Grade submissions
    print("\n🤖 Starting automated grading...")
    stats = grade_submissions(
        canvas=canvas,
        grader=grader,
        course_id=course_id,
        quiz_id=quiz_id,
        question=selected_question,
        grading_guidelines=grading_guidelines
    )

    # Step 8: Display summary
    display_summary(selected_course, selected_quiz, selected_question, stats)

    # Optional: Save results
    save = input("\nSave detailed results to CSV? (y/n): ").strip().lower()
    if save == 'y':
        import csv
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"quiz_grading_{timestamp}.csv"

        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Course', 'Quiz', 'Question', 'Total', 'Posted', 'Skipped', 'Failed', 'Avg Score'])
            writer.writerow([
                selected_course['name'],
                selected_quiz['name'],
                selected_question.get('question_name'),
                stats['total'],
                stats['posted'],
                stats['skipped'],
                stats['failed'],
                f"{sum(stats['scores']) / len(stats['scores']):.2f}" if stats['scores'] else 'N/A'
            ])

        print(f"\n💾 Results saved to: {filename}")


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
