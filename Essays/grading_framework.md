# Essay Grading Framework: Best Practices Guide

## Overview

This guide establishes the framework for creating two essential files for automated essay grading:
1. **AI Grading Instructions** (`openai_grading_instructions.md`) - For automated AI grading
2. **Manual Override Menu** (`grading_feedback_menu.md`) - For human override interface

Both files must work together seamlessly while serving different purposes.

**Key Design Principle:** Model answers are ALWAYS posted as a separate comment (second timestamp) by the script, not included in individual feedback. This simplifies both AI instructions and manual override menus while ensuring every student sees model answers.

---

## Part 1: AI Grading Instructions File

### Purpose
Direct the AI to grade essays consistently and provide structured feedback that matches your manual override options.

### Core Principles

#### 1. **Simplicity Over Complexity**
- ✅ Keep instructions concise and direct
- ✅ Use clear, actionable criteria
- ❌ Avoid complex normalization rules
- ❌ Don't over-specify formatting details
- **Why:** Simpler instructions = more consistent AI performance (we proved this: 0% vs 70-100% failure rate)

#### 2. **Structure by Parts**
- Divide the essay into clear, independent parts (e.g., Part 1, Part 2, Part 3)
- Each part should have:
  - Point value (clear maximum)
  - Specific grading criteria
  - Possible scores (e.g., 0, 0.5, 1)
  - Error categories if score < maximum

#### 3. **Output Format**
Always specify JSON output with exactly two fields:
```json
{
  "grade": <number>,
  "feedback": "<string with Part 1 and Part 2 sections>"
}
```

