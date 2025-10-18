import datetime

# Prompt user for calendar parameters
first_day = input("📅 Enter the first day of classes (YYYY-MM-DD): ")
last_day = input("📅 Enter the last day of classes (YYYY-MM-DD): ")
wellbeing_days = input("😌 Enter Well-Being Days (comma-separated YYYY-MM-DD, if any): ").split(',')
break_start = input("🌴 Enter the start date of break (YYYY-MM-DD): ")
break_end = input("🌴 Enter the end date of break (YYYY-MM-DD): ")
university_day = input("🎓 Enter University Day (YYYY-MM-DD, leave blank if none): ")
final_exam = input("📝 Enter Final Exam Date (YYYY-MM-DD): ")

# Convert to datetime
first_day = datetime.date.fromisoformat(first_day.strip())
last_day = datetime.date.fromisoformat(last_day.strip())
break_start = datetime.date.fromisoformat(break_start.strip())
break_end = datetime.date.fromisoformat(break_end.strip())
university_day = university_day.strip()
university_day = datetime.date.fromisoformat(university_day) if university_day else None
final_exam = datetime.date.fromisoformat(final_exam.strip())
wellbeing_days = [datetime.date.fromisoformat(d.strip()) for d in wellbeing_days if d.strip()]

# Collect all no-class days
off_days = set(wellbeing_days)
off_days.update([break_start + datetime.timedelta(days=i) for i in range((break_end - break_start).days + 1)])
if university_day:
    off_days.add(university_day)

# Generate T/Th schedule
current = first_day
schedule = []
while current <= last_day:
    if current.weekday() in [1, 3]:  # Tuesday=1, Thursday=3
        if current in off_days:
            schedule.append((current, f"No Class — {current.strftime('%A')} Break"))
        else:
            schedule.append((current, ""))
    current += datetime.timedelta(days=1)

# Append final exam
schedule.append((final_exam, "Final Exam"))

# Generate TikZ output
tikz = """
\\large {\\textsc{Tentative coverage} }\\\\
\\tikzset{ms1/.style={row #1 column 1/.append style={execute at begin node=Week \\space \\the\\numexpr#1-1}}}
\\tikzset{ms2/.style={row #1 column 1/.append style={execute at begin node=Week \\space \\the\\numexpr#1+7}}}
Abbreviations: PS = Problem Set; Q = Quiz; TBA = To Be Announced \\
\\begin{tikzpicture}
\\matrix[
  matrix of nodes,
  column sep=-\\pgflinewidth,
  row sep=-\\pgflinewidth,
  execute at empty cell={\\node{\\phantom{$\\cdot$}};},
  nodes={draw, align=left, anchor=north west,
    text depth=0.9cm,
    text height=0.9cm,
    minimum width=8cm},
  text width=8cm,
  ms1/.list={2,...}]{
  &Tuesday &Thursday \\
"""

# Format rows
rows = []
i = 0
while i < len(schedule):
    left = right = ""
    if i < len(schedule) and schedule[i][0].weekday() == 1:
        left = f"{schedule[i][0].strftime('%-m/%-d')}: {schedule[i][1]}"
        i += 1
    if i < len(schedule) and schedule[i][0].weekday() == 3:
        right = f"{schedule[i][0].strftime('%-m/%-d')}: {schedule[i][1]}"
        i += 1
    rows.append(f":  & {left} & {right}\\\\\n")

tikz += ''.join(rows)
tikz += "};\\end{tikzpicture}\n"

# Save to file
with open("generated_calendar.tex", "w") as f:
    f.write(tikz)

print("✅ TikZ calendar written to generated_calendar.tex")