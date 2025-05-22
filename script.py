import requests
import os
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import csv # Import the csv module

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
updated_projects_names = [] # Store names for email and summary
skipped_projects_names = [] # Store names for email and summary
filtered_out_projects_names = [] # Store names for email and summary

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
                filtered_out_projects_names.append(current_name)
                continue # Skip to the next project if it doesn't match the filter

        # Check if project was created in the last 24 hours
        try:
            date_created = datetime.strptime(project['date_created'], '%Y-%m-%dT%H:%M:%S.%fZ')
        except ValueError:
            print(f"WARNING: Could not parse date_created for project '{current_name}' (UID: {project_uid}). Skipping date check.")
            continue # Skip this project if date parsing fails

        if date_created > yesterday:
            recent_projects.append(project) # Keep full project object here if needed elsewhere
            
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
                    updated_projects_names.append(new_name)
                except requests.exceptions.RequestException as e:
                    print(f"ERROR: Failed to update project '{current_name}' (UID: {project_uid}): {e}")
                    # Log individual failures but continue processing other projects
            else:
                print(f"→ Skipped (already named): '{current_name}'")
                skipped_projects_names.append(current_name)
        # else:
        #     print(f"→ Skipped (old): '{current_name}' created on {date_created.strftime('%Y-%m-%d %H:%M:%S')}")


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
# Ensure the 'logs' directory exists
os.makedirs("logs", exist_ok=True)
log_file_path = "logs/project_update_log.csv" # Changed to .csv

# Define CSV headers
csv_headers = [
    "Timestamp (UTC)",
    "Filter Applied",
    "Projects Filtered Out by Title",
    "Projects Created Last 24h",
    "Projects Updated",
    "Projects Skipped",
    "Status" # e.g., Success, Failed Initial Fetch
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
# Check if file exists to determine if headers are needed
file_exists = os.path.exists(log_file_path)

with open(log_file_path, "a", newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=csv_headers)
    
    if not file_exists:
        writer.writeheader() # Write header only if file is new
    
    writer.writerow(csv_row_data)

print(f"Log written to {log_file_path}")

# --- Send Email Notification ---
email_subject = "KoboToolbox Project Update Summary"
email_body = f"KoboToolbox Project Update script has finished running.\n\n{full_console_summary}"

if updated_projects_names:
    email_body += "\n\nUpdated Projects:\n" + "\n".join(updated_projects_names)
if skipped_projects_names:
    email_body += "\n\nSkipped Projects (already correctly named):\n" + "\n".join(skipped_projects_names)
if filtered_out_projects_names and FILTER_TITLE_SUBSTRING:
    email_body += f"\n\nProjects Filtered Out by Title ('{FILTER_TITLE_SUBSTRING}'):\n" + "\n".join(filtered_out_projects_names[:20]) # Limit for email
    if len(filtered_out_projects_names) > 20:
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
