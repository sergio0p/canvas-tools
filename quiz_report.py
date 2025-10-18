# quiz_report_min.py
"""
Canvas New Quizzes → Student Analysis report downloader (hardcoded)
- Creates student_analysis report
- Polls /api/v1/progress
- Resolves download URL from any of: results.url, results.attachment.url, results.attachment_id via Files API
- If the reports listing 404s on your tenant, we skip it.
- Downloads to student_analysis_<course>_<assignment>.json (or .csv)
"""

import sys
import time
import json
import keyring
import requests

# === HARD-CODED CONFIG ===
SERVICE_NAME   = "canvas"
USERNAME       = "access-token"
HOST           = "https://uncch.instructure.com"
API_QZ         = f"{HOST}/api/quiz/v1"   # New Quizzes API
API_V1         = f"{HOST}/api/v1"        # Progress + Files API
COURSE_ID      = 97934                   # <-- hardcoded
ASSIGNMENT_ID  = 743848                  # <-- hardcoded (New Quiz assignment_id)
REPORT_FORMAT  = "json"                  # "json" or "csv"
POLL_INTERVAL  = 2.0                     # seconds
TIMEOUT_SEC    = 900                     # 15 min

SESSION = requests.Session()


def die(msg: str, resp: requests.Response | None = None, extra: dict | None = None):
    if resp is not None:
        msg += f"\nHTTP {resp.status_code}: {resp.text}"
    if extra is not None:
        msg += f"\nEXTRA: {json.dumps(extra, indent=2, ensure_ascii=False)}"
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def init_auth_or_die():
    token = keyring.get_password(SERVICE_NAME, USERNAME)
    if not token:
        die("No Canvas token in keychain under ('canvas','access-token').")
    SESSION.headers.update({"Authorization": f"Bearer {token}"})


def create_report_or_die() -> str:
    """
    POST /api/quiz/v1/courses/:course_id/quizzes/:assignment_id/reports
    Returns a progress_url we can poll. Some tenants don’t return report_id.
    """
    url = f"{API_QZ}/courses/{COURSE_ID}/quizzes/{ASSIGNMENT_ID}/reports"
    payload = {"quiz_report": {"report_type": "student_analysis", "format": REPORT_FORMAT}}
    r = SESSION.post(url, json=payload)
    if r.status_code not in (200, 201, 202):
        die("create report failed", r)

    data = r.json()
    progress_url = data.get("progress_url") or (data.get("progress") or {}).get("url")
    if not progress_url and (data.get("progress") or {}).get("id"):
        progress_url = f"/api/v1/progress/{data['progress']['id']}"
    if not progress_url:
        die("no progress_url in response", extra=data)
    return progress_url


def poll_progress_or_die(progress_url: str) -> dict:
    url = progress_url if progress_url.startswith("http") else f"{HOST}{progress_url}"
    start = time.time()
    while True:
        r = SESSION.get(url)
        if r.status_code != 200:
            die("progress GET failed", r)
        prog = r.json()
        state = prog.get("workflow_state")
        print(f"status: {state}")
        if state == "completed":
            return prog
        if state == "failed":
            die("report generation failed", extra=prog)
        if time.time() - start > TIMEOUT_SEC:
            die("timed out waiting for report", extra=prog)
        time.sleep(POLL_INTERVAL)


def try_progress_urls(prog: dict) -> str | None:
    """
    Try to extract a direct download URL from the progress payload.
    We check several shapes seen in the wild.
    """
    results = prog.get("results") or {}
    # 1) canonical
    if isinstance(results, dict):
        url = results.get("url")
        if url:
            return url
        # 2) attachment dict with url
        att = results.get("attachment") or {}
        if isinstance(att, dict):
            url = att.get("url") or att.get("download_url")
            if url:
                return url
        # 3) just an attachment_id
        att_id = results.get("attachment_id") or results.get("file_id")
        if att_id:
            # Resolve via Files API
            fmeta = files_metadata_or_none(att_id)
            if fmeta:
                return fmeta.get("url") or fmeta.get("download_url")
    return None


def files_metadata_or_none(file_id: int) -> dict | None:
    """
    GET /api/v1/files/:id  → returns file metadata with 'url' or 'download_url'
    """
    r = SESSION.get(f"{API_V1}/files/{file_id}")
    if r.status_code == 200:
        return r.json()
    return None


def list_reports_or_none() -> list[dict] | None:
    """
    Some tenants 404 this endpoint; if so, just return None and skip.
    GET /api/quiz/v1/courses/:course_id/quizzes/:assignment_id/reports
    """
    url = f"{API_QZ}/courses/{COURSE_ID}/quizzes/{ASSIGNMENT_ID}/reports"
    r = SESSION.get(url)
    if r.status_code == 404:
        return None
    if r.status_code != 200:
        die("reports list GET failed", r)
    data = r.json()
    if isinstance(data, dict) and "reports" in data:
        return data["reports"]
    if isinstance(data, list):
        return data
    return []


def resolve_download_url_or_die(prog: dict) -> str:
    # First: anything usable on the progress object?
    url = try_progress_urls(prog)
    if url:
        return url

    # Second: try listing reports (if the endpoint is available) and look for the latest student_analysis
    reports = list_reports_or_none()
    if reports is not None:
        # Keep the most recently updated one with a usable URL
        def report_url(rep: dict) -> str | None:
            return (
                rep.get("attachment_url")
                or rep.get("download_url")
                or (rep.get("results") or {}).get("url")
                or (rep.get("file") or {}).get("url")
            )
        # Filter by type/format; order by updated_at desc
        candidates = [
            rep for rep in reports
            if rep.get("report_type") == "student_analysis"
            and (rep.get("format", "").lower() in ("", REPORT_FORMAT))
        ]
        candidates.sort(key=lambda x: x.get("updated_at") or x.get("created_at") or "", reverse=True)
        for rep in candidates:
            url = report_url(rep)
            if url:
                return url

    # Last chance: dump progress so you can see what keys exist
    die("could not resolve a download URL from progress or reports", extra=prog)


def download_or_die(url: str, out_path: str):
    with SESSION.get(url, stream=True) as r:
        if r.status_code != 200:
            die("download failed", r)
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                if chunk:
                    f.write(chunk)


def main():
    init_auth_or_die()
    print(f"Generate student_analysis for course={COURSE_ID}, quiz={ASSIGNMENT_ID} …")
    progress_url = create_report_or_die()
    prog = poll_progress_or_die(progress_url)
    dl_url = resolve_download_url_or_die(prog)

    ext = "json" if REPORT_FORMAT == "json" else "csv"
    out_path = f"student_analysis_{COURSE_ID}_{ASSIGNMENT_ID}.{ext}"
    download_or_die(dl_url, out_path)
    print(f"saved: {out_path}")


if __name__ == "__main__":
    main()