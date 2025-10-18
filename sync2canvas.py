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
METADATA_FILE = Path('files/canvas'+COURSE_ID+'-files-metadata.json')

# === SETUP ===
DOWNLOAD_ROOT.mkdir(exist_ok=True)
metadata = {}

if METADATA_FILE.exists():
    with open(METADATA_FILE, 'r') as f:
        metadata = json.load(f)

# === UTILS ===
def compute_hash(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

# === FETCH FILE LIST FROM CANVAS ===
def get_all_files():
    files = []
    url = f'{BASE_URL}/api/v1/courses/{COURSE_ID}/files?per_page=100'
    while url:
        res = requests.get(url, headers=HEADERS)
        res.raise_for_status()
        files.extend(res.json())
        url = res.links.get('next', {}).get('url')
    return files

# === STEP 1: DOWNLOAD CANVAS FILES ===
def sync_files():
    files = get_all_files()
    updated_metadata = {}

    for f in files:
        file_id = str(f['id'])
        fname = f['filename']
        folder_path = DOWNLOAD_ROOT / (f.get('folder_path') or '').lstrip('/')
        local_path = folder_path / fname
        folder_path.mkdir(parents=True, exist_ok=True)

        modified_at = f['modified_at']
        download_url = f['url']
        response = requests.get(download_url, headers=HEADERS)
        response.raise_for_status()
        content = response.content

        recorded = metadata.get(file_id, {})
        prev_hash = recorded.get('sha256')
        current_hash = hashlib.sha256(content).hexdigest()

        if current_hash != prev_hash:
            print(f"⬇️ Downloading {fname}")
            with open(local_path, 'wb') as out_file:
                out_file.write(content)
        else:
            print(f"✅ Skipped (unchanged): {fname}")

        updated_metadata[file_id] = {
            'filename': fname,
            'folder_path': f.get('folder_path') or '',
            'modified_at': modified_at,
            'sha256': current_hash,
            'canvas_folder_id': f['folder_id']
        }


    with open(METADATA_FILE, 'w') as f:
        json.dump(updated_metadata, f, indent=2)

    return updated_metadata

# === STEP 2 + 3: DETECT LOCAL CHANGES AND UPLOAD ===
def upload_modified_files():
    changed = []
    for file_id, info in metadata.items():
        local_path = DOWNLOAD_ROOT / info['folder_path'].lstrip('/') / info['filename']
        if not local_path.exists():
            continue

        current_hash = compute_hash(local_path)
        if current_hash != info.get('sha256'):
            changed.append((file_id, info, local_path, current_hash))

    for file_id, info, path, new_hash in changed:
        print(f"⬆️ Uploading {info['filename']}...")

        size = os.path.getsize(path)
        upload_init = requests.post(
            f"{BASE_URL}/api/v1/courses/{COURSE_ID}/files",
            headers=HEADERS,
            data={
                "name": info['filename'],
                "size": size,
                "parent_folder_path": info['folder_path'],
                "on_duplicate": "overwrite"
            }
        )
        upload_init.raise_for_status()
        res_json = upload_init.json()

        upload_url = res_json['upload_url']
        upload_params = res_json['upload_params']
        files = {"file": open(path, 'rb')}

        post_data = upload_params.copy()
        post_data['file'] = files['file']
        upload_res = requests.post(upload_url, files=post_data)
        upload_res.raise_for_status()

        # Step 3: Confirm upload
        confirm_url = upload_res.headers.get("Location")
        if confirm_url:
            confirm_res = requests.post(confirm_url, headers={
                "Authorization": f"Bearer {API_TOKEN}",
                "Content-Length": "0"
            })
            confirm_res.raise_for_status()

        print(f"✅ Uploaded and confirmed: {info['filename']}")
        metadata[file_id]['sha256'] = new_hash

    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=2)

# === RUN ===
print(f"📥 Syncing files from Canvas course {COURSE_ID}...")
metadata = sync_files()
print(len(metadata))
print(f"🚀 Uploading any locally modified files...")
upload_modified_files()
print("✅ Sync complete.")