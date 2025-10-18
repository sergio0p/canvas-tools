#!/usr/bin/env python3
"""
Canvas New Quizzes: Categorization Grader

Applies partial credit grading to categorization questions in Canvas New Quizzes.
Follows the specification in categorization_grader_spec.md

Algorithm: score = (correct - 0.5 * misclassified) / total * points_possible
"""

import sys
import time
import json
import re
import keyring
import requests
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass

# Configuration
SERVICE_NAME = 'canvas'
USERNAME = 'access-token'
HOST = 'https://uncch.instructure.com'
API_V1 = f"{HOST}/api/v1"
API_QUIZ = f"{HOST}/api/quiz/v1"

POLL_INTERVAL = 2.0  # seconds
REPORT_TIMEOUT = 900  # 15 minutes


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
class CategorizationQuestion:
    """Represents a categorization question"""
    item_id: str
    title: str
    points_possible: float
    correct_answers: Dict[str, str]  # item_label -> correct_category_label
    true_distractors: Set[str]  # items that shouldn't be placed


@dataclass
class StudentGrade:
    """Represents grading results for a student"""
    student_id: int
    student_name: str
    old_question_grade: float
    new_question_grade: float
    old_total_grade: float
    new_total_grade: float
    correct_count: int
    misclassified_count: int


class CanvasAPIClient:
    """Handles all Canvas API interactions"""

    def __init__(self):
        """Initialize API client with authentication"""
        self.token = self._get_token()
        self.session = requests.Session()
        self.session.headers.update({'Authorization': f'Bearer {self.token}'})

    def _get_token(self) -> str:
        """Retrieve API token from keychain"""
        token = keyring.get_password(SERVICE_NAME, USERNAME)
        if not token:
            print(f"❌ ERROR: No Canvas API token found in keychain.")
            print(f"Set one using: keyring.set_password('{SERVICE_NAME}', '{USERNAME}', 'your_token')")
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

        # Try direct URL
        if isinstance(results, dict):
            url = results.get('url')
            if url:
                return url

            # Try attachment URL
            att = results.get('attachment') or {}
            if isinstance(att, dict):
                url = att.get('url') or att.get('download_url')
                if url:
                    return url

            # Try file ID
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


class CategorizationGrader:
    """Handles categorization question grading logic"""

    @staticmethod
    def parse_quiz_item(item: dict) -> Optional[CategorizationQuestion]:
        """Parse a quiz item to extract categorization question details"""
        entry = item.get('entry', {})

        if entry.get('interaction_type_slug') != 'categorization':
            return None

        item_id = item['id']
        title = entry.get('title', 'Untitled Question')
        points_possible = item.get('points_possible', 0.0)

        # Extract categories and items
        interaction_data = entry.get('interaction_data', {})
        categories = interaction_data.get('categories', {})
        distractors = interaction_data.get('distractors', {})

        # Build correct answer map: item_label -> category_label
        correct_answers = {}
        scoring_data = entry.get('scoring_data', {}).get('value', [])
        items_to_classify = set()

        for category_scoring in scoring_data:
            category_uuid = category_scoring['id']
            category_label = categories[category_uuid]['item_body'].strip()

            item_uuids = category_scoring.get('scoring_data', {}).get('value', [])
            items_to_classify.update(item_uuids)

            for item_uuid in item_uuids:
                item_label = distractors[item_uuid]['item_body'].strip()
                correct_answers[item_label] = category_label

        # Identify true distractors
        all_distractor_uuids = set(distractors.keys())
        true_distractor_uuids = all_distractor_uuids - items_to_classify
        true_distractors = {
            distractors[uuid]['item_body'].strip()
            for uuid in true_distractor_uuids
        }

        return CategorizationQuestion(
            item_id=item_id,
            title=title,
            points_possible=points_possible,
            correct_answers=correct_answers,
            true_distractors=true_distractors
        )

    @staticmethod
    def parse_student_answer(answer_string: str) -> Dict[str, str]:
        """
        Parse student answer string into item -> category mapping
        Format: "category1 => [item1,item2],category2 => [item3,item4]"
        """
        placements = {}

        # Split by category
        category_pattern = r'(\w+(?:\([^)]*\))?)\s*=>\s*\[([^\]]*)\]'
        matches = re.findall(category_pattern, answer_string)

        for category, items_str in matches:
            # Parse items in the list
            items = [item.strip() for item in items_str.split(',') if item.strip()]
            for item in items:
                placements[item] = category

        return placements

    @staticmethod
    def grade_student(question: CategorizationQuestion,
                     student_placements: Dict[str, str]) -> Tuple[float, int, int]:
        """
        Grade a student's categorization answer
        Returns: (score, correct_count, misclassified_count)
        """
        correct = 0
        misclassified = 0

        # Check each item that should be categorized
        for item_label, correct_category in question.correct_answers.items():
            student_category = student_placements.get(item_label)

            if student_category == correct_category:
                correct += 1
            elif student_category is not None:
                # Placed in wrong category
                misclassified += 1
            # else: not placed - loses credit but not penalized

        # Check if any true distractors were placed
        for item_label in question.true_distractors:
            if item_label in student_placements:
                misclassified += 1

        # Calculate score
        total_items = len(question.correct_answers)

        if total_items == 0 or question.points_possible == 0:
            return 0.0, 0, 0

        score = (correct - 0.5 * misclassified) / total_items * question.points_possible
        score = max(0.0, score)  # Don't go negative

        return score, correct, misclassified


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


