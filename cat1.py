#!/usr/bin/env python3
"""
Canvas New Quizzes • Categorization Grader

Implements the workflow/spec in:
- categorization_grader_workflow.md
- categorization_grader_spec.md

Key capabilities
- Auth via keyring (service='canvas', username='access-token')
- List published favorite courses
- List New Quizzes assignments; choose one
- Fetch quiz items; choose a *categorization* item
- Build correct-key + true-distractor set from item definition
- Generate/download student_analysis JSON
- Parse student responses and compute partial credit per the spec:
    score = (correct - 0.5 * misclassified) / total * points_possible
- Preview results and (optionally) update overall assignment grades
  with an explanatory comment per student.

Notes
- New Quizzes does not allow question-level writes via public API.
  We update the **total** assignment score via Submissions API.

Usage
    python3 categorization_grader.py [--course COURSE_ID] [--assignment ASSIGNMENT_ID] [--auto-apply]

Environment / keychain
- Store your token once: keyring.set_password('canvas', 'access-token', 'YOUR_TOKEN')

Tested with Python 3.10+
"""
from __future__ import annotations

import os
import sys
import re
import time
import json
import math
import argparse
import textwrap
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any

import keyring
import requests

# ===== Configuration =====
SERVICE_NAME = os.getenv("CANVAS_KEYRING_SERVICE", "canvas")
USERNAME = os.getenv("CANVAS_KEYRING_USERNAME", "access-token")
API_BASE = os.getenv("CANVAS_API_BASE", "https://uncch.instructure.com/api")
# Note: New Quizzes item/report endpoints live under /api/quiz/v1
QUIZ_API_BASE = os.getenv("CANVAS_QUIZ_API_BASE", "https://uncch.instructure.com/api/quiz/v1")

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "categorization-grader/1.0"})


# ===== Utilities =====
class CanvasHTTPError(RuntimeError):
    pass


def _bearer_headers() -> Dict[str, str]:
    token = keyring.get_password(SERVICE_NAME, USERNAME)
    if not token:
        raise RuntimeError(
            f"No Canvas API token found in keychain. Set with: keyring.set_password('{SERVICE_NAME}', '{USERNAME}', 'YOUR_TOKEN')"
        )
    return {"Authorization": f"Bearer {token}"}


def _api_url(path: str) -> str:
    if path.startswith("/api/v1/"):
        return f"{API_BASE}/v1/{path[8:]}"  # replace /api/v1/ with configured base + /v1/
    if path.startswith("/api/quiz/v1/"):
        return f"{QUIZ_API_BASE}/{path[13:]}"  # QUIZ_API_BASE already includes /api/quiz/v1
    # accept full URLs
    if path.startswith("http"):
        return path
    # fallback assume v1
    return f"{API_BASE}/v1{path}"


def _req(method: str, path: str, **kwargs) -> requests.Response:
    url = _api_url(path)
    hdrs = kwargs.pop("headers", {})
    hdrs.update(_bearer_headers())
    resp = SESSION.request(method, url, headers=hdrs, timeout=60, **kwargs)
    if resp.status_code >= 400:
        raise CanvasHTTPError(
            f"HTTP {resp.status_code} for {method} {url}\n{resp.text[:2000]}"
        )
    return resp


def _get(path: str, **kwargs) -> requests.Response:
    return _req("GET", path, **kwargs)


def _post(path: str, **kwargs) -> requests.Response:
    return _req("POST", path, **kwargs)


def _put(path: str, **kwargs) -> requests.Response:
    return _req("PUT", path, **kwargs)


def _iter_pages(path: str, params: Optional[Dict[str, Any]] = None):
    url = _api_url(path)
    hdrs = _bearer_headers()
    while True:
        resp = SESSION.get(url, headers=hdrs, params=params, timeout=60)
        if resp.status_code >= 400:
            raise CanvasHTTPError(
                f"HTTP {resp.status_code} for GET {url}\n{resp.text[:2000]}"
            )
        yield resp
        # follow Link: rel="next"
        next_url = None
        link = resp.headers.get("Link")
        if link:
            for part in link.split(","):
                if 'rel="next"' in part:
                    m = re.search(r"<(.*?)>", part)
                    if m:
                        next_url = m.group(1)
                        break
        if not next_url:
            break
        url = next_url
        params = None  # next URL already encodes params


