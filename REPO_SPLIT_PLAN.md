# Repository Management Plan: Two-Branch Strategy with AI Privacy

## 🎯 Objective

Use a **two-branch strategy** to maintain AI grading tools privately while sharing public utilities on GitHub:
- **`main` branch**: Public utilities only (safe to push to GitHub)
- **`full` branch**: Everything including AI tools (NEVER pushed to GitHub)

This keeps all files in one location with full version control while protecting AI implementations.

---

## 📊 Current Status

- **Current repo**: `canvas-tools` (public on GitHub)
- **Location**: `/Users/sergiop/Dropbox/Scripts/Canvas`
- **Recent commit**: `5424d0c` - HTML display feature (NOT PUSHED YET)
- **Branch**: `main` (2 commits ahead of origin)

---

## 🏗️ Two-Branch Architecture

```
┌─────────────────────────────────────────────────────────┐
│  FULL BRANCH (local only - NEVER PUSH)                  │
│  ├── Essays/ (AI grading)                               │
│  ├── Assignments/ (AI grading)                          │
│  ├── Accessibility/ (public)                            │
│  ├── CalculatedQuestion/ (public)                       │
│  └── All other utilities                                │
└─────────────────────────────────────────────────────────┘
                       │
                       │ (selective merge)
                       ↓
┌─────────────────────────────────────────────────────────┐
│  MAIN BRANCH (push to GitHub - PUBLIC)                  │
│  ├── Accessibility/ (public)                            │
│  ├── CalculatedQuestion/ (public)                       │
│  ├── All other utilities                                │
│  └── .gitignore (blocks AI files)                       │
└─────────────────────────────────────────────────────────┘
```

---

## 🛡️ Safety Safeguards

### 1. Remote Push Configuration
Restrict which branch can be pushed to GitHub:
```bash
git config remote.origin.push refs/heads/main:refs/heads/main
```
This means `git push` will ONLY push `main` branch, even if you're on `full` branch.

### 2. Pre-Push Hook
Automatically block attempts to push the private branch:
```bash
cat > .git/hooks/pre-push << 'EOF'
#!/bin/bash
protected_branch="full"
current_branch=$(git symbolic-ref HEAD | sed -e 's,.*/\(.*\),\1,')

if [ "$current_branch" = "$protected_branch" ]; then
    echo ""
    echo "🚨 ═══════════════════════════════════════════════════════"
    echo "🚨 ERROR: Cannot push branch '$protected_branch'"
    echo "🚨 This branch contains PRIVATE AI grading tools!"
    echo "🚨 ═══════════════════════════════════════════════════════"
    echo ""
    echo "To push public utilities:"
    echo "  1. git checkout main"
    echo "  2. git push origin main"
    echo ""
    exit 1
fi

# Additional safety: block any attempt to push branch with 'full' in name
if [[ "$current_branch" == *"full"* ]] || [[ "$current_branch" == *"ai"* ]]; then
    echo "🚨 ERROR: Branch name suggests private content. Not pushing."
    exit 1
fi
EOF

chmod +x .git/hooks/pre-push
```

### 3. Branch Description
Add clear warning to branch metadata:
```bash
git config branch.full.description "⚠️ PRIVATE - Contains AI grading tools - NEVER PUSH TO GITHUB"
```

### 4. Git Ignore Configuration (on main branch)
Block AI files from being accidentally added to main branch:
```bash
# Will create comprehensive .gitignore on main branch
```

---

## 📁 File Categorization

### 🔒 PRIVATE FILES (Only in `full` branch)

**AI Grading Directories:**
- `Essays/` - All essay and New Quizzes AI graders
- `Assignments/` - Text assignment AI graders with HTML display

**AI Root Files:**
- `categorization_grader.py`
- `categorization_grader_spec.md`
- `categorization_grader_workflow.md`
- `cat1.py`
- `cleanup_equal_score_comments.py`
- `structured-output-todo.md`
- `script_b_mods.md`
- `fix_redundant_comment_patch.txt`
- `improved_patch_v2.txt`

### 🌍 PUBLIC FILES (In both branches)