def display_questions(questions: List[CategorizationQuestion]) -> None:
    """Display list of categorization questions"""
    print("\nCategorization Questions:")
    print("-" * 80)
    for i, q in enumerate(questions, 1):
        print(f"{i}. {q.title} (ID: {q.item_id}) - {q.points_possible} pts")


def display_grade_preview(grades: List[StudentGrade]) -> None:
    """Display grading results table"""
    print("\n" + "=" * 135)
    print("GRADE PREVIEW")
    print("=" * 135)
    print(f"{'Student Name':<30} | {'ID':<8} | {'Curr Q':<8} | {'New Q':<8} | {'Correct':<8} | {'Miscl':<8} | {'New Total':<10} | {'Improved':<8}")
    print("-" * 135)

    for grade in grades:
        improved = "yes" if grade.new_question_grade >= grade.old_question_grade else "no"
        print(f"{grade.student_name:<30} | "
              f"{grade.student_id:<8} | "
              f"{grade.old_question_grade:<8.1f} | "
              f"{grade.new_question_grade:<8.1f} | "
              f"{grade.correct_count:<8} | "
              f"{grade.misclassified_count:<8} | "
              f"{grade.new_total_grade:<10.1f} | "
              f"{improved:<8}")

    print("=" * 135)


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
                return value - 1  # Return 0-indexed
            else:
                print(f"Please enter a number between 1 and {max_value}")
        except ValueError:
            print("Invalid input. Please enter a number.")


def get_yes_no(prompt: str) -> bool:
    """Get yes/no confirmation from user"""
    while True:
        response = input(f"\n{prompt} (yes/no): ").strip().lower()
        if response in ['yes', 'y']:
            return True
        elif response in ['no', 'n']:
            return False
        else:
            print("Please answer 'yes' or 'no'")


def get_next_action() -> int:
    """Get user's choice for what to do next after grading"""
    print("\nWhat would you like to do next?")
    print("  1. Grade another question in this quiz")
    print("  2. Select a different quiz in this course")
    print("  3. Return to course selection")
    print("  4. Exit")

    while True:
        try:
            choice = input("\nEnter your choice (1-4): ").strip()
            value = int(choice)
            if 1 <= value <= 4:
                return value
            else:
                print("Please enter a number between 1 and 4")
        except ValueError:
            print("Invalid input. Please enter a number between 1 and 4")


