import os
import hashlib
import json
import requests
from pathlib import Path
import keyring
import sys

# === CONFIG ===
SERVICE_NAME = 'canvas'
USERNAME = 'access-token'
COURSE_ID = "97934"  # Replace with your actual course ID
API_BASE = "https://uncch.instructure.com/api/v1"
UPLOAD_LIST_JSON = "upload_list.json"  # must exist in current dir

# === AUTH ===
API_TOKEN = keyring.get_password(SERVICE_NAME, USERNAME)
if not API_TOKEN:
    print("❌ No Canvas API token found in keyring.")
    print(f"Set one using: keyring.set_password('{SERVICE_NAME}', '{USERNAME}', 'your_token')")
    sys.exit(1)

HEADERS = {
    'Authorization': f'Bearer {API_TOKEN}',
    'Content-Type': 'application/json'
}

# === PATHS ===
CURRENT_DIR = Path.cwd()
METADATA_FILE = CURRENT_DIR / ".canvas-sync.json"
UPLOAD_LIST_FILE = CURRENT_DIR / UPLOAD_LIST_JSON

# === HELPERS ===

def file_hash(path):
    hasher = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def load_metadata():
    if METADATA_FILE.exists():
        with open(METADATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_metadata(meta):
    with open(METADATA_FILE, "w") as f:
        json.dump(meta, f, indent=2)

def upload_file(course_id, filepath):
    import mimetypes

    filename = filepath.name
    url = f"{API_BASE}/courses/{course_id}/files"

    content_type = mimetypes.guess_type(filepath)[0] or "application/octet-stream"

    # Step 1
    payload = {
        "name": filename,
        "size": filepath.stat().st_size,
        "content_type": content_type,
        "on_duplicate": "overwrite"
    }
    r = requests.post(url, headers=HEADERS, json=payload)
    r.raise_for_status()
    upload_info = r.json()

    # Step 2
    upload_url = upload_info["upload_url"]
    upload_params = upload_info["upload_params"]
    with open(filepath, "rb") as f:
        files = {"file": (filename, f)}
        r2 = requests.post(upload_url, data=upload_params, files=files, allow_redirects=False)
        r2.raise_for_status()

    # Step 3: Confirm and extract metadata
    if "Location" in r2.headers:
        confirm_url = r2.headers["Location"]
        r3 = requests.post(confirm_url, headers={"Authorization": f"Bearer {API_TOKEN}", "Content-Length": "0"})
        r3.raise_for_status()
        canvas_file = r3.json()
        file_id = canvas_file["id"]
        file_url = f"{API_BASE}/courses/{course_id}/files/{file_id}"
        print(f"✅ Uploaded: {filename}")

        # Save the Canvas URL
        update_canvas_file_url_record(filename, file_url)
    else:
        raise Exception(f"❌ Upload incomplete: no confirmation Location for {filename}")

def update_canvas_file_url_record(filename, file_url, output_file="canvas_file_urls.json"):
    if Path(output_file).exists():
        with open(output_file, "r") as f:
            data = json.load(f)
    else:
        data = {}

    if filename not in data:
        data[filename] = file_url
        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)
        print(f"📝 Canvas URL recorded: {filename} → {file_url}")
    else:
        print(f"ℹ️ Canvas URL already recorded for: {filename}")
        
# === MAIN ===

def main():
    print(f"📂 Syncing from folder: {CURRENT_DIR}")
    if not UPLOAD_LIST_FILE.exists():
        print(f"❌ {UPLOAD_LIST_JSON} not found in current directory.")
        sys.exit(1)

    with open(UPLOAD_LIST_FILE, "r") as f:
        file_list = json.load(f)

    if not isinstance(file_list, list):
        print("❌ upload_list.json must be a list of filenames.")
        sys.exit(1)

    metadata = load_metadata()
    updated = False

    for filename in file_list:
        path = CURRENT_DIR / filename
        if not path.is_file():
            print(f"⚠️ Skipping missing file: {filename}")
            continue

        h = file_hash(path)
        old = metadata.get(filename)
        if not old or old["hash"] != h:
            print(f"📤 Uploading: {filename}")
            try:
                upload_file(COURSE_ID, path)
                metadata[filename] = {
                    "hash": h,
                    "mtime": path.stat().st_mtime
                }
                updated = True
            except Exception as e:
                print(f"❌ Failed to upload {filename}: {e}")
        else:
            print(f"⏩ Skipped (unchanged): {filename}")

    if updated:
        save_metadata(metadata)
        print("✅ Metadata updated.")
    else:
        print("✅ All files already up to date.")
        

if __name__ == "__main__":
    main()