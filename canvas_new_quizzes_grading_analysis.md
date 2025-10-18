
# Canvas New Quizzes Grade Update Analysis
## HAR File Analysis Results

## Summary
When you change a grade for a question in a New Quizzes assessment, Canvas uses a **dedicated Quiz API** 
endpoint separate from the main Canvas API. This is an external tool integration that bypasses the 
standard Canvas REST API.

## Key Endpoint Discovered

**POST** `https://{institution}.quiz-api-iad-prod.instructure.com/api/quiz_sessions/{session_id}/results`

- **HTTP Method**: POST
- **Status Code**: 201 (Created)
- **Content-Type**: application/json
- **Authentication**: JWT Bearer token (in Authorization header)

## Request Structure

The request sends a `results` array containing ALL question results for the quiz session, not just 
the changed question:

```json
{
  "results": [
    {
      "id": "{session_id}_{position}",
      "itemId": "411636",
      "attempt": 1,
      "position": 1,
      "pointsPossible": 2,
      "score": 1,
      "gradingMethod": "autograde",
      "gradedAt": "2025-09-04T14:40:57.000+00:00",
      "graderId": null,
      "scoredData": {
        "gradeStatus": "graded"
      },
      "feedback": {
        "itemFeedback": {}
      },
      "answerFeedback": null,
      "regradeInfo": null,
      "errors": {}
    }
  ],
  "fudge_points": null
}
```

## Key Fields Explanation

### Per-Question Result Object:
- **id**: Format `{session_id}_{position}` (e.g., "1576616_1")
- **itemId**: The question/item ID (e.g., "411636")
- **score**: The actual score awarded (can be null for ungraded)
- **pointsPossible**: Maximum points for this question
- **gradingMethod**: "autograde" or "manual_grading"
- **gradeStatus**: "graded", "waiting", or other status
- **gradedAt**: ISO 8601 timestamp
- **graderId**: Instructor ID (null for autograde)
- **position**: Question order (1-based)
- **attempt**: Attempt number

### Top-Level Fields:
- **fudge_points**: Additional points to add/subtract from total (can adjust overall quiz score)

## Response Structure

The API returns a comprehensive result object:

```json
{
  "id": "2421675",
  "quiz_session_id": "1576616",
  "score": 1.0,
  "points_possible": 4.0,
  "percentage": 0.25,
  "status": "graded",
  "grading_method": "manual_grading",
  "fudge_points": null,
  "created_at": "2025-10-17T13:09:21.545Z",
  "updated_at": "2025-10-17T13:09:21.601Z",
  "quiz_session": {
    "id": "1576616",
    "status": "graded",
    "attempt": 1,
    "metadata": {
      "user_uuid": "...",
      "user_full_name": "Boluwatife Adeshina",
      "user_avatar_image_url": "..."
    }
  }
}
```

## Authentication

The endpoint uses **JWT-based authentication** with a Bearer token in the Authorization header:

```
Authorization: eyJhbGciOiJIUzUxMiJ9...
```

The JWT token contains:
- `host`: Quiz API host
- `consumer_key`: LTI consumer key
- `scope`: "quiz_session.grade"
- `user`: Object with user_id, canvas_user_id, role, contexts
- `resource_id`: The quiz session ID

## API Flow Sequence

1. **POST** to `/api/quiz_sessions/{session_id}/results` with updated scores
2. **GET** `/api/quiz_sessions/{session_id}?anonymous_grading` - Fetch updated session
3. **GET** `/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions/{user_id}.json` - Fetch Canvas submission
4. **GET** `/api/quiz_sessions/{session_id}/session_items` - Fetch all questions
5. **GET** `/api/quiz_sessions/{session_id}/results/{result_id}/session_item_results` - Fetch individual results

## Important Notes

1. **External Tool Integration**: New Quizzes uses `quiz-api-iad-prod.instructure.com`, NOT the main 
   Canvas API domain. This is an LTI-based external tool.

2. **Batch Updates**: The API requires sending ALL question results, not just the changed one. You 
   must include the complete results array with all questions.