def main():
    """Main program flow"""
    print("=" * 80)
    print("   CANVAS NEW QUIZZES - CATEGORIZATION GRADER")
    print("=" * 80)

    # Initialize API client
    print("\n🔐 Authenticating...")
    client = CanvasAPIClient()
    grader = CategorizationGrader()

    while True:  # Main loop for course selection
        # Step 1: Select course
        print("\n📚 Fetching favorite courses...")
        courses = client.get_favorite_courses()

        if not courses:
            print("❌ No published courses found in favorites")
            sys.exit(1)

        display_courses(courses)
        course_idx = get_user_choice("Select a course", len(courses))
        selected_course = courses[course_idx]
        print(f"\n✓ Selected: {selected_course.name}")

        while True:  # Loop for assignment selection
            # Step 2: Select assignment
            print(f"\n📝 Fetching New Quizzes for {selected_course.name}...")
            assignments = client.get_new_quizzes(selected_course.id)

            if not assignments:
                print("❌ No New Quizzes found in this course")
                break  # Return to course selection

            display_assignments(assignments)
            assignment_idx = get_user_choice("Select a quiz", len(assignments))
            selected_assignment = assignments[assignment_idx]
            print(f"\n✓ Selected: {selected_assignment.name}")

            while True:  # Loop for question selection
                # Step 3: Select categorization question
                print(f"\n❓ Fetching quiz questions...")
                quiz_items = client.get_quiz_items(selected_course.id, selected_assignment.id)

                questions = []
                for item in quiz_items:
                    q = grader.parse_quiz_item(item)
                    if q:
                        questions.append(q)

                if not questions:
                    print("❌ No categorization questions found in this quiz")
                    break  # Return to assignment selection

                display_questions(questions)
                question_idx = get_user_choice("Select a question", len(questions))
                selected_question = questions[question_idx]
                print(f"\n✓ Selected: {selected_question.title}")

                # Step 4-6: Get student submissions
                print(f"\n📊 Creating student analysis report...")
                progress_url = client.create_student_analysis_report(selected_course.id, selected_assignment.id)

                print(f"⏳ Waiting for report generation...")
                progress_data = client.poll_progress(progress_url)

                print(f"⬇️  Downloading report...")
                download_url = client.resolve_download_url(progress_data)
                student_data = client.download_report(download_url)

                print(f"✓ Report downloaded: {len(student_data)} students")

                # Step 7-8: Grade students
                print(f"\n🎯 Grading student submissions...")

                # First, get the item_id from student_analysis for the selected question
                # The item_id in student_analysis differs from the quiz structure API
                # We need to find it from the first student's responses by matching position
                question_item_id = None
                if student_data:
                    first_student_responses = student_data[0].get('item_responses', [])
                    # Find categorization question by position (question_idx)
                    cat_questions_found = 0
                    for resp in first_student_responses:
                        if resp.get('item_type') == 'categorization':
                            if cat_questions_found == question_idx:
                                question_item_id = resp.get('item_id')
                                break
                            cat_questions_found += 1

                if not question_item_id:
                    print(f"❌ Could not find item_id in student responses for selected question")
                    continue  # Return to question selection

                print(f"  ℹ️  Using item_id from student_analysis: {question_item_id}")

                grades = []
                skipped = []

                for student in student_data:
                    student_id = student['student_data']['id']
                    student_name = student['student_data']['name']

                    # Find the categorization question in responses using the correct item_id
                    question_response = None
                    for resp in student.get('item_responses', []):
                        if resp.get('item_id') == question_item_id:
                            question_response = resp
                            break

                    if not question_response:
                        skipped.append(f"{student_name}: No response found")
                        continue

                    # Extract old grades
                    old_question_grade = question_response.get('score', 0.0)
                    old_total_grade = student.get('summary', {}).get('score', 0.0)

                    # Parse and grade answer
                    answer_string = question_response.get('answer', '')

                    try:
                        student_placements = grader.parse_student_answer(answer_string)
                        new_question_grade, correct, misclassified = grader.grade_student(
                            selected_question, student_placements
                        )
                    except Exception as e:
                        skipped.append(f"{student_name}: Failed to parse answer - {str(e)}")
                        continue

                    # Calculate new total
                    new_total_grade = old_total_grade - old_question_grade + new_question_grade

                    grades.append(StudentGrade(
                        student_id=student_id,
                        student_name=student_name,
                        old_question_grade=old_question_grade,
                        new_question_grade=new_question_grade,
                        old_total_grade=old_total_grade,
                        new_total_grade=new_total_grade,
                        correct_count=correct,
                        misclassified_count=misclassified
                    ))

                if not grades:
                    print("❌ No students to grade")
                    if skipped:
                        print("\nSkipped students:")
                        for msg in skipped:
                            print(f"  - {msg}")
                    continue  # Return to question selection

                # Step 9: Display preview and get approval
                display_grade_preview(grades)

                if skipped:
                    print(f"\n⚠️  Skipped {len(skipped)} student(s):")
                    for msg in skipped[:5]:  # Show first 5
                        print(f"  - {msg}")
                    if len(skipped) > 5:
                        print(f"  ... and {len(skipped) - 5} more")

                approved = get_yes_no(f"\n✓ Update grades for {len(grades)} student(s)?")

                if not approved:
                    print("\n❌ Grade updates cancelled")
                    continue  # Return to question selection

                # Step 10: Update grades
                print(f"\n📤 Updating grades...")
                success_count = 0
                failed_count = 0

                for grade in grades:
                    # Build feedback comment
                    feedback = (
                        f"New score for {selected_question.title}: "
                        f"old score = {grade.old_question_grade:.1f}, new score = {grade.new_question_grade:.1f}\n"
                        f"Correct = {grade.correct_count}, Misclassified = {grade.misclassified_count}\n"
                        f"Grading formula: (correct - 0.5 * misclassified) / total * points_possible"
                    )

                    success = client.update_grade(
                        selected_course.id,
                        selected_assignment.id,
                        grade.student_id,
                        grade.new_total_grade,
                        feedback
                    )

                    if success:
                        success_count += 1
                        print(f"  ✓ Updated: {grade.student_name}")
                    else:
                        failed_count += 1

                # Summary
                print("\n" + "=" * 80)
                print("SUMMARY")
                print("=" * 80)
                print(f"✓ Successfully updated: {success_count} student(s)")
                if failed_count > 0:
                    print(f"❌ Failed: {failed_count} student(s)")
                if skipped:
                    print(f"⚠️  Skipped: {len(skipped)} student(s)")

                # Ask what to do next
                next_action = get_next_action()

                if next_action == 1:
                    # Grade another question in this quiz
                    continue  # Stay in question selection loop
                elif next_action == 2:
                    # Select a different quiz
                    break  # Exit question loop, return to assignment selection
                elif next_action == 3:
                    # Return to course selection
                    break  # Will break out of both loops below
                elif next_action == 4:
                    # Exit
                    print("\n👋 Exiting...")
                    sys.exit(0)

            # Check if user chose option 3 (return to course selection)
            if next_action == 3:
                break  # Exit assignment loop, return to course selection


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
