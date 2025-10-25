## TODO LIST

### ✅ 1. Fix Order in Generic Grader A (COMPLETED)
- **Current**: ~~Grading config → Course → Quiz → Question~~
- **Change to**: Course → Quiz → Question → Grading config ✅
- **Reason**: User needs to see the question before knowing which config to use
- **Status**: Implemented in `grader_a_new_quizzes.py`

### ✅ 2. Rename Files and Update Prompts for Clarity (COMPLETED)
- **Rename files**: ✅
  - `grader_a_generic.py` → `grader_a_new_quizzes.py` ✅
  - `grader_b_generic.py` → `grader_b_new_quizzes.py` ✅
- **Update first prompt** in both scripts to clearly state: ✅
  - "CANVAS NEW QUIZZES ONLY - Generic Grader"
  - "This grader works ONLY with Canvas New Quizzes, not regular assignments nor Classical Quizzes"

### 3. Create Assignment Version (MAJOR WORK)
- **New files needed**:
  - `grader_a_assignments.py`
  - `grader_b_assignments.py`
- **Major Canvas API changes required**:
  - Different endpoints for regular assignments vs New Quizzes
  - Different submission format (text entry field vs quiz items)
  - Different grading mechanism
  - Different comment/feedback system
  - No "quiz items" concept - just assignment questions with text responses
- **Note**: This is a completely different API structure - basically rewrite most Canvas interactions

---

