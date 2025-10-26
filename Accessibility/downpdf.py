#!/usr/bin/env python3
"""
Canvas PDF Downloader & Filter

Downloads PDFs from a Canvas course, classifies them, and keeps only
untagged non-TeX PDFs for manual accessibility tagging.

Deletes:
- TeX/LaTeX-generated PDFs (already accessible)
- Already-tagged PDFs (have /Marked flag)

Keeps:
- PDFs that need accessibility tagging

Saves metadata to canvas_files.json for later upload.
"""

import sys
import os
import json
import keyring
import requests
from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass, asdict
from urllib.parse import unquote_plus

try:
    from pypdf import PdfReader
except ImportError:
    print("Installing pypdf...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "pypdf"])
    from pypdf import PdfReader

# Configuration
CANVAS_SERVICE_NAME = 'canvas'
CANVAS_USERNAME = 'access-token'
HOST = 'https://uncch.instructure.com'
API_V1 = f"{HOST}/api/v1"

# Directories
SCRIPT_DIR = Path(__file__).parent
PDFS_DIR = SCRIPT_DIR / "pdfs"
METADATA_FILE = SCRIPT_DIR / "canvas_files.json"


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
        if self.display_name and self.display_name.endswith('.pdf'):
            return self.display_name
        return unquote_plus(self.filename)


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


class PDFClassifier:
    """Classifies PDFs for accessibility tagging needs"""

    @staticmethod
    def classify_pdf(file_path: Path) -> tuple:
        """
        Classify a PDF:
        Returns: (classification, reason, page_count)
        - 'tex-generated': LaTeX-generated (delete)
        - 'already-tagged': Has accessibility tags (delete)
        - 'needs-tagging': Needs accessibility tagging (keep)
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
                return 'tex-generated', "LaTeX/TeX-generated (likely accessible)", page_count
            elif has_marked_flag:
                return 'already-tagged', "Already has /Marked flag", page_count
            else:
                return 'needs-tagging', "No accessibility tags", page_count

        except Exception as e:
            return 'error', f"Error: {e}", 0


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
    print("  CANVAS PDF DOWNLOADER & FILTER")
    print("=" * 70)
    print("\nThis script will:")
    print("  1. Download all PDFs from a Canvas course")
    print("  2. DELETE TeX/LaTeX-generated PDFs (already accessible)")
    print("  3. DELETE already-tagged PDFs (have accessibility tags)")
    print("  4. KEEP only PDFs that need manual tagging")
    print("=" * 70)

    # Ensure directory exists
    PDFS_DIR.mkdir(exist_ok=True)

    # Initialize client
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
    print(f"\n📥 Downloading PDFs to {PDFS_DIR}/...")
    downloaded_files = []

    for i, pdf_file in enumerate(pdf_files, 1):
        destination = PDFS_DIR / pdf_file.get_clean_filename()
        display_progress_bar(i, len(pdf_files), prefix="Downloading")

        if api_client.download_file(pdf_file, destination):
            downloaded_files.append((pdf_file, destination))

    print()  # New line after progress bar
    print(f"✓ Downloaded {len(downloaded_files)} file(s)")

    # Classify and filter PDFs
    print(f"\n🔍 Classifying and filtering PDFs...")

    tex_deleted = []
    tagged_deleted = []
    kept_files = []
    metadata_map = {}

    for i, (canvas_file, local_path) in enumerate(downloaded_files, 1):
        display_progress_bar(i, len(downloaded_files), prefix="Processing")

        classification, reason, page_count = PDFClassifier.classify_pdf(local_path)

        if classification == 'tex-generated':
            tex_deleted.append(canvas_file.get_clean_filename())
            local_path.unlink()  # Delete file
        elif classification == 'already-tagged':
            tagged_deleted.append(canvas_file.get_clean_filename())
            local_path.unlink()  # Delete file
        elif classification == 'needs-tagging':
            kept_files.append((canvas_file, local_path, page_count))
            # Store metadata for upload script
            metadata_map[canvas_file.get_clean_filename()] = {
                'canvas_id': canvas_file.id,
                'canvas_filename': canvas_file.filename,
                'display_name': canvas_file.display_name,
                'folder_id': canvas_file.folder_id,
                'pages': page_count
            }

    print()  # New line after progress bar

    # Save metadata for upload script
    with open(METADATA_FILE, 'w') as f:
        json.dump({
            'course_id': selected_course.id,
            'course_name': selected_course.name,
            'files': metadata_map
        }, f, indent=2)

    # Display summary
    print(f"\n📊 Processing Summary:")
    print(f"  Total PDFs:          {len(downloaded_files)}")
    print(f"  TeX/LaTeX (deleted): {len(tex_deleted)}")
    print(f"  Already tagged (deleted): {len(tagged_deleted)}")
    print(f"  Needs tagging (kept): {len(kept_files)}")

    if tex_deleted:
        print(f"\n🗑️  Deleted TeX/LaTeX PDFs:")
        for filename in tex_deleted[:10]:  # Show first 10
            print(f"  - {filename}")
        if len(tex_deleted) > 10:
            print(f"  ... and {len(tex_deleted) - 10} more")

    if tagged_deleted:
        print(f"\n🗑️  Deleted already-tagged PDFs:")
        for filename in tagged_deleted[:10]:  # Show first 10
            print(f"  - {filename}")
        if len(tagged_deleted) > 10:
            print(f"  ... and {len(tagged_deleted) - 10} more")

    if kept_files:
        print(f"\n✅ PDFs ready for manual tagging in {PDFS_DIR}/:")
        for canvas_file, _, page_count in kept_files:
            print(f"  - {canvas_file.get_clean_filename()} ({page_count} pages)")

        print(f"\n" + "=" * 70)
        print("NEXT STEPS:")
        print("=" * 70)
        print(f"1. Manually tag PDFs in Acrobat Pro 2020:")
        print(f"   - Open each PDF from {PDFS_DIR}/")
        print(f"   - Tools → Accessibility → Autotag Document")
        print(f"   - Save (overwrites original)")
        print(f"2. Run upload_pdfs.py to upload tagged PDFs to Canvas")
        print("=" * 70)
    else:
        print("\n✅ All PDFs are already accessible or TeX-generated!")
        print("No manual tagging needed.")

    print()


if __name__ == "__main__":
    main()