# ===== Domain models =====
@dataclass
class Course:
    id: int
    name: str
    code: Optional[str] = None


@dataclass
class Assignment:
    id: int
    name: str
    due_at: Optional[str]
    points_possible: float
    is_new_quiz: bool


@dataclass
class CategorizationKey:
    item_id: str
    points_possible: float
    # map item_label -> category_label
    correct_map: Dict[str, str]
    # set of item_labels that are true distractors (should remain unplaced)
    true_distractors: set
    title: str


# ===== Fetchers =====

def list_published_favorites() -> List[Course]:
    courses: List[Course] = []
    for resp in _iter_pages("/api/v1/users/self/favorites/courses", params={"per_page": 100}):
        for c in resp.json():
            if c.get("workflow_state") == "available":
                courses.append(Course(id=c["id"], name=c.get("name") or str(c["id"]), code=c.get("course_code")))
    return courses


def is_new_quiz_assignment(assn: dict) -> bool:
    if assn.get("is_quiz_lti_assignment") is True:
        return True
    if "external_tool" in (assn.get("submission_types") or []):
        url = (assn.get("external_tool_tag_attributes") or {}).get("url", "")
        if "quiz-lti" in url or url.endswith("/lti/launch"):
            return True
    return False


def list_new_quiz_assignments(course_id: int) -> List[Assignment]:
    items: List[Assignment] = []
    for resp in _iter_pages(f"/api/v1/courses/{course_id}/assignments", params={"per_page": 100}):
        for a in resp.json():
            if is_new_quiz_assignment(a):
                items.append(
                    Assignment(
                        id=a["id"],
                        name=a.get("name") or str(a["id"]),
                        due_at=a.get("due_at"),
                        points_possible=float(a.get("points_possible") or 0.0),
                        is_new_quiz=True,
                    )
                )
    return items


def fetch_quiz_items(course_id: int, assignment_id: int) -> List[dict]:
    resp = _get(f"/api/quiz/v1/courses/{course_id}/quizzes/{assignment_id}/items")
    data = resp.json()
    entries = data.get("items") if isinstance(data, dict) else data
    if not isinstance(entries, list):
        raise RuntimeError("Unexpected items payload from New Quizzes API")
    return entries


def choose_categorization_item(items: List[dict]) -> dict:
    cats = [it for it in items if (it.get("entry") or {}).get("interaction_type_slug") == "categorization"]
    if not cats:
        raise RuntimeError("No categorization question found in this New Quiz.")
    if len(cats) == 1:
        return cats[0]
    # pick interactively
    print("Categorization questions found:")
    for i, it in enumerate(cats, 1):
        entry = it.get("entry", {})
        title = (entry.get("item_body") or entry.get("title") or f"Item {it.get('id')}")
        pts = float(entry.get("points_possible") or 0.0)
        print(f"  [{i}] id={it.get('id')} • points={pts} • {strip_html(title)[:80]}")
    while True:
        idx = input("Select question [1-{}]: ".format(len(cats))).strip()
        if idx.isdigit() and 1 <= int(idx) <= len(cats):
            return cats[int(idx) - 1]


# ===== Parsing item structure into grading key =====

def strip_html(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s or "").strip()


