#!/usr/bin/env python3
"""
Test script for HTML generation functionality
"""

import json
import sys
sys.path.insert(0, '/Users/sergiop/Dropbox/Scripts/Canvas/Assignments')

from grader_b_text_assignments import (
    parse_student_submission,
    generate_comparison_html,
    CORRECT_ANSWERS_ECONOMICS,
    GradingResult
)

def test_parsing():
    """Test JSON parsing functions"""
    print("=" * 80)
    print("TEST 1: Parsing Student Submission")
    print("=" * 80)

    # Load test JSON
    with open('test_sample_submission.json', 'r') as f:
        test_json = f.read()

    # Parse it
    result = parse_student_submission(test_json)

    print(f"Is JSON: {result['is_json']}")
    print(f"Parse Error: {result['parse_error']}")
    print(f"\nPart 1 baskets: {result['part1']}")
    print(f"Part 2 baskets: {result['part2']}")
    print(f"Part 3 tables:")
    for table in ['table1', 'table2', 'table3', 'table4']:
        print(f"  {table}: {len(result['part3'][table])} entries")

    return result

def test_html_generation(parsed_data):
    """Test HTML generation"""
    print("\n" + "=" * 80)
    print("TEST 2: HTML Generation")
    print("=" * 80)

    # Create a mock GradingResult
    mock_result = GradingResult(
        student_id=12345,
        student_name="Test Student",
        essay_text=json.dumps({"content": []}),
        ai_grade=3.8,
        ai_feedback="Good work overall.",
        old_assignment_grade=0.0,
        new_assignment_grade=3.8,
        approved=None
    )

    # Generate HTML
    html = generate_comparison_html(parsed_data, CORRECT_ANSWERS_ECONOMICS, mock_result)

    print(f"HTML length: {len(html)} characters")
    print(f"Contains UTF-8 chars: {'≥' in html and '>' in html}")
    print(f"Contains student name: {'Test Student' in html}")

    # Save to file for manual inspection
    output_file = 'test_output.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\n✅ HTML saved to: {output_file}")
    print(f"   Open it in your browser to inspect the layout")

    return html

def test_edge_cases():
    """Test edge cases"""
    print("\n" + "=" * 80)
    print("TEST 3: Edge Cases")
    print("=" * 80)

    # Test 1: Partial submission (missing some baskets)
    partial_json = {
        "content": [
            {"type": "text", "text": "A0 = (20, 0)"},
            {"type": "text", "text": "A1 = (22, 4)"},
            # A2 missing
            {"type": "text", "text": "M0 = (10, 10)"},
            {"type": "table", "blue_entries": ["A0 ≥DR A2", "A1 ≥DR A0"]}  # Incomplete
        ]
    }

    result = parse_student_submission(json.dumps(partial_json))
    print(f"Partial submission - Part 1 has {len(result['part1'])} baskets (expected 2)")
    print(f"Partial submission - Part 2 has {len(result['part2'])} baskets (expected 1)")

    # Test 2: Non-JSON text
    plain_text = "This is just plain text, not JSON"
    result = parse_student_submission(plain_text)
    print(f"\nPlain text - Is JSON: {result['is_json']}")
    print(f"Plain text - Error: {result['parse_error']}")

    # Test 3: Malformed JSON
    bad_json = '{"content": ['
    result = parse_student_submission(bad_json)
    print(f"\nMalformed JSON - Is JSON: {result['is_json']}")

    print("\n✅ Edge case tests completed")

if __name__ == "__main__":
    try:
        # Run tests
        parsed_data = test_parsing()
        html = test_html_generation(parsed_data)
        test_edge_cases()

        print("\n" + "=" * 80)
        print("ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print("\nNext steps:")
        print("1. Open test_output.html in your browser")
        print("2. Verify the two-column layout displays correctly")
        print("3. Check that special characters (≥, >) display properly")
        print("4. Verify colors (green=correct, red=incorrect, orange=missing)")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