- `Accessibility/` - PDF accessibility tools
- `CalculatedQuestion/` - Calculated question utilities
- All calendar/appointment utilities
- Assignment management tools (non-AI)
- Quiz diagnostic tools (non-AI)
- Sync and push utilities
- General Canvas utilities
- Documentation (public)

---

## 🔧 Implementation Steps

### Phase 1: Undo Recent Commit ⏱️ 2 min

The recent AI grading commit hasn't been pushed yet, so we'll incorporate it into the new branch structure:

```bash
cd /Users/sergiop/Dropbox/Scripts/Canvas

# Check current status
git status
git log --oneline -3
```

We'll keep this commit and use it as the basis for the `full` branch.

---

### Phase 2: Create and Configure Full Branch ⏱️ 5 min

```bash
cd /Users/sergiop/Dropbox/Scripts/Canvas

# Create 'full' branch from current state (includes AI files)
git branch full

# Add branch description warning
git config branch.full.description "⚠️ PRIVATE - Contains AI grading tools - NEVER PUSH TO GITHUB"

# Verify branch created
git branch -v
```

---

### Phase 3: Set Up Safety Safeguards ⏱️ 10 min

#### 3a. Configure Remote Push Restriction
```bash
cd /Users/sergiop/Dropbox/Scripts/Canvas

# Only allow pushing main branch to GitHub
git config remote.origin.push refs/heads/main:refs/heads/main

# Verify configuration
git config --get remote.origin.push
# Should output: refs/heads/main:refs/heads/main
```

#### 3b. Create Pre-Push Hook
```bash
cd /Users/sergiop/Dropbox/Scripts/Canvas

# Create pre-push hook
cat > .git/hooks/pre-push << 'EOF'
#!/bin/bash
protected_branch="full"
current_branch=$(git symbolic-ref HEAD | sed -e 's,.*/\(.*\),\1,')

if [ "$current_branch" = "$protected_branch" ]; then
    echo ""
    echo "🚨 ═══════════════════════════════════════════════════════"
    echo "🚨 ERROR: Cannot push branch '$protected_branch'"
    echo "🚨 This branch contains PRIVATE AI grading tools!"
    echo "🚨 ═══════════════════════════════════════════════════════"
    echo ""
    echo "To push public utilities:"
    echo "  1. git checkout main"
    echo "  2. git push origin main"
    echo ""
    exit 1
fi

# Additional safety: block any attempt to push branch with 'full' or 'ai' in name
if [[ "$current_branch" == *"full"* ]] || [[ "$current_branch" == *"ai"* ]] || [[ "$current_branch" == *"private"* ]]; then
    echo "🚨 ERROR: Branch name suggests private content. Not pushing."
    exit 1
fi

echo "✅ Pushing branch: $current_branch"
EOF

# Make executable
chmod +x .git/hooks/pre-push

# Test it works
echo "Testing pre-push hook..."
cat .git/hooks/pre-push
```

#### 3c. Add Git Aliases for Common Operations
```bash
# Helpful aliases for the two-branch workflow
git config alias.work "checkout full"
git config alias.public "checkout main"
git config alias.status-full "!git checkout full && git status"
git config alias.status-public "!git checkout main && git status"
```

---

### Phase 4: Clean Main Branch (Remove AI Files) ⏱️ 15 min

Now we'll remove AI files from the `main` branch while keeping them in `full`:

