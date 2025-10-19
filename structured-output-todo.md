# Structured Output Implementation To-Do List

## Phase 1: Design the Configuration System

### Create Question Configuration File (Per Question)
Each question gets its own config file (e.g., `question_lagrangian_config.json`):

```json
{
  "question_id": "lagrangian_constrained_opt",
  "question_title": "Constrained Optimization - Lagrangian",
  "total_points": 2.0,
  "parts": [
    {
      "part_number": 1,
      "part_name": "Lagrangian Expression",
      "max_score": 1.0,
      "possible_scores": [0, 1],
      "grading_criteria": {
        "has_correct_objective": {
          "type": "boolean",
          "label": "Correct objective function (xy - x² + log(y))"
        },
        "has_correct_constraint": {
          "type": "boolean", 
          "label": "Correct constraint (x + 3y - 100)"
        },
        "has_correct_sign": {
          "type": "boolean",
          "label": "Correct multiplier sign"
        }
      },
      "error_messages": {
        "objective_wrong": "Objective function incorrect",
        "constraint_wrong": "Constraint incorrect",
        "sign_wrong": "Lagrange multiplier sign incorrect"
      },
      "model_answer": "xy - x² + log(y) - lambda*(x + 3y - 100)",
      "feedback_rules": {
        "if_correct": "Grade: {score}/{max_score}",
        "if_incorrect": "Grade: {score}/{max_score} — {error}\nModel answer: {model_answer}"
      }
    },
    {
      "part_number": 2,
      "part_name": "Solution Procedure",
      "max_score": 1.0,
      "possible_scores": [0, 0.5, 1],
      "grading_criteria": {
        "has_lagrangian": {
          "type": "boolean",
          "label": "Forms/writes the Lagrangian"
        },
        "has_all_derivatives": {
          "type": "boolean",
          "label": "Takes derivatives w.r.t. x, y, AND lambda"
        },
        "sets_to_zero": {
          "type": "boolean",
          "label": "Sets derivatives equal to zero"
        },
        "solves_system": {
          "type": "boolean",
          "label": "Solves the system for x, y, lambda"
        }
      },
      "error_messages": {
        "missing_variable": "Gradient step omits x, y, or multiplier",
        "incomplete_steps": "The recipe steps are missing or incorrect"
      },
      "model_answer": "1. Obtain the Lagrangian\n2. Compute the gradient with respect to x, y, and lambda\n3. Set the gradient equal to zero (first-order conditions, FOCs)\n4. Solve the system of FOCs for x, y, and lambda",
      "feedback_rules": {
        "if_correct": "Grade: {score}/{max_score}\nModel answer:\n{model_answer}",
        "if_partial": "Grade: {score}/{max_score} — {error}\nModel answer:\n{model_answer}",
        "if_incorrect": "Grade: {score}/{max_score} — {error}\nModel answer:\n{model_answer}"
      }
    }
  ],
  "grading_instructions_file": "lagrangian_grading_instructions.md"
}
```

### Why This Architecture?
- **Reusable scripts**: Files A and B work with ANY question config
- **Easy to add new questions**: Just create a new config file
- **No hardcoding**: All question-specific logic in config
- **Schema auto-generated**: From the config file
- **UI menus auto-generated**: From the config file

---

## Phase 2: Update the Grading Prompt

### Simplify Instructions for AI
- [ ] Remove all formatting rules (AI no longer formats feedback)
- [ ] Remove conditional feedback logic (your code handles this)
- [ ] Focus AI instructions on **grading accuracy only**:
  - How to evaluate the Lagrangian components
  - How to evaluate the procedure steps
  - Normalization rules (Mathematica syntax, etc.)
  - When to set each boolean flag

### Key Sections to Keep
- [ ] Normalization rules (ignore Mathematica syntax, accept various lambda notations)
- [ ] Part 1 grading logic (objective, constraint, sign)
- [ ] Part 2 grading logic (4 required steps, must mention x, y, lambda)
- [ ] Examples of correct/incorrect answers

### Key Sections to Remove
- [ ] All "Feedback:" sections
- [ ] Output format instructions
- [ ] Comments string format
- [ ] Examples showing feedback text

---

## Phase 3: Implement OpenAI API Integration

### Update API Call
- [ ] Add `response_format` parameter with JSON schema
- [ ] Set up API request with structured output mode
- [ ] Handle API response parsing

### Example Code Structure
```python
response = openai.chat.completions.create(
    model="gpt-4o-2024-08-06",  # Requires this model or newer
    messages=[
        {"role": "system", "content": grading_instructions},
        {"role": "user", "content": f"Grade this: {student_answer}"}
    ],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "grading_response",
            "schema": your_schema_here
        }
    }
)
```

