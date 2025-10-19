# Script B Modifications: Two-Comment System with Menu-Driven Override

## Overview of Changes

Script B needs to:
1. Load feedback menu from `grading_feedback_menu.md`
2. Parse menu options for each part
3. Show flat menus (no conditionals on grade)
4. Post feedback as Comment #1
5. Automatically post model answers as Comment #2

---

## Step 1: Add Menu Parser Function

Add this function after the imports section:

```python
def load_feedback_menu(filename: str = "grading_feedback_menu.md") -> Dict:
    """
    Load and parse the feedback menu markdown file.
    
    Returns dict with structure:
    {
        'part1_options': [
            {'number': 1, 'name': 'Correct', 'feedback': 'Part 1: 1/1'},
            {'number': 2, 'name': 'Objective function incorrect', 'feedback': 'Part 1: 0/1 — ...'},
            ...
        ],
        'part2_options': [...],
        'model_answers': 'MODEL ANSWERS:\n\nPart 1: ...\n\nPart 2: ...'
    }
    """
    try:
        with open(filename, 'r') as f:
            content = f.read()
        
        # Extract Part 1 options
        part1_section = content.split('## Part 1:')[1].split('---')[0]
        part1_options = []
        
        # Parse numbered options (looking for pattern: number. **text**)
        import re
        # Updated pattern to handle optional text after **name**
        for match in re.finditer(r'(\d+)\.\s+\*\*(.+?)\*\*.*?\n\s*```\s*(.+?)```', part1_section, re.DOTALL):
            num = int(match.group(1))
            name = match.group(2).strip()
            feedback = match.group(3).strip()
            part1_options.append({
                'number': num,
                'name': name,
                'feedback': feedback
            })
        
        # Extract Part 2 options
        part2_section = content.split('## Part 2:')[1].split('---')[0]
        part2_options = []
        
        # Same updated pattern
        for match in re.finditer(r'(\d+)\.\s+\*\*(.+?)\*\*.*?\n\s*```\s*(.+?)```', part2_section, re.DOTALL):
            num = int(match.group(1))
            name = match.group(2).strip()
            feedback = match.group(3).strip()
            part2_options.append({
                'number': num,
                'name': name,
                'feedback': feedback
            })
        
        # Extract model answers section
        model_section = content.split('## Model Answers')[1].split('---')[0]
        # Find content between ``` markers
        model_match = re.search(r'```\s*(.+?)```', model_section, re.DOTALL)
        model_answers = model_match.group(1).strip() if model_match else "MODEL ANSWERS:\n(Not found in menu file)"
        
        return {
            'part1_options': part1_options,
            'part2_options': part2_options,
            'model_answers': model_answers
        }
        
    except FileNotFoundError:
        print(f"❌ Feedback menu file not found: {filename}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error parsing feedback menu: {e}")
        sys.exit(1)