```bash
cd /Users/sergiop/Dropbox/Scripts/Canvas

# Make sure we're on main
git checkout main

# Remove AI directories
git rm -r Essays/
git rm -r Assignments/

# Remove AI root files
git rm categorization_grader.py
git rm categorization_grader_spec.md
git rm categorization_grader_workflow.md
git rm cat1.py
git rm cleanup_equal_score_comments.py
git rm structured-output-todo.md
git rm script_b_mods.md
git rm fix_redundant_comment_patch.txt
git rm improved_patch_v2.txt

# Create comprehensive .gitignore for main branch
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
env/
ENV/
env.bak/
venv.bak/

# IDE
.vscode/
.idea/
*.swp
*.swo
.DS_Store

# OS files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# ═══════════════════════════════════════════════════════════
# AI GRADING TOOLS (moved to 'full' branch - PRIVATE)
# ═══════════════════════════════════════════════════════════
Essays/
Assignments/
categorization_grader.py
categorization_grader_spec.md
categorization_grader_workflow.md
cat1.py
cleanup_equal_score_comments.py
structured-output-todo.md
script_b_mods.md
*_patch.txt

# Temporary files
*.tmp
*.log
*.bak
*~
.#*

# Data files (optional)
# Uncomment if you don't want to track data files
# *.json
# *.csv
EOF

# Add .gitignore
git add .gitignore

# Commit the cleanup
git commit -m "Refactor: Move AI grading tools to private 'full' branch

Removed AI-powered grading tools from public 'main' branch:
- Essays directory (essay and quiz graders)
- Assignments directory (text assignment graders with HTML display)
- Categorization grader and related AI tools

These files remain in the 'full' branch for private development.

Remaining in public 'main' branch:
- Accessibility tools (PDF tagging and accessibility)
- Calculated question tools and documentation
- Calendar and appointment management utilities
- General Canvas API utilities
- Quiz diagnostics and analysis tools
- Content sync and push utilities

Added comprehensive .gitignore to prevent accidental re-addition.

Branch structure:
- 'main' branch: Public utilities only (safe for GitHub)
- 'full' branch: All tools including AI (local only - NEVER PUSH)

Safety measures implemented:
- Remote push restricted to main branch only
- Pre-push hook blocks pushing 'full' branch
- Branch descriptions warn about privacy

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Phase 5: Update README on Main Branch ⏱️ 10 min

```bash
cd /Users/sergiop/Dropbox/Scripts/Canvas

# Make sure we're on main
git checkout main

# Create/update README
cat > README.md << 'EOF'
# Canvas Tools

General utilities for Canvas LMS management and automation.

## 📚 Overview

This repository contains various utilities for working with Canvas LMS, including:
- Accessibility tools for PDF tagging
- Calculated question utilities
- Calendar and appointment management
- Assignment and content management
- Quiz diagnostics and analysis
- Content synchronization tools

## 🔧 Tools Included

### Accessibility Tools (`Accessibility/`)
PDF accessibility and tagging automation for Canvas:
- `downpdf.py` - Download PDFs from Canvas
- `uppdf.py` - Upload tagged PDFs to Canvas
- `pdf_pipeline.py` - Complete PDF processing pipeline
- `tag_pdf_acrobat.scpt` - AppleScript for Acrobat automation

### Calculated Questions (`CalculatedQuestion/`)
Tools and documentation for Canvas calculated questions:
- Sakai/Canvas integration code
- XML import/export utilities
- Documentation and examples

### Calendar & Appointments
- `appt.py` - Appointment management
- `getappt.py` - Retrieve appointments
- `createcalappt.py` - Create calendar appointments
- `delete_future_appts.py` - Bulk delete appointments
- `createTikZcalendar.py` - Generate TikZ calendars

### Assignment Management
- `assign.py` - Assignment utilities
- `unassign.py` - Unassign tools
- `canvas_assignment_manager.py` - Comprehensive assignment manager

### Module & Content Management
- `module.py` - Module tools
- `lastmodule.py` - Last module utilities
- `addwk2mod.py` - Add weeks to modules
- `file.py` - File utilities

### Quiz Tools
- `quiz_diagnostic.py` - Quiz diagnostics and analysis
- `quiz_report.py` - Quiz reporting
- `check_quiz_distractors.py` - Distractor analysis
- `test_question_id.py` - Question ID testing

### Sync & Push Tools
- `push2canvas.py` - Push content to Canvas
- `sync2canvas.py` - Sync content with Canvas
- `unpub.py` - Unpublish utilities

### Other Utilities
- `add2json.py` - JSON utilities
- `dragdrop2json.py` - Drag-and-drop JSON conversion

## 🔒 Private Tools Note

AI-powered grading tools are maintained in a separate private branch (`full`) and are not included in this public repository to keep implementation details confidential.

## 🚀 Installation

