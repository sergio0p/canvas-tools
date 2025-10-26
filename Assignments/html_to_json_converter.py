#!/usr/bin/env python3
"""
HTML to JSON Converter for Canvas Text Submissions

Converts HTML submissions to structured JSON format, extracting:
- Text sections in document order
- Tables with smart color detection for "correct" entries
- Preserves document structure

Smart Color Logic:
- Case 1: Table has blue-ish colors → extract blue entries
- Case 2: Table has ONLY red-ish colors → extract non-colored entries
- Case 3: Table has one non-red color → extract that color's entries
- Case 4: No colors OR ambiguous colors → flag for manual review
"""

import sys
import os
import json
import glob
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup


def extract_color(cell) -> Optional[str]:
    """
    Extract color from a table cell.
    
    Args:
        cell: BeautifulSoup table cell element
    
    Returns:
        Color string (normalized to lowercase) or None
    """
    # Check for span with color style
    span = cell.find('span', style=True)
    if span:
        style = span.get('style', '')
        if 'color' in style.lower():
            match = re.search(r'color:\s*([^;]+)', style, re.IGNORECASE)
            if match:
                return match.group(1).strip().lower()
    
    # Check for background color (black background case)
    cell_style = cell.get('style', '')
    if 'background' in cell_style.lower():
        if 'black' in cell_style.lower() or '#000' in cell_style:
            return 'black-background'
    
    return None


def classify_color(color: Optional[str]) -> Optional[str]:
    """
    Classify color as 'blue', 'red', or 'other'.
    
    Args:
        color: Color string from extract_color()
    
    Returns:
        'blue', 'red', 'other', or None
    """
    if not color:
        return None
    
    color = color.lower()
    
    # Blue-ish colors
    blue_patterns = [
        '#0e68b3', '#2b7abc', 
        'rgb(14', 'rgb(43', 'rgb(11', 'rgb(27',  # RGB variants
        'blue'
    ]
    if any(pattern in color for pattern in blue_patterns):
        return 'blue'
    
    # Red-ish colors
    red_patterns = [
        '#e62429', '#c71f23', '#ff0000',
        'rgb(230', 'rgb(199', 'rgb(255, 0, 0)',  # RGB variants
        'red'
    ]
    if any(pattern in color for pattern in red_patterns):
        return 'red'
    
    # Black (treat as no color)
    if 'black' in color or '#000000' in color:
        return None
    
    # White (treat as no color)
    if 'white' in color or '#ffffff' in color or '#fff' == color:
        return None
    
    # Some other color (green, purple, orange, etc.)
    return 'other'


