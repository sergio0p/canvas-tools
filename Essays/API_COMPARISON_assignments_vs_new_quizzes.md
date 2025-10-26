# API Comparison: Regular Assignments vs New Quizzes

**Purpose**: Document API differences for implementing assignment graders (TODO #3)

---

## Regular Assignments (online_text_entry)

### 1. List Assignments
**Endpoint**: `GET /api/v1/courses/:course_id/assignments`

**Filter for essay assignments**:
- Look for `submission_types` containing `"online_text_entry"`
- Assignment object includes:
  - `id` - Assignment ID
  - `name` - Assignment name
  - `points_possible` - Max points
  - `submission_types` - Array (e.g., `["online_text_entry"]`)
  - `grading_type` - Type (e.g., "points", "letter_grade", "gpa_scale")

### 2. Get Student Submissions
**Endpoint**: `GET /api/v1/courses/:course_id/assignments/:assignment_id/submissions`

**Returns**: Array of Submission objects

**Submission object** (for online_text_entry):
```json
{
  "assignment_id": 23,
  "user_id": 134,
  "score": 13.5,
  "grade": "B+",
  "submission_type": "online_text_entry",
  "body": "<p>HTML content of student's essay...</p>",
  "submitted_at": "2024-10-25T12:00:00Z",
  "grade_matches_current_submission": true,
  "grader_id": null,
  "workflow_state": "submitted"
}
```

**Key fields**:
- `body` - HTML content of the text submission
- `user_id` - Student's Canvas ID
- `score` - Current raw score
- `grade` - Current grade (translated to grading scheme)

**Optional includes** (via `include[]` parameter):
- `user` - Include user/student information
- `submission_comments` - Include existing comments
- `assignment` - Include assignment details

### 3. Grade a Submission
**Endpoint**: `PUT /api/v1/courses/:course_id/assignments/:assignment_id/submissions/:user_id`

**Parameters**:
- `submission[posted_grade]` - The grade/score (formats: number, "40%", "A-")
- `comment[text_comment]` - Add textual feedback comment
- `comment[group_comment]` - Send to entire group (boolean, default false)
- `comment[media_comment_id]` - Media comment ID (optional)
- `rubric_assessment` - Rubric grading (optional)

**Example grading with comment**:
```python
data = {
    'submission[posted_grade]': '85',
    'comment[text_comment]': 'Great work! Your analysis was thorough.'
}
```

---

## New Quizzes

### 1. List New Quizzes
**Endpoint**: `GET /api/v1/courses/:course_id/assignments`

**Filter for New Quizzes**:
- Look for `is_quiz_lti_assignment` = `true`

### 2. Get Quiz Items/Questions
**Endpoint**: `GET /api/quiz/v1/courses/:course_id/quizzes/:assignment_id/items`

**Returns**: Array of quiz item objects
- Different structure with `entry.interaction_type_slug` = `"essay"`

### 3. Get Student Submissions (Report-based)
**Endpoint**: `POST /api/quiz/v1/courses/:course_id/quizzes/:assignment_id/reports`

**Process**:
1. Create student_analysis report
2. Poll progress endpoint
3. Download JSON report

**Report structure**:
```json
[
  {
    "student_data": {
      "id": 12345,
      "name": "Student Name"
    },
    "summary": {
      "score": 75.0
    },
    "item_responses": [
      {
        "item_id": "abc123",
        "item_type": "essay",
        "score": 10.0,
        "answer": "<p>HTML essay content...</p>"
      }
    ]
  }
]
```

### 4. Grade a Quiz Submission
**Endpoint**: `PUT /api/v1/courses/:course_id/assignments/:assignment_id/submissions/:user_id`

**Parameters** (same as regular assignments):
- `submission[posted_grade]` - Total quiz score
- `comment[text_comment]` - Add feedback comment

---

## Key Differences Summary

| Feature | Regular Assignments | New Quizzes |
|---------|-------------------|-------------|
| **Identification** | `submission_types: ["online_text_entry"]` | `is_quiz_lti_assignment: true` |
| **Get Submissions** | Direct GET on submissions endpoint | Create/download report via quiz API |
| **Essay Content** | `submission.body` (HTML) | `item_response.answer` (HTML) |
| **Grading Endpoint** | Same for both! | Same for both! |
| **Comment Field** | `comment[text_comment]` | `comment[text_comment]` |
| **Score Field** | `submission[posted_grade]` | `submission[posted_grade]` |
| **Data Structure** | Flat submission object | Nested quiz report structure |
| **API Namespace** | `/api/v1/` | `/api/quiz/v1/` for data, `/api/v1/` for grading |

---

## Implementation Strategy for Assignment Graders

### grader_a_assignments.py Changes:

1. **List assignments**: Use existing `get_assignments()` but filter by:
   ```python
   if 'online_text_entry' in a.get('submission_types', [])
   ```

2. **Get submissions**: Use direct API call instead of report:
   ```python
   url = f"{API_V1}/courses/{course_id}/assignments/{assignment_id}/submissions"
   params = {'include[]': ['user']}  # Include user data
   response = session.get(url, params=params)
   submissions = response.json()
   ```

3. **Extract essay**: From `submission['body']` field (HTML)
   - Use BeautifulSoup to extract plain text (same as current code)

4. **No item_id needed**: Work directly with assignment_id and user_id

### grader_b_assignments.py Changes:

1. **Grading endpoint**: **SAME** as New Quizzes!
   ```python
   url = f"{API_V1}/courses/{course_id}/assignments/{assignment_id}/submissions/{user_id}"
   ```

2. **Comment format**: **SAME** as New Quizzes!
   ```python
   data = {
       'submission[posted_grade]': str(grade),
       'comment[text_comment]': comment
   }
   ```

3. **Minimal changes needed** for Part B - grading logic stays the same!

---

## Notes

- **HTML Sanitization**: Both use HTML in submission body/answer fields
- **Multiple Comments**: Can call update_grade() multiple times to post multiple comments (same as New Quizzes)
- **Workflow**: Assignment version is actually **simpler** - no report generation/polling needed
- **Compatibility**: Part B grader code can potentially be shared between both versions

---

## Files to Create

1. `grader_a_assignments.py`
   - Modify: Assignment listing (filter by submission_types)
   - Modify: Submission retrieval (direct API vs report)
   - Keep: OpenAI grading logic (same)
   - Keep: JSON save format (can be same structure)

2. `grader_b_assignments.py`
   - Potentially **identical** to `grader_b_new_quizzes.py`
   - Or create shared base class for both

---

**Generated**: 2025-10-25
**For**: TODO item #3 - Create Assignment Version