3. **No Direct Canvas API**: There is no standard Canvas REST API endpoint for updating New Quizzes 
   item scores. You must use the Quiz API.

4. **Token Scope**: The JWT token must have `quiz_session.grade` scope to update grades.

5. **Result ID**: Each submission of results creates a new result record with a unique ID.

## How to Use This Programmatically

To update a question grade in New Quizzes:

1. Obtain a valid JWT token with `quiz_session.grade` scope
2. Fetch current results: `GET /api/quiz_sessions/{session_id}/results/{result_id}/session_item_results`
3. Modify the score for the specific question
4. POST the complete results array back to `/api/quiz_sessions/{session_id}/results`
5. The response will contain the updated overall score and percentage

## Example Update Scenario

**Original**: Question 1 scored 1/2 points (autograde)
**Change**: Manually override to 2/2 points

```json
{
  "results": [
    {
      "id": "1576616_1",
      "itemId": "411636",
      "score": 2,              // Changed from 1 to 2
      "gradingMethod": "manual_grading",  // Changed from autograde
      "graderId": 5256,        // Add grader ID
      // ... rest of fields
    }
  ]
}
```

## Critical Limitation: No Programmatic Access

**IMPORTANT**: Based on the HAR analysis, there appears to be **NO WAY to programmatically update grades**
in New Quizzes outside of the Canvas UI. Here's why:

### Authentication Barrier

The Quiz API uses **JWT tokens that are generated by Canvas internally** when you access the grading interface
through the browser. These tokens:

1. **Are NOT obtainable via Canvas REST API**: There's no documented Canvas API endpoint to generate these tokens
2. **Use HMAC-SHA512 signing**: The token is signed with a secret key only Canvas knows
3. **Require LTI launch context**: The tokens appear to be generated during an LTI tool launch, not via API
4. **Are session-specific**: Tied to specific quiz sessions and user contexts

### Token Structure
```
Algorithm: HS512 (HMAC-SHA512)
Consumer Key: e0f78f219e7ba914a2e946a83f1895c04d3c9cb64561c79b513255656ae28f08
Scope: quiz_session.grade
Expiration: Unix timestamp
```

The token includes user context, role, and specific quiz session ID - all generated internally by Canvas.

### Why This Blocks Automation

1. **No API endpoint** to obtain quiz-api JWT tokens
2. **Can't forge tokens** without knowing Canvas's signing secret
3. **LTI-only authentication**: Requires browser-based LTI launch flow
4. **External tool integration**: New Quizzes is a separate service, not part of Canvas core

### Possible Workarounds (None Ideal)

1. **Browser automation (Selenium/Puppeteer)**:
   - Log into Canvas as instructor
   - Navigate to quiz grading interface
   - Extract JWT token from browser session
   - Use token for API calls (until it expires)
   - **Fragile and violates ToS**

2. **Request Canvas to add API support**:
   - Feature request to Canvas/Instructure
   - Ask for gradebook API to support New Quizzes item-level grading
   - Long-term solution but requires Canvas development

3. **Use Canvas Gradebook API instead**:
   - Update the overall assignment grade using Canvas REST API
   - `/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions/{user_id}`
   - **Cannot update individual question scores**, only final grade
   - Loses granularity of per-question grading

## Conclusion

Canvas New Quizzes uses a **separate external Quiz API** that is NOT part of the standard Canvas REST API.
Grade updates require posting the complete results array to the quiz-api subdomain with proper JWT authentication.

**However, there is NO documented way to obtain the required JWT tokens programmatically**, making
automated grading of individual New Quizzes questions effectively impossible without browser automation
or Canvas adding official API support for this functionality.

### Recommendation

If you need programmatic grading:
1. Use **Classic Quizzes** instead of New Quizzes (Canvas API supports them)
2. Use **Assignments** for gradable content (full API support)
3. Contact Canvas support to request New Quizzes API access
4. Accept limitation and use manual grading or grade entire quiz (not individual questions)
