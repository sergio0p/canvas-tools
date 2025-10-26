#!/usr/bin/env python3
"""
Canvas PDF Uploader

Uploads all PDFs from the pdfs/ directory to Canvas, OVERWRITING
existing versions on Canvas.

Uses metadata from canvas_files.json (created by download_pdfs.py)
to match original Canvas filenames for proper overwrite behavior.
"""

import sys
import os
import json
import keyring
import requests
from pathlib import Path
from typing import Optional

# Configuration
CANVAS_SERVICE_NAME = 'canvas'
CANVAS_USERNAME = 'access-token'
HOST = 'https://uncch.instructure.com'
API_V1 = f"{HOST}/api/v1"

# Directories
SCRIPT_DIR = Path(__file__).parent
PDFS_DIR = SCRIPT_DIR / "pdfs"
METADATA_FILE = SCRIPT_DIR / "canvas_files.json"


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

    def upload_file(self, file_path: Path, course_id: int, folder_id: Optional[int] = None,
                   canvas_filename: Optional[str] = None, file_id: Optional[int] = None) -> bool:
        """Upload a file to Canvas with overwrite support"""
        try:
            # Step 1: Tell Canvas we want to upload a file
            upload_url = f"{API_V1}/courses/{course_id}/files"

            # Use the original Canvas filename for duplicate matching
            upload_name = canvas_filename if canvas_filename else file_path.name

            upload_params = {
                'name': upload_name,
                'size': file_path.stat().st_size,
                'content_type': 'application/pdf',
                'on_duplicate': 'overwrite',
            }

            # Set parent folder to maintain organization
            if folder_id:
                upload_params['parent_folder_id'] = folder_id

            response = self.session.post(upload_url, data=upload_params)

            if response.status_code not in [200, 201]:
                print(f"\n  ⚠️  Failed to initiate upload for {file_path.name}")
                print(f"      Status: {response.status_code}")
                print(f"      URL: {upload_url}")
                print(f"      Response: {response.text[:200]}")
                return False

            upload_data = response.json()

            # Check if Canvas returned a file object (duplicate detected) or upload workflow
            if 'upload_status' in upload_data and upload_data.get('upload_status') == 'success':
                # Canvas detected an identical file already exists - no upload needed
                # This is a success case (file already has the same content)
                return True

            # Step 2: Upload the file to the provided URL
            if 'upload_url' not in upload_data:
                print(f"\n  ⚠️  Canvas response missing upload_url for {file_path.name}")
                print(f"      Response keys: {list(upload_data.keys())}")
                print(f"      Response: {str(upload_data)[:300]}")
                return False

            upload_url = upload_data['upload_url']
            upload_params = upload_data['upload_params']

            with open(file_path, 'rb') as f:
                files = {'file': f}
                response = requests.post(upload_url, data=upload_params, files=files)

            # Step 3: Confirm the upload
            # Canvas typically returns a redirect (301/302/303) with a Location header
            if response.status_code in [301, 302, 303]:
                if 'Location' not in response.headers:
                    print(f"\n  ⚠️  Upload returned redirect but no Location header")
                    print(f"      File: {file_path.name}")
                    return False

                confirm_url = response.headers['Location']
                confirm_response = self.session.get(confirm_url)

                if confirm_response.status_code not in [200, 201]:
                    print(f"\n  ⚠️  Failed to confirm upload for {file_path.name}")
                    print(f"      Status: {confirm_response.status_code}")
                    print(f"      Response: {confirm_response.text[:200]}")
                    return False

                # Verify we got a valid file response
                try:
                    file_data = confirm_response.json()
                    if 'id' not in file_data:
                        print(f"\n  ⚠️  Upload confirmation missing file ID for {file_path.name}")
                        return False
                except Exception as e:
                    print(f"\n  ⚠️  Invalid confirmation response for {file_path.name}: {e}")
                    return False

            elif response.status_code not in [200, 201]:
                print(f"\n  ⚠️  Failed to upload file: {file_path.name}")
                print(f"      Status: {response.status_code}")
                print(f"      Response: {response.text[:200]}")
                return False

            # Step 4: Force Canvas/Ally to recognize the file change
            # Touch the file metadata to trigger event notifications
            try:
                # Get file ID from the final response
                if 'confirm_response' in locals():
                    file_data = confirm_response.json()
                else:
                    file_data = upload_data

                uploaded_file_id = file_data.get('id')

                if uploaded_file_id:
                    # Update a harmless metadata field to trigger Canvas events
                    # This ensures Ally receives notification of the file change
                    touch_url = f"{API_V1}/files/{uploaded_file_id}"
                    touch_response = self.session.put(touch_url, data={})
                    # Don't fail if touch fails - upload was still successful
            except Exception:
                # Touch failed, but upload succeeded - continue
                pass

            return True

        except Exception as e:
            print(f"  ⚠️  Error uploading {file_path.name}: {e}")
            return False


