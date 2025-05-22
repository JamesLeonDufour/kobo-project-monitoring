import requests
import os
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import csv

# --- Configuration from Environment Variables ---
TOKEN = os.environ.get('KOBO_TOKEN')
if not TOKEN:
    raise ValueError("KOBO_TOKEN is not set in environment variables.")

FILTER_TITLE_SUBSTRING = os.environ.get('KOBO_PROJECT_FILTER_SUBSTRING') # Corrected variable name as per auto_update.yml
# If you are still using KOBO_PROJECT_FILTER_TITLE, please change it back.
# The updated auto_update.yml uses KOBO_PROJECT_FILTER_TITLE. I'll revert it to match the README.
# Reverting to KOBO_PROJECT_FILTER_TITLE to match previous README.md and auto_update.yml
FILTER_TITLE_SUBSTRING = os.environ.get('KOBO_PROJECT_FILTER_TITLE')


EMAIL_SENDER = os.environ.get('EMAIL_SENDER')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
EMAIL_RECEIVERS = os.environ.get('EMAIL_RECEIVERS')
SMTP_SERVER = os.environ.get('SMTP_SERVER')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))

# --- KoboToolbox API Settings ---
BASE_URL = 'https://eu.kobotoolbox.org/api/v2/assets/'
HEADERS = {'Authorization': f'Token {TOKEN}',
            'Accept': 'application/json'
          }

# --- Email Sending Function ---
def send_email_notification(subject, body, sender, password, receivers, smtp_server, smtp_port):
    if not all([sender, password, receivers, smtp_server, smtp_port]):
        print("Email credentials (sender, password, receivers, SMTP server, port) not fully set. Skipping email notification.")
        return

    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = receivers
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)
        server.quit()
        print(f"Email notification sent successfully to {receivers}.")
    except Exception as e:
        print(f"Failed to send email notification: {e}")

# --- Main Script Logic ---
critical_error_occurred = False
error_details = ""

print(f"[{datetime.utcnow()}] Script started.")
print(f"[{datetime.utcnow()}] Current working directory: {os.getcwd()}")
print(f"[{datetime.utcnow()}] Checking KOBO_TOKEN length: {len(TOKEN) if TOKEN else 0}")
print(f"[{datetime.utcnow()}] Filter title: {FILTER_TITLE_SUBSTRING if FILTER_TITLE_SUBSTRING else 'None'}")


print("Fetching all projects from KoboToolbox API...")
try:
    response = requests.get(BASE_URL, headers=HEADERS)
    response.raise_for_status()
    projects = response.json()['results']
    print(f"Total projects retrieved: {len(projects)}")
except requests.exceptions.RequestException as e:
    critical_error_occurred = True
    error_details = f"Failed to fetch projects from KoboToolbox API: {e}"
    print(f"ERROR: {error_details}")
    send_email_notification(
        subject="KoboToolbox Project Update Failed: Initial Fetch Error",
        body=f"The script encountered a critical error and failed to fetch projects from KoboToolbox API.\nError: {error_details}",
        sender=EMAIL_SENDER,
        password=EMAIL_PASSWORD,
        receivers=EMAIL_RECEIVERS,
        smtp_server=SMTP_SERVER,
        smtp_port=SMTP_PORT
    )
    exit(1)

recent_projects = []
updated_projects_names = []
skipped_projects_names = []
filtered_out_projects_names = []

now = datetime.utcnow()
yesterday = now - timedelta(days=1)

if not critical_error_occurred:
    print(f"[{datetime.utcnow()}] Starting project processing loop.")
    for project in projects:
        current_name = project['name']
        project_uid = project['uid']

        if FILTER_TITLE_SUBSTRING:
            if FILTER_TITLE_SUBSTRING.lower() not in current_name.lower():
                filtered_out_projects_names.append(current_name)
                continue

        try:
            date_created = datetime.strptime(project['date_created'], '%Y-%m-%dT%H:%M:%S.%fZ')
        except ValueError:
            print(f"WARNING: Could not parse date_created for project '{current_name}' (UID: {project_uid}). Skipping date check.")
            continue

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
                    updated_projects_names.append(new_name)
                except requests.exceptions.RequestException as e:
                    print(f"ERROR: Failed to update project '{current_name}' (UID: {project_uid}): {e}")
            else:
                print(f"→ Skipped (already named): '{current_name}'")
                skipped_projects_names.append(current_name)
    print(f"[{datetime.utcnow()}] Finished project processing loop.")

