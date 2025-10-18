# Canvas New Quizzes: Categorization Grader - User Workflow

## Overview
Interactive CLI tool for applying partial credit to Canvas New Quizzes categorization questions using a custom grading algorithm.

---

## User Interaction Flow

### 1. Authentication
- Tool authenticates to Canvas using API token from system keychain
- No user interaction required

### 2. Course Selection
- System fetches user's favorite courses via `GET /api/v1/users/self/favorites/courses`
- Filters to only show published courses (`workflow_state == "available"`)
- Display format: Course ID | Course Name
- **User action:** Select one course from the list

### 3. Assignment Selection
- System fetches assignments for the selected course via `GET /api/v1/courses/:course_id/assignments`
- Filters to only show New Quizzes assignments
- Display format: Assignment ID | Assignment Name | Due Date | Points Possible
- **User action:** Select one quiz assignment from the list

### 4. Question Selection
- System fetches quiz items/questions via `GET /api/quiz/v1/courses/:course_id/quizzes/:assignment_id/items`
- Identifies and displays only categorization-type questions (`interaction_type_slug == "categorization"`)
- Display format: Item ID | Question Title | Point Value
- **User action:** Select one categorization question from the list

### 5. Extract Correct Answer Key & Identify True Distractors
- System builds correct answer mapping using item labels (text):
  - Extract category labels from `interaction_data.categories[uuid].item_body`
  - Extract item labels from `interaction_data.distractors[uuid].item_body`
  - Map each item label to its correct category label using `scoring_data.value[]`
- **Identifies true distractors**: Items that shouldn't be placed in any category
  - Items appearing in `scoring_data.value[]` = items that must be categorized
  - Items in `distractors` but NOT in `scoring_data.value[]` = true distractors
  - True distractors should remain unplaced by students
- No user interaction

### 6. Submission Processing
- System creates student_analysis report via `POST /api/quiz/v1/courses/:course_id/quizzes/:assignment_id/reports`
  - Payload: `{"quiz_report": {"report_type": "student_analysis", "format": "json"}}`
- Polls progress via `GET /api/v1/progress/:id` until report generation completes
- Downloads report (resolves URL via `GET /api/v1/files/:id` if needed)
- Parses student responses from report JSON (answer format: `"category1 => [item1,item2],category2 => [item3]"`)
- Applies categorization grading algorithm for each student
- Skips students without submissions

### 7. Grade Preview & Approval
- System displays results in a table format:
  - **Column Headers:** Student Name | Current Question Grade | New Question Grade | Correct | Misclassified
  - **Rows:** One per student (only students with submissions)
  - Example row: `John Smith | 0.0 | 1.5 | 14 | 1`
- **User action:** Approve or reject the grade changes
  - If **No**: Quit without making changes
  - If **Yes**: Proceed to update grades

### 8. Grade Updates (if approved)
- For each student:
  - Calculate new quiz total: `new_total = old_quiz_total - old_question_grade + new_question_grade`
  - Update overall quiz grade via `PUT /api/v1/courses/:course_id/assignments/:assignment_id/submissions/:user_id`
  - Parameters: `submission[posted_grade]`, `comment[text_comment]`
  - Write feedback comment to assignment (appends to existing comments)

**Feedback format:**
```
New score for [Question Title]: old score = [X], new score = [Y]
Correct = [#], Misclassified = [#]
Grading formula: (correct - 0.5 * misclassified) / total * points_possible
```

### 9. Completion
- Display summary of updated grades
- Show any errors or skipped students

---

## Grading Algorithm

**Formula:**
```
score = (correct - 0.5 * misclassified) / total * points_possible
```

Where:
- `correct` = number of items placed in correct categories
- `misclassified` = number of items placed in wrong categories
- `total` = total number of items that should be categorized (excludes true distractors)
- `points_possible` = max points for the question

**Scoring Rules:**
1. **Correct placement**: Item placed in the correct category → +1 to correct count
2. **Wrong placement**: Item placed in incorrect category → +1 to misclassified count
3. **Not placed**: Item not placed anywhere → no penalty, just loses the point (not counted as misclassified)
4. **True distractor placed**: True distractor placed in any category → +1 to misclassified count
5. **True distractor not placed**: True distractor left unplaced → correct (no penalty)

**Example:**
- Total items to categorize: 15
- Correct placements: 14
- Misclassified: 1
- Points possible: 2.0
- Score: (14 - 0.5 * 1) / 15 * 2.0 = 1.8 points

---

## Data Format Notes

**Student answer format** (from student_analysis report):
```
"answer": "category1 => [item1,item2],category2 => [item3,item4]"
```

**All grading logic uses text labels, not UUIDs:**
- Category labels: "exogenous", "endogenous", "White", "black", etc.
- Item labels: "A(0)", "ρ", "milk", "flour", etc.
- UUIDs are only used internally by Canvas; grading converts everything to labels upfront

---

## Implementation Notes
- Students without submissions are automatically skipped
- Single approval applies to all students at once (batch operation)
- Comments are appended to existing assignment comments
- Grade updates respect Canvas posting policies
- Original question-level scores remain unchanged in Canvas (API limitation)
- Only the total quiz grade is updated to reflect the new question score
