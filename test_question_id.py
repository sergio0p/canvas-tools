#!/usr/bin/env python3
"""
Canvas New Quizzes - Question ID Test Script

This script tests which question ID format works for submitting scores
to categorization questions in Canvas New Quizzes.

Tests two methods:
  METHOD 1: item_id from student_analysis report (e.g., "411636")
  METHOD 2: id from quiz definition (e.g., "452018")

Requires manual verification on Canvas after each attempt.
"""

import sys
import json
import requests
import keyring
from typing import Dict, Optional, Tuple

# === CONFIGURATION ===
SERVICE_NAME = 'canvas'
USERNAME = 'access-token'
HOST = 'https://uncch.instructure.com'
API_V1 = f"{HOST}/api/v1"
API_QUIZ = f"{HOST}/api/quiz/v1"
COURSE_ID = 97934
ASSIGNMENT_ID = 743848  # New Quiz assignment ID

# Question IDs to test
QUESTION_ID_METHOD_1 = "411636"  # From student_analysis (item_id)
QUESTION_ID_METHOD_2 = "452018"  # From quiz definition (id)

# Test student (change if needed)
TEST_STUDENT_ID = 73860  # Zachary Lucas
TEST_STUDENT_NAME = "Zachary Lucas"


class QuestionIDTester:
    """Test which question ID format works for score submission"""
    
    def __init__(self):
        """Initialize the tester"""
        self.api_token = self._get_api_token()
        self.session = requests.Session()
        self.session.headers.update({'Authorization': f'Bearer {self.api_token}'})
        self.quiz_id = None
        self.submission_id = None
        self.original_score = None
        
    def _get_api_token(self) -> str:
        """Retrieve API token from keychain"""
        token = keyring.get_password(SERVICE_NAME, USERNAME)
        if not token:
            print(f"❌ ERROR: No Canvas API token found in keychain.")
            print(f"Set one using: keyring.set_password('{SERVICE_NAME}', '{USERNAME}', 'your_token')")
            sys.exit(1)
        return token
    
    def _api_get(self, url: str, **kwargs) -> requests.Response:
        """Make GET request"""
        response = self.session.get(url, **kwargs)
        return response
    
    def _api_put(self, url: str, **kwargs) -> requests.Response:
        """Make PUT request"""
        response = self.session.put(url, **kwargs)
        return response
    
    def discover_quiz_id(self) -> Optional[int]:
        """
        Discover the Classic Canvas quiz_id from the New Quiz assignment_id
        
        For New Quizzes, the assignment_id might equal quiz_id, or we need to look it up
        """
        print("\n🔍 Step 1: Discovering quiz_id...")
        
        # Try Method 1: assignment_id = quiz_id (common for New Quizzes)
        print(f"  Testing if assignment_id ({ASSIGNMENT_ID}) = quiz_id...")
        
        # Try to get quiz submissions using assignment_id as quiz_id
        url = f"{API_V1}/courses/{COURSE_ID}/quizzes/{ASSIGNMENT_ID}/submissions"
        response = self._api_get(url, params={'per_page': 1})
        
        if response.status_code == 200:
            print(f"  ✅ quiz_id = {ASSIGNMENT_ID} (same as assignment_id)")
            return ASSIGNMENT_ID
        
        # Try Method 2: Look up via assignment endpoint
        print(f"  ❌ Assignment ID doesn't work as quiz_id directly")
        print(f"  Trying to look up via assignment endpoint...")
        
        url = f"{API_V1}/courses/{COURSE_ID}/assignments/{ASSIGNMENT_ID}"
        response = self._api_get(url)
        
        if response.status_code == 200:
            assignment_data = response.json()
            quiz_id = assignment_data.get('quiz_id')
            
            if quiz_id:
                print(f"  ✅ Found quiz_id: {quiz_id}")
                return quiz_id
        
        print(f"  ❌ Could not discover quiz_id automatically")
        print(f"  Please provide quiz_id manually:")
        
        while True:
            user_input = input("  Enter quiz_id (or 'quit'): ").strip()
            if user_input.lower() == 'quit':
                sys.exit(0)
            try:
                return int(user_input)
            except ValueError:
                print("  Invalid input. Please enter a number.")
    
    def get_test_student_info(self) -> Dict:
        """Get current submission info for test student"""
        print(f"\n🔍 Step 2: Getting test student submission info...")
        
        # Get submissions
        url = f"{API_V1}/courses/{COURSE_ID}/quizzes/{self.quiz_id}/submissions"
        params = {'per_page': 100}
        
        response = self._api_get(url, params=params)
        
        if response.status_code != 200:
            print(f"  ❌ Failed to get submissions: {response.status_code}")
            print(f"  {response.text}")
            sys.exit(1)
        
        data = response.json()
        submissions = data.get('quiz_submissions', [])
        
        # Find test student
        for submission in submissions:
            if submission.get('user_id') == TEST_STUDENT_ID:
                self.submission_id = submission.get('id')
                self.original_score = submission.get('score', 0.0)
                
                print(f"  ✅ Found submission for {TEST_STUDENT_NAME}")
                print(f"     Submission ID: {self.submission_id}")
                print(f"     Current Quiz Score: {self.original_score} / 4.0")
                
                return submission
        
        print(f"  ❌ No submission found for student ID {TEST_STUDENT_ID}")
        sys.exit(1)
    
    def get_question_details(self) -> Dict:
        """Get details about the categorization question"""
        print(f"\n📋 Step 3: Getting question details from student_analysis...")
        
        # Check if student_analysis file exists
        analysis_file = f"student_analysis_{COURSE_ID}_{ASSIGNMENT_ID}.json"
        
        try:
            with open(analysis_file, 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            print(f"  ❌ Student analysis file not found: {analysis_file}")
            print(f"  Run quiz_report.py first to generate it.")
            sys.exit(1)
        
        # Find test student
        for student in data:
            if student['student_data']['id'] == TEST_STUDENT_ID:
                # Find categorization question
                for item in student['item_responses']:
                    if item['item_type'] == 'categorization':
                        print(f"  ✅ Found categorization question")
                        print(f"     item_id: {item['item_id']}")
                        print(f"     Current Score: {item['score']} / 2.0")
                        print(f"     Answer: {item['answer'][:80]}...")
                        
                        return item
        
        print(f"  ❌ Could not find test student or categorization question")
        sys.exit(1)
    
    def test_score_submission(self, question_id: str, test_score: float, 
                            method_name: str) -> Tuple[bool, Dict]:
        """
        Test submitting a score with given question_id
        
        Returns: (api_success, response_data)
        """
        url = f"{API_V1}/courses/{COURSE_ID}/quizzes/{self.quiz_id}/submissions/{self.submission_id}"
        
        payload = {
            "quiz_submissions": [{
                "attempt": 1,
                "questions": {
                    question_id: {
                        "score": test_score,
                        "comment": f"TEST: Score update using {method_name} (question_id: {question_id})"
                    }
                }
            }]
        }
        
        print(f"\n📤 Submitting to API...")
        print(f"   URL: {url}")
        print(f"   Question ID: {question_id}")
        print(f"   Score: {test_score}")
        
        response = self._api_put(url, json=payload)
        
        api_success = response.status_code in [200, 201]
        
        try:
            response_data = response.json()
        except:
            response_data = {"raw": response.text}
        
        return api_success, response_data
    
    def prompt_for_test_score(self, attempt: int = 1) -> float:
        """Prompt user for test score"""
        print(f"\n" + "="*70)
        print(f"TEST ATTEMPT #{attempt}")
        print("="*70)
        
        while True:
            user_input = input("\nEnter TEST SCORE to submit (0.0 - 2.0) or 'quit': ").strip()
            
            if user_input.lower() == 'quit':
                print("Exiting...")
                sys.exit(0)
            
            try:
                score = float(user_input)
                if 0.0 <= score <= 2.0:
                    return score
                else:
                    print("❌ Score must be between 0.0 and 2.0")
            except ValueError:
                print("❌ Invalid input. Please enter a number.")
    
    def verify_on_canvas(self, test_score: float) -> bool:
        """Ask user to verify the score was updated on Canvas"""
        print(f"\n" + "="*70)
        print("MANUAL VERIFICATION REQUIRED")
        print("="*70)
        print(f"\n📍 Please verify on Canvas:")
        print(f"   1. Go to SpeedGrader for quiz: {ASSIGNMENT_ID}")
        print(f"   2. Navigate to student: {TEST_STUDENT_NAME}")
        print(f"   3. Check the categorization question score")
        print(f"   4. Verify it shows: {test_score} / 2.0")
        print(f"\n   SpeedGrader URL:")
        print(f"   {HOST}/courses/{COURSE_ID}/gradebook/speed_grader?assignment_id={ASSIGNMENT_ID}")
        
        while True:
            user_input = input("\n✓ Did the score update correctly on Canvas? (yes/no/quit): ").strip().lower()
            
            if user_input == 'quit':
                print("Exiting...")
                sys.exit(0)
            elif user_input in ['yes', 'y']:
                return True
            elif user_input in ['no', 'n']:
                return False
            else:
                print("❌ Please answer 'yes' or 'no'")
    
    def save_result(self, method_name: str, question_id: str, test_score: float):
        """Save the working method to config file"""
        config = {
            "working_method": method_name,
            "question_id": question_id,
            "quiz_id": self.quiz_id,
            "verified_date": "2025-10-17",
            "test_details": {
                "assignment_id": ASSIGNMENT_ID,
                "course_id": COURSE_ID,
                "test_student": f"{TEST_STUDENT_NAME} ({TEST_STUDENT_ID})",
                "test_score": test_score,
                "canvas_verified": True
            }
        }
        
        filename = "question_id_config.json"
        with open(filename, 'w') as f:
            json.dump(config, indent=2, fp=f)
        
        print(f"\n✅ Configuration saved to: {filename}")
        print(f"\nThe main grading script should use:")
        print(f"  Question ID format: {question_id}")
        print(f"  Method: {method_name}")
    
    def run(self):
        """Main test workflow"""
        print("="*70)
        print("   CANVAS NEW QUIZZES - QUESTION ID TEST SCRIPT")
        print("="*70)
        print(f"\nCourse: {COURSE_ID}")
        print(f"Assignment: {ASSIGNMENT_ID}")
        print(f"Test Student: {TEST_STUDENT_NAME} (ID: {TEST_STUDENT_ID})")
        print(f"\nThis script will test which question ID format works")
        print(f"for submitting scores to categorization questions.")
        
        # Step 1: Discover quiz_id
        self.quiz_id = self.discover_quiz_id()
        
        # Step 2: Get test student submission
        submission_info = self.get_test_student_info()
        
        # Step 3: Get question details
        question_info = self.get_question_details()
        
        # Test METHOD 1
        print("\n" + "="*70)
        print("METHOD 1: Using item_id from student_analysis")
        print("="*70)
        print(f"Question ID: {QUESTION_ID_METHOD_1}")
        
        test_score_1 = self.prompt_for_test_score(attempt=1)
        
        api_success_1, response_1 = self.test_score_submission(
            QUESTION_ID_METHOD_1, test_score_1, "student_analysis_item_id"
        )
        
        if api_success_1:
            print(f"\n✅ API call succeeded (HTTP {response_1.get('status', 200)})")
            print(f"Response preview: {json.dumps(response_1, indent=2)[:500]}...")
            
            canvas_verified_1 = self.verify_on_canvas(test_score_1)
            
            if canvas_verified_1:
                print(f"\n🎉 SUCCESS! METHOD 1 WORKS!")
                print(f"   Use item_id from student_analysis: {QUESTION_ID_METHOD_1}")
                
                self.save_result("student_analysis_item_id", QUESTION_ID_METHOD_1, test_score_1)
                
                print(f"\n✓ Test complete. Skipping METHOD 2.")
                return
            else:
                print(f"\n❌ METHOD 1 FAILED")
                print(f"   API returned success but score didn't update on Canvas")
        else:
            print(f"\n❌ API call FAILED")
            print(f"Response: {json.dumps(response_1, indent=2)}")
        
        # Test METHOD 2
        print("\n" + "="*70)
        print("METHOD 2: Using id from quiz definition")
        print("="*70)
        print(f"Question ID: {QUESTION_ID_METHOD_2}")
        
        test_score_2 = self.prompt_for_test_score(attempt=2)
        
        api_success_2, response_2 = self.test_score_submission(
            QUESTION_ID_METHOD_2, test_score_2, "quiz_definition_id"
        )
        
        if api_success_2:
            print(f"\n✅ API call succeeded (HTTP {response_2.get('status', 200)})")
            print(f"Response preview: {json.dumps(response_2, indent=2)[:500]}...")
            
            canvas_verified_2 = self.verify_on_canvas(test_score_2)
            
            if canvas_verified_2:
                print(f"\n🎉 SUCCESS! METHOD 2 WORKS!")
                print(f"   Use id from quiz definition: {QUESTION_ID_METHOD_2}")
                
                self.save_result("quiz_definition_id", QUESTION_ID_METHOD_2, test_score_2)
                
                print(f"\n✓ Test complete.")
                return
            else:
                print(f"\n❌ METHOD 2 ALSO FAILED")
                print(f"   API returned success but score didn't update on Canvas")
        else:
            print(f"\n❌ API call FAILED")
            print(f"Response: {json.dumps(response_2, indent=2)}")
        
        # Both failed
        print("\n" + "="*70)
        print("❌ BOTH METHODS FAILED")
        print("="*70)
        print("\nNeither question ID format worked for score submission.")
        print("This may require further investigation of the Canvas API.")
        print("\nPlease check:")
        print("  1. Are you using the correct quiz_id?")
        print("  2. Does your API token have grading permissions?")
        print("  3. Is the quiz published and accepting submissions?")
        sys.exit(1)


def main():
    """Entry point"""
    try:
        tester = QuestionIDTester()
        tester.run()
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
