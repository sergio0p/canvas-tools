import requests
import keyring
import datetime

# === CONFIGURATION ===
BASE_URL = 'https://uncch.instructure.com'
COURSE_ID = '96082' # ECON 416 Id. COURSE_ID='97934' # ECON 510 Id.
SERVICE_NAME = 'canvas'
USERNAME = 'access-token'

API_TOKEN = keyring.get_password(SERVICE_NAME, USERNAME)
HEADERS = {
    'Authorization': f'Bearer {API_TOKEN}',
    'Content-Type': 'application/json'
}

# === Logging setup ===
timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
log_file = f'unpublish_log_{COURSE_ID}.txt'

def log(message):
    with open(log_file, 'a') as f:
        f.write(f"[{datetime.datetime.now()}] {message}\n")
    print(message)

def modify_file_visibility():
    url = f'{BASE_URL}/api/v1/courses/{COURSE_ID}/files?per_page=100'
    files = requests.get(url, headers=HEADERS).json()
    for f in files:
        file_url = f'{BASE_URL}/api/v1/files/{f["id"]}'
        payload = {"hidden": True}  # Change to True to hide, False to unhide
        response = requests.put(file_url, headers=HEADERS, json=payload)
        if response.status_code == 200:
            log(f"✅ Updated visibility for File \"{f['display_name']}\" → hidden={payload['hidden']}")
        else:
            log(f"⚠️ Failed to update visibility for File \"{f['display_name']}\" (status {response.status_code})")
            log(f"    → API response: {response.text}")

# === Main ===
log(f"📦 Starting file visibility update for course {COURSE_ID}")
modify_file_visibility()
log("🏁 Finished visibility update for files.\n")