# --- Summary & Console Output ---
summary_message_lines = []
summary_message_lines.append("===== Summary =====")
if FILTER_TITLE_SUBSTRING:
    summary_message_lines.append(f"Filter applied: Only processing projects containing '{FILTER_TITLE_SUBSTRING}' in their title (case-insensitive).")
    summary_message_lines.append(f"Projects filtered out by title: {len(filtered_out_projects_names)}")
summary_message_lines.append(f"Projects created in the last 24h (after title filter): {len(recent_projects)}")
summary_message_lines.append(f"Projects updated: {len(updated_projects_names)}")
summary_message_lines.append(f"Projects skipped (already named correctly): {len(skipped_projects_names)}")
summary_message_lines.append("===================")
summary_message_lines.append("Done.")

full_console_summary = "\n".join(summary_message_lines)
print(full_console_summary)

# --- CSV Logging ---
print(f"[{datetime.utcnow()}] Attempting to write CSV log.")
log_dir = "logs"
log_file_path = os.path.join(log_dir, "project_update_log.csv")

# Ensure the 'logs' directory exists
try:
    os.makedirs(log_dir, exist_ok=True)
    print(f"[{datetime.utcnow()}] Directory '{log_dir}' ensured.")
except OSError as e:
    print(f"ERROR: Failed to create directory '{log_dir}': {e}")
    # Still attempt to write CSV if directory creation fails, but it will likely fail again.
    # It might indicate a permissions issue on the runner.

# Define CSV headers
csv_headers = [
    "Timestamp (UTC)",
    "Filter Applied",
    "Projects Filtered Out by Title",
    "Projects Created Last 24h",
    "Projects Updated",
    "Projects Skipped",
    "Status"
]

# Prepare CSV row data
csv_row_data = {
    "Timestamp (UTC)": datetime.utcnow().isoformat(),
    "Filter Applied": FILTER_TITLE_SUBSTRING if FILTER_TITLE_SUBSTRING else "None",
    "Projects Filtered Out by Title": len(filtered_out_projects_names),
    "Projects Created Last 24h": len(recent_projects),
    "Projects Updated": len(updated_projects_names),
    "Projects Skipped": len(skipped_projects_names),
    "Status": "Success" if not critical_error_occurred else "Failed Initial Fetch"
}

# Write to CSV log file
file_exists = os.path.exists(log_file_path)
print(f"[{datetime.utcnow()}] Log file '{log_file_path}' exists: {file_exists}")

try:
    with open(log_file_path, "a", newline='', encoding='utf-8') as csvfile: # Added encoding for robustness
        writer = csv.DictWriter(csvfile, fieldnames=csv_headers)
        
        if not file_exists:
            writer.writeheader()
            print(f"[{datetime.utcnow()}] CSV header written.")
        
        writer.writerow(csv_row_data)
        print(f"[{datetime.utcnow()}] CSV row data written.")
    print(f"[{datetime.utcnow()}] Log written successfully to {log_file_path}")
except IOError as e:
    print(f"ERROR: Failed to write to CSV file '{log_file_path}': {e}")
    # This error might indicate a permissions problem with the file itself

# --- Send Email Notification ---
email_subject = "KoboToolbox Project Update Summary"
# Adjust email body to include the actual list of updated/skipped projects more clearly
email_body = f"KoboToolbox Project Update script has finished running.\n\n{full_console_summary}"

if updated_projects_names:
    email_body += "\n\nUpdated Projects:\n" + "\n".join([f"- {name}" for name in updated_projects_names])
if skipped_projects_names:
    email_body += "\n\nSkipped Projects (already correctly named):\n" + "\n".join([f"- {name}" for name in skipped_projects_names])
if filtered_out_projects_names and FILTER_TITLE_SUBSTRING:
    email_body += f"\n\nProjects Filtered Out by Title ('{FILTER_TITLE_SUBSTRING}'):\n" + "\n".join([f"- {name}" for name in filtered_out_projects_names[:20]])
    if len(filtered_out_projects_names) > 20:
        email_body += "\n- ... (and more)"

print(f"[{datetime.utcnow()}] Sending email notification.")
send_email_notification(
    subject=email_subject,
    body=email_body,
    sender=EMAIL_SENDER,
    password=EMAIL_PASSWORD,
    receivers=EMAIL_RECEIVERS,
    smtp_server=SMTP_SERVER,
    smtp_port=SMTP_PORT
)
print(f"[{datetime.utcnow()}] Script finished.")
