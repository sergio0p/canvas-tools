# Canvas New Quizzes: Categorization Grading - Complete API Specification

## Executive Summary

**Primary Finding**: While you **CANNOT** change individual question grades in New Quizzes via API, you **CAN** change the overall assignment grade and add feedback using the standard Canvas Assignments API.

**Recommended Approach**: Fetch student submissions via student_analysis reports, apply custom partial credit grading algorithm, and update total quiz grades using the Assignments Submissions API.

**Implementation Strategy**: Complete workflow from course selection through grade updates with detailed API endpoints and data structures.

---

## Key Findings

### ❌ What DOES NOT Work

1. **Classic Quiz Submissions API is incompatible with New Quizzes**
   - Endpoint: `PUT /api/v1/courses/:course_id/quizzes/:quiz_id/submissions/:id`
   - This API only works with Classic Canvas Quizzes
   - New Quizzes are LTI tools, not native Canvas quizzes
   - Cannot update individual question scores for New Quizzes

2. **No New Quizzes Grading API**
   - As documented at Stanford University and confirmed in multiple Canvas Community threads:
     > "No APIs for third-party tool integrations or custom scripts"
   - New Quizzes uses an external tool architecture that doesn't expose grading endpoints
   - The New Quiz Items API only allows creating/editing questions, not grading submissions

### ✅ What DOES Work

**Assignments Submissions API** - The Recommended Solution

New Quizzes create corresponding Assignment objects in Canvas. You can update grades using:

```
PUT /api/v1/courses/:course_id/assignments/:assignment_id/submissions/:user_id
```

**Key Parameters**:
- `submission[posted_grade]` - Sets the overall grade (number, percentage, letter grade, or "pass"/"complete")
- `comment[text_comment]` - Adds visible feedback text for the student
- `comment[group_comment]` - Set to true for group assignments (defaults to false)

**Important Notes**:
- `assignment_id` is the same as the New Quiz assignment ID you're already using
- This updates the TOTAL assignment grade, not individual question scores
- The grade appears in both SpeedGrader and the Gradebook
- Comments appear in the assignment's comment thread
- Requires "manage grades" permission in the course

---

## Comparison: Assignments API vs. Gradebook API

### Option 1: Assignments Submissions API (RECOMMENDED)

**Endpoint**: `PUT /api/v1/courses/:course_id/assignments/:assignment_id/submissions/:user_id`

**Advantages**:
✅ Can set grade AND add feedback text in same call  
✅ Most straightforward approach  
✅ Well-documented and stable  
✅ Feedback appears prominently in assignment view  
✅ Supports text comments and file attachments  
✅ Works for individual submissions

**Parameters**:
```json
{
  "submission[posted_grade]": "85",
  "comment[text_comment]": "Great work! Categorization: 14/15 correct items."
}
```

**Example cURL**:
```bash
curl -X PUT 'https://canvas.example.edu/api/v1/courses/97934/assignments/743848/submissions/123456' \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -F 'submission[posted_grade]=85' \
  -F 'comment[text_comment]=Excellent categorization work!'
```

### Option 2: Gradebook API (Alternative)

**Endpoint**: `POST /api/v1/courses/:course_id/submissions/update_grades`

**Advantages**:
✅ Can update multiple students at once (bulk operations)  
✅ Asynchronous processing for large batches

**Disadvantages**:
❌ **Cannot add comments** - only updates grades  
❌ More complex response handling (returns Progress object)  
❌ Requires polling to confirm completion  
❌ Less suitable for single student updates

**Use Case**: Best for batch-updating many grades without feedback

---

## Feasibility Analysis

### Can You Update Overall Quiz Grades? ✅ YES

**Method**: Assignments Submissions API  
**Feasibility**: HIGH - This is the standard, well-supported approach

**Workflow**:
1. Calculate new score based on your partial credit algorithm
2. Call Assignments API with total calculated score
3. Include feedback explaining the grading breakdown

**Example Scenario**:
- Original New Quiz score: 0 points (categorization marked wrong by Canvas)
- Your calculated score: 8.5/10 points
- API call: Set `posted_grade=8.5` with comment "Partial credit: 14/15 items correctly categorized"

### Can You Add Assignment-Level Feedback? ✅ YES

**Method**: Comment parameter in Assignments Submissions API  
**Feasibility**: HIGH

