import requests
import keyring
import json

# === CONFIGURATION ===
BASE_URL = 'https://uncch.instructure.com'
COURSE_ID = '97934'
SERVICE_NAME = 'canvas'
USERNAME = 'access-token'

API_TOKEN = keyring.get_password(SERVICE_NAME, USERNAME)
HEADERS = {'Authorization': f'Bearer {API_TOKEN}'}

# === Fetch and print first file ===
def fetch_first_file():
    url = f'{BASE_URL}/api/v1/courses/{COURSE_ID}/files?per_page=1'
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    files = response.json()
    if files:
        print(json.dumps(files[0], indent=2))
    else:
        print("No files found.")

fetch_first_file()