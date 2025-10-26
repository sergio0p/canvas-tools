# Implementation Plan: HTML Display for Student Submissions
## Issue (I) - Claude Coding Plan

---

## 🎯 Objective

Modify `grader_b_text_assignments.py` to display student submissions as HTML in browser with two-column layout (User Answers vs Correct Answers) instead of terminal JSON.

---

## 📋 Prerequisites & Setup

### Before Starting:
- ✅ Issue (II) already completed (point values fixed)
- ✅ Have `grader_b_text_assignments.py` 
- ✅ Have `grading_config_economics.json`
- ✅ Need sample student submission JSON to test with

### Files We'll Work With:
1. **Input:** `/mnt/user-data/uploads/grader_b_text_assignments.py` (read-only)
2. **Input:** `/mnt/user-data/outputs/grading_config_economics.json` (correct answers source)
3. **Output:** `/home/claude/grader_b_text_assignments.py` (modified version)
4. **Output:** `/mnt/user-data/outputs/grader_b_text_assignments.py` (final deliverable)

---

## 🏗️ Implementation Plan - 6 Phases

---

## **PHASE 1: Create Correct Answers Data Structure** ⏱️ 15 min

### Goal: 
Extract or hard-code correct answers in easily accessible format

### Decision Point:
**Option A:** Hard-code correct answers in script (FASTER, less flexible)
**Option B:** Parse from grading_config_economics.json (CLEANER, more flexible)

**Recommendation:** Start with Option A for speed, can upgrade to Option B later

### Code to Add:
```python
# Near top of file, after imports
CORRECT_ANSWERS_ECONOMICS = {
    'part1': {
        'title': "Part 1: Antonia's Baskets (0.6 points)",
        'answers': {
            'A0': '(20, 0)',
            'A1': '(22, 4)',
            'A2': '(15, 0)'
        }
    },
    'part2': {
        'title': "Part 2: Marie's Baskets (0.6 points)",
        'answers': {
            'M0': '(10, 10)',
            'M1': '(3, 13.5)',
            'M2': '(13.5, 3)'
        }
    },
    'part3': {
        'title': "Part 3: Colored Tables (2.8 points)",
        'answers': {
            'table1': {
                'name': 'Table 1 - Directly revealed (Antonia)',
                'entries': ['A0 ≥DR A2', 'A1 ≥DR A0', 'A1 ≥DR A2']
            },
            'table2': {
                'name': 'Table 2 - Strict revealed (Antonia)',
                'entries': ['A0 >SDR A2', 'A1 >SDR A0', 'A1 >SDR A2']
            },
            'table3': {
                'name': 'Table 3 - Directly revealed (Marie)',
                'entries': ['M0 ≥DR M1', 'M0 ≥DR M2', 'M1 ≥DR M0', 
                           'M1 ≥DR M2', 'M2 ≥DR M0', 'M2 ≥DR M1']
            },
            'table4': {
                'name': 'Table 4 - Strict revealed (Marie)',
                'entries': ['M0 >SDR M1', 'M0 >SDR M2', 'M1 >SDR M2', 'M2 >SDR M1']
            }
        }
    }
}
```

### Testing:
- Print the data structure to verify it's correct
- Confirm special characters (≥, >) display properly

### Success Criteria:
✅ Data structure created and accessible
✅ Matches correct answers from grading config

---

## **PHASE 2: Create JSON Parser Functions** ⏱️ 45 min

### Goal:
Extract user's answers from student submission JSON

### Functions to Create:

#### Function 1: Parse Baskets (Parts 1 & 2)
```python
def parse_baskets(essay_text: str) -> dict:
    """
    Extract basket values from student submission JSON.
    
    Returns:
        {
            'part1': {'A0': '(20, 0)', 'A1': '(22, 4)', 'A2': '(15, 0)'},
            'part2': {'M0': '(10, 10)', 'M1': '(3, 13.5)', 'M2': '(13.5, 3)'},
            'error': None or error message
        }
    """
    try:
        data = json.loads(essay_text)
        
        # Look for basket patterns in content
        # Search for text containing "A0 =", "A1 =", etc.
        # Extract the values
        
        result = {
            'part1': {},
            'part2': {},
            'error': None
        }
        
        # TODO: Implement parsing logic
        
        return result
    except Exception as e:
        return {'part1': {}, 'part2': {}, 'error': str(e)}
```

