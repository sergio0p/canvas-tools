# Conclusions: Assignment Graders Implementation (TODO #3)

**Date**: 2025-10-25
**Analysis**: Canvas API documentation review for regular assignments vs New Quizzes

---

## Executive Summary

After analyzing Canvas API documentation, implementing assignment graders (TODO #3) is **less complex than initially thought**. The "MAJOR WORK" designation applies primarily to Part A (data retrieval), while Part B (grading/uploading) requires minimal changes.

---

## Key Conclusions

### 1. Part B is Nearly Identical
- **Same grading endpoint**: `PUT /api/v1/courses/:course_id/assignments/:assignment_id/submissions/:user_id`
- **Same parameters**: `submission[posted_grade]` and `comment[text_comment]`
- **Implication**: `grader_b_assignments.py` could share 90%+ code with `grader_b_new_quizzes.py`

### 2. Part A Has Different Data Flow (But Simpler)
- **New Quizzes**: Create report → Poll progress → Download JSON → Parse nested structure
- **Assignments**: Direct GET submissions → Parse flat structure
- **Implication**: Assignment version is actually **simpler** - no polling/waiting

### 3. Assignment Version is More Straightforward

| Aspect | New Quizzes | Regular Assignments |
|--------|-------------|---------------------|
| Complexity | High (multi-step report) | Low (single API call) |
| Wait time | Yes (report generation) | No (instant) |
| Data structure | Nested (quiz items) | Flat (submissions) |
| API namespace | Mixed (`/api/quiz/v1/` + `/api/v1/`) | Single (`/api/v1/`) |

---

## Implementation Plan

### grader_a_assignments.py - Changes Needed

#### 1. Assignment Filtering (Small change)
```python
# OLD (New Quizzes):
if a.get('is_quiz_lti_assignment')

# NEW (Assignments):
if 'online_text_entry' in a.get('submission_types', [])
```

#### 2. Submissions Retrieval (Major change)
```python
# OLD: Create/poll/download report
progress_url = create_student_analysis_report(...)
poll_progress(progress_url)
student_data = download_report(...)

# NEW: Direct API call
url = f"{API_V1}/courses/{course_id}/assignments/{assignment_id}/submissions"
response = session.get(url, params={'include[]': ['user']})
submissions = response.json()
```

#### 3. Essay Text Extraction (Small change)
```python
# OLD: From nested quiz structure
essay_html = item_response.get('answer', '')

# NEW: From flat submission
essay_html = submission.get('body', '')
```

#### 4. Remove item_id Logic (Simplification)
- No need to match question_idx to item_id
- Work directly with assignment_id

#### 5. Keep Unchanged
- OpenAI grading logic (100% same)
- JSON save format (can use same structure)
- BeautifulSoup HTML parsing (same)
- Parallel grading with ThreadPoolExecutor (same)

### grader_b_assignments.py - Minimal Changes

**Option A: Duplicate & Modify**
- Copy `grader_b_new_quizzes.py`
- Change title/warnings only
- Possibly remove quiz-specific language

**Option B: Shared Code (Better)**
- Create base class or shared functions
- Both graders use same grading logic
- DRY principle

---

## Files to Create

1. **grader_a_assignments.py** (New)
   - ~700 lines (similar to grader_a_new_quizzes.py)
   - Moderate effort

2. **grader_b_assignments.py** (New)
   - ~700 lines OR share code with grader_b_new_quizzes.py
   - Low effort (mostly duplicate)

3. **Sample config files** (Optional)
   - Can reuse existing `grading_config_*.json`
   - Can reuse existing `grading_instructions_*.md`

---

## Effort Estimate

| Task | Effort | Reason |
|------|--------|--------|
| grader_a_assignments.py | Medium | Different API calls, simpler logic |
| grader_b_assignments.py | Low | Nearly identical to New Quizzes version |
| Testing | Medium | Need test course with text assignments |
| Documentation | Low | Update QUICKSTART.md and README |
| **Total** | **Medium** | Not "MAJOR WORK" as originally stated |

---

## Risks & Considerations

### 1. Submission Types
- Assignments can have multiple `submission_types`
- Example: `["online_text_entry", "online_upload"]`
- Need to handle mixed types gracefully

### 2. Empty Submissions
- Students may submit blank text
- Handle same as New Quizzes (skip with message)

### 3. HTML Sanitization
- Both use HTML in submission body
- Canvas sanitizes on submission
- Same BeautifulSoup parsing works

### 4. Group Assignments
- Assignments support group submissions
- Need to handle `group_comment` parameter
- New Quizzes don't have this complexity

---

## Recommended Approach

1. **Start with grader_a_assignments.py**
   - Focus on data retrieval differences
   - Reuse all OpenAI/grading logic
   - Test thoroughly with sample assignment

2. **Then create grader_b_assignments.py**
   - Copy grader_b_new_quizzes.py
   - Update titles/warnings
   - Minimal testing needed (same API)

3. **Future enhancement: Refactor for code sharing**
   - Extract common grading logic
   - Create base class or utility functions
   - Both graders inherit/use shared code

---

## Questions to Resolve

1. **Do we want to support mixed submission types?**
   - Assignment with both text entry AND file upload
   - Grade only the text portion?

2. **Should we filter out group assignments?**
   - More complex grading logic
   - Or handle with `comment[group_comment]=true`?

3. **Should Part B graders be unified?**
   - One grader for both New Quizzes and Assignments?
   - User selects mode at runtime?

---

## Next Steps

When ready to implement TODO #3:

1. Read this document
2. Review `API_COMPARISON_assignments_vs_new_quizzes.md` for API details
3. Start with `grader_a_assignments.py`
4. Copy and adapt from `grader_a_new_quizzes.py`
5. Test with a real Canvas course
6. Create `grader_b_assignments.py` (quick copy/modify)
7. Update `currentTODOlist.md` when complete

---

## Final Verdict

**TODO #3 is NOT "MAJOR WORK"** - it's **MODERATE WORK** with most effort in Part A data retrieval. Part B is nearly free. The assignment version is actually simpler than New Quizzes due to direct API access instead of report-based workflow.

Estimated implementation time: **4-6 hours** for both graders (not days).

---

**End of conclusions**