def display_progress_bar(current: int, total: int, prefix: str = "", length: int = 40):
    """Display a simple progress bar"""
    percent = current / total
    filled = int(length * percent)
    bar = '█' * filled + '░' * (length - filled)
    print(f"\r{prefix} [{bar}] {current}/{total} ({percent*100:.1f}%)", end='', flush=True)


def main():
    """Main execution flow"""

    print("\n" + "=" * 70)
    print("  CANVAS PDF UPLOADER")
    print("=" * 70)
    print("\nThis script will upload all PDFs from pdfs/ to Canvas")
    print("and OVERWRITE existing versions on Canvas.")
    print("=" * 70)

    # Check if pdfs directory exists
    if not PDFS_DIR.exists():
        print(f"\n❌ ERROR: Directory not found: {PDFS_DIR}/")
        print("Run download_pdfs.py first to download PDFs.")
        sys.exit(1)

    # Check if metadata file exists
    if not METADATA_FILE.exists():
        print(f"\n❌ ERROR: Metadata file not found: {METADATA_FILE}")
        print("Run download_pdfs.py first to create metadata.")
        sys.exit(1)

    # Load metadata
    with open(METADATA_FILE, 'r') as f:
        metadata = json.load(f)

    course_id = metadata['course_id']
    course_name = metadata['course_name']
    files_metadata = metadata['files']

    print(f"\n📚 Course: {course_name} (ID: {course_id})")

    # Get list of PDFs in directory
    pdf_files = list(PDFS_DIR.glob("*.pdf"))

    if not pdf_files:
        print(f"\n❌ No PDF files found in {PDFS_DIR}/")
        sys.exit(1)

    print(f"\n✓ Found {len(pdf_files)} PDF file(s) to upload")

    # Show files to be uploaded
    print(f"\n📄 Files to upload:")
    for pdf_path in pdf_files:
        filename = pdf_path.name
        if filename in files_metadata:
            pages = files_metadata[filename].get('pages', '?')
            print(f"  - {filename} ({pages} pages)")
        else:
            print(f"  - {filename} (⚠️  no metadata - will use local filename)")

    # Confirm upload
    print(f"\n⚠️  This will OVERWRITE existing files on Canvas!")
    confirm = input("Continue with upload? (y/n): ").strip().lower()

    if confirm != 'y':
        print("\nCancelled.")
        sys.exit(0)

    # Initialize client
    print("\n📡 Connecting to Canvas...")
    api_client = CanvasAPIClient()

    # Upload files
    print(f"\n📤 Uploading PDFs to Canvas...")
    successful_uploads = []
    failed_uploads = []

    for i, pdf_path in enumerate(pdf_files, 1):
        filename = pdf_path.name
        display_progress_bar(i, len(pdf_files), prefix="Uploading")

        # Get Canvas metadata (filename, folder_id, and file_id for overwrite)
        canvas_filename = None
        folder_id = None
        file_id = None

        if filename in files_metadata:
            canvas_filename = files_metadata[filename].get('canvas_filename')
            folder_id = files_metadata[filename].get('folder_id')
            file_id = files_metadata[filename].get('canvas_id')

        # Upload file
        success = api_client.upload_file(
            pdf_path,
            course_id,
            folder_id=folder_id,
            canvas_filename=canvas_filename,
            file_id=file_id
        )

        if success:
            successful_uploads.append(filename)
        else:
            failed_uploads.append(filename)

    print()  # New line after progress bar

    # Summary
    print(f"\n" + "=" * 70)
    print("  UPLOAD COMPLETE")
    print("=" * 70)
    print(f"\nTotal files:       {len(pdf_files)}")
    print(f"Successfully uploaded: {len(successful_uploads)}")
    print(f"Failed:            {len(failed_uploads)}")

    if failed_uploads:
        print(f"\n⚠️  Failed uploads:")
        for filename in failed_uploads:
            print(f"  - {filename}")

    print("\n" + "=" * 70)
    print("Done!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
