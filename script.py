import requests
import os
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- Configuration from Environment Variables ---
TOKEN = os.environ.get('KOBO_TOKEN')
if not TOKEN:
    raise ValueError("KOBO_TOKEN is not set in environment variables.")

FILTER_TITLE_SUBSTRING = os.environ.get('KOBO_PROJECT_FILTER_TITLE')

# Email Configuration
EMAIL_SENDER = os.environ.get('EMAIL_SENDER')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD') # App password for Gmail/Outlook, or actual password
EMAIL_RECEIVERS = os.environ.get('EMAIL_RECEIVERS') # Comma-separated list of recipients
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com') # Default for Gmail
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587)) # Default for TLS

# --- KoboToolbox API Settings ---
BASE_URL = 'https://eu.kobotoolbox.org/api/v2/assets/'
HEADERS = {'Authorization': f'Token {TOKEN}',
            'Accept': 'application/json'
          }

# --- Email Sending Function ---
def send_email_notification(subject, body, sender, password, receivers, smtp_server, smtp_port):
    if not all([sender, password, receivers, smtp_server, smtp_port]):
        print("Email credentials or receivers not fully set. Skipping email notification.")
        return

    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = receivers # This can be a comma-separated string for multiple recipients
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls() # Enable TLS encryption
        server.login(sender, password)
        server.send_message(msg)
        server.quit()
        print(f"Email notification sent successfully to {receivers}.")
    except Exception as e:
        print(f"Failed to send email notification: {e}")

# --- Main Script Logic ---
print("Fetching all projects from KoboToolbox API...")
try:
    response = requests.get(BASE_URL, headers=HEADERS)
    response.raise_for_status()
    projects = response.json()['results']
    print(f"Total projects retrieved: {len(projects)}")
except requests.exceptions.RequestException as e:
    print(f"ERROR: Failed to fetch projects from KoboToolbox API: {e}")
    # If initial fetch fails, we can't proceed, but we might still want to email about it
    send_email_notification(
        subject="KoboToolbox Project Update Failed: Initial Fetch",
        body=f"The script failed to fetch projects from KoboToolbox API. Error: {e}",
        sender=EMAIL_SENDER,
        password=EMAIL_PASSWORD,
        receivers=EMAIL_RECEIVERS,
        smtp_server=SMTP_SERVER,
        smtp_port=SMTP_PORT
    )
    exit(1) # Exit if we can't get projects

# Time window
now = datetime.utcnow()
yesterday = now - timedelta(days=1)

# Tracking
recent_projects = []
updated_projects = []
skipped_projects = []
filtered_out_projects = []

# Process projects
for project in projects:
    current_name = project['name']
    project_uid = project['uid']

    if FILTER_TITLE_SUBSTRING:
        if FILTER_TITLE_SUBSTRING.lower() not in current_name.lower():
            filtered_out_projects.append(current_name)
            continue

    date_created = datetime.strptime(project['date_created'], '%Y-%m-%dT%H:%M:%S.%fZ')
    if date_created > yesterday:
        recent_projects.append(project)
        
        SUFFIX = " - To Be Verified"
        
        if not current_name.endswith(SUFFIX):
            new_name = current_name + SUFFIX
            print(f"→ Updating project: '{current_name}' (UID: {project_uid}) → '{new_name}'")
            update_data = {'name': new_name}
            update_url = BASE_URL + f"{project_uid}/"
            
            try:
                update_response = requests.patch(update_url, headers=HEADERS, json=update_data)
                update_response.raise_for_status()
                updated_projects.append(new_name)
            except requests.exceptions.RequestException as e:
                print(f"ERROR: Failed to update project '{current_name}' (UID: {project_uid}): {e}")
                # Log individual failures but continue processing
        else:
            print(f"→ Skipped (already named): '{current_name}'")
            skipped_projects.append(current_name)

# --- Summary & Logging ---
summary_message = []
summary_message.append("===== Summary =====")
if FILTER_TITLE_SUBSTRING:
    summary_message.append(f"Filter applied: Only processing projects containing '{FILTER_TITLE_SUBSTRING}' in their title (case-insensitive).")
    summary_message.append(f"Projects filtered out by title: {len(filtered_out_projects)}")
summary_message.append(f"Projects created in the last 24h (after title filter): {len(recent_projects)}")
summary_message.append(f"Projects updated: {len(updated_projects)}")
summary_message.append(f"Projects skipped (already named correctly): {len(skipped_projects)}")
summary_message.append("===================")
summary_message.append("Done.")

full_summary = "\n".join(summary_message)
print(full_summary)


# Ensure the 'logs' directory exists
os.makedirs("logs", exist_ok=True)

# Then write to the log file
with open("logs/project_update_log.txt", "a") as log_file:
    log_file.write(f"\n=== {datetime.utcnow()} ===\n")
    log_file.write(full_summary)
    log_file.write("\n") # Ensure a newline after summary for proper formatting

# --- Send Email Notification ---
email_subject = "KoboToolbox Project Update Summary"
email_body = f"KoboToolbox Project Update script has finished running.\n\n{full_summary}"

# Add detailed project names to the email body
if updated_projects:
    email_body += "\n\nUpdated Projects:\n" + "\n".join(updated_projects)
if skipped_projects:
    email_body += "\n\nSkipped Projects (already correctly named):\n" + "\n".join(skipped_projects)
if filtered_out_projects and FILTER_TITLE_SUBSTRING:
    email_body += f"\n\nProjects Filtered Out by Title ('{FILTER_TITLE_SUBSTRING}'):\n" + "\n".join(filtered_out_projects[:20]) # Limit for email
    if len(filtered_out_projects) > 20:
        email_body += "\n... (and more)"


send_email_notification(
    subject=email_subject,
    body=email_body,
    sender=EMAIL_SENDER,
    password=EMAIL_PASSWORD,
    receivers=EMAIL_RECEIVERS,
    smtp_server=SMTP_SERVER,
    smtp_port=SMTP_PORT
)
