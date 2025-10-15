# Canvas Assignment Manager

Convert assignment groups to non-graded status in bulk.

## Purpose

This script allows Canvas instructors to quickly convert all assignments in a selected assignment group to non-graded status. This is useful when you want to:

- Change assignments from graded to practice/ungraded
- Reorganize grading structure
- Convert old assignments to non-graded status

## Features

- **Favorited Courses Only**: Shows only courses you've starred in Canvas (appears in your course menu)
- **Assignment Group View**: Displays all assignment groups with assignment counts
- **Bulk Conversion**: Converts all assignments in a group to non-graded with one action
- **Safety Features**:
  - Confirmation prompt before making changes
  - Detailed success/failure reporting
  - Error handling with informative messages
- **Interactive Loop**: Process multiple assignment groups in one session

## Requirements

- Python 3.6+
- `requests` library
- `keyring` library
- Canvas API token stored in keychain

## Setup

### 1. Install Dependencies

```bash
pip install requests keyring
```

### 2. Store API Token

```python
import keyring
keyring.set_password('canvas', 'access-token', 'your_canvas_api_token_here')
```

Get your token from Canvas: Account → Settings → "+ New Access Token"

### 3. Star Your Courses

In Canvas, star (favorite) the courses you want to manage. Only starred courses will appear in the script.

## Usage

### Basic Usage

```bash
python3 canvas_assignment_manager.py
```

### Workflow

1. **Select Course**: Choose from your starred courses
2. **View Assignment Groups**: See all groups with assignment counts
3. **Select Group**: Choose which group to modify
4. **Confirm Action**: Review and confirm the changes
5. **Process Assignments**: Script converts all assignments to non-graded
6. **Continue or Exit**: Option to process another group or exit

### Example Session

```
============================================================
CANVAS ASSIGNMENT GROUP MANAGER
============================================================

🔍 Fetching your favorited courses...

============================================================
YOUR COURSES
============================================================
1. [ECON416.001.FA25] ECON416.001.FA25
2. [ECON510.ALL.FA25] ECON510.ALL.FA25
============================================================

Enter course number (or 'q' to quit): 1

✅ Selected: ECON416.001.FA25

🔍 Fetching assignment groups...

============================================================
ASSIGNMENT GROUPS
============================================================
1. Assignments (15 assignments)
2. Final Exam (1 assignments)
3. Midterm (2 assignments)
4. Practice (8 assignments)
5. Exit
============================================================

Enter assignment group number: 4

⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠
You are about to convert 8 assignment(s)
in the group 'Practice' to NON-GRADED status.
⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠

Are you sure? (yes/no): yes

🔄 Processing 8 assignment(s)...
  ✅ Practice Problem 1
  ✅ Practice Problem 2
  ✅ Practice Problem 3
  ✅ Practice Problem 4
  ✅ Practice Problem 5
  ✅ Practice Problem 6
  ✅ Practice Problem 7
  ✅ Practice Problem 8

============================================================
✅ SUCCESS: All 8 assignment(s) converted to non-graded.
============================================================

------------------------------------------------------------
Process another assignment group? (yes/no): no

👋 Exiting...
```

## API Details

### Endpoints Used

- `GET /api/v1/users/self/favorites/courses` - Fetch starred courses
- `GET /api/v1/courses/:id/assignment_groups?include[]=assignments` - Get assignment groups with assignments
- `PUT /api/v1/courses/:id/assignments/:assignment_id` - Update assignment to non-graded

### Assignment Update

When converting to non-graded, the script sets:
```python
{
    'assignment[grading_type]': 'not_graded',
    'assignment[points_possible]': ''
}
```

## Error Handling

The script handles various error scenarios:

- **No API Token**: Exits with instructions to set token
- **No Favorited Courses**: Prompts to star courses in Canvas
- **No Assignment Groups**: Notifies if course has no groups
- **No Assignments in Group**: Skips processing if group is empty
- **API Errors**: Displays HTTP errors with response details
- **Network Issues**: Catches connection errors

## Code Structure

```python
class CanvasAssignmentManager:
    def __init__()                          # Initialize with API token
    def _get_api_token()                    # Retrieve token from keychain
    def _make_request()                     # Make API requests with error handling
    def get_teaching_courses()              # Fetch favorited courses
    def display_courses()                   # Show course menu
    def select_course()                     # Handle course selection
    def get_assignment_groups()             # Fetch groups with assignments
    def display_assignment_groups()         # Show group menu
    def select_assignment_group()           # Handle group selection
    def get_assignments_in_group()          # Fetch specific group assignments
    def confirm_action()                    # Get user confirmation
    def make_assignment_non_graded()        # Convert single assignment
    def process_assignment_group()          # Process entire group
    def run()                               # Main application loop
```

## Customization

### Change Canvas Instance

Edit the API_BASE constant:

```python
API_BASE = "https://your-institution.instructure.com/api/v1"
```

### Show All Courses (Not Just Favorites)

Replace the `get_teaching_courses()` method to use:

```python
url = f"{API_BASE}/courses"
params = {
    'enrollment_type': 'teacher',
    'enrollment_state': 'active',
    'per_page': 100
}
```

## Troubleshooting

### "No favorited courses found"
- Star courses in Canvas by clicking the star icon on the course card

### "HTTP ERROR: 401"
- API token is invalid or expired
- Generate a new token and update keychain

### "No assignment groups found"
- Course may not have any assignment groups created
- Check Canvas course settings

### Assignments not converting
- Verify you have instructor/TA permissions
- Check Canvas permissions for assignment editing

## Safety Notes

- **Backup First**: Consider exporting gradebook before bulk changes
- **Test on Practice Course**: Try on a test course first
- **Confirmation Required**: Script requires explicit "yes" confirmation
- **Irreversible**: Converting to non-graded removes point values

## Related Scripts

- `push2canvas.py` - Push content to Canvas
- `sync2canvas.py` - Sync assignments to Canvas
- `unassign.py` - Unassign assignments

## Version History

- **v1.0** (2024-10-15): Initial release
  - Favorited courses filter
  - Bulk assignment group conversion
  - Interactive confirmation prompts