**Feedback appears**:
- In the assignment submission view
- In SpeedGrader
- In student's submission comments thread
- Email notifications to student (if enabled)

**Feedback Format**:
- Plain text or basic HTML
- Can include file attachments (uploaded separately)
- Visible to student immediately (unless gradebook posting policy prevents it)

### Can You Update Individual Question Grades? ❌ NO

**Feasibility**: NOT POSSIBLE via API

**Why It Doesn't Work**:
- New Quizzes stores question-level data in its own external database
- No API endpoint exposes question-level grading for New Quizzes
- The LTI architecture prevents direct question manipulation

**Implications**:
- You can only change the total quiz score
- Individual question scores remain as originally graded by Canvas
- Students will see updated total but original question-by-question breakdown
- Your feedback comments should explain the grade adjustment

---

## Complete API Workflow

### Step 1: Get Favorite Courses

**Endpoint**: `GET /api/v1/users/self/favorites/courses`

**Purpose**: Fetch user's favorite courses

**Filter**: Only show published courses (`workflow_state == "available"`)

**Response fields**:
- `id` - Course ID
- `name` - Course name
- `workflow_state` - "available", "unpublished", etc.

---

### Step 2: List Quiz Assignments

**Endpoint**: `GET /api/v1/courses/:course_id/assignments`

**Purpose**: Fetch all assignments for the selected course

**Parameters**:
- `per_page`: Number of results per page (default: 10, max: 100)

**Filter for New Quizzes**: `is_quiz_lti_assignment == true`

**Response fields**:
- `id` - Assignment ID (same as quiz assignment ID for New Quizzes)
- `name` - Assignment name
- `due_at` - Due date
- `points_possible` - Maximum points
- `submission_types` - Array containing `["external_tool"]` for New Quizzes
- `is_quiz_lti_assignment` - **true** for New Quizzes, false otherwise
- `is_quiz_assignment` - false for New Quizzes (true only for Classic Quizzes)

**Example filtering**:
```python
assignments = response.json()
new_quizzes = [a for a in assignments if a.get('is_quiz_lti_assignment')]
```

---

### Step 3: Get Quiz Items/Questions

**Endpoint**: `GET /api/quiz/v1/courses/:course_id/quizzes/:assignment_id/items`

**Purpose**: Fetch all questions/items in the quiz to get correct answers

**Filter**: Identify categorization questions (`entry.interaction_type_slug == "categorization"`)

**Response structure for categorization questions**:
```json
{
  "id": "470425",
  "entry": {
    "title": "Question title",
    "item_body": "<p>Question text</p>",
    "interaction_type_slug": "categorization",
    "interaction_data": {
      "categories": {
        "uuid1": {"id": "uuid1", "item_body": "Category 1"},
        "uuid2": {"id": "uuid2", "item_body": "Category 2"}
      },
      "distractors": {
        "uuid3": {"id": "uuid3", "item_body": "Item A"},
        "uuid4": {"id": "uuid4", "item_body": "Item B"},
        "uuid5": {"id": "uuid5", "item_body": "Item C (true distractor)"}
      }
    },
    "scoring_data": {
      "value": [
        {
          "id": "uuid1",
          "scoring_data": {"value": ["uuid3", "uuid4"]}
        }
      ]
    }
  },
  "points_possible": 3.0
}
```

**Key data extraction**:
1. **Categories**: Extract from `interaction_data.categories` - map UUID to category label
2. **Items**: Extract from `interaction_data.distractors` - map UUID to item label (Note: ALL items are in "distractors", confusing naming!)
3. **Correct answers**: From `scoring_data.value[]` - which item UUIDs belong to which category UUIDs
4. **True distractors**: Items in `distractors` but NOT in any `scoring_data.value[]` - these should remain unplaced

---

### Step 4: Create Student Analysis Report

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

**Response**:
```json
{
  "progress_url": "/api/v1/progress/12345"
}
```

---

### Step 5: Poll Report Progress

**Endpoint**: `GET /api/v1/progress/:progress_id`

**Purpose**: Check if report generation is complete

**Poll interval**: Every 2 seconds

**Response states**:
- `"workflow_state": "queued"` - Still processing
- `"workflow_state": "running"` - Still processing
- `"workflow_state": "completed"` - Ready to download
- `"workflow_state": "failed"` - Error occurred

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