def process_table_smart(table_element, student_name: str) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Smart table processing: detect what color means 'correct'.
    
    Logic:
    - Case 1: Blue exists → blue = correct
    - Case 2: ONLY red exists → non-colored = correct
    - Case 3: One non-red, non-blue color → that color = correct
    - Case 4: No colors OR multiple different colors → flag for manual review
    
    Args:
        table_element: BeautifulSoup table element
        student_name: Student name for error messages
    
    Returns:
        (table_dict or None, error_message or None)
    """
    # Step 1: Collect all cells with their colors
    cells = []
    for cell in table_element.find_all(['td', 'th']):
        text = cell.get_text(strip=True)
        color = extract_color(cell)
        color_type = classify_color(color)
        
        cells.append({
            'text': text,
            'color': color,
            'color_type': color_type
        })
    
    # Step 2: Analyze color distribution
    color_types = [c['color_type'] for c in cells if c['color_type']]
    
    has_blue = 'blue' in color_types
    has_red = 'red' in color_types
    has_other = 'other' in color_types
    has_any_color = bool(color_types)
    
    # Step 3: Determine what "correct" means for this table
    correct_entries = []
    
    if has_blue:
        # Case 1: Blue exists → blue = correct ✅
        correct_entries = [c['text'] for c in cells if c['color_type'] == 'blue' and c['text']]
        
    elif has_red and not has_blue and not has_other:
        # Case 2: ONLY red exists → non-colored = correct ✅
        correct_entries = [c['text'] for c in cells if not c['color_type'] and c['text']]
        
    elif has_other and not has_blue and not has_red:
        # Case 3: Has ONE non-red, non-blue color → that color = correct ✅
        other_colors = [c['color'] for c in cells if c['color_type'] == 'other']
        unique_other_colors = set(other_colors)
        
        if len(unique_other_colors) == 1:
            # Only one "other" color used
            target_color = list(unique_other_colors)[0]
            correct_entries = [c['text'] for c in cells if c['color'] == target_color and c['text']]
        else:
            # Multiple different "other" colors → ambiguous
            return None, f"{student_name}: Table has multiple different colors (ambiguous)"
    
    elif not has_any_color:
        # Case 4: No colors at all → FLAG FOR MANUAL REVIEW ⚠️
        return None, f"{student_name}: Table has no colored entries"
    
    else:
        # Case 4: Mixed colors (blue + red + other) → ambiguous
        return None, f"{student_name}: Table has ambiguous color scheme (multiple color types)"
    
    # Get table title (usually first cell)
    title = ""
    first_cell = table_element.find(['td', 'th'])
    if first_cell:
        title = first_cell.get_text(strip=True)
    
    return {
        "type": "table",
        "title": title,
        "blue_entries": correct_entries  # "blue" = "correct" conceptually
    }, None


def convert_html_to_json(html: str, student_name: str) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Convert HTML submission to structured JSON with sequential content.
    
    Args:
        html: Raw HTML from Canvas submission
        student_name: Student name for error tracking
    
    Returns:
        (structured_dict or None, error_message or None)
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    result = {"content": []}
    
    # Process all top-level elements in document order
    for element in soup.find_all(['p', 'div', 'table'], recursive=False):
        if element.name == 'table':
            # Process table with smart color detection
            table_data, error = process_table_smart(element, student_name)
            
            if error:
                # Case 4: Return error immediately
                return None, error
            
            if table_data:
                result["content"].append(table_data)
        
        else:
            # Process text element
            # Skip if this element contains a table (already processed)
            if element.find('table'):
                continue
            
            text = element.get_text(strip=True)
            if text:
                result["content"].append({
                    "type": "text",
                    "text": text
                })
    
    return result, None


def process_submissions_file(input_filename: str) -> None:
    """
    Process a submissions JSON file and create processed output.
    
    Args:
        input_filename: Path to text_submissions_*.json file
    """
    print(f"\n{'=' * 100}")
    print(f"Processing: {input_filename}")
    print('=' * 100)
    
    # Load input file
    try:
        with open(input_filename, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Failed to load file: {e}")
        return
    
    submissions = data.get('submissions', [])
    if not submissions:
        print("❌ No submissions found in file")
        return
    
    print(f"Found {len(submissions)} submission(s)")
    
    # Process each submission
    processed_submissions = []
    manual_review_needed = []
    
    for idx, submission in enumerate(submissions, 1):
        student_name = submission.get('user', {}).get('name', 'Unknown Student')
        essay_html = submission.get('body', '')
        
        print(f"\n[{idx}/{len(submissions)}] Processing {student_name}...")
        
        if not essay_html or essay_html.strip() == '':
            print(f"  ⚠️  Empty submission - skipping")
            continue
        
        # Convert HTML to structured JSON
        structured_data, error = convert_html_to_json(essay_html, student_name)
        
        if error:
            # Case 4: Flag for manual review
            print(f"  🔍 Flagged for manual review: {error}")
            manual_review_needed.append({
                "student_id": submission.get('user_id'),
                "student_name": student_name,
                "reason": error,
                "original_html": essay_html,
                "submission_id": submission.get('id')
            })
        else:
            # Successfully processed
            print(f"  ✅ Processed successfully")
            print(f"     - {len([c for c in structured_data['content'] if c['type'] == 'text'])} text section(s)")
            print(f"     - {len([c for c in structured_data['content'] if c['type'] == 'table'])} table(s)")
            
            # Add structured data to submission
            submission['structured_content'] = structured_data
            processed_submissions.append(submission)
    
    # Create output filename
    output_filename = input_filename.replace('.json', '_processed.json')
    
    # Save processed data
    output_data = {
        "course": data.get('course'),
        "assignment": data.get('assignment'),
        "total_submissions": len(processed_submissions),
        "submissions": processed_submissions,
        "manual_review_needed": manual_review_needed,
        "processing_metadata": {
            "processed_at": datetime.now().isoformat(),
            "input_file": input_filename,
            "successful": len(processed_submissions),
            "flagged_for_review": len(manual_review_needed)
        }
    }
    
    with open(output_filename, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    # Summary
    print(f"\n{'=' * 100}")
    print("PROCESSING COMPLETE")
    print('=' * 100)
    print(f"✅ Successfully processed:  {len(processed_submissions)} submission(s)")
    print(f"🔍 Manual review needed:    {len(manual_review_needed)} submission(s)")
    
    if manual_review_needed:
        print("\nStudents flagged for manual review:")
        for item in manual_review_needed:
            print(f"  - {item['student_name']}: {item['reason']}")
    
    print(f"\n💾 Output saved to: {output_filename}")
    
    if manual_review_needed:
        # Save separate manual review file
        review_filename = input_filename.replace('.json', '_manual_review.json')
        with open(review_filename, 'w') as f:
            json.dump({
                "manual_review_needed": manual_review_needed,
                "total": len(manual_review_needed)
            }, f, indent=2)
        print(f"🔍 Manual review list saved to: {review_filename}")


def select_submission_file() -> str:
    """Let user select a submissions JSON file"""
    json_files = glob.glob("text_submissions_*.json")
    
    # Exclude already processed files
    json_files = [f for f in json_files if '_processed' not in f and '_manual_review' not in f]
    
    if not json_files:
        print("❌ No text submission files found (text_submissions_*.json)")
        print("   Run analyze_text_submissions.py first to download submissions")
        sys.exit(1)
    
    # Sort by modification time, newest first
    json_files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
    
    print("\n" + "=" * 100)
    print("SELECT SUBMISSIONS FILE TO PROCESS")
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


def main():
    """Main program flow"""
    print("=" * 100)
    print("   HTML TO JSON CONVERTER")
    print("   Converts Canvas text submissions to structured JSON")
    print("=" * 100)
    
    # Select input file
    input_filename = select_submission_file()
    print(f"\n✅ Selected: {input_filename}")
    
    # Process the file
    process_submissions_file(input_filename)
    
    print("\n" + "=" * 100)
    print("Next step: Use the *_processed.json file with grader_a_text_assignments.py")
    print("=" * 100)


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
