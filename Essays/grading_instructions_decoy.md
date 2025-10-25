# Grading Instructions: Decoy Effect Question

## The Problem

Students are shown SD memory card pricing:
- 32GB: $39.99
- 64GB: $59.99
- 128GB: $107.99
- 256GB: $229.99
- 512GB: $599.99

Students must answer three questions:
1. Can you find evidence of a decoy effect? (Answer yes or no)
2. If yes, what is the decoy?
3. If yes, what choice is the decoy trying to promote?

## Grading Criteria

**Grade = 4 points** if ALL of the following are true:
- Answers to parts 1, 2, and 3 are internally consistent with each other
- The logic and reasoning are sound (no contradictions)
- Any factual claims about prices or GB amounts are correct
- The concept of decoy effect is used correctly (a decoy must make another option look better by comparison)

**Grade = 3 points** if ANY of the following problems exist:
- Inconsistencies between answers (e.g., says "no decoy" in part 1 but identifies one in part 2)
- Misunderstanding of decoy effect concept (e.g., calling the cheapest or most expensive option a decoy without proper justification)
- Illogical reasoning or contradictions in the argument
- Factual errors (e.g., wrong price-per-GB calculations, incorrect capacity amounts)

## Key Concepts

**What is a decoy effect?**
A decoy is an option positioned to make another specific option look more attractive by comparison. The decoy is typically inferior or less attractive in a way that highlights the target option's value.

**Valid interpretations:**
- Different students may identify different options as decoys
- Students may answer "yes" or "no" to part 1
- What matters is internal consistency and logical soundness of their argument

## Output Format

Return ONLY a JSON object with this structure:

```json
{
  "grade": <number 3 or 4>,
  "feedback": "<brief string or empty string>"
}
```

## Feedback Guidelines

**When grade = 4:**
- Return empty feedback: `"feedback": ""`
- No explanation needed for correct answers

**When grade = 3:**
- Provide brief, specific feedback ONLY if there's evidence of conceptual misunderstanding
- Point out the specific error: inconsistency, factual error, or conceptual confusion
- Keep it to 1-2 sentences maximum
- Do NOT provide feedback for minor issues if the core understanding is sound

**Examples of feedback:**
- "Your answers are inconsistent: you said there is no decoy effect but then identified 512GB as a decoy."
- "The price-per-GB for 256GB is $0.90, not $1.20 as stated."
- "A decoy effect requires one option to make another look better; the cheapest option doesn't typically serve this role."

## Examples

**Example 1 - Consistent "Yes" answer:**
```
Student: "Yes, there is a decoy effect. The 512GB at $599.99 is the decoy because it has a worse price-per-GB ($1.17) than 256GB ($0.90), making 256GB look like better value."

Response:
{
  "grade": 4,
  "feedback": ""
}
```

**Example 2 - Consistent "No" answer:**
```
Student: "No, there is no clear decoy effect. The pricing follows typical market segmentation where higher capacities cost more per GB due to premium positioning and manufacturing costs. Each option serves a different customer segment."

Response:
{
  "grade": 4,
  "feedback": ""
}
```

**Example 3 - Inconsistent answer:**
```
Student: "No decoy effect exists. But the 128GB option is the decoy to promote 256GB."

Response:
{
  "grade": 3,
  "feedback": "Your answers are inconsistent: you said there is no decoy effect but then identified 128GB as a decoy."
}
```

**Example 4 - Factual error:**
```
Student: "Yes, 256GB is the decoy. It costs $2.00 per GB while 128GB only costs $0.50 per GB."

Response:
{
  "grade": 3,
  "feedback": "The price-per-GB calculations are incorrect. 256GB is $0.90/GB and 128GB is $0.84/GB."
}
```

**Example 5 - Conceptual misunderstanding:**
```
Student: "Yes, the 32GB option is the decoy because it's the cheapest and makes people want to buy more expensive options."

Response:
{
  "grade": 3,
  "feedback": "A decoy effect requires one option to make another specific option look better by comparison, not simply being cheap to encourage upselling."
}
```

## Important Notes

- Be generous with interpretation - multiple valid answers exist
- Focus on internal consistency and logical soundness, not on agreeing with a specific interpretation
- Only provide feedback when there's clear conceptual confusion or factual errors
- Empty feedback is preferred for correct answers
- The grade must be exactly 3 or 4 - no other values allowed
- Always return valid JSON with no markdown code blocks