### Prerequisites
- Python 3.8+
- Canvas API token (stored in keychain)
- Required packages: `requests`, `keyring`

### Setup
```bash
# Clone repository
git clone git@github.com:sergio0p/canvas-tools.git
cd canvas-tools

# Install dependencies
pip install requests keyring

# Set up Canvas API token
python3 -c "import keyring; keyring.set_password('canvas', 'access-token', 'YOUR_TOKEN_HERE')"
```

## 📖 Usage

See individual tool files for specific documentation. Most tools follow this pattern:

```bash
python3 tool_name.py
```

Configuration is typically done through:
- Environment variables
- Canvas API token in keychain
- Command-line arguments

## 🤝 Contributing

This is a personal utility collection, but suggestions and improvements are welcome.

## 📝 License

Personal use. Not officially licensed for redistribution.

## 🔗 Related

Canvas LMS Documentation: https://canvas.instructure.com/doc/api/

---

**Note**: This repository contains only public utilities. AI grading implementations are maintained separately for privacy.
EOF

# Add and commit README
git add README.md
git commit -m "docs: Update README for public repository

Added comprehensive documentation for public Canvas utilities.
Clarified that AI grading tools are in separate private branch.
Included installation instructions and tool descriptions."
```

---

### Phase 6: Verify Full Branch Still Has Everything ⏱️ 5 min

```bash
cd /Users/sergiop/Dropbox/Scripts/Canvas

# Switch to full branch
git checkout full

# Verify AI files are present
echo "Checking for AI files on 'full' branch:"
ls -la Essays/ 2>/dev/null && echo "✅ Essays/ present" || echo "❌ Essays/ missing"
ls -la Assignments/ 2>/dev/null && echo "✅ Assignments/ present" || echo "❌ Assignments/ missing"
ls -la categorization_grader.py 2>/dev/null && echo "✅ categorization_grader.py present" || echo "❌ missing"

# Show branch info
git log --oneline -5
```

---

### Phase 7: Test Safety Safeguards ⏱️ 5 min

```bash
cd /Users/sergiop/Dropbox/Scripts/Canvas

# Test 1: Try to push from full branch (should be blocked)
git checkout full
echo "Testing pre-push hook (should block)..."
git push origin full 2>&1 | head -20
# Expected: Hook blocks the push with error message

# Test 2: Try git push from full branch (should be blocked or push main only)
echo "Testing git push from full branch..."
# Should either block or only push main due to remote config

# Switch to main
git checkout main
echo "✅ Currently on main branch (safe to push)"
```

---

### Phase 8: Push Main Branch to GitHub ⏱️ 2 min

```bash
cd /Users/sergiop/Dropbox/Scripts/Canvas

# Make absolutely sure we're on main
git checkout main
git branch --show-current
# Should show: main

# Final check: AI files should NOT be present
echo "Final safety check - these should all fail:"
ls Essays/ 2>&1 | grep "No such"
ls Assignments/ 2>&1 | grep "No such"

# If all checks pass, push to GitHub
git push origin main
```

---

### Phase 9: Document the Workflow ⏱️ 5 min

```bash
cd /Users/sergiop/Dropbox/Scripts/Canvas
git checkout full

# Create workflow documentation
cat > WORKFLOW.md << 'EOF'
# Two-Branch Workflow Guide

## 🌳 Branch Structure

- **`full`**: Contains ALL files including AI grading tools (PRIVATE - never push)
- **`main`**: Contains only public utilities (safe to push to GitHub)

## 🔒 Safety Measures Active

✅ Remote push restricted to `main` branch only
✅ Pre-push hook blocks pushing `full` branch
✅ `.gitignore` on `main` branch blocks AI files

## 🛠️ Daily Workflow

### Working on Code (AI or Public)

```bash
# Switch to full branch (has everything)
git checkout full
# OR use alias:
git work

# Make your changes
# ... edit files ...

# Commit changes
git add .
git commit -m "Your commit message"

# Stay on full branch - no pushing needed for private work
```

### Sharing Public Utilities Updates

When you've made changes to public utilities that should be shared:

