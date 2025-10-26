#!/usr/bin/env python3
"""
Canvas PDF Accessibility Auto-Tagger

Downloads PDFs from a Canvas course, classifies them, auto-tags untagged PDFs
using Adobe Acrobat Pro 2020, and uploads them back to Canvas with overwrite.

Workflow:
1. Download PDFs to ./originals/
2. Classify each PDF (TeX-generated/already-tagged/needs-tagging)
3. For PDFs needing tags:
   - Backup to ./backups/
   - Auto-tag using Acrobat Pro 2020 via AppleScript
   - Verify success
4. Upload tagged PDFs with overwrite

Author: Claude Code
"""

import sys
import os
import time
import json
import shutil
import subprocess
import keyring
import requests
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from urllib.parse import unquote_plus

try:
    from pypdf import PdfReader
except ImportError:
    print("Installing pypdf...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "pypdf"])
    from pypdf import PdfReader

# Configuration
CANVAS_SERVICE_NAME = 'canvas'
CANVAS_USERNAME = 'access-token'
HOST = 'https://uncch.instructure.com'
API_V1 = f"{HOST}/api/v1"

# Directories
SCRIPT_DIR = Path(__file__).parent
ORIGINALS_DIR = SCRIPT_DIR / "originals"
BACKUPS_DIR = SCRIPT_DIR / "backups"
APPLESCRIPT_PATH = SCRIPT_DIR / "tag_pdf_acrobat.scpt"

# Timing for auto-tagging
SECONDS_PER_PAGE = 1.2
BUFFER_SECONDS = 5


@dataclass
class Course:
    """Represents a Canvas course"""
    id: int
    name: str
    workflow_state: str


@dataclass
class CanvasFile:
    """Represents a file in Canvas"""
    id: int
    filename: str
    display_name: str
    url: str
    size: int
    content_type: str
    folder_id: Optional[int] = None

    def get_clean_filename(self) -> str:
        """Get filename with proper spacing (decode URL encoding if present)"""
        # Try display_name first (usually cleaner)
        if self.display_name and self.display_name.endswith('.pdf'):
            return self.display_name
        # Fall back to decoded filename
        return unquote_plus(self.filename)


@dataclass
class PDFClassification:
    """Classification result for a PDF"""
    file: CanvasFile
    classification: str  # 'tex-generated', 'already-tagged', 'needs-tagging'
    page_count: int
    has_marked_flag: bool
    reason: str


@dataclass
class ProcessingResult:
    """Result of processing a PDF"""
    file: CanvasFile
    success: bool
    classification: str
    action_taken: str  # 'skipped', 'tagged', 'error'
    error_message: Optional[str] = None


class CanvasAPIClient:
    """Handles all Canvas API interactions"""

    def __init__(self):
        """Initialize API client with authentication"""
        self.token = self._get_token()
        self.session = requests.Session()
        self.session.headers.update({'Authorization': f'Bearer {self.token}'})

    def _get_token(self) -> str:
        """Retrieve API token from keychain"""
        token = keyring.get_password(CANVAS_SERVICE_NAME, CANVAS_USERNAME)
        if not token:
            print(f"❌ ERROR: No Canvas API token found in keychain.")
            print(f"Set one using: keyring.set_password('{CANVAS_SERVICE_NAME}', '{CANVAS_USERNAME}', 'your_token')")
            sys.exit(1)
        return token

    def get_favorite_courses(self) -> List[Course]:
        """Fetch user's favorite courses, filtered for published only"""
        url = f"{API_V1}/users/self/favorites/courses"
        response = self.session.get(url)

        if response.status_code != 200:
            print(f"❌ Failed to fetch courses: {response.status_code}")
            sys.exit(1)

        courses = response.json()
        published = [
            Course(c['id'], c['name'], c['workflow_state'])
            for c in courses
            if c.get('workflow_state') == 'available'
        ]

        return published

    def get_course_files(self, course_id: int) -> List[CanvasFile]:
        """Fetch all PDF files from a course"""
        all_files = []
        url = f"{API_V1}/courses/{course_id}/files"

        while url:
            response = self.session.get(url, params={'per_page': 100})

            if response.status_code != 200:
                print(f"❌ Failed to fetch files: {response.status_code}")
                sys.exit(1)

            files = response.json()
            all_files.extend(files)

            # Check for pagination
            url = response.links.get('next', {}).get('url')

        # Filter for PDFs only
        pdf_files = [
            CanvasFile(
                id=f['id'],
                filename=f['filename'],
                display_name=f['display_name'],
                url=f['url'],
                size=f['size'],
                content_type=f['content-type'],
                folder_id=f.get('folder_id')
            )
            for f in all_files
            if f.get('content-type') == 'application/pdf'
        ]

        return pdf_files

    def download_file(self, file: CanvasFile, destination: Path) -> bool:
        """Download a file from Canvas"""
        try:
            response = self.session.get(file.url, stream=True)

            if response.status_code != 200:
                print(f"  ⚠️  Failed to download {file.get_clean_filename()}: {response.status_code}")
                return False

            with open(destination, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            return True
        except Exception as e:
            print(f"  ⚠️  Error downloading {file.get_clean_filename()}: {e}")
            return False

    def upload_file(self, file_path: Path, course_id: int, folder_id: Optional[int] = None,
                   on_duplicate: str = "overwrite", canvas_filename: Optional[str] = None) -> bool:
        """Upload a file to Canvas with overwrite support

        Args:
            file_path: Local path to the file
            course_id: Canvas course ID
            folder_id: Optional folder ID
            on_duplicate: Action for duplicates ('overwrite', 'rename', etc.)
            canvas_filename: Original Canvas filename (for matching duplicates)
        """
        try:
            # Step 1: Tell Canvas we want to upload a file
            upload_url = f"{API_V1}/courses/{course_id}/files"

            # Use the original Canvas filename for duplicate matching
            upload_name = canvas_filename if canvas_filename else file_path.name

            upload_params = {
                'name': upload_name,
                'size': file_path.stat().st_size,
                'content_type': 'application/pdf',
                'on_duplicate': on_duplicate
            }

            if folder_id:
                upload_params['parent_folder_id'] = folder_id

            response = self.session.post(upload_url, data=upload_params)

            if response.status_code not in [200, 201]:
                print(f"  ⚠️  Failed to initiate upload: {response.status_code}")
                return False

            upload_data = response.json()

            # Step 2: Upload the file to the provided URL
            upload_url = upload_data['upload_url']
            upload_params = upload_data['upload_params']

            with open(file_path, 'rb') as f:
                files = {'file': f}
                response = requests.post(upload_url, data=upload_params, files=files)

            if response.status_code not in [200, 201, 301]:
                print(f"  ⚠️  Failed to upload file: {response.status_code}")
                return False

            # Step 3: Confirm the upload (if needed)
            if 'Location' in response.headers:
                confirm_url = response.headers['Location']
                response = self.session.get(confirm_url)

            return True

        except Exception as e:
            print(f"  ⚠️  Error uploading {file_path.name}: {e}")
            return False


class PDFClassifier:
    """Classifies PDFs for accessibility tagging needs"""

    @staticmethod
    def classify_pdf(file_path: Path, file: CanvasFile) -> PDFClassification:
        """
        Classify a PDF into one of three categories:
        - 'tex-generated': LaTeX-generated (likely already accessible)
        - 'already-tagged': Has accessibility tags
        - 'needs-tagging': Needs accessibility tagging
        """
        try:
            reader = PdfReader(file_path)
            page_count = len(reader.pages)

            # Check for /MarkInfo /Marked flag
            has_marked_flag = False
            if reader.trailer.get("/Root"):
                root = reader.trailer["/Root"]
                if "/MarkInfo" in root:
                    mark_info = root["/MarkInfo"]
                    if "/Marked" in mark_info:
                        has_marked_flag = bool(mark_info["/Marked"])

            # Check metadata for TeX/LaTeX indicators
            metadata = reader.metadata
            is_tex = False

            if metadata:
                producer = str(metadata.get('/Producer', '')).lower()
                creator = str(metadata.get('/Creator', '')).lower()

                tex_indicators = ['tex', 'latex', 'pdftex', 'xetex', 'luatex']
                is_tex = any(ind in producer or ind in creator for ind in tex_indicators)

            # Classification logic
            if is_tex:
                classification = 'tex-generated'
                reason = "LaTeX/TeX-generated PDF (likely accessible)"
            elif has_marked_flag:
                classification = 'already-tagged'
                reason = "Already has /Marked flag set"
            else:
                classification = 'needs-tagging'
                reason = "No accessibility tags detected"

            return PDFClassification(
                file=file,
                classification=classification,
                page_count=page_count,
                has_marked_flag=has_marked_flag,
                reason=reason
            )

        except Exception as e:
            print(f"  ⚠️  Error classifying {file.get_clean_filename()}: {e}")
            return PDFClassification(
                file=file,
                classification='error',
                page_count=0,
                has_marked_flag=False,
                reason=f"Error: {e}"
            )


class AcrobatAutoTagger:
    """Handles auto-tagging PDFs using Adobe Acrobat Pro 2020 via AppleScript"""

    def __init__(self, applescript_path: Path):
        self.applescript_path = applescript_path

        if not self.applescript_path.exists():
            print(f"❌ ERROR: AppleScript not found at {self.applescript_path}")
            sys.exit(1)

    def calculate_wait_time(self, page_count: int) -> int:
        """Calculate wait time based on page count"""
        return int((page_count * SECONDS_PER_PAGE) + BUFFER_SECONDS)

    def tag_pdf(self, pdf_path: Path, page_count: int) -> Tuple[bool, str]:
        """
        Auto-tag a PDF using Acrobat Pro 2020

        Returns:
            (success, message)
        """
        wait_time = self.calculate_wait_time(page_count)

        try:
            # Call AppleScript
            result = subprocess.run(
                ['osascript', str(self.applescript_path), str(pdf_path), str(wait_time)],
                capture_output=True,
                text=True,
                timeout=wait_time + 30  # Extra timeout buffer
            )

            output = result.stdout.strip()

            if result.returncode != 0:
                error_msg = result.stderr.strip() or output
                return False, f"AppleScript error: {error_msg}"

            if output.startswith("SUCCESS"):
                return True, "Successfully tagged"
            elif output.startswith("ERROR"):
                return False, output
            else:
                return False, f"Unexpected output: {output}"

        except subprocess.TimeoutExpired:
            return False, f"Timeout after {wait_time + 30} seconds"
        except Exception as e:
            return False, f"Exception: {e}"


def display_courses(courses: List[Course]) -> None:
    """Display list of courses"""
    print("\nAvailable Courses:")
    print("-" * 60)
    for i, course in enumerate(courses, 1):
        print(f"{i}. {course.name} (ID: {course.id})")


def get_user_choice(prompt: str, max_value: int) -> int:
    """Get user selection from menu"""
    while True:
        try:
            choice = input(f"\n{prompt} (1-{max_value}, or 'q' to quit): ").strip()
            if choice.lower() == 'q':
                print("\nExiting...")
                sys.exit(0)

            value = int(choice)
            if 1 <= value <= max_value:
                return value - 1
            else:
                print(f"Please enter a number between 1 and {max_value}")
        except ValueError:
            print("Invalid input. Please enter a number.")


def display_progress_bar(current: int, total: int, prefix: str = "", length: int = 40):
    """Display a simple progress bar"""
    percent = current / total
    filled = int(length * percent)
    bar = '█' * filled + '░' * (length - filled)
    print(f"\r{prefix} [{bar}] {current}/{total} ({percent*100:.1f}%)", end='', flush=True)


def main():
    """Main execution flow"""

    print("\n" + "=" * 70)
    print("  CANVAS PDF ACCESSIBILITY AUTO-TAGGER")
    print("=" * 70)
    print("\nThis tool will:")
    print("  1. Download PDFs from a Canvas course")
    print("  2. Classify each PDF (TeX/tagged/needs-tagging)")
    print("  3. Auto-tag untagged PDFs using Acrobat Pro 2020")
    print("  4. Upload tagged PDFs back to Canvas")
    print("=" * 70)

    # Ensure directories exist
    ORIGINALS_DIR.mkdir(exist_ok=True)
    BACKUPS_DIR.mkdir(exist_ok=True)

    # Initialize clients
    print("\n📡 Connecting to Canvas...")
    api_client = CanvasAPIClient()

    # Select course
    courses = api_client.get_favorite_courses()

    if not courses:
        print("\n❌ No favorite published courses found.")
        sys.exit(1)

    display_courses(courses)
    course_idx = get_user_choice("Select a course", len(courses))
    selected_course = courses[course_idx]

    print(f"\n✓ Selected: {selected_course.name}")

    # Fetch PDFs
    print(f"\n📥 Fetching PDF files from course...")
    pdf_files = api_client.get_course_files(selected_course.id)

    if not pdf_files:
        print("\n❌ No PDF files found in this course.")
        sys.exit(1)

    print(f"✓ Found {len(pdf_files)} PDF file(s)")

    # Download PDFs
    print(f"\n📥 Downloading PDFs to {ORIGINALS_DIR}/...")
    downloaded_files = []

    for i, pdf_file in enumerate(pdf_files, 1):
        # Use clean filename for local storage (spaces instead of +)
        destination = ORIGINALS_DIR / pdf_file.get_clean_filename()
        display_progress_bar(i, len(pdf_files), prefix="Downloading")

        if api_client.download_file(pdf_file, destination):
            downloaded_files.append((pdf_file, destination))

    print()  # New line after progress bar
    print(f"✓ Downloaded {len(downloaded_files)} file(s)")

    # Classify PDFs
    print(f"\n🔍 Classifying PDFs...")
    classifier = PDFClassifier()
    classifications = []

    for i, (canvas_file, local_path) in enumerate(downloaded_files, 1):
        display_progress_bar(i, len(downloaded_files), prefix="Classifying")
        classification = classifier.classify_pdf(local_path, canvas_file)
        classifications.append(classification)

    print()  # New line after progress bar

    # Display classification summary
    tex_count = sum(1 for c in classifications if c.classification == 'tex-generated')
    tagged_count = sum(1 for c in classifications if c.classification == 'already-tagged')
    needs_tagging_count = sum(1 for c in classifications if c.classification == 'needs-tagging')

    print(f"\n📊 Classification Summary:")
    print(f"  TeX-generated:   {tex_count} (will skip)")
    print(f"  Already tagged:  {tagged_count} (will skip)")
    print(f"  Needs tagging:   {needs_tagging_count} (will process)")

    if needs_tagging_count == 0:
        print("\n✅ All PDFs are already accessible or TeX-generated!")
        print("No auto-tagging needed.")
        sys.exit(0)

    # Confirm before processing
    print(f"\n⚠️  About to auto-tag {needs_tagging_count} PDF(s) using Acrobat Pro 2020")
    confirm = input("Continue? (y/n): ").strip().lower()

    if confirm != 'y':
        print("\nCancelled.")
        sys.exit(0)

    # Initialize auto-tagger
    tagger = AcrobatAutoTagger(APPLESCRIPT_PATH)

    # Process PDFs that need tagging
    print(f"\n🏷️  Auto-tagging PDFs...")
    processing_results = []

    pdfs_to_tag = [c for c in classifications if c.classification == 'needs-tagging']

    for i, classification in enumerate(pdfs_to_tag, 1):
        clean_filename = classification.file.get_clean_filename()
        pdf_path = ORIGINALS_DIR / clean_filename
        backup_path = BACKUPS_DIR / f"{clean_filename}.bak.pdf"

        print(f"\n[{i}/{len(pdfs_to_tag)}] Processing: {clean_filename}")
        print(f"  Pages: {classification.page_count}")

        # Backup original
        print(f"  Creating backup...")
        shutil.copy2(pdf_path, backup_path)

        # Auto-tag
        wait_time = tagger.calculate_wait_time(classification.page_count)
        print(f"  Auto-tagging (will take ~{wait_time} seconds)...")

        success, message = tagger.tag_pdf(pdf_path, classification.page_count)

        if success:
            print(f"  ✓ {message}")
            processing_results.append(ProcessingResult(
                file=classification.file,
                success=True,
                classification=classification.classification,
                action_taken='tagged'
            ))
        else:
            print(f"  ✗ {message}")
            processing_results.append(ProcessingResult(
                file=classification.file,
                success=False,
                classification=classification.classification,
                action_taken='error',
                error_message=message
            ))

    # Upload tagged PDFs
    successful_tags = [r for r in processing_results if r.success]

    if successful_tags:
        print(f"\n📤 Uploading {len(successful_tags)} tagged PDF(s) to Canvas...")

        for i, result in enumerate(successful_tags, 1):
            # Use clean filename for local path, but pass original Canvas filename for overwrite matching
            pdf_path = ORIGINALS_DIR / result.file.get_clean_filename()
            display_progress_bar(i, len(successful_tags), prefix="Uploading")

            api_client.upload_file(
                pdf_path,
                selected_course.id,
                folder_id=result.file.folder_id,
                on_duplicate="overwrite",
                canvas_filename=result.file.filename  # Original Canvas filename for duplicate matching
            )

        print()  # New line after progress bar
        print(f"✓ Uploaded {len(successful_tags)} file(s)")

    # Final summary
    print("\n" + "=" * 70)
    print("  PROCESSING COMPLETE")
    print("=" * 70)
    print(f"\nTotal PDFs found:        {len(pdf_files)}")
    print(f"Skipped (TeX):           {tex_count}")
    print(f"Skipped (already tagged): {tagged_count}")
    print(f"Successfully tagged:      {len(successful_tags)}")
    print(f"Failed to tag:            {needs_tagging_count - len(successful_tags)}")

    if processing_results:
        failed = [r for r in processing_results if not r.success]
        if failed:
            print(f"\n⚠️  Failed PDFs:")
            for result in failed:
                print(f"  - {result.file.get_clean_filename()}: {result.error_message}")

    print("\n" + "=" * 70)
    print("Done!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
