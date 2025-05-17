import requests
import keyring
import datetime

# === CONFIGURATION ===
BASE_URL = 'https://uncch.instructure.com'
COURSE_ID = '97934'
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

def unpublish_object(url, label='object', payload=None, json_payload=True):
    if payload is None:
        payload = {'published': False}
    try:
        if json_payload:
            response = requests.put(url, headers=HEADERS, json=payload)
        else:
            response = requests.put(url, headers=HEADERS, data=payload)
        if response.status_code == 200:
            log(f"✅ Unpublished {label} → {url}")
        elif response.status_code == 403:
            log(f"⛔ Skipped (forbidden): {label} → {url}")
            log(f"    → API response: {response.text}")
        else:
            log(f"⚠️ Failed to unpublish {label} → {url} (status {response.status_code})")
            log(f"    → API response: {response.text}")
    except Exception as e:
        log(f"❌ Exception for {label}: {str(e)}")

# === Unpublish Files ===
def unpublish_files():
    url = f'{BASE_URL}/api/v1/courses/{COURSE_ID}/files?per_page=100'
    for f in requests.get(url, headers=HEADERS).json():
        if f.get('published'):
            file_url = f'{BASE_URL}/api/v1/files/{f["id"]}'
            unpublish_object(file_url, f'File "{f["display_name"]}"', {'published': False}, json_payload=True)

# === Unpublish Pages ===
def unpublish_pages():
    url = f'{BASE_URL}/api/v1/courses/{COURSE_ID}/pages'
    for p in requests.get(url, headers=HEADERS).json():
        if p.get('published'):
            page_url = f'{url}/{p["url"]}'
            unpublish_object(page_url, f'Page "{p["title"]}"', {'wiki_page[published]': False}, json_payload=False)

# === Unpublish Assignments ===
def unpublish_assignments():
    url = f'{BASE_URL}/api/v1/courses/{COURSE_ID}/assignments'
    for a in requests.get(url, headers=HEADERS).json():
        if a.get('published'):
            assignment_url = f'{url}/{a["id"]}'
            unpublish_object(assignment_url, f'Assignment "{a["name"]}"', {'assignment[published]': False}, json_payload=False)

# === Unpublish Module Items ===
def unpublish_module_items():
    url = f'{BASE_URL}/api/v1/courses/{COURSE_ID}/modules'
    for m in requests.get(url, headers=HEADERS).json():
        item_url = f'{url}/{m["id"]}/items'
        for item in requests.get(item_url, headers=HEADERS).json():
            if item.get('published'):
                unpublish_object(f'{item_url}/{item["id"]}', f'Module Item "{item.get("title")}"', {'module_item[published]': False}, json_payload=False)

# === Unpublish Modules ===
def unpublish_modules():
    url = f'{BASE_URL}/api/v1/courses/{COURSE_ID}/modules'
    for m in requests.get(url, headers=HEADERS).json():
        if m.get('published'):
            module_url = f'{url}/{m["id"]}'
            payload = {'module[published]': False, 'module[name]': m['name']}
            unpublish_object(module_url, f'Module "{m["name"]}"', payload, json_payload=False)

# === Main ===
log(f"📦 Starting unpublish pass for course {COURSE_ID}")
unpublish_files()
unpublish_pages()
unpublish_assignments()
unpublish_module_items()
unpublish_modules()
log("🏁 Finished unpublishing all supported content.\n")
