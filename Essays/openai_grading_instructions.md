# Simplified Grading Instructions

## The Problem

**Maximize:** f(x,y) = xy - x² + log(y)  
**Subject to:** x + 3y = 100

Students must answer two questions:
1. Write the Lagrangian expression
2. Describe the solution steps (no computations needed)

## Model Answers

### Part 1: Lagrangian Expression
```
xy - x² + log(y) - λ(x + 3y - 100)
```

**Valid variations:**
- Different multiplier names: λ, lambda, l, μ, delta, δ, Δ, "Lagrangian multiplier", "multiplier"
- Flipped constraint sign: `+ λ(100 - x - 3y)` is also correct
- Different orderings of terms
- Implicit multiplication: `xy` or `x*y` both fine

### Part 2: Solution Procedure
1. Set up/write the Lagrangian
2. Take partial derivatives (i.e., gradient) with respect to x, y, AND λ (must mention all three)
3. Set derivatives equal to zero
4. Solve the system of equations

## Grading Criteria

### Part 1: Lagrangian Expression (1 point)

**Award 1 point if the student writes an expression equivalent to:**
```
xy - x² + log(y) - λ(x + 3y - 100)
```

**Award 0 points if:**
- Missing or wrong terms in the objective function
- Wrong constraint expression
- Wrong sign on the multiplier term

### Part 2: Solution Procedure (1 point)

**Award 1 point if student describes ALL four steps:**
1. Set up/write the Lagrangian
2. Take partial derivatives (i.e., gradient) with respect to x, y, AND λ (must mention all three)
3. Set derivatives equal to zero
4. Solve the system of equations

**Award 0 points if:**
- Missing any of the four steps
- Step 2 doesn't mention all three variables (x, y, λ)
- Steps are in illogical order

## Output Format

Return ONLY a JSON object with this structure:

```json
{
  "grade": <number 0.0 to 2.0>,
  "feedback": "<multi-line string>"
}
```

### Feedback Format

**For Part 1:**
- If correct (1 pt): Just say "Part 1: 1/1"
- If incorrect (0 pt): Say "Part 1: 0/1 — [brief reason]"

**For Part 2:**
- If correct (1 pt): Just say "Part 2: 1/1"  
- If incorrect (0 pt): Say "Part 2: 0/1 — [brief reason]"

Keep feedback concise. One sentence per part is enough. **Do not include model answers in the feedback.**

## Examples

**Example 1 - Perfect answer:**
```
Student: "L = xy - x² + log(y) - λ(x + 3y - 100). Steps: write Lagrangian, take derivatives wrt x,y,λ, set to zero, solve system"

Response:
{
  "grade": 2.0,
  "feedback": "Part 1: 1/1\nPart 2: 1/1"
}
```

**Example 2 - Wrong sign in Part 1, incomplete Part 2:**
```
Student: "L = xy - x² + log(y) + λ(x + 3y - 100). Take derivatives and solve"

Response:
{
  "grade": 0.0,
  "feedback": "Part 1: 0/1 — Wrong sign on multiplier for this constraint form\nPart 2: 0/1 — Missing steps: setting derivatives to zero, taking derivative wrt λ"
}
```

**Example 3 - Correct Part 1, missing variable in Part 2:**
```
Student: "L = xy - x² + log(y) - λ(x + 3y - 100). Take derivatives wrt x and y, set to zero, solve"

Response:
{
  "grade": 1.0,
  "feedback": "Part 1: 1/1\nPart 2: 0/1 — Must take derivative with respect to λ (the multiplier) as well"
}
```

## Key Points

- Be generous with notation variations (λ vs lambda vs l, etc.)
- Be strict about the four-step procedure in Part 2
- Keep feedback brief and actionable
- Always return valid JSON with no markdown code blocks
- The `grade` field must equal sum of part scores (0, 1, or 2)
- **Do not include model answers in your feedback response**
