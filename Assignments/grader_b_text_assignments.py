#!/usr/bin/env python3
"""
Canvas Text Entry Assignments: Generic Grader - PART B

Reviews AI-graded submissions and uploads approved grades to Canvas.
Loads grading results from JSON files created by Part A.
Uses a menu configuration JSON file for feedback options.
"""

import sys
import os
import json
import glob
import shutil
import keyring
import requests
import tempfile
import webbrowser
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

# Configuration
CANVAS_SERVICE_NAME = 'canvas'
CANVAS_USERNAME = 'access-token'
HOST = 'https://uncch.instructure.com'
API_V1 = f"{HOST}/api/v1"

# Correct answers for Economics assignment
CORRECT_ANSWERS_ECONOMICS = {
    'part1': {
        'title': "Part 1: Antonia's Baskets (0.6 points)",
        'answers': {
            'A0': '(20, 0)',
            'A1': '(22, 4)',
            'A2': '(15, 0)'
        }
    },
    'part2': {
        'title': "Part 2: Marie's Baskets (0.6 points)",
        'answers': {
            'M0': '(10, 10)',
            'M1': '(3, 13.5)',
            'M2': '(13.5, 3)'
        }
    },
    'part3': {
        'title': "Part 3: Colored Tables (2.8 points)",
        'answers': {
            'table1': {
                'name': 'Table 1 - Directly revealed (Antonia)',
                'entries': ['A0 ≥DR A2', 'A1 ≥DR A0', 'A1 ≥DR A2']
            },
            'table2': {
                'name': 'Table 2 - Strict revealed (Antonia)',
                'entries': ['A0 >SDR A2', 'A1 >SDR A0', 'A1 >SDR A2']
            },
            'table3': {
                'name': 'Table 3 - Directly revealed (Marie)',
                'entries': ['M0 ≥DR M1', 'M0 ≥DR M2', 'M1 ≥DR M0',
                           'M1 ≥DR M2', 'M2 ≥DR M0', 'M2 ≥DR M1']
            },
            'table4': {
                'name': 'Table 4 - Strict revealed (Marie)',
                'entries': ['M0 >SDR M1', 'M0 >SDR M2', 'M1 >SDR M2', 'M2 >SDR M1']
            }
        }
    }
}


@dataclass
class GradingResult:
    """Represents AI grading results for a student"""
    student_id: int
    student_name: str
    essay_text: str
    ai_grade: float
    ai_feedback: str
    old_assignment_grade: float
    new_assignment_grade: float
    approved: Optional[bool] = None


class CanvasAPIClient:
    """Handles all Canvas API interactions"""

    def __init__(self):
        """Initialize API client with authentication"""
        self.token = self._get_token()
        self.session = requests.Session()
        self.session.headers.update({'Authorization': f'Bearer {self.token}'})

    def _get_token(self) -> str:
        """Retrieve API token from keychain"""
        token = keyring.get_password(CANVAS_SERVICE_NAME, CANVAS_USERNAME)
        if not token:
            print(f"❌ ERROR: No Canvas API token found in keychain.")
            print(f"Set one using: keyring.set_password('{CANVAS_SERVICE_NAME}', '{CANVAS_USERNAME}', 'your_token')")
            sys.exit(1)
        return token

    def update_grade(self, course_id: int, assignment_id: int, user_id: int,
                    grade: float, comment: str) -> bool:
        """Update student's assignment grade and add feedback comment"""
        url = f"{API_V1}/courses/{course_id}/assignments/{assignment_id}/submissions/{user_id}"

        data = {
            'submission[posted_grade]': str(grade),
            'comment[text_comment]': comment
        }

        response = self.session.put(url, data=data)

        if response.status_code == 200:
            return True
        else:
            print(f"  ❌ Failed to update grade for user {user_id}: {response.status_code}")
            return False


