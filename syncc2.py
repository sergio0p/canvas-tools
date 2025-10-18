import os
import json
import hashlib
import requests
import keyring
from pathlib import Path
from urllib.parse import urljoin

# === CONFIGURATION ===
BASE_URL = 'https://uncch.instructure.com'
COURSE_ID = '97934'
SERVICE_NAME = 'canvas'
USERNAME = 'access-token'
API_TOKEN = keyring.get_password(SERVICE_NAME, USERNAME)
HEADERS = {'Authorization': f'Bearer {API_TOKEN}'}
DOWNLOAD_ROOT = Path('files')
METADATA_FILE = Path('files/metadata.json')

# === HELPERS ===
def sha256sum(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def fetch_all_pages(url):
    results = []
    while url:
        r = requests.get(url, headers=HEADERS)
        r.raise_for_status()
        results.extend(r.json())
        url = r.links.get("next", {}).get("url")
    return results

# === NEW: Folder Path Builder ===
def fetch_folder_map():
    url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}/folders"
    folders = fetch_all_pages(url)
    folder_map = {f["id"]: f for f in folders}
    full_paths = {}
    for folder_id in folder_map:
        path = []
        current_id = folder_id
        while current_id is not None:
            folder = folder_map.get(current_id)
            if not folder:
                break
            path.append(folder["name"])
            current_id = folder.get("parent_folder_id")
        full_path = "/".join(reversed(path)).replace("course files/", "")
        full_paths[folder_id] = full_path
    return full_paths

# === MAIN SYNC FUNCTION ===
def sync_files():
    DOWNLOAD_ROOT.mkdir(exist_ok=True)
    metadata = json.loads(METADATA_FILE.read_text()) if METADATA_FILE.exists() else {}

    folder_paths = fetch_folder_map()
    url = f"{BASE_URL}/api/v1/courses/{COURSE_ID}/files?per_page=100"
    files = fetch_all_pages(url)

    for f in files:
        folder_id = f.get("folder_id")
        relative_path = folder_paths.get(folder_id, "")
        folder_path = DOWNLOAD_ROOT / relative_path
        folder_path.mkdir(parents=True, exist_ok=True)

        dest = folder_path / f["filename"]
        file_id = str(f["id"])
        modified = f["modified_at"]
        url = f["url"]

        if file_id in metadata:
            local_sha = sha256sum(dest) if dest.exists() else None
            if metadata[file_id].get("sha256") == local_sha:
                continue

        r = requests.get(url, headers=HEADERS)
        r.raise_for_status()
        with open(dest, "wb") as out:
            out.write(r.content)

        metadata[file_id] = {
            "filename": f["filename"],
            "folder_path": relative_path,
            "modified_at": modified,
            "sha256": sha256sum(dest),
            "canvas_folder_id": folder_id,
        }

    METADATA_FILE.write_text(json.dumps(metadata, indent=2))
    return metadata

if __name__ == "__main__":
    metadata = sync_files()
    print(f"✅ Synced {len(metadata)} files.")
