import requests
import os
from datetime import datetime, timedelta

# Lire le token d'environnement (fourni par GitHub Actions)
TOKEN = os.environ.get('KOBO_TOKEN')
if not TOKEN:
    raise ValueError("KOBO_TOKEN is not set in environment variables.")

BASE_URL = 'https://eu.kobotoolbox.org/api/v2/assets/'
HEADERS = {'Authorization': f'Token {TOKEN}',
            'Accept': 'application/json'
          }
# Fetch all projects
response = requests.get(BASE_URL, headers=HEADERS)
response.raise_for_status()
projects = response.json()['results']

print(f"Total projects retrieved: {len(projects)}")

# Time window
now = datetime.utcnow()
yesterday = now - timedelta(days=1)

# Tracking
recent_projects = []
updated_projects = []
skipped_projects = []

# Process projects
for project in projects:
    date_created = datetime.strptime(project['date_created'], '%Y-%m-%dT%H:%M:%S.%fZ')
    if date_created > yesterday:
        recent_projects.append(project)
        current_name = project['name']
        if not current_name.endswith(" - To Be Verified"):
            new_name = current_name + " - To Be Verified"
            print(f"→ Updating project: '{current_name}' → '{new_name}'")
            update_data = {'name': new_name}
            update_url = BASE_URL + f"{project['uid']}/"
            update_response = requests.patch(update_url, headers=HEADERS, json=update_data)
            update_response.raise_for_status()
            updated_projects.append(new_name)
        else:
            print(f"→ Skipped (already named): '{current_name}'")
            skipped_projects.append(current_name)

# Summary
print("\n===== Summary =====")
print(f"Projects created in the last 24h: {len(recent_projects)}")
print(f"Projects updated: {len(updated_projects)}")
print(f"Projects skipped (already named correctly): {len(skipped_projects)}")
print("===================")
print("Done.")
