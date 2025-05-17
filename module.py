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
log_file = f'unpublish_modules_log_{COURSE_ID}.txt'

def log(message):
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(log_file, 'a') as f:
        f.write(f"[{timestamp}] {message}\n")
    print(message)

# === UnPublish All Modules ===
def unpublish_modules():
    modules_url = f'{BASE_URL}/api/v1/courses/{COURSE_ID}/modules'
    modules = requests.get(modules_url, headers=HEADERS).json()

    for m in modules:
        module_id = m['id']
        update_url = f'{modules_url}/{module_id}'
        payload = {
            'module[published]': False,
            'module[name]': m['name']
        }
        response = requests.put(update_url, headers=HEADERS, data=payload)

        if response.status_code == 200:
            log(f"✅ Unpublished module: {m['name']}")
        else:
            log(f"⚠️ Failed to unpublish module: {m['name']} (status {response.status_code})")
            log(f"    → API response: {response.text}")

# === Main ===
log(f"📦 Starting unpublish pass for modules in course {COURSE_ID}")
unpublish_modules()
log("🏁 Finished unpublishing modules.")