#### Function 2: Parse Blue Entries (Part 3)
```python
def parse_blue_entries(essay_text: str) -> dict:
    """
    Extract blue entries from student submission JSON.
    
    Returns:
        {
            'table1': ['A0 ≥DR A2', ...],
            'table2': [...],
            'table3': [...],
            'table4': [...],
            'error': None or error message
        }
    """
    try:
        data = json.loads(essay_text)
        
        # Look in data['content'] for tables
        # Each table has 'blue_entries' field
        
        result = {
            'table1': [],
            'table2': [],
            'table3': [],
            'table4': [],
            'error': None
        }
        
        # TODO: Implement parsing logic
        
        return result
    except Exception as e:
        return {'table1': [], 'table2': [], 'table3': [], 'table4': [], 'error': str(e)}
```

#### Function 3: Main Parser Wrapper
```python
def parse_student_submission(essay_text: str) -> dict:
    """
    Parse complete student submission.
    
    Returns:
        {
            'part1': {...},
            'part2': {...},
            'part3': {...},
            'is_json': True/False,
            'parse_error': None or error message
        }
    """
    try:
        json.loads(essay_text)
        is_json = True
    except:
        is_json = False
        return {'is_json': False, 'parse_error': 'Not JSON format'}
    
    baskets = parse_baskets(essay_text)
    blue_entries = parse_blue_entries(essay_text)
    
    return {
        'is_json': True,
        'part1': baskets['part1'],
        'part2': baskets['part2'],
        'part3': blue_entries,
        'parse_error': baskets['error'] or blue_entries['error']
    }
```

### Testing Strategy:
1. Create sample student JSON (based on actual format)
2. Test parser with perfect submission
3. Test parser with partial submission (missing values)
4. Test parser with malformed JSON
5. Verify error handling

### Success Criteria:
✅ Can extract all Part 1 baskets (A0, A1, A2)
✅ Can extract all Part 2 baskets (M0, M1, M2)
✅ Can extract all Part 3 blue entries from 4 tables
✅ Handles missing values gracefully
✅ Returns clear error messages

---

## **PHASE 3: Create HTML Generator Function** ⏱️ 45 min

### Goal:
Generate beautiful HTML comparison page

### Function to Create:
```python
def generate_comparison_html(user_answers: dict, correct_answers: dict, 
                             result: GradingResult) -> str:
    """
    Generate HTML page with side-by-side comparison.
    
    Args:
        user_answers: Parsed student answers
        correct_answers: Correct answers (CORRECT_ANSWERS_ECONOMICS)
        result: GradingResult object with metadata
    
    Returns:
        Complete HTML string
    """
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Grading Review: {student_name}</title>
        <style>
            /* CSS styling here */
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Grading Review</h1>
            <div class="student-info">
                <p><strong>Student:</strong> {student_name}</p>
                <p><strong>Old Grade:</strong> {old_grade} | 
                   <strong>AI Grade:</strong> {ai_grade} | 
                   <strong>New Grade:</strong> {new_grade}</p>
            </div>
        </div>
        
        <div class="container">
            <div class="column user-column">
                <h2>👤 User's Answers</h2>
                {user_content}
            </div>
            
            <div class="column correct-column">
                <h2>✅ Correct Answers</h2>
                {correct_content}
            </div>
        </div>
        
        <div class="footer">
            <p>Return to terminal to (v)alidate, (o)verride, or (s)kip this submission.</p>
        </div>
    </body>
    </html>
    """
    
    # TODO: Build user_content HTML
    # TODO: Build correct_content HTML
    # TODO: Format and return
    
    return html
```

### HTML Structure Design:

```html
<div class="container">
    <div class="column user-column">
        <!-- PART 1 -->
        <div class="part">
            <h3>Part 1: Antonia's Baskets</h3>
            <table>
                <tr>
                    <td>A0</td>
                    <td class="correct">(20, 0) ✓</td>
                </tr>
                <tr>
                    <td>A1</td>
                    <td class="correct">(22, 4) ✓</td>
                </tr>
                <tr>
                    <td>A2</td>
                    <td class="incorrect">(10, 5) ✗</td>
                </tr>
            </table>
        </div>
        
        <!-- PART 2 - Similar structure -->
        
        <!-- PART 3 -->
        <div class="part">
            <h3>Part 3: Colored Tables</h3>
            <h4>Table 1 - Direct Revealed (2/3)</h4>
            <ul>
                <li class="correct">A0 ≥DR A2 ✓</li>
                <li class="correct">A1 ≥DR A0 ✓</li>
                <li class="missing">A1 ≥DR A2 (missing)</li>
            </ul>
            <!-- Tables 2, 3, 4... -->
        </div>
    </div>
    
    <div class="column correct-column">
        <!-- Mirror structure with correct answers -->
    </div>
</div>
```

