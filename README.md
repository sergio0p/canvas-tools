# Canvas Tools

Automation scripts for UNC's Canvas LMS: appointment groups, file management, module administration, assignment handling, AI-powered grading, and quiz partial credit.

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

## Main Tools

### AI-Powered Essay Grading

Automated AI grading system for Canvas New Quizzes essay questions with human-in-the-loop validation. Supports GPT-4o, GPT-5, and Claude Sonnet 4.5 with structured JSON output validation.

**Quick Start:**
```bash
cd Essays
python3 essay_grader_a.py    # Grade essays
python3 essay_grader_b.py    # Review and upload
python3 essay_grader_aa.py   # Test different models (optional)
```

[Full Documentation](Essays/README.md)

### Categorization Question Partial Grading

Apply partial credit to Canvas New Quizzes categorization questions using a custom grading algorithm. Awards points for correct placements while penalizing misclassifications.

**Quick Start:**
```bash
python3 categorization_grader.py
```

**Grading Formula:** `(correct - 0.5 × misclassified) / total × points_possible`

[Full Documentation](docs/categorization_grader.md)

### Canvas Assignment Manager

Bulk convert assignment groups to non-graded status. Shows only favorited courses and includes safety confirmation prompts.

**Usage:**
```bash
python3 canvas_assignment_manager.py
```

[Full Documentation](docs/canvas_assignment_manager.md)

## Utility Scripts

| Script | Description | Usage |
|--------|-------------|-------|
| `addwk2mod.py` | Add module blocks (e.g., "Week 8" to "Week 16") | `python3 addwk2mod.py` |
| `file2.py` | Unpublish all course files | `python3 file2.py` |
| `assign.py` | Unpublish all assignments | `python3 assign.py` |
| `module.py` | Unpublish all modules | `python3 module.py` |
| `getappt.py` | Create calendar appointment slots in batch | `python3 getappt.py` |
| `delete_future_appts.py` | Delete future calendar appointments | `python3 delete_future_appts.py` |
| `sync2canvas.py` | Synchronize assignments and content to Canvas | `python3 sync2canvas.py` |
| `push2canvas.py` | Push content to Canvas courses | `python3 push2canvas.py` |
| `createcalappt.py` | Create calendar appointments | `python3 createcalappt.py` |
| `file.py` | Fetch and print file attributes | `python3 file.py` |
| `lastmodule.py` | Fetch and print module attributes | `python3 lastmodule.py` |
| `add2json.py` | Add data to JSON files | `python3 add2json.py` |
| `dragdrop2json.py` | Convert drag-and-drop to JSON | `python3 dragdrop2json.py` |
| `createTikZcalendar.py` | Generate TikZ calendar | `python3 createTikZcalendar.py` |
| `unassign.py` | Unassign assignments | `python3 unassign.py` |

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