---

## Phase 4: Build Feedback Generator (Your Code)

### Create Feedback Generation Logic
- [ ] Write function `generate_part1_feedback(part1_data)`
  - If score is 1: return "Grade: 1/1"
  - If score is 0: 
    - Determine what's wrong from boolean flags
    - Return appropriate error message
    - Append model answer

- [ ] Write function `generate_part2_feedback(part2_data)`
  - If score is 1: return grade + model answer
  - If score is 0.5 or 0:
    - Determine what's wrong from boolean flags
    - Return appropriate error message
    - Append model answer

### Feedback Mapping Logic
```python
def generate_part1_feedback(data):
    if data['part1_score'] == 1:
        return "Grade: 1/1"
    
    # Determine specific error
    if not data['part1_has_correct_objective']:
        error = "Objective function incorrect"
    elif not data['part1_has_correct_constraint']:
        error = "Constraint incorrect"
    elif not data['part1_has_correct_sign']:
        error = "Lagrange multiplier sign incorrect"
    else:
        error = "Lagrangian incorrect"
    
    return f"Grade: 0/1 — {error}\nModel answer: xy - x² + log(y) - lambda*(x + 3y - 100)"

def generate_part2_feedback(data):
    model_answer = """Model answer:
1. Obtain the Lagrangian
2. Compute the gradient with respect to x, y, and lambda
3. Set the gradient equal to zero (first-order conditions, FOCs)
4. Solve the system of FOCs for x, y, and lambda"""
    
    if data['part2_score'] == 1:
        return f"Grade: 1/1\n{model_answer}"
    
    # Determine specific error
    if not data['part2_has_all_derivatives']:
        error = "Gradient step omits x, y, or multiplier"
    else:
        error = "The recipe steps are missing or incorrect"
    
    return f"Grade: {data['part2_score']}/1 — {error}\n{model_answer}"

def generate_complete_feedback(grading_data):
    part1 = generate_part1_feedback(grading_data)
    part2 = generate_part2_feedback(grading_data)
    return f"Part 1\n{part1}\n\nPart 2\n{part2}"
```

---

## Phase 5: Testing & Validation

### Test Cases to Verify
- [ ] Test with Joseph Sharpe's answer (missing parentheses)
  - Should get: part1_has_correct_constraint = false
  - Should generate: "Constraint incorrect" feedback

- [ ] Test with Jacob Hoskins' answer (Lagrangian Multiplier notation)
  - Should get: all Part 1 booleans = true
  - Should get: part1_score = 1

- [ ] Test with Anna Lin's answer (Mathematica notation)
  - Should get: all booleans = true for both parts
  - Should get: total score = 2

- [ ] Test with Travis Kimball's answer (perfect)
  - Should get: all booleans = true
  - Should get: total score = 2

### Validation Checks
- [ ] Verify schema compliance (every response matches schema)
- [ ] Verify grading accuracy (scores match expected)
- [ ] Verify feedback quality (students get specific error info)
- [ ] Test edge cases (missing steps, partial answers)

---

## Phase 6: Deployment

### Before Going Live
- [ ] Run on all previous student submissions
- [ ] Compare new grades vs old grades
- [ ] Flag any significant discrepancies for manual review
- [ ] Document the new system for future reference

### Monitoring
- [ ] Track API costs (structured outputs may have different pricing)
- [ ] Monitor grading consistency over time
- [ ] Collect feedback from students about clarity of error messages

---

## Benefits of This Approach

✅ **Guaranteed consistency** - Schema forces same structure every time  
✅ **Detailed feedback preserved** - Students still know exactly what's wrong  
✅ **Your code controls formatting** - No more "conversational" deviations  
✅ **Easier debugging** - Boolean flags make it clear what AI detected  
✅ **Uses your OpenAI tokens** - No need to switch platforms  
✅ **Grading logic separated from formatting** - Easier to maintain  

---

## Potential Issues to Watch

⚠️ **Still relies on OpenAI's judgment** - May still have accuracy issues like Anna Lin case  
⚠️ **Requires gpt-4o-2024-08-06 or newer** - Check model availability  
⚠️ **Schema must be comprehensive** - Need flags for all possible error types  
⚠️ **More complex codebase** - Feedback generation moves to your code  

---

## Alternative: Hybrid Approach

Consider keeping a "confidence" flag in the schema:
```json
{
  "grading_confidence": "high" | "medium" | "low",
  "needs_human_review": boolean,
  "review_reason": "string explaining why unsure"
}
```

This allows you to:
- Auto-grade high-confidence cases
- Flag low-confidence cases for manual review
- Build a database of edge cases over time

Would you like me to add this to the schema design?