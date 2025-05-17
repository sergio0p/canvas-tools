# Canvas Appointment Tools

Scripts for automating appointment group creation, file unpublishing, and module management in UNC's Canvas LMS.

## 📁 Scripts

| File           | Description                                      |
|----------------|--------------------------------------------------|
| `addwk2mod.py` | Adds module blocks like “Week 8” to “Week 16”   |
| `file2.py`     | Unpublishes all course files |
| `assign.py`     | Unpublishes all assignments |
| `module.py`     | Unpublishes all modules |
| `getappt.py`   | Create calendar slots appointments in batch  |
| `file.py`   | Fetch and print attributes of a file  |
| `lastmodule.py` | Fetch and print attributes of a module |

## 🔧 Requirements

- Python 3.9+
- `requests` and `keyring` modules
- Canvas API key stored in macOS Keychain

## 🚀 Usage

```bash
python3 appt.py
