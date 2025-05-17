import requests
import keyring
import json

# === CONFIGURATION ===
BASE_URL = 'https://uncch.instructure.com'
COURSE_ID = '97934'
MODULE_NAME = 'Week 16'
SERVICE_NAME = 'canvas'
USERNAME = 'access-token'

API_TOKEN = keyring.get_password(SERVICE_NAME, USERNAME)
HEADERS = {
    'Authorization': f'Bearer {API_TOKEN}'
}

# === Get Module ID by Name ===
def get_module_id_by_name(name):
    url = f'{BASE_URL}/api/v1/courses/{COURSE_ID}/modules?per_page=100'
    modules = requests.get(url, headers=HEADERS).json()
    for m in modules:
        if m['name'] == name:
            return m['id']
    return None

# === Get Module Items ===
def get_module_items(module_id):
    url = f'{BASE_URL}/api/v1/courses/{COURSE_ID}/modules/{module_id}/items'
    items = requests.get(url, headers=HEADERS).json()
    return items

# === Main ===
module_id = get_module_id_by_name(MODULE_NAME)
if module_id:
    print(f"✅ Found module '{MODULE_NAME}' with ID {module_id}\n")
    module_items = get_module_items(module_id)
    print(f"📦 Module contains {len(module_items)} items:\n")
    print(json.dumps(module_items, indent=2))
else:
    print(f"❌ Module named '{MODULE_NAME}' not found.")
