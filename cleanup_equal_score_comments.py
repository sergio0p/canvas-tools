#!/usr/bin/env python3
"""
Canvas New Quizzes: Redundant Equal-Score Comment Cleaner

Purpose
-------
Scan submission comments for a selected New Quizzes assignment and delete *our own*
auto-posted comments whose “old score” equals “new score” (numerically).

It keeps the same first-part structure/UX as categorization_grader.py:
- Auth via keyring
- Course selection (favorites)
- Assignment selection (New Quizzes LTI)
After selection, this tool only reads/deletes comments — no grading.
"""

import sys, time, json, re, keyring, requests
from typing import List, Optional
from dataclasses import dataclass

# ========= BASE CONFIG (copied from categorization_grader.py) =========
SERVICE_NAME = "canvas"
USERNAME = "access-token"
HOST = "https://uncch.instructure.com"
API_V1 = f"{HOST}/api/v1"
POLL_INTERVAL = 2.0
REPORT_TIMEOUT = 900
# =====================================================================

@dataclass
class Course:
    id: int
    name: str
    workflow_state: str

@dataclass
class Assignment:
    id: int
    name: str
    points_possible: float
    due_at: Optional[str]

class CanvasAPIClient:
    """Handles all Canvas API interactions"""

    def __init__(self):
        self.token = self._get_token()
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})

    def _get_token(self) -> str:
        token = keyring.get_password(SERVICE_NAME, USERNAME)
        if not token:
            print("❌ No Canvas API token in keychain.")
            print(f"Use: keyring.set_password('{SERVICE_NAME}','{USERNAME}','your_token')")
            sys.exit(1)
        return token

    def get_self_user_id(self) -> int:
        r = self.session.get(f"{API_V1}/users/self")
        r.raise_for_status()
        return int(r.json()["id"])

    def get_favorite_courses(self) -> List[Course]:
        r = self.session.get(f"{API_V1}/users/self/favorites/courses")
        r.raise_for_status()
        return [
            Course(c["id"], c["name"], c["workflow_state"])
            for c in r.json()
            if c.get("workflow_state") == "available"
        ]

    def get_new_quizzes(self, course_id: int) -> List[Assignment]:
        r = self.session.get(f"{API_V1}/courses/{course_id}/assignments", params={"per_page": 100})
        r.raise_for_status()
        return [
            Assignment(a["id"], a["name"], a.get("points_possible", 0.0), a.get("due_at"))
            for a in r.json()
            if a.get("is_quiz_lti_assignment")
        ]

    def iter_submissions_with_comments(self, course_id: int, assignment_id: int):
        url = f"{API_V1}/courses/{course_id}/assignments/{assignment_id}/submissions"
        params = {"per_page": 100, "include[]": "submission_comments"}
        while True:
            r = self.session.get(url, params=params)
            r.raise_for_status()
            for sub in r.json():
                yield sub
            nxt = None
            if "Link" in r.headers:
                for part in r.headers["Link"].split(","):
                    if 'rel="next"' in part:
                        nxt = part[part.find("<")+1:part.find(">")]
                        break
            if not nxt:
                break
            url, params = nxt, None

    def delete_comment(self, course_id: int, assignment_id: int, user_id: int, comment_id: int) -> bool:
        url = f"{API_V1}/courses/{course_id}/assignments/{assignment_id}/submissions/{user_id}/comments/{comment_id}"
        r = self.session.delete(url)
        return r.status_code in (200, 204)


# ---------- Utility ----------
SCORE_RE = re.compile(
    r"^New score for .*?:\s*old score\s*=\s*([0-9]+(?:\.[0-9]+)?),\s*new score\s*=\s*([0-9]+(?:\.[0-9]+)?)",
    re.I | re.S,
)
EPS = 1e-9

def parse_equal_comment(text: str):
    m = SCORE_RE.search(text or "")
    if not m:
        return None
    try:
        old, new = float(m.group(1)), float(m.group(2))
        return (old, new) if abs(old - new) < EPS else None
    except Exception:
        return None

def choose(items, label):
    print(f"\n{label}:")
    for i, it in enumerate(items, 1):
        print(f"{i}. {it.name if hasattr(it,'name') else it[1]} (ID {it.id if hasattr(it,'id') else it[0]})")
    while True:
        s = input(f"Select {label.lower()} [1-{len(items)}] (q to quit): ").strip().lower()
        if s == "q": sys.exit(0)
        if s.isdigit() and 1 <= int(s) <= len(items): return items[int(s)-1]
        print("Invalid choice.")

# ---------- Main ----------
def main():
    print("="*80)
    print("CANVAS NEW QUIZZES — REDUNDANT EQUAL-SCORE COMMENT CLEANER")
    print("="*80)

    client = CanvasAPIClient()
    my_id = client.get_self_user_id()

    courses = client.get_favorite_courses()
    if not courses: sys.exit("No favorite courses found.")
    course = choose(courses, "Courses")

    quizzes = client.get_new_quizzes(course.id)
    if not quizzes: sys.exit("No New Quizzes found.")
    quiz = choose(quizzes, "New Quizzes")

    print(f"\nScanning comments in: {course.name} → {quiz.name}\n")

    deleted = skipped = not_mine = failed = 0
    for sub in client.iter_submissions_with_comments(course.id, quiz.id):
        uid = sub.get("user_id")
        for c in sub.get("submission_comments") or []:
            cid, author, body = c.get("id"), c.get("author_id"), c.get("comment","")
            eq = parse_equal_comment(body)
            if not eq: skipped += 1; continue
            if int(author) != my_id: not_mine += 1; continue
            print("-"*60)
            print(f"User {uid}, comment #{cid}:")
            print(body.strip())
            print(f"→ Detected equal scores: old == new == {eq[0]}")
            while True:
                ans = input("[d]elete / [s]kip / [q]uit? ").lower().strip()
                if ans in ("d","s","q"): break
            if ans == "q": print("Stopping."); return
            if ans == "s": print("Skipped."); continue
            if client.delete_comment(course.id, quiz.id, uid, cid):
                print("✓ Deleted."); deleted += 1
            else:
                print("✗ Failed."); failed += 1

    print("\nSummary")
    print("="*80)
    print(f"Deleted: {deleted}")
    print(f"Skipped (not match): {skipped}")
    print(f"Skipped (not mine): {not_mine}")
    print(f"Failed deletes: {failed}")

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: print("\nInterrupted."); sys.exit(1)