### CSS Styling:
```css
body {
    font-family: 'Segoe UI', Arial, sans-serif;
    margin: 0;
    padding: 20px;
    background: #f5f5f5;
}

.header {
    background: white;
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    margin-bottom: 20px;
}

.container {
    display: flex;
    gap: 20px;
}

.column {
    flex: 1;
    background: white;
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.user-column {
    border-left: 4px solid #2196F3;
}

.correct-column {
    border-left: 4px solid #4CAF50;
}

.part {
    margin-bottom: 30px;
}

.correct {
    color: #4CAF50;
    font-weight: bold;
}

.incorrect {
    color: #f44336;
    font-weight: bold;
}

.missing {
    color: #FF9800;
    font-style: italic;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 10px;
}

td {
    padding: 8px;
    border-bottom: 1px solid #eee;
}

ul {
    list-style: none;
    padding-left: 0;
}

li {
    padding: 5px 0;
}
```

### Testing:
1. Generate HTML with sample data
2. Save to file and open in browser
3. Check responsiveness (resize window)
4. Test special characters display (≥, >)
5. Verify color coding works

### Success Criteria:
✅ HTML renders correctly in browser
✅ Two columns display side by side
✅ Correct/incorrect answers color-coded
✅ Special characters display properly
✅ Responsive design (works on different screen sizes)

---

## **PHASE 4: Create Browser Display Function** ⏱️ 20 min

### Goal:
Open HTML in browser automatically

### Function to Create:
```python
import tempfile
import webbrowser
import os

def display_submission_in_browser(result: GradingResult) -> Optional[str]:
    """
    Generate HTML comparison and open in browser.
    
    Args:
        result: GradingResult object
    
    Returns:
        Path to temp HTML file, or None if failed
    """
    try:
        # Parse student submission
        user_answers = parse_student_submission(result.essay_text)
        
        if not user_answers['is_json']:
            return None
        
        # Get correct answers
        correct_answers = CORRECT_ANSWERS_ECONOMICS
        
        # Generate HTML
        html_content = generate_comparison_html(user_answers, correct_answers, result)
        
        # Create temp file
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, f'grading_review_{result.student_id}.html')
        
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Open in browser
        webbrowser.open(f'file://{temp_file}')
        
        return temp_file
    
    except Exception as e:
        print(f"  ⚠️  Error generating HTML: {e}")
        return None
```

### Testing:
1. Call function with test GradingResult
2. Verify browser opens automatically
3. Verify HTML displays correctly
4. Check temp file location
5. Test error handling (bad JSON, etc.)

### Success Criteria:
✅ HTML file created in temp directory
✅ Browser opens automatically
✅ File path returned for cleanup
✅ Graceful error handling

---

## **PHASE 5: Modify Main Display Function** ⏱️ 20 min

### Goal:
Integrate HTML display into existing workflow

### Original Function (lines 239-258):
```python
def display_submission_for_review(result: GradingResult, index: int, total: int) -> None:
    """Display a student submission for review"""
    print("\n" + "=" * 100)
    print(f"SUBMISSION {index}/{total}")
    print("=" * 100)
    print(f"Student: {result.student_name}")
    print(f"Old grade: {result.old_assignment_grade}")
    print("\n" + "-" * 100)
    print("STUDENT ANSWER:")
    print("-" * 100)
    print(result.essay_text)  # <-- This is what we're replacing
    print("-" * 100)
    print("\n" + "-" * 100)
    print("AI GRADING:")
    print("-" * 100)
    print(f"AI Grade: {result.ai_grade}")
    print(f"New grade: {result.new_assignment_grade}")
    print(f"\nAI Feedback:")
    print(result.ai_feedback)
    print("-" * 100)
```

### Modified Function:
```python
def display_submission_for_review(result: GradingResult, index: int, total: int) -> None:
    """Display a student submission for review"""
    print("\n" + "=" * 100)
    print(f"SUBMISSION {index}/{total}")
    print("=" * 100)
    print(f"Student: {result.student_name}")
    print(f"Old grade: {result.old_assignment_grade}")
    
    # Try to display as HTML in browser
    temp_html_file = None
    try:
        json.loads(result.essay_text)
        is_json = True
    except:
        is_json = False
    
    if is_json:
        print("\n  🌐 Opening comparison in browser...")
        temp_html_file = display_submission_in_browser(result)
        
        if temp_html_file:
            print(f"  ✅ Review the comparison in your browser")
            print(f"  📄 HTML file: {temp_html_file}")
        else:
            print(f"  ⚠️  Could not generate HTML, showing text instead")
            is_json = False
    
    # Fallback: display in terminal if not JSON or HTML generation failed
    if not is_json or temp_html_file is None:
        print("\n" + "-" * 100)
        print("STUDENT ANSWER:")
        print("-" * 100)
        print(result.essay_text)
        print("-" * 100)
    
    # Always show AI grading in terminal
    print("\n" + "-" * 100)
    print("AI GRADING:")
    print("-" * 100)
    print(f"AI Grade: {result.ai_grade}")
    print(f"New grade: {result.new_assignment_grade}")
    print(f"\nAI Feedback:")
    print(result.ai_feedback)
    print("-" * 100)
```

