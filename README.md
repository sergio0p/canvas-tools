# Canvas Tools

Scripts for automating appointment group creation, file unpublishing, module management, and assignment administration in UNC's Canvas LMS.

## Setup

### Prerequisites

- Python 3.9+
- Canvas API access token
- Required packages: `requests`, `keyring`

### Installation

```bash
pip install requests keyring
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

## Scripts

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
