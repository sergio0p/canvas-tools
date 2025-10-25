# Quick Start Guide: Generic Grader B

## For Your Decoy Effect Question

Since you want simple override (just enter grade and feedback manually), here's what to do:

### Step 1: Run Part A (As Before)
```bash
python essay_grader_a.py
```
- Select course, assignment, question
- Provide grading instructions (from `grading_instructions_decoy.md`)
- Let AI grade all submissions
- Creates `essays_XXXXX.json` file

### Step 2: Run Part B (New Generic Version)
```bash
python grader_b_generic.py
```

### Step 3: Select Grading Results
- Choose the `essays_XXXXX.json` file from Part A

### Step 4: Choose Menu Mode
When asked "Use menu configuration? (y/n)":
- **Type 'n'** for manual entry mode
- This skips the menu entirely

### Step 5: Review Each Submission
For each student, you'll see:
- Student name
- Their answer
- AI grade and feedback
- Old/new scores

Then choose:
- **(v)alidate**: Upload AI grade as-is → Done, next student
- **(o)verride**: Enter your own grade and feedback
  1. Enter grade (e.g., 3 or 4)
  2. Type feedback (press Enter twice when done)
  3. Preview appears
  4. Type 'y' to confirm and post to Canvas
- **(s)kip**: Skip this student for now
- **(q)uit**: Exit (can resume later)

## Example Override Flow

```
(v)alidate | (o)verride | (s)kip | (q)uit: o

Enter new grade (0-4): 3

================================================================================
ENTER FEEDBACK
================================================================================
Enter feedback for the student (press Enter twice when done):

Your analysis shows inconsistency: you stated there is no decoy effect
but then identified 512GB as a decoy in your answer.
[press Enter]
[press Enter again]

================================================================================
PREVIEW OF NEW GRADE
================================================================================
Total Score: 3/4

Feedback Comment #1:
--------------------------------------------------------------------------------
Your analysis shows inconsistency: you stated there is no decoy effect
but then identified 512GB as a decoy in your answer.
--------------------------------------------------------------------------------

New total quiz grade: X.X

Post these grades and comments to Canvas? (y/n): y

📤 Uploading override grade to Canvas...
✅ Uploaded override grade for Student Name
```

## Key Points

✅ **Confirmation required**: You must type 'y' before posting to Canvas
✅ **No menus needed**: Just type your feedback freely
✅ **Can't undo**: Once posted to Canvas, you can't unpublish (but you can add more comments)
✅ **Progress saved**: JSON file updates after each upload
✅ **Can resume**: If you quit, run Part B again to continue

## What About Menu Mode?

If you ever want to use menus (like for the Lagrangian question):
- Answer 'y' when asked "Use menu configuration?"
- Select a `menu_*.json` file
- Override workflow will show predefined feedback options

But for the decoy question, **just use 'n' for manual entry mode**.
