# Categorization Grader

Interactive CLI tool for applying partial credit to Canvas New Quizzes categorization questions.

## Overview

Canvas New Quizzes categorization questions are typically graded as all-or-nothing. This tool implements a custom partial grading algorithm that awards credit for correct placements while penalizing misclassifications.

## Features

- **Partial Credit Grading**: Awards points based on correct placements minus penalties for misclassifications
- **True Distractor Support**: Correctly identifies items that shouldn't be categorized
- **Batch Processing**: Grade all student submissions with a single approval
- **Detailed Feedback**: Automatically adds grading breakdown to student comments
- **Safe Preview**: Review all grade changes before applying them

## Grading Algorithm

```
score = (correct - 0.5 * misclassified) / total * points_possible
```

Where:
- `correct` = items placed in correct categories
- `misclassified` = items placed in wrong categories
- `total` = total items that should be categorized (excludes true distractors)
- `points_possible` = max points for the question

**Example**: 15 total items, 14 correct, 1 misclassified, 2 points possible
- Score: (14 - 0.5 × 1) / 15 × 2.0 = **1.8 points**

## Scoring Rules

1. **Correct placement**: Item in right category → +1 correct
2. **Wrong placement**: Item in wrong category → +1 misclassified
3. **Not placed**: Item left unplaced → no penalty, loses point (not misclassified)
4. **True distractor placed**: Distractor placed anywhere → +1 misclassified
5. **True distractor unplaced**: Distractor left alone → correct behavior (no penalty)

## Usage

```bash
python3 categorization_grader.py
```

### Workflow

1. **Select Course**: Choose from your favorited courses
2. **Select Assignment**: Pick a New Quizzes assignment
3. **Select Question**: Choose a categorization question to grade
4. **Review Results**: See table of proposed grade changes
5. **Approve/Reject**: Apply all changes or cancel

### Preview Table

```
Student Name      | Current Grade | New Grade | Correct | Misclassified
John Smith        | 0.0          | 1.8       | 14      | 1
Jane Doe          | 2.0          | 2.0       | 15      | 0
```

## Student Feedback

The tool automatically adds a comment to each student submission:

```
New score for [Question Title]: old score = 0.0, new score = 1.8
Correct = 14, Misclassified = 1
Grading formula: (correct - 0.5 * misclassified) / total * points_possible
```

## Technical Details

- Uses Canvas API and New Quizzes API
- Generates student_analysis reports to extract responses
- Updates quiz total grades (Canvas API limitation prevents updating individual question scores)
- Skips students without submissions
- Preserves existing assignment comments

## Related Documentation

- [Workflow Documentation](../categorization_grader_workflow.md) - Detailed user interaction flow
- [Technical Specification](../categorization_grader_spec.md) - API endpoints and data structures

## Requirements

- Canvas API access token (stored in system keychain)
- Python packages: `requests`, `keyring`
