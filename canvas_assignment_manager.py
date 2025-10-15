# canvas_assignment_manager.py
"""
Canvas Assignment Group Manager
This script allows instructors to manage assignment groups and convert assignments to non-graded status.
"""

import sys
import requests
import keyring
from typing import List, Dict, Optional


# === CONFIGURATION ===
SERVICE_NAME = 'canvas'
USERNAME = 'access-token'
API_BASE = "https://uncch.instructure.com/api/v1"


class CanvasAssignmentManager:
    """Manages Canvas assignments through the API"""
    
    def __init__(self):
        """Initialize the manager and authenticate"""
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
            sys.exit(1)
        except requests.exceptions.RequestException as e:
            print(f"❌ REQUEST ERROR: {e}")
            sys.exit(1)
    
    def get_teaching_courses(self) -> List[Dict]:
        """Fetch all favorited (starred) courses"""
        print("\n🔍 Fetching your favorited courses...")

        courses = []
        url = f"{API_BASE}/users/self/favorites/courses"
        params = {'per_page': 100}

        while url:
            response = self._make_request('GET', url, params=params)
            courses.extend(response.json())

            # Handle pagination
            if 'next' in response.links:
                url = response.links['next']['url']
                params = {}  # Params are included in the next URL
            else:
                url = None

        if not courses:
            print("❌ No favorited courses found.")
            print("💡 Tip: Star courses in Canvas to see them here.")
            sys.exit(1)

        return courses
    
    def display_courses(self, courses: List[Dict]) -> None:
        """Display courses in a numbered list"""
        print("\n" + "="*60)
        print("YOUR COURSES")
        print("="*60)
        for idx, course in enumerate(courses, 1):
            course_code = course.get('course_code', 'N/A')
            course_name = course.get('name', 'Unnamed Course')
            print(f"{idx}. [{course_code}] {course_name}")
        print("="*60)
    
    def select_course(self, courses: List[Dict]) -> Optional[Dict]:
        """Prompt user to select a course"""
        while True:
            try:
                choice = input("\nEnter course number (or 'q' to quit): ").strip()
                
                if choice.lower() == 'q':
                    print("👋 Exiting...")
                    return None
                
                course_num = int(choice)
                
                if 1 <= course_num <= len(courses):
                    return courses[course_num - 1]
                else:
                    print(f"❌ Invalid choice. Please enter a number between 1 and {len(courses)}.")
            except ValueError:
                print("❌ Invalid input. Please enter a number or 'q' to quit.")
    
    def get_assignment_groups(self, course_id: int) -> List[Dict]:
        """Fetch all assignment groups for a course"""
        print("\n🔍 Fetching assignment groups...")

        url = f"{API_BASE}/courses/{course_id}/assignment_groups"
        params = {
            'include[]': 'assignments',
            'per_page': 100
        }
        
        groups = []
        while url:
            response = self._make_request('GET', url, params=params)
            groups.extend(response.json())
            
            if 'next' in response.links:
                url = response.links['next']['url']
                params = {}
            else:
                url = None
        
        if not groups:
            print("❌ No assignment groups found in this course.")
        
        return groups
    
    def display_assignment_groups(self, groups: List[Dict]) -> None:
        """Display assignment groups in a numbered list"""
        print("\n" + "="*60)
        print("ASSIGNMENT GROUPS")
        print("="*60)
        for idx, group in enumerate(groups, 1):
            group_name = group.get('name', 'Unnamed Group')
            # Count assignments in the group
            assignment_count = len(group.get('assignments', []))
            print(f"{idx}. {group_name} ({assignment_count} assignments)")
        print(f"{len(groups) + 1}. Exit")
        print("="*60)
    
    def select_assignment_group(self, groups: List[Dict]) -> Optional[Dict]:
        """Prompt user to select an assignment group"""
        while True:
            try:
                choice = input("\nEnter assignment group number: ").strip()
                group_num = int(choice)
                
                if group_num == len(groups) + 1:
                    return None
                
                if 1 <= group_num <= len(groups):
                    return groups[group_num - 1]
                else:
                    print(f"❌ Invalid choice. Please enter a number between 1 and {len(groups) + 1}.")
            except ValueError:
                print("❌ Invalid input. Please enter a number.")
    
    def get_assignments_in_group(self, course_id: int, group_id: int) -> List[Dict]:
        """Fetch all assignments in a specific group"""
        url = f"{API_BASE}/courses/{course_id}/assignments"
        params = {
            'assignment_group_id': group_id,
            'per_page': 100
        }
        
        assignments = []
        while url:
            response = self._make_request('GET', url, params=params)
            assignments.extend(response.json())
            
            if 'next' in response.links:
                url = response.links['next']['url']
                params = {}
            else:
                url = None
        
        return assignments
    
    def confirm_action(self, group_name: str, assignment_count: int) -> bool:
        """Ask user to confirm the action"""
        print("\n" + "⚠"*30)
        print(f"You are about to convert {assignment_count} assignment(s)")
        print(f"in the group '{group_name}' to NON-GRADED status.")
        print("⚠"*30)
        
        while True:
            confirm = input("\nAre you sure? (yes/no): ").strip().lower()
            if confirm in ['yes', 'y']:
                return True
            elif confirm in ['no', 'n']:
                return False
            else:
                print("❌ Please enter 'yes' or 'no'.")
    
    def make_assignment_non_graded(self, course_id: int, assignment_id: int, assignment_name: str) -> bool:
        """Convert a single assignment to non-graded"""
        url = f"{API_BASE}/courses/{course_id}/assignments/{assignment_id}"
        
        # Set grading_type to 'not_graded' and points_possible to None
        data = {
            'assignment[grading_type]': 'not_graded',
            'assignment[points_possible]': ''
        }
        
        try:
            response = self._make_request('PUT', url, data=data)
            print(f"  ✅ {assignment_name}")
            return True
        except Exception as e:
            print(f"  ❌ Failed: {assignment_name} - {str(e)}")
            return False
    
    def process_assignment_group(self, course_id: int, group: Dict) -> None:
        """Process all assignments in a group to make them non-graded"""
        group_id = group['id']
        group_name = group['name']
        
        # Fetch assignments in this group
        assignments = self.get_assignments_in_group(course_id, group_id)
        
        if not assignments:
            print(f"\n❌ No assignments found in group '{group_name}'.")
            return
        
        # Confirm action
        if not self.confirm_action(group_name, len(assignments)):
            print("\n❌ Action cancelled.")
            return
        
        # Process each assignment
        print(f"\n🔄 Processing {len(assignments)} assignment(s)...")
        success_count = 0
        
        for assignment in assignments:
            if self.make_assignment_non_graded(
                course_id,
                assignment['id'],
                assignment.get('name', 'Unnamed Assignment')
            ):
                success_count += 1
        
        # Summary
        print("\n" + "="*60)
        if success_count == len(assignments):
            print(f"✅ SUCCESS: All {success_count} assignment(s) converted to non-graded.")
        else:
            print(f"⚠️  PARTIAL SUCCESS: {success_count}/{len(assignments)} assignment(s) converted.")
        print("="*60)
    
    def run(self) -> None:
        """Main application loop"""
        print("\n" + "="*60)
        print("CANVAS ASSIGNMENT GROUP MANAGER")
        print("="*60)
        
        # Step 1: Get teaching courses
        courses = self.get_teaching_courses()
        
        # Step 2: Display and select course
        self.display_courses(courses)
        selected_course = self.select_course(courses)
        
        if not selected_course:
            return
        
        course_id = selected_course['id']
        course_name = selected_course['name']
        print(f"\n✅ Selected: {course_name}")
        
        # Step 3: Get assignment groups
        groups = self.get_assignment_groups(course_id)
        
        if not groups:
            return
        
        # Step 4: Display and select assignment group
        while True:
            self.display_assignment_groups(groups)
            selected_group = self.select_assignment_group(groups)
            
            if not selected_group:
                print("\n👋 Exiting...")
                break
            
            # Step 5 & 6: Confirm and process
            self.process_assignment_group(course_id, selected_group)
            
            # Ask if user wants to process another group
            print("\n" + "-"*60)
            continue_choice = input("Process another assignment group? (yes/no): ").strip().lower()
            if continue_choice not in ['yes', 'y']:
                print("\n👋 Exiting...")
                break


def main():
    """Entry point"""
    try:
        manager = CanvasAssignmentManager()
        manager.run()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Exiting...")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()