### Step 6: Resolve Download URL

**Primary**: Use `results.url` or `results.attachment.url` from progress response

**Fallback**: If only `attachment_id` available, fetch file metadata

**Endpoint**: `GET /api/v1/files/:file_id`

**Response**:
```json
{
  "id": 123,
  "url": "https://...",
  "download_url": "https://..."
}
```

---

### Step 7: Parse Student Submissions

**Downloaded file format**: JSON array of student submission objects

**Structure**:
```json
[
  {
    "student_data": {
      "id": 73860,
      "name": "Student Name",
      "submitted_at": "2025-09-04T14:39:37.268Z"
    },
    "item_responses": [
      {
        "item_id": "411636",
        "item_type": "categorization",
        "score": 0.0,
        "answer": "category1 => [itemA,itemB],category2 => [itemC,itemD]"
      }
    ],
    "summary": {
      "score": 2.0,
      "points_possible": 4.0
    }
  }
]
```

**Answer parsing**:
- Format: `"category1 => [item1,item2],category2 => [item3]"`
- Parse to extract student's categorization placements
- Use text labels (not UUIDs) for grading

**Current grade extraction** (required for Step 9 grade calculation):
- **Old question grade**: Find the categorization question in `item_responses[]` by matching `item_id`, extract its `score` field
- **Old total quiz grade**: `summary.score`
- Example: If `item_responses[0].score = 0.0` and `summary.score = 0.0`, and new question grade calculated as 1.8, then `new_quiz_total = 0.0 - 0.0 + 1.8 = 1.8`

**Multiple attempts**:
- If present, `student_data.attempt` indicates which attempt number
- Student_analysis report returns the most recent/latest attempt
- **Always use the most recent attempt** - no user selection needed

---

### Step 8: Apply Grading Algorithm

**Formula**:
```
new_score = (correct - 0.5 * misclassified) / total * points_possible
```

**Algorithm**:
1. Build correct answer map: `{item_label: correct_category_label}` from quiz structure
2. Build true distractor set: items that shouldn't be placed
3. Parse student answer to get their placements
4. Compare:
   - **Correct**: Item placed in correct category
   - **Misclassified**: Item placed in wrong category OR true distractor placed anywhere
   - **Not placed**: Item not placed (loses credit but not penalized)
5. Calculate score using formula

**Example**:
- Total items to categorize: 15
- Student placed correctly: 14
- Student misclassified: 1
- Points possible: 2.0
- Score: (14 - 0.5 * 1) / 15 * 2.0 = 1.8 points

---

### Step 9: Update Assignment Grade with Feedback

**Endpoint**: `PUT /api/v1/courses/:course_id/assignments/:assignment_id/submissions/:user_id`

**Purpose**: Update the overall quiz grade and add feedback comment

**Parameters**:
- `submission[posted_grade]` - New total quiz score
- `comment[text_comment]` - Feedback explaining the grade

**Grade calculation**:
```
new_quiz_total = old_quiz_total - old_question_grade + new_question_grade
```

**Feedback format**:
```
New score for [Question Title]: old score = [X], new score = [Y]
Correct = [#], Misclassified = [#]
Grading formula: (correct - 0.5 * misclassified) / total * points_possible
```

**Notes**:
- Comments are automatically appended to existing submission comments (no special logic needed - Canvas API handles this)
- Grade updates respect posting policies (manual vs automatic)
- Updates appear in SpeedGrader and Gradebook

---

## Limitations and Considerations

### 1. **No Question-Level Detail in Canvas UI**
- Students will see: "Total: 8.5/10" but original question grades unchanged
- **Mitigation**: Provide detailed feedback comment explaining the breakdown

### 2. **Gradebook Posting Policy**
- If course uses Manual posting, grades won't be visible until posted
- Submissions API respects the course's grade posting policy
- **Check**: Ensure grades are posted after updating

### 3. **Existing Submissions Required**
- API only works if a submission exists (student completed the quiz)
- **Error handling**: Check for 404 errors if no submission exists

### 4. **Grading Type Compatibility**
- **Algorithm assumes points-based grading** (most common for quizzes)
- For points: Use numeric value (e.g., "8.5")
- For percentage/letter/pass-fail: Convert calculated points to appropriate format before API call
- Assignment's `grading_type` field indicates which format to use

