import requests
import keyring
from datetime import datetime, timedelta

# === CONFIGURATION ===
BASE_URL = 'https://uncch.instructure.com'
COURSE_IDS = ['96082', '97934']
SERVICE_NAME = 'canvas'
USERNAME = 'access-token'
API_TOKEN = keyring.get_password(SERVICE_NAME, USERNAME)
HEADERS = {
    'Authorization': f'Bearer ' + API_TOKEN,
    'Content-Type': 'application/json'
}

# === FALL 2025 M-W-F CLASS DAYS (EXCLUDING HOLIDAYS AND BREAKS) ===
MWF_DATES = [
    '2025-08-18', '2025-08-20', '2025-08-22', '2025-08-25', '2025-08-27', '2025-08-29',
    '2025-09-03', '2025-09-05', '2025-09-08', '2025-09-10', '2025-09-12', '2025-09-17',
    '2025-09-19', '2025-09-22', '2025-09-24', '2025-09-26', '2025-09-29',
    '2025-10-01', '2025-10-03', '2025-10-06', '2025-10-08', '2025-10-10', '2025-10-13',
    '2025-10-15', '2025-10-20', '2025-10-22', '2025-10-24', '2025-10-27', '2025-10-29',
    '2025-10-31', '2025-11-03', '2025-11-05', '2025-11-07', '2025-11-10', '2025-11-12',
    '2025-11-14', '2025-11-17', '2025-11-19', '2025-11-21', '2025-11-24', '2025-12-03'
]

# === CREATE APPOINTMENT GROUP WITH SLOTS USING new_appointments ===
def create_group_with_slots(date_str):
    day = datetime.strptime(date_str, "%Y-%m-%d")
    release_day = day - timedelta(days=7)

    context_codes = [f"course_{cid}" for cid in COURSE_IDS]

    # Build new_appointments array
    new_appointments = []
    for i in range(4):  # 4 slots: 9:00, 9:15, 9:30, 9:45
        start = (day + timedelta(minutes=9*60 + i*15)).isoformat()
        end = (day + timedelta(minutes=9*60 + (i+1)*15)).isoformat()
        new_appointments.append([start, end])

    payload = {
        "appointment_group": {
            "title": f"Office Hours {date_str}",
            "context_codes": context_codes,
            "sub_context_codes": context_codes,
            "description": "15-minute individual office hour slots from 9–10AM",
            "location_name": "https://unc.zoom.us/j/9733572701",
            "max_appointments_per_participant": 1,
            "min_appointments_per_participant": 1,
            "participants_per_appointment": 1,
            "participant_visibility": "private",
            "start_at": release_day.isoformat(),
            "end_at": (day + timedelta(hours=1)).isoformat(),
            "new_appointments": new_appointments,
            "publish": True
        }
    }

    url = f"{BASE_URL}/api/v1/appointment_groups"
    response = requests.post(url, headers=HEADERS, json=payload)
    response.raise_for_status()
    print(f"✅ Created appointment group for {date_str} with 4 slots.")

# === MAIN LOOP ===
print("📅 Creating daily Office Hours appointment groups with slots...")
for date in MWF_DATES:
    print(f"⏳ Processing {date}...")
    create_group_with_slots(date)
print("🏁 All appointment groups and time slots created.")
