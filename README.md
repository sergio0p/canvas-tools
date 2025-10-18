# Canvas Tools

Scripts for automating appointment group creation, file unpublishing, module management, assignment administration, and AI-powered quiz grading in UNC's Canvas LMS.

## Setup

### Prerequisites

- Python 3.9+
- Canvas API access token
- OpenAI API key (for AI grading scripts)
- Required packages: `requests`, `keyring`, `openai`, `tqdm` (optional)

### Installation

```bash
pip install requests keyring openai tqdm
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
security add-generic-password -s "openai" -a "openai" -w "your_openai_api_key_here"
```

## Scripts

### AI-Powered Quiz Grading

#### quiz_ai_grader_collect.py

Collects student quiz submissions and grades them using OpenAI API. Results are saved to JSON files for validation.

**Features:**
- Select course, quiz, and essay question interactively
- Custom grading guidelines for AI
- Grades all submissions automatically
- Menu-driven workflow to grade multiple questions/quizzes/courses
- Saves results to JSON (does not post to Canvas)

**Usage:**
```bash
python3 quiz_ai_grader_collect.py
```

**Workflow:**
1. Select course → quiz → essay question
2. Provide grading guidelines
3. AI grades all submissions
4. Results saved to `grading_session_<course>_<quiz>_<question>_<timestamp>.json`
5. Choose to grade another question, quiz, or course

#### quiz_ai_grader_validate.py

Reviews AI-graded submissions and posts validated grades to Canvas.

**Features:**
- Load grading session from JSON file
- Automatic backup creation
- Review each submission with full answer text
- Options per submission:
  - **(v) Validate** - Accept and post AI grade immediately
  - **(o) Override** - Provide manual grade and post immediately
  - **(s) Skip** - Leave ungraded for manual review in SpeedGrader
  - **(q) Quit** - Save progress and exit (resumable)
- Updates JSON file after each posted grade
- Resumable workflow

**Usage:**
```bash
python3 quiz_ai_grader_validate.py grading_session_file.json
```

**Workflow:**
1. Load JSON file from collection script
2. Review each submission
3. Validate, override, or skip
4. Posted grades removed from JSON immediately
5. Quit anytime and resume later

#### openai_grading_instructions.md

Detailed grading rubric and instructions for constrained optimization problems, designed for use with OpenAI API.

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
