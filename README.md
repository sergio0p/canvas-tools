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

This repository contains a **completed and working** essay grading system for Canvas New Quizzes that uses AI models (OpenAI GPT-5, Claude Sonnet 4.5, etc.) for automated grading with human-in-the-loop validation.

**New Framework Feature**: The grading system now **requires structured output** using OpenAI's JSON Schema response format to ensure consistent, validated grading results.

All essay grading tools are located in the `Essays/` subdirectory. See [Essays/README.md](Essays/README.md) for detailed documentation.

#### Key Features

- **Structured Output Enforcement**: Uses JSON Schema (`response_format`) to guarantee valid grade values and feedback format
- **Multi-Model Support**: GPT-4o, GPT-5, Claude Sonnet 4.5, with automatic API provider detection
- **Model Testing**: Compare different AI models on the same essays (Script AA)
- **Parallel Grading**: 5 concurrent API requests for faster processing
- **Two-Phase Workflow**: Separate grading (Script A) and validation (Script B) phases
- **State Persistence**: Full resumability with JSON checkpoint files
- **Student Analysis Caching**: Reuse Canvas submissions across model tests
- **Two-Comment System**: Separate feedback and model answers
- **Menu-Driven Overrides**: Quick feedback selection from predefined templates

#### Scripts

- `Essays/essay_grader_a.py` - **Main grading script** (fetch submissions + AI grading)
- `Essays/essay_grader_aa.py` - **Model testing script** (compare different AI models)
- `Essays/essay_grader_b.py` - **Validation script** (review grades + upload to Canvas)
- `Essays/essay_grader.py` - Legacy monolithic version (deprecated)

#### Structured Output Schema

The new framework enforces grading consistency using OpenAI's structured output:

```python
response_format={
    "type": "json_schema",
    "json_schema": {
        "name": "grading_schema",
        "schema": {
            "type": "object",
            "properties": {
                "grade": {"type": "number", "enum": [0, 1, 1.5, 2]},
                "feedback": {"type": "string"}
            },
            "required": ["grade", "feedback"]
        }
    }
}
```

This guarantees AI responses contain only valid grades and properly formatted feedback.

#### Quick Start

```bash
cd Essays

# Step 1: Grade essays with AI
python3 essay_grader_a.py

# Step 2: Review and upload
python3 essay_grader_b.py

# Optional: Test different models
python3 essay_grader_aa.py
```

See the [Essays README](Essays/README.md) for complete setup instructions, API key configuration, and detailed workflow documentation.

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