def load_menu_config(filename: str) -> Dict:
    """
    Load menu configuration from JSON file.
    
    Expected format:
    {
        "num_parts": 1,  // or 2, 3, etc.
        "parts": [
            {
                "name": "Part 1",
                "options": [
                    {"number": 1, "name": "Option name", "feedback": "Feedback text"},
                    ...
                ]
            },
            ...
        ],
        "model_answers": "Optional model answers text" // optional field
    }
    """
    try:
        with open(filename, 'r') as f:
            config = json.load(f)
        
        # Validate structure
        if 'num_parts' not in config:
            print(f"❌ Menu config missing 'num_parts' field")
            sys.exit(1)
        
        if 'parts' not in config or not isinstance(config['parts'], list):
            print(f"❌ Menu config missing or invalid 'parts' field")
            sys.exit(1)
        
        if len(config['parts']) != config['num_parts']:
            print(f"❌ Menu config 'num_parts' ({config['num_parts']}) doesn't match parts list length ({len(config['parts'])})")
            sys.exit(1)
        
        # Validate each part
        for i, part in enumerate(config['parts']):
            if 'name' not in part or 'options' not in part:
                print(f"❌ Part {i+1} missing 'name' or 'options' field")
                sys.exit(1)
            
            if not isinstance(part['options'], list) or len(part['options']) == 0:
                print(f"❌ Part {i+1} has invalid or empty 'options' list")
                sys.exit(1)
            
            # Validate each option
            for j, opt in enumerate(part['options']):
                if 'number' not in opt or 'name' not in opt or 'feedback' not in opt:
                    print(f"❌ Part {i+1}, option {j+1} missing required fields")
                    sys.exit(1)
        
        return config
        
    except FileNotFoundError:
        print(f"❌ Menu config file not found: {filename}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing menu config JSON: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error loading menu config: {e}")
        sys.exit(1)


