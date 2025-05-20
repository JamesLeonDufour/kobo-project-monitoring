import requests
from datetime import datetime, timedelta

# Configuration
TOKEN = 'YOUR_KOBO_TOKEN'
BASE_URL = 'https://eu.kobotoolbox.org/api/v2/assets/'
HEADERS = {'Authorization': f'Token {TOKEN}'}

# Récupérer les projets
response = requests.get(BASE_URL, headers=HEADERS)
response.raise_for_status()
projects = response.json()['results']

# Filtrer les projets créés dans les dernières 24h
now = datetime.utcnow()
yesterday = now - timedelta(days=1)

for project in projects:
    date_created = datetime.strptime(project['date_created'], '%Y-%m-%dT%H:%M:%S.%fZ')
    if date_created > yesterday:
        current_name = project['name']
        if not current_name.endswith(" - To Be Verified"):
            new_name = current_name + " - To Be Verified"
            print(f"Updating project: {current_name} -> {new_name}")
            update_data = {'name': new_name}
            update_url = BASE_URL + f"{project['uid']}/"
            update_response = requests.patch(update_url, headers=HEADERS, json=update_data)
            update_response.raise_for_status()

print("Done.")
