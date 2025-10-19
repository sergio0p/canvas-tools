# Manual Override Feedback Menu
## Constrained Optimization Essay - Lagrangian Method

---

## Part 1: Lagrangian Expression

**Select ONE feedback option:**

1. **Correct**
   ```
   Part 1: 1/1
   ```

2. **Objective function incorrect**
   ```
   Part 1: 0/1 — Objective function incorrect
   ```

3. **Constraint incorrect**
   ```
   Part 1: 0/1 — Constraint incorrect
   ```

4. **Lagrange multiplier sign incorrect**
   ```
   Part 1: 0/1 — Lagrange multiplier sign incorrect
   ```

---

## Part 2: Solution Procedure

**Select ONE feedback option:**

1. **Correct**
   ```
   Part 2: 1/1
   ```

2. **Gradient step omits x, y, or multiplier** (partial credit)
   ```
   Part 2: 0.5/1 — Gradient step omits x, y, or multiplier
   ```

3. **The recipe steps are missing or incorrect**
   ```
   Part 2: 0/1 — The recipe steps are missing or incorrect
   ```

4. **Missing explicit mention of taking derivatives with respect to all three variables**
   ```
   Part 2: 0/1 — Must explicitly mention taking partial derivatives with respect to x, y, and λ
   ```

---

## Model Answers (Posted Separately as Second Comment)

**This text will be automatically posted as a separate comment after grading feedback:**

```
MODEL ANSWERS:

Part 1: Lagrangian Expression
xy - x² + log(y) - λ(x + 3y - 100)

Part 2: Solution Procedure
1. Set up/write the Lagrangian
2. Take partial derivatives (gradient) with respect to x, y, and lambda
3. Set derivatives equal to zero (first-order conditions, FOCs)
4. Solve the system of equations for x, y, and lambda
```

---

## Quick Reference: Total Grade to Part Scores

**Total 2.0** = Part 1: 1/1 + Part 2: 1/1  
**Total 1.5** = Part 1: 1/1 + Part 2: 0.5/1  
**Total 1.0** = Part 1: 1/1 + Part 2: 0/1 OR Part 1: 0/1 + Part 2: 1/1  
**Total 0.5** = Part 1: 0/1 + Part 2: 0.5/1  
**Total 0.0** = Part 1: 0/1 + Part 2: 0/1

---

## Usage Notes for Script Implementation

**Workflow:**
1. Get total grade from user (0-2.0)
2. Show Part 1 menu → user selects option (1-4)
3. Show Part 2 menu → user selects option (1-4)
4. Post feedback as Comment #1
5. Automatically post model answers as Comment #2

**Part 1 Menu has 4 options**
**Part 2 Menu has 4 options**
**Always post model answers separately**
