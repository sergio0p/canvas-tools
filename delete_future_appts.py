#!/usr/bin/env python3
"""
delete_future_appts.py

Deletes all future "Office Hours" appointment groups in Canvas by
hitting the generic appointment_groups endpoint, filtering to only those
groups whose title begins with "Office Hours" and whose start date is
after today.
"""

import requests
import keyring
from datetime import datetime, date

# === CONFIGURATION ===
BASE_URL     = 'https://uncch.instructure.com'
SERVICE_NAME = 'canvas'
USERNAME     = 'access-token'
API_TOKEN    = keyring.get_password(SERVICE_NAME, USERNAME)
HEADERS      = {
    'Authorization': f'Bearer {API_TOKEN}',
}


def fetch_all_groups():
    """
    Retrieves all appointment groups (past and future) from Canvas.
    Handles pagination automatically.
    """
    url = f"{BASE_URL}/api/v1/appointment_groups"
    params = {'scope': 'manageable'}
    groups = []

    while url:
        resp = requests.get(url, headers=HEADERS, params=params)
        resp.raise_for_status()
        page = resp.json()
        print(f"DEBUG: Fetched {len(page)} groups from {resp.url}")
        groups.extend(page)

        # follow pagination link if present
        url = resp.links.get('next', {}).get('url')
        params = None  # params only needed for first request

    return groups


def delete_group(group_id, start_ts, title):
    """
    Deletes the appointment group by ID.

    Args:
        group_id: The Canvas appointment_group ID.
        start_ts: The ISO timestamp of the group's start time (for logging).
        title:    The title of the group (for logging).
    """
    del_url = f"{BASE_URL}/api/v1/appointment_groups/{group_id}"
    resp = requests.delete(del_url, headers=HEADERS)
    if 200 <= resp.status_code < 300:
        print(f"✅ Deleted {group_id} — '{title}' (start: {start_ts})")
    else:
        print(f"❌ Failed to delete {group_id}: {resp.status_code} - {resp.text}")


def main():
    today = date.today()
    resp = requests.get(f"{BASE_URL}/api/v1/appointment_groups?per_page=1", headers=HEADERS); print("✅ Token works" if resp.status_code == 200 else f"❌ Token failed: {resp.status_code}")
    groups = fetch_all_groups()

    if not groups:
        print("No appointment groups found.")
        return

    for grp in groups:
        title = grp.get('title', '')
        # Filter to only "Office Hours" groups
        if not title.startswith('Office Hours'):
            continue

        start_ts = grp.get('start_at')
        if not start_ts:
            continue

        # Parse ISO timestamp and compare date
        dt = datetime.fromisoformat(start_ts.replace('Z', '+00:00'))
        if dt.date() > today:
            delete_group(grp['id'], start_ts, title)


if __name__ == '__main__':
    main()