**CRITICAL: Do NOT include model answers in feedback.** Model answers are posted separately by the script as a second comment. This:
- Simplifies AI logic (no conditional model answer formatting)
- Improves AI grading accuracy (AI knows model answers for grading, doesn't format them)
- Ensures consistency (every student sees model answers the same way)

#### 4. **Feedback Structure Template**
```
Part 1: X/Y
[If incorrect: brief reason]

Part 2: X/Y  
[If incorrect: brief reason]
```

**Note:** No model answers in this feedback string.

### File Structure Template

```markdown
# Grading Instructions for [Essay Topic]

## The Problem
[State the essay question/problem clearly]

## Model Answers

### Part 1: [Part Name]
[Complete model answer for Part 1]

### Part 2: [Part Name]  
[Complete model answer for Part 2]

**Note:** These model answers are for your reference during grading. Do NOT include them in your feedback response. The script will post them separately.

## Grading Criteria

### Part 1: [Part Name] (X points)

**Award X points if:**
- [Criterion 1]
- [Criterion 2]

**Award 0 points if:**
- [Error type 1]
- [Error type 2]

### Part 2: [Part Name] (Y points)

**Award Y points if student [does all four things]:**
1. [Required element 1]
2. [Required element 2]
3. [Required element 3]
4. [Required element 4]

**Award 0 points if:**
- [Missing elements or error types]

## Output Format

Return ONLY a JSON object:
```json
{
  "grade": <total score 0.0 to Z.0>,
  "feedback": "<multi-line string>"
}
```

### Feedback Format

**For Part X:**
- If correct: Just say "Part X: X/X"
- If incorrect: Say "Part X: 0/X — [brief reason]"

**For Part Y:**
- If correct: Just say "Part Y: Y/Y"  
- If incorrect: Say "Part Y: 0/Y — [brief reason]"

Keep feedback concise. **Do not include model answers in the feedback.**

## Examples

[Provide 2-3 complete examples showing student answers and expected JSON responses]
```

### Critical Dos and Don'ts

**DO:**
- ✅ Use direct, imperative language ("Award 1 point if...", "Return ONLY JSON")
- ✅ Provide 2-3 complete examples with actual student text and expected outputs
- ✅ Keep error categories to 2-3 per part maximum
- ✅ Make criteria binary when possible (correct/incorrect, not partially correct)
- ✅ Specify exact feedback wording for consistency
- ✅ Include model answers at the TOP for AI reference (but not in feedback output)

**DON'T:**
- ❌ Include complex normalization rules (let AI handle variations naturally)
- ❌ Over-specify formatting (markdown, bullets, etc.)
- ❌ Create more than 4-5 parts (cognitive overload)
- ❌ Use subjective criteria ("good", "poor", "adequate")
- ❌ Write long explanations about grading theory
- ❌ Tell AI to include model answers in feedback (script handles this separately)

---

## Part 2: Manual Override Menu File

### Purpose
Provide structured menu options for human graders to quickly override AI decisions with consistent feedback.

### Core Principles

#### 1. **Menu-Driven Structure**
- Every feedback option must be a selectable menu item
- Use flat structure - no conditionals based on score
- User always selects from ALL options for each part

#### 2. **Match AI Feedback Categories**
- Error categories must exactly match those in AI instructions
- This ensures consistency whether graded by AI or human

#### 3. **Separate Model Answers**
- Model answers are NOT in individual menu options
- Model answers are posted as a separate second comment by the script
- Include a "Model Answers" section showing what will be auto-posted

#### 4. **Simplified Workflow**
User enters grade → Select Part 1 feedback → Select Part 2 feedback → Done
(No conditionals, no logic about which menus to show)

### File Structure Template

```markdown
# Manual Override Feedback Menu for [Essay Topic]

---

## Part 1: [Part Name]

**Select ONE feedback option:**

1. **Correct**
   ```
   Part 1: X/X
   ```

2. **[Error Type 1]**
   ```
   Part 1: 0/X — [Error description 1]
   ```

3. **[Error Type 2]**
   ```
   Part 1: 0/X — [Error description 2]
   ```

---

## Part 2: [Part Name]

**Select ONE feedback option:**

1. **Correct**
   ```
   Part 2: Y/Y
   ```

2. **[Error Type 1]** (partial credit if applicable)
   ```
   Part 2: Z/Y — [Error description 1]
   ```

3. **[Error Type 2]**
   ```
   Part 2: 0/Y — [Error description 2]
   ```

---

## Model Answers (Posted Separately as Second Comment)

**This text will be automatically posted as a separate comment after grading feedback:**

```
MODEL ANSWERS:

Part 1: [Part Name]
[Complete model answer]

Part 2: [Part Name]
[Complete model answer with all steps]
```

---

## Quick Reference: Total Grade to Part Scores

[Helpful mapping of total grades to part breakdowns]

---

## Usage Notes for Script Implementation

**Workflow:**
1. Get total grade from user (0-Z)
2. Show Part 1 menu → user selects option (1-N)
3. Show Part 2 menu → user selects option (1-M)
4. Post feedback as Comment #1
5. Automatically post model answers as Comment #2
```

### Critical Design Rules

**DO:**
- ✅ Number every menu option (1, 2, 3...)
- ✅ Show exact feedback text that will be posted
- ✅ Use flat structure - all options visible, no conditionals
- ✅ Include "Correct" as first option for each part
- ✅ Show model answers in separate section (auto-posted by script)
- ✅ Provide "Quick Reference" section for total grade mapping

**DON'T:**
- ❌ Make users type feedback from scratch
- ❌ Create more than 5 options per menu (decision paralysis)
- ❌ Use ambiguous option names
- ❌ Hide the actual feedback text users will post
- ❌ Include model answers in individual feedback options
- ❌ Create conditional menus based on scores

---

## Part 3: Ensuring Consistency Between Files

### The Golden Rule
**Every error category in the AI instructions MUST have a corresponding menu item in the override file.**

### Consistency Checklist

Before finalizing, verify:

- [ ] Part names and point values match exactly
- [ ] Error categories are identical (same wording)
- [ ] Feedback format is consistent (but no model answers in AI feedback)
- [ ] Number of parts matches
- [ ] Score options match (0, 0.5, 1, etc.)
- [ ] Model answers are identical in both files
- [ ] AI instructions say "Do not include model answers in feedback"
- [ ] Override menu has separate "Model Answers" section

### Testing Process

1. **Test AI Instructions:**
   - Grade 5-10 sample student answers with temp=1.0
   - Check for "No feedback provided" (should be 0%)
   - Verify feedback follows the expected format
   - Confirm error categories appear as specified

2. **Test Override Menu:**
   - Manually walk through each menu path
   - Ensure every score/error combination is covered
   - Verify feedback generation produces clean output
   - Check that model answers display correctly

3. **Cross-Check Consistency:**
   - Compare AI feedback to menu feedback for same errors
   - Confirm wording matches exactly
   - Ensure both produce valid Canvas comments

---

## Part 4: Common Patterns by Essay Type

### Pattern A: Multi-Part Mathematical Problem
**Structure:** 2-4 parts, each with clear right/wrong answer
**Example:** Lagrangian optimization, proofs, derivations

**AI Instructions Focus:**
- Binary scoring (correct/incorrect)
- Check for required mathematical elements
- Allow notation variations

**Override Menu Focus:**
- Error types: missing terms, wrong signs, incomplete steps
- Include model answer for each part

---

### Pattern B: Conceptual Explanation
**Structure:** 2-3 parts evaluating understanding
**Example:** "Explain X concept", "Why does Y happen?"

**AI Instructions Focus:**
- Key concepts that must be mentioned
- Depth of explanation (surface vs detailed)
- Logical flow

**Override Menu Focus:**
- Missing concepts
- Incorrect reasoning
- Incomplete explanation

---

### Pattern C: Multi-Step Procedure
**Structure:** Sequential steps that build on each other
**Example:** "Describe the steps to solve...", "Outline the method for..."

**AI Instructions Focus:**
- All required steps present
- Steps in logical order
- Key variables/elements mentioned

**Override Menu Focus:**
- Missing steps
- Wrong sequence
- Incomplete descriptions

---

## Part 5: File Naming and Organization

### Standard File Names
```
openai_grading_instructions_[topic].md    # AI instructions
grading_feedback_menu_[topic].md          # Override menu
```

### Version Control
When updating rubrics mid-semester:
```
openai_grading_instructions_[topic]_v2.md
grading_feedback_menu_[topic]_v2.md
```

Keep old versions for reference and consistency checking.

---

## Part 6: Quick Start Checklist

When setting up grading for a new essay:

### Step 1: Design the Rubric
- [ ] Divide essay into 2-4 clear parts
- [ ] Assign point values to each part
- [ ] List 2-3 error types per part
- [ ] Decide on model answer (if applicable)

### Step 2: Write AI Instructions
- [ ] Use the template above
- [ ] Keep it simple (< 200 lines)
- [ ] Include 2-3 examples
- [ ] Specify JSON output format

### Step 3: Write Override Menu
- [ ] Use the template above
- [ ] Number all menu options
- [ ] Show exact feedback text
- [ ] Include quick reference section

### Step 4: Test Everything
- [ ] Test AI on 10 sample essays
- [ ] Check consistency (0% "No feedback provided")
- [ ] Walk through all override menu paths
- [ ] Verify AI and menu produce identical error messages

### Step 5: Production Use
- [ ] Run Part AA (model testing) on 10 students
- [ ] Compare results across models
- [ ] Select best model
- [ ] Grade full class with Part A
- [ ] Review and override with Part B (which auto-posts model answers) model
- [ ] Grade full class with Part A
- [ ] Review and override with Part B

---

## Part 7: Troubleshooting Guide

### Problem: High "No Feedback Provided" Rate
**Solution:** Instructions too complex. Simplify by:
- Removing normalization rules
- Shortening examples
- Using more direct language
- Reducing number of parts

### Problem: Inconsistent AI Grading
**Solution:** Criteria too subjective. Fix by:
- Making criteria binary (yes/no)
- Adding specific examples
- Reducing judgment calls
- Clarifying ambiguous terms

### Problem: Override Menu Too Complex
**Solution:** Too many options. Simplify by:
- Combining similar error types
- Limiting to 3-4 options per menu
- Adding "Other" catch-all option
- Providing quick reference for common cases

### Problem: AI and Menu Feedback Don't Match
**Solution:** Ensure exact wording matches between files. Model answers should be in both files but only posted by script, not by AI.

### Problem: Students complain they don't see model answers
**Solution:** Verify script is posting model answers as second comment. Check Canvas to confirm both comments appear.

---

## Summary: The Four Keys to Success

1. **Simplicity:** Keep both files simple, direct, and actionable
2. **Consistency:** Match error categories and feedback wording exactly
3. **Separation:** Model answers posted separately by script, not in feedback
4. **Testing:** Always test with real student essays before production use

Following this framework will save hours of trial-and-error and produce reliable, consistent essay grading systems.