### 5. **Authentication and Permissions**
- Requires API token with "manage grades" scope (sufficient for all operations: reading courses/assignments/quiz items and updating grades)
- User must have Teacher, TA, or Grader role in course

### 6. **Item ID Mismatch Between APIs** ⚠️
- **Critical Issue**: The quiz structure API (`GET /api/quiz/v1/.../items`) returns a DIFFERENT `item_id` than the student_analysis report
  - Example: Quiz structure returns `id: "452018"` for a question
  - Student_analysis report shows `item_id: "411636"` for the same question
- **Solution**: Match questions by position/index, not by ID
  - User selects question from quiz structure (which provides correct answers)
  - Code finds corresponding `item_id` in student_analysis by matching position among categorization questions
  - Use that student_analysis `item_id` to find responses in all student records
- **Implementation**: After question selection, extract the correct `item_id` from first student's responses at the same position index

### 7. **Error Handling Scenarios**
- **Report timeout**: Poll for max 15 minutes (900 seconds), then fail gracefully
- **Malformed answer string**: Skip student and log error if answer format cannot be parsed
- **Division by zero**: If `points_possible` is 0 or null, skip question and warn user
- **Missing data**: If `summary.score` or `item_responses[].score` missing, skip student

---

## Testing Recommendations

### Test Script (Python)
```python
def test_grade_update():
    """Test grade update on single student submission"""
    
    # Test parameters
    CANVAS_URL = "https://your-canvas.edu"
    COURSE_ID = 97934
    ASSIGNMENT_ID = 743848
    TEST_USER_ID = 123456  # Use a test student
    
    # Test with small grade change
    test_score = 9.0
    test_feedback = "TEST: Partial credit algorithm applied"
    
    url = f"{CANVAS_URL}/api/v1/courses/{COURSE_ID}/assignments/{ASSIGNMENT_ID}/submissions/{TEST_USER_ID}"
    
    response = requests.put(
        url,
        headers={"Authorization": f"Bearer {API_TOKEN}"},
        data={
            "submission[posted_grade]": str(test_score),
            "comment[text_comment]": test_feedback
        }
    )
    
    # Verify
    assert response.status_code == 200
    result = response.json()
    assert result['grade'] == str(test_score)
    print("✅ Grade update successful")
    print(f"   New grade: {result['grade']}")
    print(f"   Graded at: {result['graded_at']}")
    
    # Check comment was added
    comments = result.get('submission_comments', [])
    assert any(test_feedback in c['comment'] for c in comments)
    print("✅ Comment added successfully")
```

---

## Documentation References

### Canvas API Documentation
1. **Assignments Submissions API**: https://canvas.instructure.com/doc/api/submissions.html
   - Method: `PUT /api/v1/courses/:course_id/assignments/:assignment_id/submissions/:user_id`
   
2. **Grade Posting Policy**: https://canvas.instructure.com/doc/api/submissions.html#method.submissions_api.update
   - Note: Updates respect manual/automatic posting settings

### Community Resources
3. **New Quizzes Limitations**: https://canvashelp.stanford.edu/hc/en-us/articles/4405462061843
   - Documents API limitations for New Quizzes

4. **Grading New Quizzes**: Multiple university documentation confirms only total grade updates are possible

---

## Final Recommendation

### ✅ FEASIBLE APPROACH:

**Use the Assignments Submissions API** to:
1. Update the total New Quiz grade to your calculated partial credit score
2. Provide detailed feedback explaining the score breakdown
3. Process all students programmatically

### 📋 Implementation Checklist:

- [x] Confirmed New Quizzes create Assignment objects
- [x] Verified Assignments API accepts grade updates
- [x] Confirmed feedback comments are supported
- [x] Identified API token requirements
- [ ] Test with single student first
- [ ] Verify grade appears in SpeedGrader and Gradebook
- [ ] Confirm feedback is visible to students
- [ ] Implement bulk processing for all students
- [ ] Add error handling for edge cases

### 🎯 Expected Outcome:

Students will see:
- **Updated total grade** in Gradebook and SpeedGrader
- **Assignment feedback** explaining partial credit
- Original question-by-question breakdown (unchanged)

This approach successfully achieves your goal of applying partial credit while working within New Quizzes' API limitations.