def build_categorization_key(cat_item: dict) -> CategorizationKey:
    entry = cat_item.get("entry", {})
    item_id = str(cat_item.get("id") or entry.get("id"))
    title = strip_html(entry.get("item_body") or entry.get("title") or f"Item {item_id}")
    points_possible = float(entry.get("points_possible") or 0.0)
    interaction = entry.get("interaction_data") or {}
    categories = interaction.get("categories") or {}
    distractors = interaction.get("distractors") or {}
    scoring = (entry.get("scoring_data") or {}).get("value") or []

    # map category UUID -> label
    cat_label_by_uuid: Dict[str, str] = {}
    for uuid, cat in categories.items():
        label = strip_html(cat.get("item_body") or "").replace("\xa0", " ")
        if label:
            cat_label_by_uuid[uuid] = label

    # map item UUID -> label
    item_label_by_uuid: Dict[str, str] = {}
    for uuid, itm in distractors.items():
        label = strip_html(itm.get("item_body") or "").replace("\xa0", " ")
        if label:
            item_label_by_uuid[uuid] = label

    # Build correct item_label -> category_label map from scoring_data.value list
    correct_map: Dict[str, str] = {}
    referenced_item_uuids: set[str] = set()
    for pair in scoring:
        # observed structures vary; try common keys
        itm_uuid = None
        cat_uuid = None
        if isinstance(pair, dict):
            itm_uuid = pair.get("distractor_id") or pair.get("item_uuid") or pair.get("item_id")
            cat_uuid = pair.get("category_id") or pair.get("category_uuid")
        if itm_uuid and cat_uuid:
            item_label = item_label_by_uuid.get(itm_uuid)
            cat_label = cat_label_by_uuid.get(cat_uuid)
            if item_label and cat_label:
                correct_map[item_label] = cat_label
                referenced_item_uuids.add(itm_uuid)

    # True distractors: items in distractors but not referenced in scoring list
    true_distractors = {lbl for u, lbl in item_label_by_uuid.items() if u not in referenced_item_uuids}

    if not correct_map:
        raise RuntimeError("Could not build correct_map from scoring_data; structure may differ.")

    return CategorizationKey(
        item_id=item_id,
        points_possible=points_possible,
        correct_map=correct_map,
        true_distractors=true_distractors,
        title=title,
    )


# ===== Student analysis report handling =====

def start_student_analysis(course_id: int, assignment_id: int) -> int:
    payload = {"quiz_report": {"report_type": "student_analysis", "format": "json"}}
    resp = _post(f"/api/quiz/v1/courses/{course_id}/quizzes/{assignment_id}/reports", json=payload)
    js = resp.json()
    # Progress object id
    prog = js.get("progress") or {}
    prog_id = prog.get("id") if isinstance(prog, dict) else js.get("progress_id")
    if not prog_id:
        # Some tenants return just an id
        prog_id = js.get("id")
    if not prog_id:
        raise RuntimeError("Report creation did not return a progress id.")
    return int(prog_id)


def poll_progress(progress_id: int, timeout_sec: int = 900, interval: float = 3.0) -> Dict[str, Any]:
    t0 = time.time()
    last = None
    while True:
        resp = _get(f"/api/v1/progress/{progress_id}")
        js = resp.json()
        workflow = js.get("workflow_state")
        if workflow in {"completed", "failed"}:
            return js
        last = workflow
        if time.time() - t0 > timeout_sec:
            raise TimeoutError("Report progress timed out.")
        time.sleep(interval)


def resolve_report_download(progress_obj: Dict[str, Any]) -> Tuple[str, bytes]:
    """Return (filename, content). Handles results.url or results.attachment_id."""
    results = progress_obj.get("results") or {}
    # Direct URL
    url = results.get("url")
    if url:
        r = SESSION.get(url, timeout=120)
        r.raise_for_status()
        fname = os.path.basename(r.url.split("?")[0]) or "student_analysis.json"
        return fname, r.content
    # Attachment resolution path
    attach_id = results.get("attachment_id") or results.get("id")
    if attach_id:
        meta = _get(f"/api/v1/files/{attach_id}").json()
        f_url = meta.get("url") or meta.get("download_url") or meta.get("public_url")
        if not f_url:
            # Some instances return a redirect if we hit /files/:id directly with download=1
            f_url = _api_url(f"/api/v1/files/{attach_id}?download=1")
        r = SESSION.get(f_url, headers=_bearer_headers(), allow_redirects=True, timeout=120)
        r.raise_for_status()
        fname = meta.get("filename") or meta.get("display_name") or "student_analysis.json"
        return fname, r.content
    raise RuntimeError("No results.url or attachment_id in progress results.")


def save_bytes(path: str, content: bytes) -> None:
    with open(path, "wb") as f:
        f.write(content)


# ===== Student response parsing and grading =====
ANSWER_RE = re.compile(r"\s*([^=]+?)\s*=>\s*\[([^\]]*)\]\s*")


def parse_answer_mapping(answer_str: str) -> Dict[str, List[str]]:
    """Parse "category => [item1,item2], category2 => [item3]" into dict.
    Returns {category_label: [item_label, ...]}
    """
    mapping: Dict[str, List[str]] = {}
    if not answer_str:
        return mapping
    for part in split_top_level(answer_str, ","):
        m = ANSWER_RE.match(part)
        if not m:
            # tolerate formats with quotes/spaces
            continue
        cat = strip_html(m.group(1))
        items_csv = m.group(2).strip()
        items = [strip_html(x) for x in split_top_level(items_csv, ",") if strip_html(x)]
        mapping.setdefault(cat, []).extend(items)
    return mapping


