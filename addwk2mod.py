import requests
import keyring

# ==== CONFIGURATION ====
SERVICE_NAME = "canvas"     # Keychain service name
USERNAME = "access-token"        # Keychain account name
BASE_URL = 'https://uncch.instructure.com'  # Use your actual Canvas instance URL
#COURSE_ID = '96082' # ECON 416 Id
COURSE_ID = '97934'  # ECON 510 Id
API_TOKEN = keyring.get_password(SERVICE_NAME, USERNAME)
HEADERS = {'Authorization': f'Bearer {API_TOKEN}'}
# === Range of new modules to insert ===
k = 15   # First week to add
l = 16  # Last week to add

def get_modules():
    url = f'{BASE_URL}/api/v1/courses/{COURSE_ID}/modules'
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()

def create_module(name, position):
    url = f'{BASE_URL}/api/v1/courses/{COURSE_ID}/modules'
    payload = {
        'module[name]': name,
        'module[position]': position
    }
    response = requests.post(url, headers=HEADERS, data=payload)
    response.raise_for_status()
    return response.json()

modules = get_modules()


# === Get current modules ===
modules = get_modules()

# Determine the position after the last existing module
last_position = max(m['position'] for m in modules) + 1

# Insert Week k to Week l modules
for week_num in range(k, l + 1):
    module_name = f'Week {week_num}'
    print(f'Creating {module_name} at position {last_position}')
    create_module(module_name, last_position)
    last_position += 1

print("✅ All modules Week {k} through Week {l} were created.")