### Testing:
1. Test with JSON submission (should open browser)
2. Test with non-JSON submission (should show terminal text)
3. Test with malformed JSON (should fallback to terminal)
4. Verify terminal display still works
5. Check that workflow continues normally

### Success Criteria:
✅ JSON submissions open in browser
✅ Non-JSON submissions show in terminal
✅ Error cases fallback gracefully
✅ Terminal still shows AI grading info
✅ User can proceed to validate/override/skip

---

## **PHASE 6: Testing & Polish** ⏱️ 30 min

### Goal:
Comprehensive testing and cleanup

### Test Cases:

#### Test 1: Perfect Submission
```json
{
  "content": [
    {"type": "text", "text": "A0 = (20, 0)"},
    {"type": "text", "text": "A1 = (22, 4)"},
    {"type": "text", "text": "A2 = (15, 0)"},
    {"type": "text", "text": "M0 = (10, 10)"},
    {"type": "text", "text": "M1 = (3, 13.5)"},
    {"type": "text", "text": "M2 = (13.5, 3)"},
    {
      "type": "table",
      "blue_entries": ["A0 ≥DR A2", "A1 ≥DR A0", "A1 ≥DR A2"]
    }
  ]
}
```

#### Test 2: Partial Submission
- Missing A2
- Missing some blue entries
- Verify it doesn't crash

#### Test 3: Incorrect Answers
- Wrong basket values
- Verify colors show incorrect (red)

#### Test 4: Non-JSON Submission
- Plain text essay
- Should fallback to terminal display

#### Test 5: Malformed JSON
- Invalid JSON syntax
- Should fallback gracefully

### Polish Items:
1. Add cleanup function for temp HTML files
2. Add better error messages
3. Improve HTML styling
4. Add print statement tips ("Review in browser, then return here")
5. Handle edge cases (empty submissions, missing parts)

### Success Criteria:
✅ All test cases pass
✅ No crashes on edge cases
✅ Clean error messages
✅ Professional HTML appearance
✅ Smooth user experience

---

## 📦 Deliverables

### Final Files to Provide:
1. **Modified Script:** `grader_b_text_assignments.py`
   - All new functions added
   - Main display function modified
   - Fully tested

2. **Test Sample:** Sample student JSON for testing

3. **Documentation:** 
   - How to use the new feature
   - What to do if browser doesn't open
   - How to cleanup temp files

4. **Summary:** What changed, what to test

---

## ⏱️ Timeline Summary

| Phase | Duration | Description |
|-------|----------|-------------|
| Phase 1 | 15 min | Create correct answers data |
| Phase 2 | 45 min | JSON parsing functions |
| Phase 3 | 45 min | HTML generation |
| Phase 4 | 20 min | Browser display function |
| Phase 5 | 20 min | Integrate into main flow |
| Phase 6 | 30 min | Testing & polish |
| **TOTAL** | **~2.5 hours** | Claude coding time |

**Your testing time:** +30-60 min with real data

---

## 🚦 Decision Points

Before starting, please confirm:

1. ✅ Should correct answers be hard-coded (faster) or parsed from config (cleaner)?
   - **Recommendation:** Hard-code for now

2. ✅ Should we create temp HTML files or use a persistent location?
   - **Recommendation:** Temp files (auto-cleanup)

3. ✅ What should happen if browser doesn't auto-open?
   - **Recommendation:** Print file path for manual opening

4. ✅ Should we keep terminal display as fallback for non-JSON?
   - **Recommendation:** Yes, definitely

---

## 🎯 Success Metrics

After implementation:
- ✅ JSON submissions display in browser (2-column HTML)
- ✅ Non-JSON submissions still work (terminal display)
- ✅ All existing functionality preserved
- ✅ No new dependencies required
- ✅ Works on Mac/Linux/Windows
- ✅ User can validate/override/skip as before

---

## 📝 Notes for Human Testing

When you test the modified script:

1. **First test:** Use the sample JSON provided
2. **Second test:** Try with real Canvas data
3. **Check:** Does browser open automatically?
4. **Check:** Can you see user vs correct answers?
5. **Check:** Can you still validate/override/skip?
6. **Report:** Any errors, weird behavior, or suggestions

---

## 🚀 Ready to Start?

This plan provides:
- ✅ Clear phases with time estimates
- ✅ Specific functions to create
- ✅ Testing strategy for each phase
- ✅ Success criteria
- ✅ Fallback plans for errors

**If you approve this plan, Claude will implement it phase by phase, showing you progress after each phase.**

Shall we proceed? 🎯