def split_top_level(s: str, sep: str) -> List[str]:
    # naive split that respects bracket nesting depth
    out = []
    buf = []
    depth = 0
    for ch in s:
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth = max(0, depth - 1)
        if ch == sep and depth == 0:
            out.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        out.append("".join(buf))
    return out


@dataclass
class GradeOutcome:
    user_id: int
    name: str
    attempt: int
    old_q_score: float
    new_q_score: float
    old_total: float
    new_total: float
    correct: int
    misclassified: int


def grade_student_entry(entry: dict, key: CategorizationKey) -> Optional[GradeOutcome]:
    student = entry.get("student_data") or {}
    name = student.get("name") or "?"
    user_id = int(student.get("id") or 0)
    attempt = int(student.get("attempt") or 1)

    item_responses = entry.get("item_responses") or []
    target = None
    for ir in item_responses:
        if str(ir.get("item_id")) == key.item_id:
            target = ir
            break
    if not target:
        # no attempt for this item
        return None

    # Current grades from report
    old_q_score = float(target.get("score") or 0.0)
    summary = entry.get("summary") or {}
    old_total = float(summary.get("score") or 0.0)

    # Parse their placements
    ans_str = target.get("answer") or ""
    placements = parse_answer_mapping(ans_str)

    # Compute metrics
    correct = 0
    mis = 0

    # Flatten student's placed items with their picked category
    student_item_to_cat: Dict[str, str] = {}
    for cat, items in placements.items():
        for it in items:
            student_item_to_cat[it] = cat

    # Items that should be categorized
    should_items = set(key.correct_map.keys())

    # Count correct / misclassified for items that should be categorized
    for it_label in should_items:
        chosen = student_item_to_cat.get(it_label)
        if not chosen:
            # not placed: no penalty, loses the point
            continue
        if chosen == key.correct_map[it_label]:
            correct += 1
        else:
            mis += 1

    # True distractors: penalize if placed anywhere
    for d in key.true_distractors:
        if d in student_item_to_cat:
            mis += 1
    total = max(1, len(should_items))  # avoid div by zero

    new_q_score = max(0.0, (correct - 0.5 * mis) / total * key.points_possible)

    new_total = old_total - old_q_score + new_q_score

    return GradeOutcome(
        user_id=user_id,
        name=name,
        attempt=attempt,
        old_q_score=old_q_score,
        new_q_score=new_q_score,
        old_total=old_total,
        new_total=new_total,
        correct=correct,
        misclassified=mis,
    )


# ===== Grade updates =====

def update_grade(course_id: int, assignment_id: int, outcome: GradeOutcome, feedback_title: str) -> None:
    comment = (
        f"New score for {feedback_title}: old score = {outcome.old_q_score:.2f}, new score = {outcome.new_q_score:.2f}\n"
        f"Correct = {outcome.correct}, Misclassified = {outcome.misclassified}\n"
        f"Grading formula: (correct - 0.5 * misclassified) / total * points_possible"
    )
    data = {
        "submission[posted_grade]": f"{outcome.new_total:.4g}",
        "comment[text_comment]": comment,
    }
    _put(f"/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions/{outcome.user_id}", data=data)


# ===== CLI =====

def pick_one(prompt: str, rows: List[Tuple[str, Any]]) -> Any:
    for i, (label, _) in enumerate(rows, 1):
        print(f"  [{i}] {label}")
    while True:
        sel = input(prompt).strip()
        if sel.isdigit() and 1 <= int(sel) <= len(rows):
            return rows[int(sel) - 1][1]


