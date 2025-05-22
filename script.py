import requests
import os
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- Configuration from Environment Variables ---
# KoboToolbox API Token
TOKEN = os.environ.get('KOBO_TOKEN')
if not TOKEN:
    raise ValueError("KOBO_TOKEN is not set in environment variables.")

# Optional: Filter for project titles (substring match, case-insensitive)
FILTER_TITLE_SUBSTRING = os.environ.get('KOBO_PROJECT_FILTER_TITLE')

# Email Configuration (read from GitHub Secrets)
EMAIL_SENDER = os.environ.get('EMAIL_SENDER')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD') # App password for Gmail/Outlook, or actual password
EMAIL_RECEIVERS = os.environ.get('EMAIL_RECEIVERS') # Comma-separated list of recipients
SMTP_SERVER = os.environ.get('SMTP_SERVER') # Read from secret (e.g., smtp.gmail.com)
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587)) # Read from secret, default to 587 if not set or invalid

# --- KoboToolbox API Settings ---
BASE_URL = 'https://eu.kobotoolbox.org/api/v2/assets/'
HEADERS = {'Authorization': f'Token {TOKEN}',
            'Accept': 'application/json'
          }

# --- Email Sending Function ---
def send_email_notification(subject, body, sender, password, receivers, smtp_server, smtp_port):
    """
    Sends an email notification with the given subject and body.
    Requires all email configuration parameters to be set.
    """
    if not all([sender, password, receivers, smtp_server, smtp_port]):
        print("Email credentials (sender, password, receivers, SMTP server, port) not fully set. Skipping email notification.")
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
# Track if the script encountered a critical error (e.g., initial API fetch failure)
critical_error_occurred = False
error_details = ""

print("Fetching all projects from KoboToolbox API...")
try:
    response = requests.get(BASE_URL, headers=HEADERS)
    response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
    projects = response.json()['results']
    print(f"Total projects retrieved: {len(projects)}")
except requests.exceptions.RequestException as e:
    critical_error_occurred = True
    error_details = f"Failed to fetch projects from KoboToolbox API: {e}"
    print(f"ERROR: {error_details}")
    # Even if critical, try to send an email about the failure
    send_email_notification(
        subject="KoboToolbox Project Update Failed: Initial Fetch Error",
        body=f"The script encountered a critical error and failed to fetch projects from KoboToolbox API.\nError: {error_details}",
        sender=EMAIL_SENDER,
        password=EMAIL_PASSWORD,
        receivers=EMAIL_RECEIVERS,
        smtp_server=SMTP_SERVER,
        smtp_port=SMTP_PORT
    )
    exit(1) # Exit the script if initial project fetch fails

# Initialize tracking lists only if initial fetch was successful
recent_projects = []
updated_projects = []
skipped_projects = []
filtered_out_projects = []

# Time window for "recent" projects (last 24 hours)
now = datetime.utcnow()
yesterday = now - timedelta(days=1)

# Process projects (only if no critical error occurred)
if not critical_error_occurred:
    for project in projects:
        current_name = project['name']
        project_uid = project['uid']

        # Apply title filter if specified
        if FILTER_TITLE_SUBSTRING:
            if FILTER_TITLE_SUBSTRING.lower() not in current_name.lower():
                filtered_out_projects.append(current_name)
                continue # Skip to the next project if it doesn't match the filter

        # Check if project was created in the last 24 hours
        try:
            date_created = datetime.strptime(project['date_created'], '%Y-%m-%dT%H:%M:%S.%fZ')
        except ValueError:
            print(f"WARNING: Could not parse date_created for project '{current_name}' (UID: {project_uid}). Skipping date check.")
            continue # Skip this project if date parsing fails

        if date_created > yesterday:
            recent_projects.append(project)
            
            # Define the suffix once
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
                    # Log individual failures but continue processing other projects
            else:
                print(f"→ Skipped (already named): '{current_name}'")
                skipped_projects.append(current_name)
        # else:
        #     print(f"→ Skipped (old): '{current_name}' created on {date_created.strftime('%Y-%m-%d %H:%M:%S')}")


# --- Summary & Logging ---
summary_message_lines = []
summary_message_lines.append("===== Summary =====")
if FILTER_TITLE_SUBSTRING:
    summary_message_lines.append(f"Filter applied: Only processing projects containing '{FILTER_TITLE_SUBSTRING}' in their title (case-insensitive).")
    summary_message_lines.append(f"Projects filtered out by title: {len(filtered_out_projects)}")
summary_message_lines.append(f"Projects created in the last 24h (after title filter): {len(recent_projects)}")
summary_message_lines.append(f"Projects updated: {len(updated_projects)}")
summary_message_lines.append(f"Projects skipped (already named correctly): {len(skipped_projects)}")
summary_message_lines.append("===================")
summary_message_lines.append("Done.")

full_summary_text = "\n".join(summary_message_lines)
print(full_summary_text)

# Ensure the 'logs' directory exists
os.makedirs("logs", exist_ok=True)

# Write to the log file
with open("logs/project_update_log.txt", "a") as log_file:
    log_file.write(f"\n=== {datetime.utcnow()} ===\n")
    log_file.write(full_summary_text)
    log_file.write("\n") # Ensure a newline after summary for proper formatting

# --- Send Email Notification ---
email_subject = "KoboToolbox Project Update Summary"
email_body = f"KoboToolbox Project Update script has finished running.\n\n{full_summary_text}"

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
