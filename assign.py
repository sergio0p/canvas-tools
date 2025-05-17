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
    'Authorization': f'Bearer ' + API_TOKEN
}

# === Logging setup ===
log_file = f'unpublish_assignments_log_{COURSE_ID}.txt'

def log(message):
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(log_file, 'a') as f:
        f.write(f"[{timestamp}] {message}\n")
    print(message)

# === Unpublish Assignments ===
def unpublish_assignments():
    url = f'{BASE_URL}/api/v1/courses/{COURSE_ID}/assignments?per_page=100'
    assignments = requests.get(url, headers=HEADERS).json()

    for a in assignments:
        if a.get('published'):
            update_url = f'{BASE_URL}/api/v1/courses/{COURSE_ID}/assignments/{a["id"]}'
            payload = {
                'assignment[published]': False
            }
            response = requests.put(update_url, headers=HEADERS, data=payload)
            if response.status_code == 200:
                log(f"✅ Unpublished assignment: {a['name']}")
            else:
                log(f"⚠️ Failed to unpublish assignment: {a['name']} (status {response.status_code})")
                log(f"    → API response: {response.text}")

# === Main ===
log(f"📦 Starting unpublish pass for assignments in course {COURSE_ID}")
unpublish_assignments()
log("🏁 Finished unpublishing assignments.")