```

---

## Step 2: Add Menu Display Function

```python
def display_feedback_menu(part_name: str, options: List[Dict]) -> int:
    """
    Display a feedback menu and get user selection.
    
    Args:
        part_name: Name of the part (e.g., "Part 1")
        options: List of menu options from load_feedback_menu()
    
    Returns:
        Selected option number (1-based)
    """
    print(f"\n{'=' * 80}")
    print(f"SELECT FEEDBACK FOR {part_name}")
    print('=' * 80)
    
    for opt in options:
        print(f"\n{opt['number']}. {opt['name']}")
        print(f"   Feedback: \"{opt['feedback']}\"")
    
    print('=' * 80)
    
    while True:
        try:
            choice = input(f"\nSelect option (1-{len(options)}): ").strip()
            choice_num = int(choice)
            if 1 <= choice_num <= len(options):
                return choice_num
            else:
                print(f"Please enter a number between 1 and {len(options)}")
        except ValueError:
            print("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print("\n\n👋 Cancelled by user")
            sys.exit(0)
```

---

## Step 3: Modify the Override Section in main()

Replace the existing override section (around line 270-310) with:

```python
elif action == 'override':
    # Load feedback menu
    print(f"\n📋 Loading feedback menu...")
    feedback_menu = load_feedback_menu()
    
    # Get new grade from user
    new_grade = get_override_grade(selected_question['points_possible'])
    
    # Select Part 1 feedback
    part1_choice = display_feedback_menu("Part 1: Lagrangian Expression", 
                                         feedback_menu['part1_options'])
    part1_feedback = feedback_menu['part1_options'][part1_choice - 1]['feedback']
    
    # Select Part 2 feedback
    part2_choice = display_feedback_menu("Part 2: Solution Procedure",
                                         feedback_menu['part2_options'])
    part2_feedback = feedback_menu['part2_options'][part2_choice - 1]['feedback']
    
    # Combine feedback
    combined_feedback = f"{part1_feedback}\n\n{part2_feedback}"
    
    # Calculate new total grade
    new_total_grade = result.old_total_grade - result.old_question_grade + new_grade
    
    # Show preview
    print("\n" + "=" * 100)
    print("PREVIEW OF NEW GRADE")
    print("=" * 100)
    print(f"Total Score: {new_grade}/{selected_question['points_possible']}")
    print(f"\nFeedback Comment #1:")
    print("-" * 100)
    print(combined_feedback)
    print("-" * 100)
    print(f"\nModel Answers Comment #2:")
    print("-" * 100)
    print(feedback_menu['model_answers'])
    print("-" * 100)
    print(f"\nNew total quiz grade: {new_total_grade}")
    
    # Confirm before uploading
    confirm = input("\nPost these grades and comments to Canvas? (y/n): ").strip().lower()
    if confirm != 'y':
        print("  ↩️  Override cancelled")
        i += 1
        continue
    
    # Build first comment (feedback)
    feedback_comment = (
        f"Manually Graded Essay: {selected_question['title']}\n"
        f"Old score: {result.old_question_grade:.1f}\n"
        f"New score: {new_grade:.1f}\n\n"
        f"{combined_feedback}"
    )
    
    print(f"\n📤 Uploading override grade to Canvas...")
    
    # Post Comment #1: Feedback
    success1 = canvas_client.update_grade(
        selected_course['id'],
        selected_assignment['id'],
        result.student_id,
        new_total_grade,
        feedback_comment
    )
    
    if not success1:
        print(f"  ❌ Failed to upload feedback - keeping in queue")
        i += 1
        continue
    
    # Post Comment #2: Model Answers
    print(f"  📤 Posting model answers...")
    success2 = canvas_client.update_grade(
        selected_course['id'],
        selected_assignment['id'],
        result.student_id,
        new_total_grade,  # Grade unchanged, just adding comment
        feedback_menu['model_answers']
    )
    
    if success2:
        print(f"  ✅ Uploaded override grade and model answers for {result.student_name}")
        uploaded_count += 1
        # Remove from grading_results and update JSON
        grading_results.pop(i)
        data['grading_results'] = [r.__dict__ if hasattr(r, '__dict__') else r for r in grading_results]
        save_grading_data(data, json_filename)
        # Don't increment i since we removed an item
    else:
        print(f"  ⚠️  Posted feedback but model answers failed")
        # Still count as success since feedback was posted
        uploaded_count += 1
        grading_results.pop(i)
        data['grading_results'] = [r.__dict__ if hasattr(r, '__dict__') else r for r in grading_results]
        save_grading_data(data, json_filename)
```

---

## Step 4: Modify the Validate Section

Around line 240-260, update the validate action to also post model answers:

```python
if action == 'validate':
    # Load feedback menu (for model answers)
    print(f"\n📋 Loading feedback menu...")
    feedback_menu = load_feedback_menu()
    
    # Upload AI grade and feedback
    feedback = (
        f"AI-Graded Essay: {selected_question['title']}\n"
        f"Old score: {result.old_question_grade:.1f}\n"
        f"New score: {result.new_question_grade:.1f}\n\n"
        f"Feedback:\n{result.ai_feedback}"
    )
    
    print(f"\n📤 Uploading AI grade to Canvas...")
    
    # Post Comment #1: AI Feedback
    success1 = canvas_client.update_grade(
        selected_course['id'],
        selected_assignment['id'],
        result.student_id,
        result.new_total_grade,
        feedback
    )
    
    if not success1:
        print(f"  ❌ Failed to upload - keeping in queue")
        i += 1
        continue
    
    # Post Comment #2: Model Answers
    print(f"  📤 Posting model answers...")
    success2 = canvas_client.update_grade(
        selected_course['id'],
        selected_assignment['id'],
        result.student_id,
        result.new_total_grade,  # Grade unchanged, just adding comment
        feedback_menu['model_answers']
    )
    
    if success2:
        print(f"  ✅ Uploaded AI grade and model answers for {result.student_name}")
        uploaded_count += 1
        # Remove from grading_results and update JSON
        grading_results.pop(i)
        data['grading_results'] = [r.__dict__ if hasattr(r, '__dict__') else r for r in grading_results]
        save_grading_data(data, json_filename)
        # Don't increment i since we removed an item
    else:
        print(f"  ⚠️  Posted feedback but model answers failed")
        # Still count as success
        uploaded_count += 1
        grading_results.pop(i)
        data['grading_results'] = [r.__dict__ if hasattr(r, '__dict__') else r for r in grading_results]
        save_grading_data(data, json_filename)
```

---

## Step 5: Add Import at Top

Add `re` to the imports at the top of the file:

```python
import re
```

---

## Summary of Changes

### New Functions Added:
1. `load_feedback_menu()` - Parses markdown menu file
2. `display_feedback_menu()` - Shows menu and gets selection

### Modified Functions:
1. `main()` - validate action: Posts two comments
2. `main()` - override action: Uses menu system, posts two comments

### Behavior Changes:
- **Validate:** AI feedback (Comment #1) + Model answers (Comment #2)
- **Override:** User feedback from menus (Comment #1) + Model answers (Comment #2)
- **Menu-driven:** No typing, just selections
- **Flat structure:** All options shown, no conditionals

---

## Testing Checklist

After modifications:
- [ ] Script loads without errors
- [ ] Feedback menu file loads successfully
- [ ] Part 1 menu displays 4 options
- [ ] Part 2 menu displays 4 options
- [ ] Preview shows both comments
- [ ] Validate posts 2 comments to Canvas
- [ ] Override posts 2 comments to Canvas
- [ ] Model answers are identical in both paths
- [ ] Progress saves correctly after uploads

---

## Error Handling Notes

The parser assumes the menu markdown follows the exact structure we created. If you modify the menu format, you may need to adjust the regex patterns in `load_feedback_menu()`.

The script will exit gracefully if:
- Menu file not found
- Menu parsing fails
- Canvas upload fails (keeps student in queue)
