# Canvas New Quizzes: Grading Framework for Custom Scripts

## Overview

This document contains reusable components, API patterns, and implementation details for building custom grading scripts for Canvas New Quizzes. It is based on the successful implementation of `categorization_grader.py` and provides a foundation for grading other question types (essays, fill-in-the-blank, etc.).

---

## Table of Contents

1. [Core API Endpoints](#core-api-endpoints)
2. [Authentication & Setup](#authentication--setup)
3. [Data Structures](#data-structures)
4. [Common Workflows](#common-workflows)
5. [Grade Extraction & Updates](#grade-extraction--updates)
6. [User Interface Patterns](#user-interface-patterns)
7. [Error Handling](#error-handling)
8. [Known Issues & Solutions](#known-issues--solutions)

---

## Core API Endpoints

### 1. Get Favorite Courses

**Endpoint**: `GET /api/v1/users/self/favorites/courses`

**Purpose**: Fetch user's favorite courses

**Filter**: Only show published courses (`workflow_state == "available"`)

**Example**:
```python
url = f"{API_V1}/users/self/favorites/courses"
response = session.get(url)
courses = response.json()

# Filter for published only
published = [c for c in courses if c.get('workflow_state') == 'available']
```

**Response fields**:
- `id` - Course ID
- `name` - Course name
- `workflow_state` - "available", "unpublished", etc.

---

### 2. List New Quizzes Assignments

**Endpoint**: `GET /api/v1/courses/:course_id/assignments`

**Purpose**: Fetch all assignments for a course

**Parameters**:
- `per_page`: Number of results per page (default: 10, max: 100)

**Filter for New Quizzes**: `is_quiz_lti_assignment == true`

**Example**:
```python
url = f"{API_V1}/courses/{course_id}/assignments"
response = session.get(url, params={'per_page': 100})
assignments = response.json()

# Filter for New Quizzes only
new_quizzes = [a for a in assignments if a.get('is_quiz_lti_assignment')]
```

**Response fields**:
- `id` - Assignment ID (same as quiz ID for New Quizzes)
- `name` - Assignment name
- `due_at` - Due date (ISO 8601 format)
- `points_possible` - Maximum points
- `grading_type` - "points", "percent", "letter_grade", "pass_fail"
- `submission_types` - Array containing `["external_tool"]` for New Quizzes
- `is_quiz_lti_assignment` - **true** for New Quizzes
- `is_quiz_assignment` - false for New Quizzes (true only for Classic Quizzes)

---

### 3. Get Quiz Items/Questions

**Endpoint**: `GET /api/quiz/v1/courses/:course_id/quizzes/:assignment_id/items`

**Purpose**: Fetch all questions/items in the quiz

**Example**:
```python
url = f"{API_QUIZ}/courses/{course_id}/quizzes/{assignment_id}/items"
response = session.get(url)
quiz_items = response.json()
```

**Response structure** (general):
```json
[
  {
    "id": "452018",
    "position": 1,
    "points_possible": 2.0,
    "entry_type": "Item",
    "entry": {
      "title": "Question Title",
      "item_body": "<p>Question text</p>",
      "interaction_type_slug": "essay" | "categorization" | "fill_in_multiple_blanks" | etc.,
      "interaction_data": { /* type-specific data */ },
      "scoring_data": { /* type-specific scoring info */ }
    }
  }
]
```

**Common question types** (`interaction_type_slug`):
- `"essay"` - Essay questions
- `"categorization"` - Categorization (drag-and-drop)
- `"fill_in_multiple_blanks"` - Fill in the blank
- `"multiple_answers_question"` - Multiple choice
- `"matching"` - Matching questions
- `"hot_spot"` - Hotspot questions

---

### 4. Create Student Analysis Report

**Endpoint**: `POST /api/quiz/v1/courses/:course_id/quizzes/:assignment_id/reports`

**Purpose**: Generate a report containing all student submissions with detailed responses

**Payload**:
```json
{
  "quiz_report": {
    "report_type": "student_analysis",
    "format": "json"
  }
}
```

**Example**:
```python
url = f"{API_QUIZ}/courses/{course_id}/quizzes/{assignment_id}/reports"
payload = {
    "quiz_report": {
        "report_type": "student_analysis",
        "format": "json"
    }
}
response = session.post(url, json=payload)
data = response.json()
progress_url = data.get('progress_url')
```

**Response**:
```json
{
  "progress_url": "/api/v1/progress/12345"
}
```

---

### 5. Poll Report Progress

**Endpoint**: `GET /api/v1/progress/:progress_id`

**Purpose**: Check if report generation is complete

**Poll interval**: Every 2 seconds

**Timeout**: 15 minutes (900 seconds)

**Example**:
```python
import time

url = progress_url if progress_url.startswith("http") else f"{HOST}{progress_url}"
start = time.time()

while True:
    response = session.get(url)
    prog = response.json()
    state = prog.get('workflow_state')

    if state == 'completed':
        return prog
    elif state == 'failed':
        raise Exception("Report generation failed")
    elif time.time() - start > 900:  # 15 minutes
        raise Exception("Report generation timed out")

    time.sleep(2.0)
```

**Response states**:
- `"queued"` - Still processing
- `"running"` - Still processing
- `"completed"` - Ready to download
- `"failed"` - Error occurred

**Completed response structure**:
```json
{
  "workflow_state": "completed",
  "results": {
    "url": "https://...",
    "attachment": {"url": "https://...", "id": 123},
    "attachment_id": 123
  }
}
```

---

### 6. Resolve Download URL

**Primary**: Use `results.url` or `results.attachment.url` from progress response

**Fallback**: If only `attachment_id` available, fetch file metadata

**Endpoint**: `GET /api/v1/files/:file_id`

**Example**:
```python
results = progress_data.get('results') or {}

# Try direct URL
url = results.get('url')
if url:
    return url

# Try attachment URL
att = results.get('attachment') or {}
url = att.get('url') or att.get('download_url')
if url:
    return url

# Fallback: fetch file metadata
file_id = results.get('attachment_id') or results.get('file_id')
if file_id:
    file_url = f"{API_V1}/files/{file_id}"
    response = session.get(file_url)
    file_data = response.json()
    return file_data.get('url') or file_data.get('download_url')
```

---

### 7. Download and Parse Student Analysis Report

**Format**: JSON array of student submission objects

**Example**:
```python
response = session.get(download_url, stream=True)
student_data = response.json()
```

**Structure**:
```json
[
  {
    "created_timestamp": "2025-10-16T18:18:41.075Z",
    "student_data": {
      "id": 73860,
      "name": "Student Name",
      "uuid": "...",
      "sis_id": "730559629",
      "submitted_at": "2025-09-04T14:39:37.268Z",
      "elapsed_time": "00:09:27",
      "attempt": 1,
      "section_info": {
        "section_ids": [94481],
        "section_sis_ids": ["ECON510.001.FA25"],
        "section_names": ["ECON510.001.FA25"]
      }
    },
    "item_responses": [
      {
        "item_id": "411636",
        "item_type": "categorization",
        "score": 0.0,
        "answer": "category1 => [itemA,itemB],category2 => [itemC]"
      },
      {
        "item_id": "411637",
        "item_type": "essay",
        "score": 0,
        "answer": "<p>Essay text here...</p>"
      }
    ],
    "summary": {
      "number_of_correct": 0,
      "number_of_incorrect": 1,
      "number_of_no_answer": 0,
      "points_possible": 4.0,
      "score": 0.0
    }
  }
]
```

**Key fields**:
- `student_data.id` - Student Canvas ID
- `student_data.name` - Student name
- `student_data.submitted_at` - Submission timestamp
- `student_data.attempt` - Attempt number (if multiple attempts allowed)
- `item_responses[]` - Array of question responses
  - `item_id` - Question identifier (**NOTE**: Different from quiz structure ID!)
  - `item_type` - Question type
  - `score` - Current Canvas grade for this question
  - `answer` - Student's answer (format varies by question type)
- `summary.score` - Current total quiz grade
- `summary.points_possible` - Total quiz points

---

### 8. Update Assignment Grade with Feedback

**Endpoint**: `PUT /api/v1/courses/:course_id/assignments/:assignment_id/submissions/:user_id`

**Purpose**: Update the overall quiz grade and add feedback comment

**Parameters**:
- `submission[posted_grade]` - New total quiz score (string)
- `comment[text_comment]` - Feedback text

**Example**:
```python
url = f"{API_V1}/courses/{course_id}/assignments/{assignment_id}/submissions/{user_id}"
data = {
    'submission[posted_grade]': str(new_total_grade),
    'comment[text_comment]': feedback_text
}
response = session.put(url, data=data)
```

**Grade calculation**:
```python
new_quiz_total = old_quiz_total - old_question_grade + new_question_grade
```

**Notes**:
- Comments are automatically appended to existing submission comments
- Grade updates respect posting policies (manual vs automatic)
- Updates appear in SpeedGrader and Gradebook
- **Cannot update individual question grades** - only total assignment grade

---

## Authentication & Setup

### API Token Storage

Use system keychain for secure token storage:

```python
import keyring

SERVICE_NAME = 'canvas'
USERNAME = 'access-token'

# Store token (one-time setup)
keyring.set_password(SERVICE_NAME, USERNAME, 'your_api_token_here')

# Retrieve token
token = keyring.get_password(SERVICE_NAME, USERNAME)
if not token:
    print(f"❌ ERROR: No Canvas API token found in keychain.")
    print(f"Set one using: keyring.set_password('{SERVICE_NAME}', '{USERNAME}', 'your_token')")
    sys.exit(1)
```

### Session Configuration

```python
import requests

HOST = 'https://your-canvas-instance.instructure.com'
API_V1 = f"{HOST}/api/v1"
API_QUIZ = f"{HOST}/api/quiz/v1"

session = requests.Session()
session.headers.update({'Authorization': f'Bearer {api_token}'})
```

### Required Permissions

- API token requires **"manage grades"** scope
- User must have Teacher, TA, or Grader role in course

---

## Data Structures

### Course

```python
@dataclass
class Course:
    """Represents a Canvas course"""
    id: int
    name: str
    workflow_state: str
```

### Assignment

```python
@dataclass
class Assignment:
    """Represents a Canvas assignment (New Quiz)"""
    id: int
    name: str
    points_possible: float
    due_at: Optional[str]
```

### StudentGrade

```python
@dataclass
class StudentGrade:
    """Represents grading results for a student"""
    student_id: int
    student_name: str
    old_question_grade: float
    new_question_grade: float
    old_total_grade: float
    new_total_grade: float
    # Add question-type-specific fields as needed
```

---

## Common Workflows

### Basic Grading Workflow

```python
def main():
    # 1. Authenticate
    client = CanvasAPIClient()

    # 2. Select course
    courses = client.get_favorite_courses()
    selected_course = user_selects_from_list(courses)

    # 3. Select quiz
    assignments = client.get_new_quizzes(selected_course.id)
    selected_assignment = user_selects_from_list(assignments)

    # 4. Get quiz structure
    quiz_items = client.get_quiz_items(selected_course.id, selected_assignment.id)

    # 5. Filter for specific question type
    target_questions = [
        item for item in quiz_items
        if item['entry'].get('interaction_type_slug') == 'essay'  # or other type
    ]

    # 6. Select question
    selected_question = user_selects_from_list(target_questions)

    # 7. Get student submissions
    progress_url = client.create_student_analysis_report(
        selected_course.id,
        selected_assignment.id
    )
    progress_data = client.poll_progress(progress_url)
    download_url = client.resolve_download_url(progress_data)
    student_data = client.download_report(download_url)

    # 8. Grade each student
    grades = []
    for student in student_data:
        # Extract student info
        student_id = student['student_data']['id']
        old_total = student['summary']['score']

        # Find question response (match by position or other method)
        question_response = find_question_in_responses(
            student['item_responses'],
            selected_question
        )

        if not question_response:
            continue

        old_question_grade = question_response['score']
        answer = question_response['answer']

        # Apply custom grading logic
        new_question_grade = your_grading_algorithm(answer)

        # Calculate new total
        new_total = old_total - old_question_grade + new_question_grade

        grades.append(StudentGrade(
            student_id=student_id,
            old_question_grade=old_question_grade,
            new_question_grade=new_question_grade,
            old_total_grade=old_total,
            new_total_grade=new_total
        ))

    # 9. Preview and confirm
    display_grade_preview(grades)
    if not user_confirms():
        return

    # 10. Update grades
    for grade in grades:
        client.update_grade(
            selected_course.id,
            selected_assignment.id,
            grade.student_id,
            grade.new_total_grade,
            feedback_text
        )
```

### Continuous Navigation Pattern

Use nested loops for continuous grading:

```python
def main():
    client = CanvasAPIClient()

    while True:  # Course selection loop
        courses = client.get_favorite_courses()
        selected_course = select_course(courses)

        while True:  # Assignment selection loop
            assignments = client.get_new_quizzes(selected_course.id)
            selected_assignment = select_assignment(assignments)

            while True:  # Question selection loop
                quiz_items = client.get_quiz_items(
                    selected_course.id,
                    selected_assignment.id
                )
                selected_question = select_question(quiz_items)

                # Grade students...
                grade_students(selected_course, selected_assignment, selected_question)

                # Ask what to do next
                action = get_next_action()

                if action == 1:  # Grade another question
                    continue
                elif action == 2:  # Select different quiz
                    break
                elif action == 3:  # Return to course selection
                    break
                elif action == 4:  # Exit
                    sys.exit(0)

            if action == 3:  # Propagate to outer loop
                break
```

---

## Grade Extraction & Updates

### Extract Current Grades from Student Analysis

```python
def extract_grades(student, question_item_id):
    """
    Extract current grades for a specific question

    Args:
        student: Student object from student_analysis report
        question_item_id: The item_id from student_analysis (not quiz structure!)

    Returns:
        (old_question_grade, old_total_grade, question_response)
    """
    # Get total quiz grade
    old_total_grade = student.get('summary', {}).get('score', 0.0)

    # Find specific question response
    question_response = None
    for resp in student.get('item_responses', []):
        if resp.get('item_id') == question_item_id:
            question_response = resp
            break

    if not question_response:
        return None, None, None

    # Get current question grade
    old_question_grade = question_response.get('score', 0.0)

    return old_question_grade, old_total_grade, question_response
```

### Calculate New Total Grade

```python
def calculate_new_total(old_total, old_question_grade, new_question_grade):
    """
    Calculate new total quiz grade after updating one question

    Formula: new_total = old_total - old_question_grade + new_question_grade
    """
    return old_total - old_question_grade + new_question_grade
```

### Build Feedback Comment

```python
def build_feedback(question_title, old_grade, new_grade, **details):
    """
    Build standardized feedback comment

    Args:
        question_title: Title of the question
        old_grade: Original Canvas grade
        new_grade: New calculated grade
        **details: Additional grading details (correct count, reasoning, etc.)
    """
    feedback = f"New score for {question_title}: "
    feedback += f"old score = {old_grade:.1f}, new score = {new_grade:.1f}\n"

    # Add custom details
    for key, value in details.items():
        feedback += f"{key} = {value}\n"

    return feedback
```

---

## User Interface Patterns

### Display Functions

```python
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
        print(f"{i}. {assignment.name} (ID: {assignment.id}) - "
              f"{assignment.points_possible} pts - Due: {due_str}")


def display_grade_preview(grades: List[StudentGrade]) -> None:
    """Display grading results table"""
    print("\n" + "=" * 135)
    print("GRADE PREVIEW")
    print("=" * 135)
    print(f"{'Student Name':<30} | {'ID':<8} | {'Curr Q':<8} | "
          f"{'New Q':<8} | {'New Total':<10} | {'Improved':<8}")
    print("-" * 135)

    for grade in grades:
        improved = "yes" if grade.new_question_grade >= grade.old_question_grade else "no"
        print(f"{grade.student_name:<30} | "
              f"{grade.student_id:<8} | "
              f"{grade.old_question_grade:<8.1f} | "
              f"{grade.new_question_grade:<8.1f} | "
              f"{grade.new_total_grade:<10.1f} | "
              f"{improved:<8}")

    print("=" * 135)
```

### Input Functions

```python
def get_user_choice(prompt: str, max_value: int) -> int:
    """Get user selection from menu (returns 0-indexed)"""
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
```

---

## Error Handling

### Report Generation Errors

```python
REPORT_TIMEOUT = 900  # 15 minutes
POLL_INTERVAL = 2.0   # seconds

def poll_progress_with_error_handling(progress_url: str) -> dict:
    """Poll progress with timeout and error handling"""
    url = progress_url if progress_url.startswith("http") else f"{HOST}{progress_url}"
    start = time.time()

    while True:
        response = session.get(url)

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
```

### Missing Data Handling

```python
def safe_extract_student_data(student, question_item_id):
    """Safely extract student data with error handling"""
    try:
        student_id = student['student_data']['id']
        student_name = student['student_data']['name']
    except (KeyError, TypeError):
        return None, "Missing student data"

    # Find question response
    question_response = None
    for resp in student.get('item_responses', []):
        if resp.get('item_id') == question_item_id:
            question_response = resp
            break

    if not question_response:
        return None, f"{student_name}: No response found"

    # Extract grades with defaults
    old_question_grade = question_response.get('score', 0.0)
    old_total_grade = student.get('summary', {}).get('score', 0.0)
    answer = question_response.get('answer', '')

    return {
        'student_id': student_id,
        'student_name': student_name,
        'old_question_grade': old_question_grade,
        'old_total_grade': old_total_grade,
        'answer': answer,
        'question_response': question_response
    }, None
```

### API Request Error Handling

```python
def safe_api_request(session, method, url, **kwargs):
    """Make API request with error handling"""
    try:
        response = session.request(method, url, **kwargs)

        if response.status_code not in [200, 201, 202]:
            print(f"❌ API request failed: {response.status_code}")
            print(f"   URL: {url}")
            print(f"   Response: {response.text[:200]}")
            return None

        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return None
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON response from: {url}")
        return None
```

---

## Known Issues & Solutions

### Issue 1: Item ID Mismatch Between APIs ⚠️

**Problem**: The quiz structure API (`GET /api/quiz/v1/.../items`) returns a DIFFERENT `item_id` than the student_analysis report.

**Example**:
- Quiz structure returns: `id: "452018"`
- Student_analysis shows: `item_id: "411636"` (for the same question)

**Solution**: Match questions by **position/index**, not by ID.

**Implementation**:
```python
def find_item_id_from_student_analysis(student_data, question_position, question_type):
    """
    Find the correct item_id from student_analysis by matching position

    Args:
        student_data: Array of student objects from student_analysis
        question_position: Index of question in quiz structure (0-indexed)
        question_type: Question type to match (e.g., 'essay', 'categorization')

    Returns:
        item_id from student_analysis, or None
    """
    if not student_data:
        return None

    first_student_responses = student_data[0].get('item_responses', [])

    # Find question by position among questions of same type
    questions_found = 0
    for resp in first_student_responses:
        if resp.get('item_type') == question_type:
            if questions_found == question_position:
                return resp.get('item_id')
            questions_found += 1

    return None
```

**Usage**:
```python
# User selects question from quiz structure (provides correct answer key)
selected_question = questions[question_idx]  # question_idx is 0-indexed

# Get corresponding item_id from student_analysis
question_item_id = find_item_id_from_student_analysis(
    student_data,
    question_idx,
    'essay'  # or other type
)

# Use this item_id to match student responses
for student in student_data:
    for resp in student['item_responses']:
        if resp['item_id'] == question_item_id:
            # This is the correct response!
            process_response(resp)
```

---

### Issue 2: Whitespace in Item Labels

**Problem**: Quiz structure may have trailing/leading whitespace in labels (e.g., `"ρ "` with trailing space).

**Solution**: Always `.strip()` labels when parsing from quiz structure.

```python
# When building answer keys or label maps
item_label = distractors[item_uuid]['item_body'].strip()
category_label = categories[cat_uuid]['item_body'].strip()
```

---

### Issue 3: Cannot Update Individual Question Grades

**Problem**: Canvas New Quizzes API does not allow updating individual question grades.

**Limitation**: You can only update the **total assignment grade**, not question-level scores.

**Workaround**:
1. Calculate new question grade using custom algorithm
2. Calculate new total: `new_total = old_total - old_question_grade + new_question_grade`
3. Update total with detailed feedback comment explaining the breakdown

**Student View**:
- Total grade reflects the custom grading
- Individual question scores remain as originally graded by Canvas
- Feedback comment explains the adjustment

---

### Issue 4: Gradebook Posting Policy

**Problem**: If course uses Manual posting, grades won't be visible until posted.

**Note**: The Submissions API respects the course's grade posting policy automatically.

**Recommendation**: Remind users to post grades if using manual posting policy.

---

### Issue 5: Multiple Attempts

**Behavior**: Student_analysis report returns the **most recent/latest attempt** by default.

**Implementation**: No special handling needed - always use the data from the report (which is already the latest attempt).

**Optional**: Check `student_data.attempt` field if you need to verify which attempt is being graded.

---

## Question Type Specific Notes

### Essay Questions

**Question type**: `interaction_type_slug == "essay"`

**Answer format**: HTML string (may contain rich text formatting)

**Typical workflow**:
1. Extract essay text from `answer` field (may need HTML parsing)
2. Apply AI grading, rubric-based grading, or other custom logic
3. Calculate new grade
4. Update with detailed feedback

**Example answer**:
```json
{
  "item_id": "411637",
  "item_type": "essay",
  "score": 0,
  "answer": "<p>Student's essay response here...</p>"
}
```

---

### Fill in the Blank Questions

**Question type**: `interaction_type_slug == "fill_in_multiple_blanks"`

**Answer format**: Varies - typically key-value pairs for each blank

**Note**: Requires parsing the question structure to identify blank IDs and correct answers.

---

### Matching Questions

**Question type**: `interaction_type_slug == "matching"`

**Answer format**: Pairs of matched items

**Note**: Similar to categorization - requires building correct answer key from quiz structure.

---

## Configuration Constants

```python
# API Configuration
SERVICE_NAME = 'canvas'
USERNAME = 'access-token'
HOST = 'https://your-instance.instructure.com'
API_V1 = f"{HOST}/api/v1"
API_QUIZ = f"{HOST}/api/quiz/v1"

# Polling Configuration
POLL_INTERVAL = 2.0   # seconds between progress checks
REPORT_TIMEOUT = 900  # 15 minutes timeout for report generation

# Display Configuration
TABLE_WIDTH = 135  # characters for grade preview table
```

---

## Complete Example: Essay Grader Skeleton

```python
#!/usr/bin/env python3
"""
Canvas New Quizzes: Essay Grader
Template for AI-powered or rubric-based essay grading
"""

import sys
import time
import keyring
import requests
from typing import List, Optional
from dataclasses import dataclass

# Configuration
SERVICE_NAME = 'canvas'
USERNAME = 'access-token'
HOST = 'https://uncch.instructure.com'
API_V1 = f"{HOST}/api/v1"
API_QUIZ = f"{HOST}/api/quiz/v1"

POLL_INTERVAL = 2.0
REPORT_TIMEOUT = 900


@dataclass
class StudentGrade:
    student_id: int
    student_name: str
    old_question_grade: float
    new_question_grade: float
    old_total_grade: float
    new_total_grade: float
    essay_text: str  # Question-type specific field


class CanvasAPIClient:
    def __init__(self):
        self.token = keyring.get_password(SERVICE_NAME, USERNAME)
        if not self.token:
            print(f"❌ ERROR: No Canvas API token found in keychain.")
            sys.exit(1)
        self.session = requests.Session()
        self.session.headers.update({'Authorization': f'Bearer {self.token}'})

    # ... (implement API methods as shown above)


class EssayGrader:
    @staticmethod
    def parse_quiz_item(item: dict) -> Optional[dict]:
        """Parse a quiz item to extract essay question details"""
        entry = item.get('entry', {})

        if entry.get('interaction_type_slug') != 'essay':
            return None

        return {
            'item_id': item['id'],
            'title': entry.get('title', 'Untitled Question'),
            'points_possible': item.get('points_possible', 0.0),
            'prompt': entry.get('item_body', '')
        }

    @staticmethod
    def grade_essay(essay_text: str, rubric: dict) -> float:
        """
        Apply custom essay grading logic

        Args:
            essay_text: Student's essay response
            rubric: Grading rubric or criteria

        Returns:
            Calculated grade (0.0 to points_possible)
        """
        # TODO: Implement your grading logic here
        # Could use AI API, keyword matching, length checks, etc.
        pass


def main():
    client = CanvasAPIClient()
    grader = EssayGrader()

    # Follow the workflow pattern shown above...
    # 1. Select course
    # 2. Select assignment
    # 3. Filter for essay questions
    # 4. Get student submissions
    # 5. Grade each essay
    # 6. Preview and update grades


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Exiting...")
        sys.exit(0)
```

---

## Additional Resources

### Canvas API Documentation
- Assignments API: https://canvas.instructure.com/doc/api/assignments.html
- Submissions API: https://canvas.instructure.com/doc/api/submissions.html
- Quiz API: https://canvas.instructure.com/doc/api/quiz_submissions.html

### Important Notes
- New Quizzes are LTI tools, not native Canvas quizzes
- Many Classic Quiz APIs do not work with New Quizzes
- Always use `is_quiz_lti_assignment == true` to identify New Quizzes
- The student_analysis report is the primary data source for submissions

---

## Summary

This framework provides:
✅ Complete API endpoint documentation
✅ Reusable code patterns and workflows
✅ Error handling strategies
✅ UI/UX patterns for interactive grading
✅ Solutions to known issues
✅ Template for new grading scripts

**When creating new graders:**
1. Copy the skeleton structure
2. Implement question-type specific parsing
3. Implement custom grading algorithm
4. Reuse API client and UI patterns
5. Follow the continuous navigation workflow

**Key takeaway**: The main differences between question types are in:
- Parsing the quiz structure (Step 3)
- Parsing student answers (Step 7)
- The grading algorithm (Step 8)

All other components (API calls, navigation, grade updates) remain the same!