def display_feedback_menu(part_name: str, options: List[Dict]) -> int:
    """
    Display a feedback menu and get user selection.
    
    Args:
        part_name: Name of the part (e.g., "Part 1")
        options: List of menu options
    
    Returns:
        Selected option number (1-based), where len(options)+1 indicates manual input
    """
    print(f"\n{'=' * 80}")
    print(f"SELECT FEEDBACK FOR {part_name}")
    print('=' * 80)
    
    for opt in options:
        print(f"\n{opt['number']}. {opt['name']}")
        print(f"   Feedback: \"{opt['feedback']}\"")
    
    # Add manual input option as the last option
    manual_option_num = len(options) + 1
    print(f"\n{manual_option_num}. Manual input")
    print(f"   Feedback: (You will be prompted to enter custom feedback)")
    
    print('=' * 80)
    
    while True:
        try:
            choice = input(f"\nSelect option (1-{manual_option_num}): ").strip()
            choice_num = int(choice)
            if 1 <= choice_num <= manual_option_num:
                return choice_num
            else:
                print(f"Please enter a number between 1 and {manual_option_num}")
        except ValueError:
            print("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print("\n\n👋 Cancelled by user")
            sys.exit(0)


def get_manual_feedback(part_name: str) -> str:
    """Get manual feedback input from user"""
    print(f"\n{'=' * 80}")
    print(f"ENTER MANUAL FEEDBACK FOR {part_name}")
    print('=' * 80)
    print("Enter feedback (press Enter twice when done):\n")
    
    lines = []
    empty_count = 0
    
    while True:
        try:
            line = input()
            if line == "":
                empty_count += 1
                if empty_count >= 2:
                    break
            else:
                empty_count = 0
                lines.append(line)
        except KeyboardInterrupt:
            print("\n\n👋 Cancelled by user")
            sys.exit(0)
    
    feedback = "\n".join(lines).strip()
    
    if not feedback:
        print("⚠️  Empty feedback entered")
        retry = input("Try again? (y/n): ").strip().lower()
        if retry == 'y':
            return get_manual_feedback(part_name)
        else:
            return ""
    
    return feedback


def get_override_grade(max_points: float) -> float:
    """Get override grade from user"""
    while True:
        try:
            grade_input = input(f"\nEnter new grade (0-{max_points}): ").strip()
            grade = float(grade_input)
            if 0 <= grade <= max_points:
                return grade
            else:
                print(f"Grade must be between 0 and {max_points}")
        except ValueError:
            print("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print("\n\n👋 Cancelled by user")
            sys.exit(0)


def parse_baskets(essay_text: str) -> dict:
    """
    Extract basket values from student submission JSON.

    Returns:
        {
            'part1': {'A0': '(20, 0)', 'A1': '(22, 4)', 'A2': '(15, 0)'},
            'part2': {'M0': '(10, 10)', 'M1': '(3, 13.5)', 'M2': '(13.5, 3)'},
            'error': None or error message
        }
    """
    import re

    try:
        data = json.loads(essay_text)

        result = {
            'part1': {},
            'part2': {},
            'error': None
        }

        # Get content array
        content = data.get('content', [])

        # Look for basket patterns: A0 = (x, y), M0 = (x, y), etc.
        basket_pattern = r'([AM]\d)\s*=\s*\(([^)]+)\)'

        for item in content:
            if isinstance(item, dict) and item.get('type') == 'text':
                text = item.get('text', '')
                matches = re.findall(basket_pattern, text)

                for basket_id, values in matches:
                    # Clean up values
                    formatted_value = f"({values.strip()})"

                    # Assign to appropriate part
                    if basket_id.startswith('A'):
                        result['part1'][basket_id] = formatted_value
                    elif basket_id.startswith('M'):
                        result['part2'][basket_id] = formatted_value

        return result

    except Exception as e:
        return {'part1': {}, 'part2': {}, 'error': str(e)}


def parse_blue_entries(essay_text: str) -> dict:
    """
    Extract blue entries from student submission JSON.

    Returns:
        {
            'table1': ['A0 ≥DR A2', ...],
            'table2': [...],
            'table3': [...],
            'table4': [...],
            'error': None or error message
        }
    """
    try:
        data = json.loads(essay_text)

        result = {
            'table1': [],
            'table2': [],
            'table3': [],
            'table4': [],
            'error': None
        }

        # Get content array
        content = data.get('content', [])

        # Track which table we're on
        table_num = 0

        for item in content:
            if isinstance(item, dict) and item.get('type') == 'table':
                table_num += 1
                blue_entries = item.get('blue_entries', [])

                if table_num <= 4:
                    result[f'table{table_num}'] = blue_entries

        return result

    except Exception as e:
        return {'table1': [], 'table2': [], 'table3': [], 'table4': [], 'error': str(e)}


def parse_student_submission(essay_text: str) -> dict:
    """
    Parse complete student submission.

    Returns:
        {
            'part1': {...},
            'part2': {...},
            'part3': {...},
            'is_json': True/False,
            'parse_error': None or error message
        }
    """
    try:
        json.loads(essay_text)
        is_json = True
    except:
        is_json = False
        return {'is_json': False, 'parse_error': 'Not JSON format'}

    baskets = parse_baskets(essay_text)
    blue_entries = parse_blue_entries(essay_text)

    return {
        'is_json': True,
        'part1': baskets['part1'],
        'part2': baskets['part2'],
        'part3': blue_entries,
        'parse_error': baskets['error'] or blue_entries['error']
    }


def generate_comparison_html(user_answers: dict, correct_answers: dict,
                             result: GradingResult) -> str:
    """
    Generate HTML page with side-by-side comparison.

    Args:
        user_answers: Parsed student answers
        correct_answers: Correct answers (CORRECT_ANSWERS_ECONOMICS)
        result: GradingResult object with metadata

    Returns:
        Complete HTML string
    """

    # Helper function to build basket HTML
    def build_basket_html(part_key: str, user_baskets: dict, correct_baskets: dict, is_user: bool) -> str:
        html_parts = []
        part_info = correct_answers[part_key]

        html_parts.append(f'<div class="part">')
        html_parts.append(f'<h3>{part_info["title"]}</h3>')
        html_parts.append('<table>')

        for basket_id in ['A0', 'A1', 'A2'] if part_key == 'part1' else ['M0', 'M1', 'M2']:
            user_val = user_baskets.get(basket_id, '')
            correct_val = correct_baskets.get(basket_id, '')

            html_parts.append('<tr>')
            html_parts.append(f'<td style="font-weight: bold; width: 60px;">{basket_id}</td>')

            if is_user:
                # User column - show correctness
                if user_val:
                    if user_val == correct_val:
                        css_class = 'correct'
                        marker = ' ✓'
                    else:
                        css_class = 'incorrect'
                        marker = ' ✗'
                    html_parts.append(f'<td class="{css_class}">{user_val}{marker}</td>')
                else:
                    html_parts.append(f'<td class="missing">(missing)</td>')
            else:
                # Correct column - just show answer
                html_parts.append(f'<td>{correct_val}</td>')

            html_parts.append('</tr>')

        html_parts.append('</table>')
        html_parts.append('</div>')

        return '\n'.join(html_parts)

    # Helper function to build table HTML
    def build_table_html(table_key: str, user_entries: list, correct_entries: list, is_user: bool) -> str:
        html_parts = []
        table_info = correct_answers['part3']['answers'][table_key]

        count_correct = sum(1 for entry in user_entries if entry in correct_entries) if is_user else len(correct_entries)
        total = len(correct_entries)

        html_parts.append(f'<h4>{table_info["name"]}'
                         + (f' ({count_correct}/{total})' if is_user else '')
                         + '</h4>')
        html_parts.append('<ul>')

        if is_user:
            # Show user's entries with correctness
            all_entries = set(user_entries) | set(correct_entries)
            for entry in sorted(all_entries):
                if entry in user_entries and entry in correct_entries:
                    html_parts.append(f'<li class="correct">{entry} ✓</li>')
                elif entry in user_entries and entry not in correct_entries:
                    html_parts.append(f'<li class="incorrect">{entry} ✗</li>')
                elif entry not in user_entries and entry in correct_entries:
                    html_parts.append(f'<li class="missing">{entry} (missing)</li>')
        else:
            # Just show correct entries
            for entry in correct_entries:
                html_parts.append(f'<li>{entry}</li>')

        html_parts.append('</ul>')

        return '\n'.join(html_parts)

    # Build user content
    user_content_parts = []
    user_content_parts.append(build_basket_html('part1', user_answers.get('part1', {}),
                                                correct_answers['part1']['answers'], True))
    user_content_parts.append(build_basket_html('part2', user_answers.get('part2', {}),
                                                correct_answers['part2']['answers'], True))

    # Part 3 - Tables
    user_content_parts.append('<div class="part">')
    user_content_parts.append(f'<h3>{correct_answers["part3"]["title"]}</h3>')

    user_part3 = user_answers.get('part3', {})
    for table_key in ['table1', 'table2', 'table3', 'table4']:
        user_entries = user_part3.get(table_key, [])
        correct_entries = correct_answers['part3']['answers'][table_key]['entries']
        user_content_parts.append(build_table_html(table_key, user_entries, correct_entries, True))

    user_content_parts.append('</div>')

    user_content = '\n'.join(user_content_parts)

    # Build correct content
    correct_content_parts = []
    correct_content_parts.append(build_basket_html('part1', correct_answers['part1']['answers'],
                                                   correct_answers['part1']['answers'], False))
    correct_content_parts.append(build_basket_html('part2', correct_answers['part2']['answers'],
                                                   correct_answers['part2']['answers'], False))

    # Part 3 - Tables
    correct_content_parts.append('<div class="part">')
    correct_content_parts.append(f'<h3>{correct_answers["part3"]["title"]}</h3>')

    for table_key in ['table1', 'table2', 'table3', 'table4']:
        correct_entries = correct_answers['part3']['answers'][table_key]['entries']
        correct_content_parts.append(build_table_html(table_key, [], correct_entries, False))

    correct_content_parts.append('</div>')

    correct_content = '\n'.join(correct_content_parts)

    # Generate complete HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Grading Review: {result.student_name}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}

        .header {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}

        .header h1 {{
            margin: 0 0 15px 0;
            color: #333;
        }}

        .student-info {{
            color: #666;
        }}

        .student-info p {{
            margin: 5px 0;
        }}

        .container {{
            display: flex;
            gap: 20px;
        }}

        .column {{
            flex: 1;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        .user-column {{
            border-left: 4px solid #2196F3;
        }}

        .correct-column {{
            border-left: 4px solid #4CAF50;
        }}

        .column h2 {{
            margin-top: 0;
            padding-bottom: 10px;
            border-bottom: 2px solid #eee;
        }}

        .part {{
            margin-bottom: 30px;
        }}

        .part h3 {{
            color: #333;
            margin-bottom: 10px;
        }}

        .part h4 {{
            color: #555;
            margin: 15px 0 8px 0;
            font-size: 0.95em;
        }}

        .correct {{
            color: #4CAF50;
            font-weight: bold;
        }}

        .incorrect {{
            color: #f44336;
            font-weight: bold;
        }}

        .missing {{
            color: #FF9800;
            font-style: italic;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}

        td {{
            padding: 8px;
            border-bottom: 1px solid #eee;
        }}

        ul {{
            list-style: none;
            padding-left: 0;
        }}

        li {{
            padding: 5px 0;
        }}

        .footer {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-top: 20px;
            text-align: center;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Grading Review</h1>
        <div class="student-info">
            <p><strong>Student:</strong> {result.student_name}</p>
            <p><strong>Old Grade:</strong> {result.old_assignment_grade:.1f} |
               <strong>AI Grade:</strong> {result.ai_grade:.1f} |
               <strong>New Grade:</strong> {result.new_assignment_grade:.1f}</p>
        </div>
    </div>

    <div class="container">
        <div class="column user-column">
            <h2>👤 User's Answers</h2>
            {user_content}
        </div>

        <div class="column correct-column">
            <h2>✅ Correct Answers</h2>
            {correct_content}
        </div>
    </div>

    <div class="footer">
        <p>Return to terminal to (v)alidate, (o)verride, or (s)kip this submission.</p>
    </div>
</body>
</html>"""

    return html


def display_submission_in_browser(result: GradingResult) -> Optional[str]:
    """
    Generate HTML comparison and open in browser.

    Args:
        result: GradingResult object

    Returns:
        Path to temp HTML file, or None if failed
    """
    try:
        # Parse student submission
        user_answers = parse_student_submission(result.essay_text)

        if not user_answers['is_json']:
            return None

        # Get correct answers
        correct_answers = CORRECT_ANSWERS_ECONOMICS

        # Generate HTML
        html_content = generate_comparison_html(user_answers, correct_answers, result)

        # Create temp file
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, f'grading_review_{result.student_id}.html')

        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        # Open in browser
        webbrowser.open(f'file://{temp_file}')

        return temp_file

    except Exception as e:
        print(f"  ⚠️  Error generating HTML: {e}")
        return None


def display_submission_for_review(result: GradingResult, index: int, total: int) -> None:
    """Display a student submission for review"""
    print("\n" + "=" * 100)
    print(f"SUBMISSION {index}/{total}")
    print("=" * 100)
    print(f"Student: {result.student_name}")
    print(f"Old grade: {result.old_assignment_grade}")

    # Try to display as HTML in browser
    temp_html_file = None
    try:
        json.loads(result.essay_text)
        is_json = True
    except:
        is_json = False

    if is_json:
        print("\n  🌐 Opening comparison in browser...")
        temp_html_file = display_submission_in_browser(result)

        if temp_html_file:
            print(f"  ✅ Review the comparison in your browser")
            print(f"  📄 HTML file: {temp_html_file}")
        else:
            print(f"  ⚠️  Could not generate HTML, showing text instead")
            is_json = False

    # Fallback: display in terminal if not JSON or HTML generation failed
    if not is_json or temp_html_file is None:
        print("\n" + "-" * 100)
        print("STUDENT ANSWER:")
        print("-" * 100)
        print(result.essay_text)
        print("-" * 100)

    # Always show AI grading in terminal
    print("\n" + "-" * 100)
    print("AI GRADING:")
    print("-" * 100)
    print(f"AI Grade: {result.ai_grade}")
    print(f"New grade: {result.new_assignment_grade}")
    print(f"\nAI Feedback:")
    print(result.ai_feedback)
    print("-" * 100)


def get_validation_action() -> str:
    """Get validation action from user"""
    while True:
        try:
            action = input("\n(v)alidate | (o)verride | (s)kip | (q)uit: ").strip().lower()
            if action in ['v', 'validate']:
                return 'validate'
            elif action in ['o', 'override']:
                return 'override'
            elif action in ['s', 'skip']:
                return 'skip'
            elif action in ['q', 'quit']:
                return 'quit'
            else:
                print("Invalid choice. Enter v, o, s, or q")
        except KeyboardInterrupt:
            print("\n\n👋 Cancelled by user")
            sys.exit(0)


def select_json_file() -> str:
    """Let user select a JSON grading results file"""
    json_files = glob.glob("text_entries_*.json")
    
    if not json_files:
        print("❌ No grading result files found (text_entries_*.json)")
        sys.exit(1)
    
    # Sort by modification time, newest first
    json_files.sort(key=os.path.getmtime, reverse=True)
    
    print("\n" + "=" * 100)
    print("SELECT GRADING RESULTS FILE")
    print("=" * 100)
    
    for i, filename in enumerate(json_files, 1):
        mod_time = datetime.fromtimestamp(os.path.getmtime(filename))
        print(f"{i}. {filename} (modified: {mod_time.strftime('%Y-%m-%d %H:%M:%S')})")
    
    print("=" * 100)
    
    while True:
        try:
            choice = input(f"\nSelect file (1-{len(json_files)}): ").strip()
            choice_num = int(choice)
            if 1 <= choice_num <= len(json_files):
                return json_files[choice_num - 1]
            else:
                print(f"Please enter a number between 1 and {len(json_files)}")
        except ValueError:
            print("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print("\n\n👋 Cancelled by user")
            sys.exit(0)


def select_menu_config() -> Optional[str]:
    """
    Ask user if they want to use a menu configuration.
    Returns filename if yes, None if no.
    """
    print("\n" + "=" * 100)
    print("MENU CONFIGURATION")
    print("=" * 100)
    print("Do you want to use a menu configuration for override feedback?")
    print("  - Yes: Select from predefined feedback options when overriding")
    print("  - No:  Manually enter grade and feedback when overriding")
    print("=" * 100)
    
    while True:
        try:
            choice = input("\nUse menu configuration? (y/n): ").strip().lower()
            if choice in ['y', 'yes']:
                # Check for menu files
                json_files = glob.glob("menu_*.json")
                
                if not json_files:
                    print("❌ No menu configuration files found (menu_*.json)")
                    print("   Create a menu_*.json file or choose 'n' for manual entry")
                    continue
                
                # Sort alphabetically
                json_files.sort()
                
                print("\n" + "=" * 100)
                print("SELECT MENU CONFIGURATION FILE")
                print("=" * 100)
                
                for i, filename in enumerate(json_files, 1):
                    print(f"{i}. {filename}")
                
                print("=" * 100)
                
                while True:
                    try:
                        file_choice = input(f"\nSelect file (1-{len(json_files)}): ").strip()
                        file_choice_num = int(file_choice)
                        if 1 <= file_choice_num <= len(json_files):
                            return json_files[file_choice_num - 1]
                        else:
                            print(f"Please enter a number between 1 and {len(json_files)}")
                    except ValueError:
                        print("Invalid input. Please enter a number.")
                    except KeyboardInterrupt:
                        print("\n\n👋 Cancelled by user")
                        sys.exit(0)
                        
            elif choice in ['n', 'no']:
                return None
            else:
                print("Please enter 'y' or 'n'")
        except KeyboardInterrupt:
            print("\n\n👋 Cancelled by user")
            sys.exit(0)


def save_grading_data(data: Dict, filename: str) -> None:
    """Save grading data back to JSON file"""
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)


def main():
    """Main program flow"""
    print("=" * 100)
    print("   CANVAS TEXT ENTRY ASSIGNMENTS - Generic Grader - PART B")
    print("   This grader works with Canvas Assignments that accept online text entry")
    print("=" * 100)
    
    # Initialize Canvas client
    print("\n🔐 Authenticating with Canvas...")
    canvas_client = CanvasAPIClient()
    
    # Step 1: Select grading results JSON file
    json_filename = select_json_file()
    print(f"\n✅ Selected: {json_filename}")
    
    # Step 2: Load grading results
    print(f"\n📂 Loading grading results...")
    try:
        with open(json_filename, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Failed to load JSON: {e}")
        sys.exit(1)
    
    # Create backup
    backup_filename = json_filename.replace('.json', f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
    shutil.copy(json_filename, backup_filename)
    print(f"💾 Backup created: {backup_filename}")
    
    # Extract data
    grading_results_raw = data.get('grading_results', [])
    skipped = data.get('skipped', [])
    selected_course = data.get('selected_course', {})
    selected_assignment = data.get('selected_assignment', {})
    
    # Convert to GradingResult objects
    grading_results = []
    for r in grading_results_raw:
        grading_results.append(GradingResult(
            student_id=r['student_id'],
            student_name=r['student_name'],
            essay_text=r['essay_text'],
            ai_grade=r['ai_grade'],
            ai_feedback=r['ai_feedback'],
            old_assignment_grade=r['old_assignment_grade'],
            new_assignment_grade=r['new_assignment_grade'],
            approved=r.get('approved')
        ))
    
    if not grading_results:
        print("❌ No grading results found in file")
        sys.exit(1)
    
    print(f"\n✅ Loaded {len(grading_results)} student submission(s)")
    if skipped:
        print(f"   ({len(skipped)} were skipped during grading)")
    
    # Step 3: Ask about menu configuration
    menu_config_filename = select_menu_config()
    
    if menu_config_filename:
        print(f"\n✅ Selected menu config: {menu_config_filename}")
        
        # Step 4: Load menu configuration
        print(f"\n📋 Loading menu configuration...")
        menu_config = load_menu_config(menu_config_filename)
        print(f"✅ Menu configured with {menu_config['num_parts']} part(s)")
    else:
        print(f"\n✅ Manual entry mode selected (no menu)")
        menu_config = None
    
    # Step 5: Individual validation loop
    print("\n" + "=" * 100)
    print("INDIVIDUAL SUBMISSION REVIEW")
    print("=" * 100)
    print("Review each submission:")
    print("  (v)alidate - Upload AI grade/feedback immediately")
    print("  (o)verride - Enter new grade/feedback and upload immediately")
    print("  (s)kip     - Move to next student (keeps in queue)")
    print("  (q)uit     - Exit (remaining students stay in queue)")
    
    uploaded_count = 0
    skipped_count = 0
    i = 0
    
    while i < len(grading_results):
        result = grading_results[i]
        
        display_submission_for_review(result, i + 1, len(grading_results))
        
        action = get_validation_action()
        
        if action == 'validate':
            # Upload AI grade and feedback
            feedback = (
                f"Assignment: {selected_assignment['name']}\n"
                f"Old score: {result.old_assignment_grade:.1f}\n"
                f"New score: {result.new_assignment_grade:.1f}\n\n"
                f"Feedback:\n{result.ai_feedback}"
            )
            
            print(f"\n📤 Uploading AI grade to Canvas...")
            
            # Post Comment #1: AI Feedback
            success1 = canvas_client.update_grade(
                selected_course['id'],
                selected_assignment['id'],
                result.student_id,
                result.new_assignment_grade,
                feedback
            )
            
            if not success1:
                print(f"  ❌ Failed to upload - keeping in queue")
                i += 1
                continue
            
            # Post Comment #2: Model Answers (if available and menu config exists)
            if menu_config and 'model_answers' in menu_config and menu_config['model_answers']:
                print(f"  📤 Posting model answers...")
                success2 = canvas_client.update_grade(
                    selected_course['id'],
                    selected_assignment['id'],
                    result.student_id,
                    result.new_assignment_grade,
                    menu_config['model_answers']
                )
                
                if success2:
                    print(f"  ✅ Uploaded AI grade and model answers for {result.student_name}")
                else:
                    print(f"  ⚠️  Posted feedback but model answers failed")
            else:
                print(f"  ✅ Uploaded AI grade for {result.student_name}")
            
            uploaded_count += 1
            grading_results.pop(i)
            data['grading_results'] = [r.__dict__ for r in grading_results]
            save_grading_data(data, json_filename)
        
        elif action == 'override':
            # Get new grade from user
            new_grade = get_override_grade(selected_assignment['points_possible'])
            
            # Get feedback based on menu config availability
            if menu_config:
                # Menu mode: Select feedback for each part
                part_feedbacks = []
                for part in menu_config['parts']:
                    part_choice = display_feedback_menu(part['name'], part['options'])
                    
                    if part_choice == len(part['options']) + 1:
                        # Manual input selected
                        part_feedback = get_manual_feedback(part['name'])
                    else:
                        part_feedback = part['options'][part_choice - 1]['feedback']
                    
                    part_feedbacks.append(part_feedback)
                
                # Combine feedback
                if menu_config['num_parts'] == 1:
                    combined_feedback = part_feedbacks[0]
                else:
                    combined_feedback = "\n\n".join(part_feedbacks)
            else:
                # Manual mode: Just ask for feedback directly
                print("\n" + "=" * 100)
                print("ENTER FEEDBACK")
                print("=" * 100)
                print("Enter feedback for the student (press Enter twice when done):\n")
                
                lines = []
                empty_count = 0
                
                while True:
                    try:
                        line = input()
                        if line == "":
                            empty_count += 1
                            if empty_count >= 2:
                                break
                        else:
                            empty_count = 0
                            lines.append(line)
                    except KeyboardInterrupt:
                        print("\n\n👋 Cancelled by user")
                        sys.exit(0)
                
                combined_feedback = "\n".join(lines).strip()
                
                if not combined_feedback:
                    print("  ⚠️  No feedback entered")
                    confirm_empty = input("Continue with empty feedback? (y/n): ").strip().lower()
                    if confirm_empty != 'y':
                        print("  ↩️  Override cancelled")
                        i += 1
                        continue
            
            # Show preview
            print("\n" + "=" * 100)
            print("PREVIEW OF NEW GRADE")
            print("=" * 100)
            print(f"Total Score: {new_grade}/{selected_assignment['points_possible']}")
            print(f"\nFeedback Comment #1:")
            print("-" * 100)
            print(combined_feedback)
            print("-" * 100)
            
            if menu_config and 'model_answers' in menu_config and menu_config['model_answers']:
                print(f"\nModel Answers Comment #2:")
                print("-" * 100)
                print(menu_config['model_answers'])
                print("-" * 100)
            
            # Confirm before uploading
            confirm = input("\nPost these grades and comments to Canvas? (y/n): ").strip().lower()
            if confirm != 'y':
                print("  ↩️  Override cancelled")
                i += 1
                continue
            
            # Build first comment (feedback)
            feedback_comment = (
                f"Assignment: {selected_assignment['name']}\n"
                f"Old score: {result.old_assignment_grade:.1f}\n"
                f"New score: {new_grade:.1f}\n\n"
                f"{combined_feedback}"
            )
            
            print(f"\n📤 Uploading override grade to Canvas...")
            
            # Post Comment #1: Feedback
            success1 = canvas_client.update_grade(
                selected_course['id'],
                selected_assignment['id'],
                result.student_id,
                new_grade,
                feedback_comment
            )
            
            if not success1:
                print(f"  ❌ Failed to upload feedback - keeping in queue")
                i += 1
                continue
            
            # Post Comment #2: Model Answers (if available)
            if menu_config and 'model_answers' in menu_config and menu_config['model_answers']:
                print(f"  📤 Posting model answers...")
                success2 = canvas_client.update_grade(
                    selected_course['id'],
                    selected_assignment['id'],
                    result.student_id,
                    new_grade,
                    menu_config['model_answers']
                )
                
                if success2:
                    print(f"  ✅ Uploaded override grade and model answers for {result.student_name}")
                else:
                    print(f"  ⚠️  Posted feedback but model answers failed")
            else:
                print(f"  ✅ Uploaded override grade for {result.student_name}")
            
            uploaded_count += 1
            grading_results.pop(i)
            data['grading_results'] = [r.__dict__ for r in grading_results]
            save_grading_data(data, json_filename)
        
        elif action == 'skip':
            print(f"  ⏭️  Skipped {result.student_name}")
            skipped_count += 1
            i += 1
        
        elif action == 'quit':
            print(f"\n👋 Exiting validation...")
            break
    
    # Step 6: Final summary
    print("\n" + "=" * 100)
    print("VALIDATION SUMMARY")
    print("=" * 100)
    print(f"✅ Uploaded to Canvas:      {uploaded_count} grade(s)")
    print(f"⏭️  Skipped (still in queue): {skipped_count} student(s)")
    print(f"📋 Remaining in queue:      {len(grading_results)} student(s)")
    
    if len(grading_results) > 0:
        print(f"\n💾 Progress saved to: {json_filename}")
        print(f"   Run Part B again to continue validation")
    else:
        print(f"\n🎉 All submissions processed!")
        print(f"   You can delete: {json_filename}")
        if backup_filename:
            print(f"   Backup available at: {backup_filename}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Exiting...")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
