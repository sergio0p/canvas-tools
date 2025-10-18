
# quiz_diagnostic.py
"""
Canvas Quiz Diagnostic Tool
Extracts quiz question structures and sample submissions to understand categorization question formats.
"""

import sys
import json
import requests
import keyring
from typing import List, Dict, Optional
from datetime import datetime


# === CONFIGURATION ===
SERVICE_NAME = 'canvas'
USERNAME = 'access-token'
API_BASE = "https://uncch.instructure.com/api/v1"
COURSE_ID = 97934  # ECON 510 course ID


class CanvasQuizDiagnostic:
    """Diagnostic tool for analyzing Canvas quiz structures"""

    def __init__(self, course_id: int):
        """Initialize the diagnostic tool"""
        self.course_id = course_id
        self.api_token = self._get_api_token()
        self.headers = {'Authorization': f'Bearer {self.api_token}'}
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def _get_api_token(self) -> str:
        """Retrieve API token from keychain"""
        token = keyring.get_password(SERVICE_NAME, USERNAME)
        if not token:
            print(f"❌ ERROR: No Canvas API token found in keychain.")
            print(f"Set one using: keyring.set_password('{SERVICE_NAME}', '{USERNAME}', 'your_token')")
            sys.exit(1)
        return token

    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make an API request with error handling"""
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            print(f"❌ HTTP ERROR: {e}")
            print(f"Response: {e.response.text}")
            raise
        except requests.exceptions.RequestException as e:
            print(f"❌ REQUEST ERROR: {e}")
            raise

    def get_quiz_assignments(self) -> List[Dict]:
        """Fetch all quiz assignments for the course"""
        print(f"\n🔍 Fetching quiz assignments for course {self.course_id}...")

        assignments = []
        url = f"{API_BASE}/courses/{self.course_id}/assignments"
        params = {'per_page': 100}

        while url:
            try:
                response = self._make_request('GET', url, params=params)
                batch = response.json()

                # Filter for quiz assignments (both Classic and New Quizzes)
                # Classic quizzes have is_quiz_assignment == True
                # New Quizzes are external_tool assignments with "quiz" in the URL
                quizzes = []
                for a in batch:
                    # Classic quiz
                    if a.get('is_quiz_assignment', False):
                        quizzes.append(a)
                    # New Quiz (LTI assignment with quiz in external tool)
                    elif 'external_tool' in a.get('submission_types', []):
                        ext_tool = a.get('external_tool_tag_attributes', {})
                        if ext_tool and 'quiz' in ext_tool.get('url', '').lower():
                            quizzes.append(a)

                assignments.extend(quizzes)

                # Handle pagination
                if 'next' in response.links:
                    url = response.links['next']['url']
                    params = {}
                else:
                    url = None
            except Exception as e:
                print(f"❌ ERROR fetching assignments: {e}")
                sys.exit(1)

        if not assignments:
            print("❌ No quiz assignments found in this course.")
            sys.exit(1)

        print(f"✅ Found {len(assignments)} quiz assignment(s)")
        return assignments

    def display_quizzes(self, quizzes: List[Dict]) -> None:
        """Display quizzes in a numbered list"""
        print("\n" + "="*60)
        print("QUIZ ASSIGNMENTS")
        print("="*60)
        for idx, quiz in enumerate(quizzes, 1):
            name = quiz.get('name', 'Unnamed Quiz')
            quiz_id = quiz.get('quiz_id')
            assignment_id = quiz.get('id')

            # Classic quizzes have quiz_id, New Quizzes use assignment_id
            if quiz_id:
                print(f"{idx}. {name} (Quiz ID: {quiz_id})")
            else:
                print(f"{idx}. {name} (Assignment ID: {assignment_id}) [New Quiz]")
        print("="*60)

    def select_quiz(self, quizzes: List[Dict]) -> Optional[Dict]:
        """Prompt user to select a quiz"""
        while True:
            try:
                choice = input("\nEnter quiz number (or 'q' to quit): ").strip()

                if choice.lower() == 'q':
                    print("👋 Exiting...")
                    return None

                quiz_num = int(choice)

                if 1 <= quiz_num <= len(quizzes):
                    return quizzes[quiz_num - 1]
                else:
                    print(f"❌ Invalid choice. Please enter a number between 1 and {len(quizzes)}.")
            except ValueError:
                print("❌ Invalid input. Please enter a number or 'q' to quit.")

    def get_quiz_questions(self, quiz_id: int, is_new_quiz: bool = False) -> Dict:
        """Get quiz questions - tries both Classic and New Quiz APIs"""
        print(f"\n🔍 Fetching question structure for quiz {quiz_id}...")

        if not is_new_quiz:
            # Try Classic Quiz API
            classic_url = f"{API_BASE}/courses/{self.course_id}/quizzes/{quiz_id}/questions"

            try:
                response = self._make_request('GET', classic_url, params={'per_page': 100})
                questions = response.json()
                print(f"✅ Retrieved {len(questions)} question(s) from Classic Quiz API")
                return {
                    'quiz_type': 'classic',
                    'questions': questions
                }
            except Exception as e:
                print(f"⚠️  Classic Quiz API failed: {e}")

        # Try New Quiz API (uses different base path)
        print("🔄 Trying New Quiz API...")

        # New Quizzes API endpoints
        new_quiz_base = "https://uncch.instructure.com/api/quiz/v1"
        new_quiz_url = f"{new_quiz_base}/courses/{self.course_id}/quizzes/{quiz_id}"

        try:
            response = self._make_request('GET', new_quiz_url)
            quiz_data = response.json()
            print(f"✅ Retrieved quiz data from New Quiz API")

            # Try to get items/questions
            items_url = f"{new_quiz_url}/items"
            try:
                items_response = self._make_request('GET', items_url)
                items = items_response.json()
                quiz_data['items'] = items
                print(f"✅ Retrieved {len(items)} item(s)")
            except Exception as e:
                print(f"⚠️  Could not fetch items: {e}")
                quiz_data['items'] = []

            return {
                'quiz_type': 'new',
                'quiz_data': quiz_data
            }
        except Exception as e:
            print(f"❌ New Quiz API also failed: {e}")
            print("⚠️  Note: New Quizzes may require special permissions or different API access")
            return {
                'quiz_type': 'unknown',
                'error': str(e),
                'questions': []
            }

    def get_quiz_submissions(self, quiz_id: int, is_new_quiz: bool = False, limit: int = 5) -> List[Dict]:
        """Get completed quiz submissions (up to limit)
        For New Quizzes, uses the assignment submissions API instead
        """
        print(f"\n🔍 Fetching completed submissions for quiz {quiz_id}...")

        if is_new_quiz:
            # For New Quizzes, use the assignment submissions API
            url = f"{API_BASE}/courses/{self.course_id}/assignments/{quiz_id}/submissions"
            params = {
                'per_page': 100,
                'include[]': ['user', 'submission_history', 'submission_comments', 'rubric_assessment', 'visibility']
            }
        else:
            # For Classic Quizzes, use the quiz submissions API
            url = f"{API_BASE}/courses/{self.course_id}/quizzes/{quiz_id}/submissions"
            params = {
                'per_page': 100,
                'include[]': ['user', 'submission', 'quiz']
            }

        submissions = []

        try:
            while url and len(submissions) < limit:
                response = self._make_request('GET', url, params=params)

                if is_new_quiz:
                    batch = response.json()
                    # Filter for graded/submitted submissions
                    completed = [s for s in batch if s.get('workflow_state') in ['graded', 'submitted', 'pending_review']]
                else:
                    batch = response.json().get('quiz_submissions', [])
                    # Filter for completed submissions
                    completed = [s for s in batch if s.get('workflow_state') == 'complete']

                submissions.extend(completed)

                # Handle pagination
                if 'next' in response.links and len(submissions) < limit:
                    url = response.links['next']['url']
                    params = {}
                else:
                    url = None

            # Limit to requested number
            submissions = submissions[:limit]

            if not submissions:
                print("⚠️  No completed submissions found")
            else:
                print(f"✅ Found {len(submissions)} completed submission(s)")

            return submissions

        except Exception as e:
            print(f"❌ ERROR fetching submissions: {e}")
            return []

    def get_quiz_submission_id_from_assignment(self, assignment_id: int, user_id: int) -> Optional[int]:
        """Get quiz_submission_id from assignment submission (for New Quizzes)"""
        try:
            # Try to get the quiz submission through the quiz submissions API
            url = f"{API_BASE}/courses/{self.course_id}/quizzes/{assignment_id}/submissions"
            params = {'per_page': 100}

            response = self._make_request('GET', url, params=params)
            submissions = response.json().get('quiz_submissions', [])

            # Find the submission for this user
            for sub in submissions:
                if sub.get('user_id') == user_id:
                    return sub.get('id')

            return None
        except Exception as e:
            print(f"  ⚠️  Could not get quiz_submission_id: {e}")
            return None

    def try_get_new_quiz_answers_from_urls(self, preview_url: str = None, external_tool_url: str = None,
                                           participant_session_id: str = None, quiz_session_id: str = None,
                                           submissions_download_url: str = None) -> Dict:
        """Try to fetch answer data from New Quiz URLs or via New Quizzes API"""
        result = {
            'preview_url_data': None,
            'quiz_api_data': None,
            'submissions_download_data': None,
            'errors': []
        }

        # Try to get data from preview URL (Canvas submission preview)
        # COMMENTED OUT - Preview URL just returns HTML, not answer data
        # if preview_url:
        #     try:
        #         print(f"  🔍 Trying to fetch preview URL...")
        #         # The preview URL is a Canvas page that might contain structured data
        #         response = self._make_request('GET', preview_url)
        #         # Save the full response content
        #         result['preview_url_data'] = {
        #             'url': preview_url,
        #             'content_type': response.headers.get('content-type'),
        #             'content_length': len(response.text),
        #             'full_content': response.text  # Save the complete HTML/data
        #         }
        #         print(f"  ✅ Got preview URL response ({len(response.text)} bytes)")
        #     except Exception as e:
        #         error_msg = f"Preview URL failed: {e}"
        #         print(f"  ⚠️  {error_msg}")
        #         result['errors'].append(error_msg)

        # Try to get data from submissions download URL (without zip parameter)
        if submissions_download_url:
            try:
                print(f"  🔍 Trying submissions download endpoint...")
                # Remove the zip parameter to potentially get JSON instead
                base_url = submissions_download_url.split('?')[0]
                response = self._make_request('GET', base_url)

                # Check if it's JSON
                if 'application/json' in response.headers.get('content-type', ''):
                    result['submissions_download_data'] = response.json()
                    print(f"  ✅ Got JSON data from submissions endpoint")
                else:
                    result['submissions_download_data'] = {
                        'note': 'Not JSON response',
                        'content_type': response.headers.get('content-type'),
                        'content_length': len(response.text)
                    }
                    print(f"  ⚠️  Submissions endpoint returned {response.headers.get('content-type')}")
            except Exception as e:
                error_msg = f"Submissions download endpoint failed: {e}"
                print(f"  ⚠️  {error_msg}")
                result['errors'].append(error_msg)

        # Try to get data from participant session (New Quizzes API)
        # COMMENTED OUT - Testing other approaches first
        # if participant_session_id and quiz_session_id:
        #     try:
        #         print(f"  🔍 Trying New Quizzes API with session IDs...")
        #         # New Quizzes API endpoint for getting responses
        #         new_quiz_base = "https://uncch.instructure.com/api/quiz/v1"
        #         session_url = f"{new_quiz_base}/quiz_sessions/{quiz_session_id}"
        #
        #         response = self._make_request('GET', session_url)
        #         result['quiz_api_data'] = response.json()
        #         print(f"  ✅ Got data from New Quizzes API")
        #     except Exception as e:
        #         error_msg = f"New Quizzes API failed: {e}"
        #         print(f"  ⚠️  {error_msg}")
        #         result['errors'].append(error_msg)

        return result

    def get_submission_answers(self, quiz_submission_id: int = None, assignment_id: int = None, user_id: int = None, is_new_quiz: bool = False) -> Dict:
        """Get the answers for a specific quiz submission
        For New Quizzes, may need to look up quiz_submission_id first
        """

        # For New Quizzes, we might need to get the quiz_submission_id first
        if is_new_quiz and quiz_submission_id is None and assignment_id and user_id:
            print(f"  🔍 Looking up quiz_submission_id for user {user_id}...")
            quiz_submission_id = self.get_quiz_submission_id_from_assignment(assignment_id, user_id)
            if not quiz_submission_id:
                return {
                    'error': 'Could not find quiz_submission_id',
                    'answers': []
                }

        print(f"  🔍 Fetching answers for submission {quiz_submission_id}...")

        url = f"{API_BASE}/quiz_submissions/{quiz_submission_id}/questions"

        try:
            response = self._make_request('GET', url, params={'per_page': 100})
            data = response.json()

            # The response contains quiz_submission_questions array
            questions = data.get('quiz_submission_questions', [])
            print(f"  ✅ Retrieved {len(questions)} answer(s)")

            return {
                'quiz_submission_id': quiz_submission_id,
                'answers': questions
            }

        except Exception as e:
            print(f"  ❌ ERROR fetching submission answers: {e}")
            return {
                'quiz_submission_id': quiz_submission_id,
                'error': str(e),
                'answers': []
            }

    def save_diagnostic_data(self, quiz_info: Dict, question_structure: Dict,
                            sample_submissions: List[Dict]) -> str:
        """Save all diagnostic data to a JSON file"""
        quiz_id = quiz_info.get('quiz_id', 'unknown')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"quiz_diagnostic_{quiz_id}_{timestamp}.json"

        diagnostic_data = {
            'quiz_info': quiz_info,
            'question_structure': question_structure,
            'sample_submissions': sample_submissions,
            'metadata': {
                'course_id': self.course_id,
                'timestamp': timestamp,
                'num_submissions_sampled': len(sample_submissions)
            }
        }

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(diagnostic_data, f, indent=2, ensure_ascii=False)

            print(f"\n✅ Diagnostic data saved to: {filename}")
            return filename

        except Exception as e:
            print(f"❌ ERROR saving diagnostic data: {e}")
            raise

    def run_diagnostic(self, quiz_id: int, quiz_info: Dict) -> None:
        """Run the complete diagnostic process for a quiz"""
        print("\n" + "="*60)
        print(f"RUNNING DIAGNOSTIC FOR: {quiz_info.get('name', 'Unknown Quiz')}")
        print("="*60)

        # Determine if this is a New Quiz
        is_new_quiz = not quiz_info.get('quiz_id')

        # Step 1: Get question structure
        question_structure = self.get_quiz_questions(quiz_id, is_new_quiz=is_new_quiz)

        # Step 2: Get completed submissions (up to 5)
        submissions = self.get_quiz_submissions(quiz_id, is_new_quiz=is_new_quiz, limit=5)

        # Step 3: Get answers for each submission
        sample_submissions = []

        if submissions:
            print(f"\n🔄 Fetching answers for {len(submissions)} submission(s)...")
            for submission in submissions:
                user_id = submission.get('user_id')

                if is_new_quiz:
                    # For New Quizzes, save the FULL submission object to explore
                    # We'll try to get answers but also save everything for analysis
                    submission_id = submission.get('id')  # This is the assignment submission id

                    # Try traditional method first
                    answers_data = self.get_submission_answers(
                        assignment_id=quiz_id,
                        user_id=user_id,
                        is_new_quiz=True
                    )

                    # Extract session IDs from external_tool_url if available
                    external_tool_url = submission.get('external_tool_url', '')
                    participant_session_id = None
                    quiz_session_id = None

                    if external_tool_url:
                        import re
                        # Extract IDs from URL like: ?participant_session_id=1563551&quiz_session_id=1576640
                        ps_match = re.search(r'participant_session_id=(\d+)', external_tool_url)
                        qs_match = re.search(r'quiz_session_id=(\d+)', external_tool_url)
                        if ps_match:
                            participant_session_id = ps_match.group(1)
                        if qs_match:
                            quiz_session_id = qs_match.group(1)

                    # Try to get data from New Quizzes API
                    new_quiz_data = None
                    if quiz_session_id or submission.get('preview_url'):
                        # Get submissions_download_url from quiz_info
                        submissions_download_url = quiz_info.get('submissions_download_url')

                        new_quiz_data = self.try_get_new_quiz_answers_from_urls(
                            preview_url=submission.get('preview_url'),
                            external_tool_url=external_tool_url,
                            participant_session_id=participant_session_id,
                            quiz_session_id=quiz_session_id,
                            submissions_download_url=submissions_download_url
                        )

                    # Save the complete submission object for New Quizzes
                    sample_submissions.append({
                        'submission_id': submission.get('id'),
                        'user_id': user_id,
                        'workflow_state': submission.get('workflow_state'),
                        'score': submission.get('score'),
                        'answers': answers_data.get('answers', []),
                        'error': answers_data.get('error'),
                        'new_quiz_api_data': new_quiz_data,
                        'full_submission_object': submission  # Save everything!
                    })
                else:
                    # For Classic Quizzes, submission.id is the quiz_submission_id
                    submission_id = submission.get('id')
                    answers_data = self.get_submission_answers(quiz_submission_id=submission_id)

                    sample_submissions.append({
                        'submission_id': submission.get('id'),
                        'user_id': user_id,
                        'workflow_state': submission.get('workflow_state'),
                        'score': submission.get('score'),
                        'answers': answers_data.get('answers', []),
                        'error': answers_data.get('error')
                    })

        # Step 4: Save to JSON
        filename = self.save_diagnostic_data(quiz_info, question_structure, sample_submissions)

        # Summary
        print("\n" + "="*60)
        print("DIAGNOSTIC COMPLETE")
        print("="*60)
        print(f"Quiz Type: {question_structure.get('quiz_type', 'unknown')}")
        print(f"Questions Found: {len(question_structure.get('questions', question_structure.get('items', [])))}")
        print(f"Submissions Sampled: {len(sample_submissions)}")
        print(f"Output File: {filename}")
        print("="*60)

    def run(self) -> None:
        """Main application flow"""
        print("\n" + "="*60)
        print("CANVAS QUIZ DIAGNOSTIC TOOL")
        print("="*60)
        print(f"Course ID: {self.course_id}")

        # Step 1: Get quiz assignments
        quizzes = self.get_quiz_assignments()

        # Step 2: Display and select quiz
        self.display_quizzes(quizzes)
        selected_quiz = self.select_quiz(quizzes)

        if not selected_quiz:
            return

        # For Classic Quizzes, use quiz_id; for New Quizzes, use assignment id
        quiz_id = selected_quiz.get('quiz_id') or selected_quiz.get('id')
        if not quiz_id:
            print("❌ ERROR: Selected quiz has no valid ID")
            sys.exit(1)

        # Step 3: Run diagnostic
        self.run_diagnostic(quiz_id, selected_quiz)


def main():
    """Entry point"""
    # TODO: Update COURSE_ID to your ECON 510 course ID
    if COURSE_ID == 12345:
        print("\n⚠️  WARNING: Please update COURSE_ID in the script with your ECON 510 course ID")
        course_id_input = input("Enter ECON 510 course ID: ").strip()
        try:
            course_id = int(course_id_input)
        except ValueError:
            print("❌ Invalid course ID")
            sys.exit(1)
    else:
        course_id = COURSE_ID

    try:
        diagnostic = CanvasQuizDiagnostic(course_id)
        diagnostic.run()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Exiting...")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