def run(course_id: Optional[int], assignment_id: Optional[int], auto_apply: bool) -> None:
    print("🔐 Auth…", end=" ")
    # ensure token present
    _ = _bearer_headers()
    print("ok")

    # Course selection
    if course_id is None:
        print("📚 Fetching published favorite courses…")
        courses = list_published_favorites()
        if not courses:
            print("No published favorite courses found.")
            sys.exit(2)
        chosen = pick_one("Select a course: ", [(f"{c.id} | {c.name}", c) for c in courses])
        course_id = chosen.id
    else:
        print(f"📚 Using course {course_id}")

    # Assignment selection
    if assignment_id is None:
        print("🧩 Fetching New Quizzes assignments…")
        quizzes = list_new_quiz_assignments(course_id)
        if not quizzes:
            print("No New Quizzes assignments found in this course.")
            sys.exit(2)
        rows = []
        for a in quizzes:
            due = a.due_at or "(no due date)"
            rows.append((f"{a.id} | {a.name} | due {due} | pts {a.points_possible}", a))
        chosen = pick_one("Select a quiz assignment: ", rows)
        assignment_id = chosen.id
        assignment_points = chosen.points_possible
    else:
        # fetch single assignment to get points
        a = _get(f"/api/v1/courses/{course_id}/assignments/{assignment_id}").json()
        assignment_points = float(a.get("points_possible") or 0.0)
        print(f"🧩 Using assignment {assignment_id} • {a.get('name')} • pts={assignment_points}")

    # Items
    print("📝 Fetching quiz items…")
    items = fetch_quiz_items(course_id, assignment_id)
    cat_item = choose_categorization_item(items)
    key = build_categorization_key(cat_item)
    print(f"✅ Selected categorization item {key.item_id} • '{key.title}' • points={key.points_possible}")

    # Report
    print("📊 Requesting student_analysis report…")
    prog_id = start_student_analysis(course_id, assignment_id)
    print(f"   progress id = {prog_id}")
    print("⏳ Waiting for report…")
    prog = poll_progress(prog_id)
    if prog.get("workflow_state") != "completed":
        raise RuntimeError(f"Report not completed: {prog}")
    fname, content = resolve_report_download(prog)
    out_path = f"student_analysis_{course_id}_{assignment_id}.json"
    save_bytes(out_path, content)
    print(f"✅ Downloaded report → {out_path}")

    # Parse and grade
    data = json.loads(content.decode("utf-8"))
    if not isinstance(data, list):
        raise RuntimeError("Unexpected report JSON (expected list)")

    outcomes: List[GradeOutcome] = []
    for entry in data:
        try:
            oc = grade_student_entry(entry, key)
            if oc is not None:
                outcomes.append(oc)
        except Exception as e:
            name = ((entry.get("student_data") or {}).get("name"))
            print(f"⚠️  Skipping {name or 'unknown'}: {e}")

    if not outcomes:
        print("No gradable submissions found.")
        return

    # Preview top N and summary
    print("\nPreview (first 15):")
    print(f"{'Student':30}  {'old_q':>6} → {'new_q':>6}   {'old_total':>8} → {'new_total':>8}   {'C':>2}/{"M":>2}")
    for oc in outcomes[:15]:
        print(f"{oc.name[:30]:30}  {oc.old_q_score:6.2f} → {oc.new_q_score:6.2f}   {oc.old_total:8.2f} → {oc.new_total:8.2f}   {oc.correct:2d}/{oc.misclassified:2d}")
    changed = [o for o in outcomes if abs(o.new_total - o.old_total) > 1e-9]
    print(f"\nTotals: {len(outcomes)} graded, {len(changed)} with changed total scores.")

    if not auto_apply:
        ans = input("Apply these updates to Canvas? [y/N]: ").strip().lower()
        if ans != "y":
            print("Aborted without changes.")
            return

    print("\n✍️  Updating grades in Canvas…")
    for oc in outcomes:
        try:
            update_grade(course_id, assignment_id, oc, key.title)
        except Exception as e:
            print(f"❌ Failed for {oc.name} ({oc.user_id}): {e}")
        else:
            print(f"✅ {oc.name}: total {oc.old_total:.2f} → {oc.new_total:.2f} (q {oc.old_q_score:.2f} → {oc.new_q_score:.2f})")
    print("\nDone.")


def main():
    ap = argparse.ArgumentParser(
        description="Canvas New Quizzes categorization grader (partial credit)",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    ap.add_argument("--course", type=int, default=None, help="Course ID (optional; otherwise pick from favorites)")
    ap.add_argument("--assignment", type=int, default=None, help="Assignment ID (optional; otherwise pick from list)")
    ap.add_argument("--auto-apply", action="store_true", help="Skip preview confirmation and update grades")
    args = ap.parse_args()

    try:
        run(args.course, args.assignment, args.auto_apply)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
