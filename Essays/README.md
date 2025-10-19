# Canvas Essay Grading System

AI-powered essay grading for Canvas New Quizzes using OpenAI and Anthropic APIs.

## Overview

This system automates the grading of essay questions in Canvas New Quizzes using AI models (GPT-5, Claude Sonnet 4.5, etc.) with a human-in-the-loop validation workflow.

## Scripts

### Script A: Main Essay Grader (`essay_grader_a.py`)
- **Purpose**: Fetch submissions from Canvas and grade using AI
- **Model**: GPT-5 (temperature=1.0)
- **Output**: JSON file with grading results for review
- **Features**:
  - Parallel grading (5 concurrent requests)
  - Loads grading instructions from file
  - Saves intermediate state for resumability

### Script AA: Model Testing (`essay_grader_aa.py`)
- **Purpose**: Test and compare different AI models
- **Models**: GPT-4o, GPT-5 variants, Claude Sonnet 4.5
- **Features**:
  - Hardcoded grading instructions
  - Student analysis caching (skip Canvas API on reruns)
  - Grades only first 10 students to save tokens
  - Auto-detects API provider (OpenAI vs Anthropic)
  - Temperature control (0.3 for GPT-4/5, 1.0 for Claude)
  - Output: `model_test_{model}_{timestamp}.json`

### Script B: Review & Upload (`essay_grader_b.py`)
- **Purpose**: Review AI grades and upload to Canvas
- **Features**:
  - Menu-driven override system
  - Two-comment workflow:
    - Comment #1: Feedback (AI or manual)
    - Comment #2: Model answers (always posted)
  - Loads feedback menus from `feedback_menu.md`
  - State persistence (resume after interruption)

## Workflow

```
┌─────────────┐
│  Script A   │  Fetch & Grade with AI
│   (or AA)   │  → Saves to JSON
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Script B   │  Review AI Grades
│             │  → Validate or Override
│             │  → Upload to Canvas
└─────────────┘
```

## Setup

### 1. Install Dependencies
```bash
pip3 install --user --break-system-packages openai anthropic keyring requests beautifulsoup4
```

### 2. Store API Keys in macOS Keychain
```bash
# Canvas API token
security add-generic-password -a access-token -s canvas -w 'your_canvas_token'

# OpenAI API key
security add-generic-password -a openai -s openai_api_key -w 'your_openai_key'

# Claude API key (for Script AA)
security add-generic-password -a claude -s claude_api_key -w 'your_claude_key'
```

### 3. Prepare Grading Instructions
- For Script A: Use any markdown file
- For Script AA: Must use `openai_grading_instructions.md`
- For Script B overrides: Must have `feedback_menu.md`

## Usage

### Standard Workflow
```bash
# Step 1: Grade essays with AI
python3 essay_grader_a.py

# Step 2: Review and upload
python3 essay_grader_b.py
```

### Model Testing Workflow
```bash
# Test multiple models on same essays
python3 essay_grader_aa.py  # Select model from menu
python3 essay_grader_aa.py  # Select different model
# Compare model_test_*.json files
```

## Files

### Python Scripts
- `essay_grader_a.py` - Main grading script
- `essay_grader_aa.py` - Model testing script
- `essay_grader_b.py` - Review and upload script
- `essay_grader.py` - Legacy version (deprecated)

### Configuration Files
- `openai_grading_instructions.md` - AI grading rubric
- `feedback_menu.md` - Manual override menu options
- `grading_framework.md` - Grading methodology documentation
- `canvas_new_quizzes_grading_framework.md` - Canvas integration docs
- `canvas_new_quizzes_grading_analysis.md` - Analysis documentation

### Data Files
- `essays_*.json` - Grading results from Script A
- `model_test_*.json` - Model comparison results from Script AA
- `student_analysis_*.json` - Cached Canvas submissions (for AA)
- `*.bak.json` - Automatic backups

## Features

### Student Analysis Caching (Script AA)
- Caches Canvas student submissions to avoid repeated API calls
- Filename: `student_analysis_{course_id}_{assignment_id}_{question_id}.json`
- Automatically reused on subsequent runs
- Enables fast model comparison

### Temperature Control
- **GPT-4, GPT-4o, GPT-5**: temperature=0.3 (more consistent)
- **Claude Sonnet 4.5**: temperature=1.0 (default)
- **GPT-5-pro, o1, o3**: No temperature (not supported)

### API Endpoint Detection
- **Standard models** (GPT-4, GPT-5): `/v1/chat/completions`
- **Reasoning models** (GPT-5-pro, o1, o3): `/v1/completions`
- **Claude models**: Anthropic Messages API

### Two-Comment System (Script B)
1. **Feedback Comment**: Grade change + specific feedback
2. **Model Answers Comment**: Always posted, shows correct answers

## Model Support

| Model | Provider | Temperature | Endpoint | Cost (10 students) |
|-------|----------|-------------|----------|-------------------|
| gpt-4o | OpenAI | 0.3 | chat/completions | ~$0.08 |
| gpt-4o-mini | OpenAI | 0.3 | chat/completions | ~$0.005 |
| gpt-5 | OpenAI | 0.3 | chat/completions | TBD |
| gpt-5-pro | OpenAI | N/A | completions | TBD |
| claude-sonnet-4-5 | Anthropic | 1.0 | messages | ~$0.10 |

## Error Handling

- **Script A/AA**: Skips failed submissions, continues with rest
- **Script B**: Failed uploads remain in queue for retry
- **Cache errors**: Falls back to fresh Canvas API calls
- **All scripts**: State saved to JSON for resumability

## Safety Features

- Automatic JSON backups (`.bak.json`)
- Confirmation prompts before uploads
- Preview of changes before posting
- State persistence across sessions
- Grade validation (0 to max points)

## Requirements

- Python 3.7+
- macOS (for Keychain integration)
- Canvas LMS with New Quizzes
- OpenAI API access
- Anthropic API access (for Claude models)

## License

Educational use - UNC Chapel Hill

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
