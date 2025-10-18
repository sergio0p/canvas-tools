# Canvas Tools

Scripts for automating appointment group creation, file unpublishing, module management, assignment administration, and AI-powered essay grading in UNC's Canvas LMS.

## Setup

### Prerequisites

- Python 3.x
- Canvas API access token
- OpenAI API key (for AI grading scripts)
- Required packages: `requests`, `keyring`, `openai`, `beautifulsoup4`

### Installation

```bash
pip install requests keyring openai beautifulsoup4
```

### API Token Setup

Store your Canvas API token securely in your system keychain:

```python
import keyring
keyring.set_password('canvas', 'access-token', 'your_canvas_api_token_here')
```

To generate a Canvas API token:
1. Log into Canvas
2. Go to Account → Settings
3. Scroll to "Approved Integrations"
4. Click "+ New Access Token"
5. Generate and copy the token

### OpenAI API Key Setup

For AI grading scripts, store your OpenAI API key in macOS keychain:

```bash
security add-generic-password -a openai -s openai_api_key -w 'your_openai_api_key_here'
```

## Scripts

### AI-Powered Essay Grading

This repository contains an essay grading system for Canvas New Quizzes that uses OpenAI API for automated grading. The system is split into two parts for flexibility and resumability.

#### Files

- `essay_grader.py` - Original monolithic script (kept for reference)
- `essay_grader_part_a.py` - Script A: Fetches submissions and grades with AI
- `essay_grader_part_b.py` - Script B: Reviews and uploads grades to Canvas

#### How It Works

**Script A - Grading Phase:**
1. Authenticates with Canvas and OpenAI
2. Prompts user to select course → assignment → essay question
3. Gets grading guidelines (from file or manual input)
4. Fetches all student submissions
5. Grades essays in parallel using OpenAI API
6. Serializes complete state to `essays_{course_id}_{timestamp}.json`

**Script B - Validation Phase:**
1. Lists all available grading sessions from JSON files
2. User selects which session to continue
3. Creates backup (.bak.json)
4. Deserializes state and resumes validation
5. For each student, displays essay and AI grading
6. User chooses:
   - **(v)alidate** - Upload AI grade immediately
   - **(o)verride** - Provide custom grade/feedback and upload
   - **(s)kip** - Move to next student
   - **(q)uit** - Exit and save progress
7. Updates JSON after each upload (removes processed students)
8. Can pause/resume anytime

#### State Serialization (Checkpointing)

The scripts use state serialization to split the workflow. Script A saves all necessary data to JSON:
- Grading results (student submissions, AI grades, AI feedback)
- Course/assignment/question metadata
- Skipped students list

Script B loads this exact state and continues from validation, requiring no additional user input about course/assignment selection.

#### Usage

**Step 1: Grade essays**
```bash
python3 essay_grader_part_a.py
```

**Step 2: Review and upload (can be done later, on different machine, etc.)**
```bash
python3 essay_grader_part_b.py
```

### canvas_assignment_manager.py

Convert assignment groups to non-graded status in bulk.

**Features:**
- Shows only your favorited (starred) Canvas courses
- Lists all assignment groups with assignment counts
- Bulk converts assignments to non-graded status
- Includes confirmation prompts for safety

**Usage:**
```bash
python3 canvas_assignment_manager.py
```

[Full documentation](docs/canvas_assignment_manager.md)

### Other Scripts

| File                   | Description                                      |
|------------------------|--------------------------------------------------|
| `addwk2mod.py`         | Adds module blocks like "Week 8" to "Week 16"   |
| `file2.py`             | Unpublishes all course files                     |
| `assign.py`            | Unpublishes all assignments                      |
| `module.py`            | Unpublishes all modules                          |
| `getappt.py`           | Create calendar slots appointments in batch      |
| `file.py`              | Fetch and print attributes of a file             |
| `lastmodule.py`        | Fetch and print attributes of a module           |
| `sync2canvas.py`       | Synchronize assignments and content to Canvas    |
| `push2canvas.py`       | Push content to Canvas courses                   |
| `createcalappt.py`     | Create calendar appointments in Canvas           |
| `delete_future_appts.py` | Delete future calendar appointments            |
| `add2json.py`          | Add data to JSON files                           |
| `dragdrop2json.py`     | Convert drag-and-drop to JSON                    |
| `createTikZcalendar.py`| Generate TikZ calendar                           |
| `unassign.py`          | Unassign assignments                             |

## Configuration

All scripts use the same Canvas API configuration:
- **Service Name:** `canvas`
- **Username:** `access-token`
- **API Base URL:** `https://uncch.instructure.com/api/v1`

## Contributing

When adding new scripts:
1. Use the keyring for secure token storage
2. Include error handling and confirmation prompts
3. Add documentation to the docs folder
4. Update this README

## License

For educational and administrative use.