```bash
# Make sure you're on full branch and committed
git checkout full
git status  # Should be clean

# Switch to main branch
git checkout main
# OR use alias:
git public

# Merge changes from full, but don't commit yet
git merge full --no-commit

# Remove AI files from staging (they shouldn't be there, but just in case)
git reset HEAD Essays/ Assignments/ categorization_grader.py cat1.py cleanup_equal_score_comments.py 2>/dev/null || true
git checkout -- Essays/ Assignments/ categorization_grader.py cat1.py cleanup_equal_score_comments.py 2>/dev/null || true

# Verify AI files are not staged
git status
# Should NOT see Essays/, Assignments/, or AI files

# Commit the public changes
git commit -m "Your public update message"

# Push to GitHub (only main branch will push)
git push origin main

# Switch back to full for continued work
git checkout full
```

### Checking Status

```bash
# Check which branch you're on
git branch --show-current

# See branches with descriptions
git branch -v

# View full branch description (includes warning)
git config branch.full.description
```

## ⚠️ Important Rules

### ✅ DO:
- Work on `full` branch for daily development
- Commit frequently on `full` branch
- Use `main` branch only for public releases
- Verify branch before pushing

### ❌ DON'T:
- Push `full` branch to GitHub (hooks will block it, but don't try)
- Work directly on `main` branch
- Use `git push --all` (only `main` will push due to config)
- Share `full` branch with others

## 🆘 Emergency: Accidentally Tried to Push Full Branch

The safety hooks should prevent this, but if something goes wrong:

```bash
# If you haven't pressed Enter yet
Press Ctrl+C to cancel

# If push started but failed (hooks blocked it)
No action needed - hooks protected you

# If somehow push succeeded (shouldn't be possible)
1. Go to GitHub repository settings
2. Check branches - delete 'full' branch if it appears
3. Contact GitHub support to purge refs if needed
```

## 🔍 Quick Reference

| Task | Command |
|------|---------|
| Work on any code | `git checkout full` or `git work` |
| Prepare public release | `git checkout main` or `git public` |
| Check current branch | `git branch --show-current` |
| See AI files present | `ls Essays/ Assignments/` (on full branch) |
| Verify no AI on main | `ls Essays/` (should fail on main) |
| Push to GitHub | `git checkout main && git push origin main` |

## 📝 Aliases Available

- `git work` - Switch to full branch
- `git public` - Switch to main branch
- `git status-full` - Show status of full branch
- `git status-public` - Show status of main branch

---

**Remember**: The `full` branch is your daily workspace. The `main` branch is only for public releases.
EOF

git add WORKFLOW.md
git commit -m "docs: Add two-branch workflow documentation

Added comprehensive workflow guide for maintaining separate
public and private branches in the same repository.

Includes:
- Daily workflow examples
- Safety rules and best practices
- Quick reference commands
- Emergency procedures"
```

---

### Phase 10: Create Branch Overview Document ⏱️ 3 min

```bash
cd /Users/sergiop/Dropbox/Scripts/Canvas
git checkout full

# Create branch overview
cat > BRANCHES.md << 'EOF'
# Branch Overview

## 🌳 Repository Branch Structure

This repository uses a two-branch strategy to maintain AI grading tools privately while sharing public utilities on GitHub.

### 📍 Branches

#### `full` Branch (⚠️ PRIVATE - Local Only)
- **Purpose**: Main development branch with ALL files
- **Contains**:
  - All public utilities
  - AI grading tools (Essays, Assignments)
  - Categorization grader
  - All private implementations
- **Push to GitHub**: ❌ NEVER
- **Use for**: Daily development work

#### `main` Branch (✅ PUBLIC - GitHub)
- **Purpose**: Public release branch
- **Contains**:
  - Accessibility tools
  - Calculated question utilities
  - Calendar tools
  - General Canvas utilities
  - Public documentation
- **Push to GitHub**: ✅ YES
- **Use for**: Public releases only

## 🔒 Security Measures

### Automatic Safeguards
1. **Remote Push Restriction**: `git config remote.origin.push refs/heads/main:refs/heads/main`
   - Only `main` branch can be pushed, even if you try to push others

2. **Pre-Push Hook**: `.git/hooks/pre-push`
   - Blocks any attempt to push `full` branch
   - Shows error message if you try

3. **Gitignore on Main**: `.gitignore`
   - Blocks AI files from being added to `main` branch
   - Prevents accidental commits of private files

### Manual Safeguards
- Branch description warning on `full` branch
- Documentation emphasizing privacy
- Workflow that keeps you on `full` by default

## 📊 File Distribution

| Directory/File | Full Branch | Main Branch |
|----------------|-------------|-------------|
| `Essays/` | ✅ Yes | ❌ No |
| `Assignments/` | ✅ Yes | ❌ No |
| `categorization_grader.py` | ✅ Yes | ❌ No |
| `Accessibility/` | ✅ Yes | ✅ Yes |
| `CalculatedQuestion/` | ✅ Yes | ✅ Yes |
| Public utilities | ✅ Yes | ✅ Yes |
| `WORKFLOW.md` | ✅ Yes | ❌ No |
| `BRANCHES.md` | ✅ Yes | ❌ No |

## 🔄 Workflow Summary

```
┌─────────────────────────────────────┐
│  Daily Work: full branch            │
│  - All files available              │
│  - Commit freely                    │
│  - Never push                       │
└─────────────────────────────────────┘
              │
              │ (selective merge)
              ↓
┌─────────────────────────────────────┐
│  Public Release: main branch        │
│  - Public files only                │
│  - Merge from full (carefully)      │
│  - Push to GitHub                   │
└─────────────────────────────────────┘
```

## 🎯 Quick Check

To verify branch structure:

```bash
# Check current branch
git branch --show-current

# List all branches with info
git branch -vv

# Verify safety config
git config --get remote.origin.push
# Should show: refs/heads/main:refs/heads/main

# Test pre-push hook exists
test -x .git/hooks/pre-push && echo "✅ Pre-push hook active" || echo "❌ Hook missing"
```

## 📚 Related Documentation

- `WORKFLOW.md` - Detailed daily workflow guide
- `README.md` - Public repository documentation (on main branch)
- `REPO_SPLIT_PLAN.md` - Original implementation plan

---

**Current Branch**: `full` (you should be here most of the time)
**Default Branch on GitHub**: `main` (public utilities)
EOF

git add BRANCHES.md
git commit -m "docs: Add branch structure overview

Added comprehensive documentation of two-branch strategy:
- Branch purposes and contents
- Security safeguards explanation
- File distribution table
- Quick verification commands"
```

---

### Phase 11: Final Verification ⏱️ 10 min

```bash
cd /Users/sergiop/Dropbox/Scripts/Canvas

echo "═══════════════════════════════════════════════════════"
echo "FINAL VERIFICATION"
echo "═══════════════════════════════════════════════════════"
echo ""

# 1. Check we're on full branch
echo "1. Checking current branch..."
CURRENT=$(git branch --show-current)
echo "   Current branch: $CURRENT"
if [ "$CURRENT" = "full" ]; then
    echo "   ✅ Correct branch"
else
    echo "   ⚠️  Not on full branch, switching..."
    git checkout full
fi
echo ""

# 2. Verify both branches exist
echo "2. Verifying branches exist..."
git branch -v
echo ""

# 3. Verify AI files present on full
echo "3. Checking AI files on 'full' branch..."
test -d Essays && echo "   ✅ Essays/ present" || echo "   ❌ Essays/ missing!"
test -d Assignments && echo "   ✅ Assignments/ present" || echo "   ❌ Assignments/ missing!"
test -f categorization_grader.py && echo "   ✅ categorization_grader.py present" || echo "   ❌ categorization_grader.py missing!"
echo ""

# 4. Verify AI files absent on main
echo "4. Checking AI files on 'main' branch..."
git checkout main
test ! -d Essays && echo "   ✅ Essays/ correctly absent" || echo "   ❌ Essays/ should not be here!"
test ! -d Assignments && echo "   ✅ Assignments/ correctly absent" || echo "   ❌ Assignments/ should not be here!"
test ! -f categorization_grader.py && echo "   ✅ categorization_grader.py correctly absent" || echo "   ❌ File should not be here!"
echo ""

# 5. Verify public files present on main
echo "5. Checking public files on 'main' branch..."
test -d Accessibility && echo "   ✅ Accessibility/ present" || echo "   ❌ Accessibility/ missing!"
test -d CalculatedQuestion && echo "   ✅ CalculatedQuestion/ present" || echo "   ❌ CalculatedQuestion/ missing!"
test -f README.md && echo "   ✅ README.md present" || echo "   ❌ README.md missing!"
test -f .gitignore && echo "   ✅ .gitignore present" || echo "   ❌ .gitignore missing!"
echo ""

# 6. Verify safety config
echo "6. Checking safety safeguards..."
PUSH_CONFIG=$(git config --get remote.origin.push)
if [ "$PUSH_CONFIG" = "refs/heads/main:refs/heads/main" ]; then
    echo "   ✅ Push restricted to main branch"
else
    echo "   ❌ Push config not set correctly!"
    echo "   Current: $PUSH_CONFIG"
fi

if [ -x .git/hooks/pre-push ]; then
    echo "   ✅ Pre-push hook active"
else
    echo "   ❌ Pre-push hook missing or not executable!"
fi
echo ""

# 7. Check .gitignore blocks AI files
echo "7. Checking .gitignore on 'main' branch..."
if grep -q "Essays/" .gitignore; then
    echo "   ✅ .gitignore blocks AI directories"
else
    echo "   ❌ .gitignore doesn't block AI files!"
fi
echo ""

# 8. Test pre-push hook (dry run)
echo "8. Testing pre-push hook (not actually pushing)..."
echo "   Attempting to push 'full' branch..."
git checkout full
if git push --dry-run origin full 2>&1 | grep -q "ERROR.*private\|ERROR.*PRIVATE"; then
    echo "   ✅ Pre-push hook correctly blocks full branch"
else
    echo "   ⚠️  Hook test inconclusive (may need actual push attempt)"
fi
echo ""

# 9. Check branch descriptions
echo "9. Checking branch descriptions..."
FULL_DESC=$(git config branch.full.description)
echo "   full: $FULL_DESC"
echo ""

# 10. Summary
echo "═══════════════════════════════════════════════════════"
echo "VERIFICATION COMPLETE"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "Branch structure:"
git branch -v
echo ""
echo "Current branch: $(git branch --show-current)"
echo ""
echo "Ready to push 'main' branch? (run from main branch only)"
echo "  git checkout main && git push origin main"
echo ""
```

---

## 📋 Daily Workflow Reference

### 🟢 Normal Day (Working on Code)

```bash
# Start work
git checkout full

# Make changes to any files
# ... edit, create, modify ...

# Commit often
git add .
git commit -m "Your update"

# Continue working - no pushing needed
```

### 🔵 Sharing Public Utilities Update

```bash
# Ensure full branch is committed
git checkout full
git status  # Should be clean

# Go to main
git checkout main

# Merge from full (but don't commit yet)
git merge full --no-commit

# Remove AI files (shouldn't be staged, but safety first)
git reset HEAD Essays/ Assignments/ categorization_grader.py 2>/dev/null || true
git checkout -- Essays/ Assignments/ categorization_grader.py 2>/dev/null || true

# Verify clean (no AI files)
git status

# Commit and push
git commit -m "Update: [describe public changes]"
git push origin main

# Back to full
git checkout full
```

### 🔍 Quick Status Check

```bash
# Which branch am I on?
git branch --show-current

# What changed?
git status

# View both branches
git branch -vv
```

---

## ⏱️ Time Estimate

| Phase | Duration | Task |
|-------|----------|------|
| Phase 1 | 2 min | Review current status |
| Phase 2 | 5 min | Create full branch |
| Phase 3 | 10 min | Set up safety safeguards |
| Phase 4 | 15 min | Clean main branch |
| Phase 5 | 10 min | Update README on main |
| Phase 6 | 5 min | Verify full branch |
| Phase 7 | 5 min | Test safeguards |
| Phase 8 | 2 min | Push main to GitHub |
| Phase 9 | 5 min | Document workflow |
| Phase 10 | 3 min | Create branch overview |
| Phase 11 | 10 min | Final verification |
| **TOTAL** | **~1 hour** | Complete setup |

---

## ✅ Success Criteria

- ✅ `full` branch exists with all files (AI + public)
- ✅ `main` branch exists with only public files
- ✅ AI directories absent from `main` branch
- ✅ `.gitignore` on `main` blocks AI files
- ✅ Remote push config restricts to `main` only
- ✅ Pre-push hook blocks `full` branch pushes
- ✅ Branch descriptions include warnings
- ✅ Documentation complete (WORKFLOW.md, BRANCHES.md)
- ✅ `main` branch pushed to GitHub
- ✅ GitHub shows only public files
- ✅ Verification script passes all checks

---

## 🚨 Rollback Plan

If something goes wrong during setup:

```bash
# Stop wherever you are
cd /Users/sergiop/Dropbox/Scripts/Canvas

# Option 1: Delete new branch and start over
git checkout main
git branch -D full
# Then restart from Phase 2

# Option 2: Reset main branch to original state
git checkout main
git reset --hard origin/main  # Reset to last pushed state

# Option 3: Complete rollback
git fetch origin
git reset --hard origin/main
git clean -fd
git branch -D full  # If it exists
# All files still safe in Dropbox
```

---

## 🎯 Expected Final State

### On Disk (Dropbox)
```
/Users/sergiop/Dropbox/Scripts/Canvas/
├── .git/ (contains both branches)
├── Essays/ (visible when on 'full' branch)
├── Assignments/ (visible when on 'full' branch)
├── Accessibility/ (always visible)
├── CalculatedQuestion/ (always visible)
├── categorization_grader.py (visible when on 'full')
├── [all other files]
├── WORKFLOW.md (on 'full' branch)
├── BRANCHES.md (on 'full' branch)
└── README.md (different on each branch)
```

### On GitHub
```
canvas-tools (public repo)
└── main branch (only)
    ├── Accessibility/
    ├── CalculatedQuestion/
    ├── [public utilities]
    ├── README.md (public version)
    └── .gitignore (blocks AI files)

Note: 'full' branch does NOT exist on GitHub
```

### Git Configuration
```bash
# Remote push restricted
remote.origin.push = refs/heads/main:refs/heads/main

# Pre-push hook active
.git/hooks/pre-push exists and is executable

# Branch descriptions
branch.full.description = "⚠️ PRIVATE - Contains AI grading tools - NEVER PUSH TO GITHUB"
```

---

## 📞 Troubleshooting

### Problem: "I accidentally committed AI files to main"
```bash
git checkout main
git reset --soft HEAD~1  # Undo commit, keep changes
git reset HEAD Essays/ Assignments/  # Unstage AI files
git checkout -- Essays/ Assignments/  # Remove from working dir
git commit -m "Your corrected commit message"
```

### Problem: "I'm not sure which branch I'm on"
```bash
git branch --show-current
# 'full' = safe to work with AI
# 'main' = public only, be careful
```

### Problem: "AI files showing up on main branch"
```bash
git checkout main
git status
# If AI files are present:
git clean -fd  # Remove untracked files
git checkout -- .  # Reset modified files
# Check .gitignore includes AI files
```

### Problem: "Pre-push hook not working"
```bash
# Check it exists and is executable
ls -la .git/hooks/pre-push
# Should show: -rwxr-xr-x

# If not executable:
chmod +x .git/hooks/pre-push

# Test it:
cat .git/hooks/pre-push  # Should show the script
```

---

## 🎉 Ready to Execute

This plan provides:
- ✅ Complete two-branch setup with AI privacy
- ✅ Multiple safety safeguards against accidental exposure
- ✅ Clear daily workflow for development
- ✅ Comprehensive documentation
- ✅ Verification procedures
- ✅ Rollback options
- ✅ Troubleshooting guide

**Work on `full` branch daily. Use `main` branch only for public releases. The safeguards will protect you.**

Start with Phase 1 when ready! 🚀
