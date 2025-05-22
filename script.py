import requests
import os
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import csv

# ==============================================================================
# SCRIPT CONFIGURATION (Read from GitHub Actions Environment Variables/Secrets)
# ==============================================================================

# KoboToolbox API Token:
# This token is essential for authenticating with the KoboToolbox API.
# It should be set as a GitHub Secret named 'KOBO_TOKEN'.
TOKEN = os.environ.get('KOBO_TOKEN')
if not TOKEN:
    raise ValueError("KOBO_TOKEN is not set in environment variables. Please configure this GitHub Secret.")

# Optional Project Title Filter:
# If set, the script will ONLY process projects whose names contain this specified
# substring. The comparison is case-insensitive.
# This should be set as a GitHub Secret or environment variable named 'KOBO_PROJECT_FILTER_TITLE'.
# Example: If set to "Survey 2024", only projects like "My Survey 2024 Data"
# or "Results for Survey 2024" will be considered.
FILTER_TITLE_SUBSTRING = os.environ.get('KOBO_PROJECT_FILTER_TITLE')

# Email Configuration:
# These variables are used to send email notifications.
# They MUST be set as GitHub Secrets: EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECEIVERS, SMTP_SERVER.
# SMTP_PORT can be a secret or defaults to 587 (TLS).
EMAIL_SENDER = os.environ.get('EMAIL_SENDER')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD') # Use an App Password for Gmail/Outlook
EMAIL_RECEIVERS = os.environ.get('EMAIL_RECEIVERS') # Comma-separated list (e.g., "email1@example.com,email2@example.com")
SMTP_SERVER = os.environ.get('SMTP_SERVER') # E.g., 'smtp.gmail.com' for Gmail, 'smtp.office365.com' for Outlook
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587)) # Default to 587 if not explicitly set

# KoboToolbox API Base URL:
# This is the base endpoint for KoboToolbox assets (projects).
BASE_URL = 'https://eu.kobotoolbox.org/api/v2/assets/'

# API Request Headers:
# Defines the authorization token and expected response format.
HEADERS = {'Authorization': f'Token {TOKEN}',
            'Accept': 'application/json'
          }

# Define the suffix to be added to project names.
PROJECT_NAME_SUFFIX = " - To Be Verified"

# ==============================================================================
# HELPER FUNCTION: EMAIL NOTIFICATION
# ==============================================================================
def send_email_notification(subject, body, sender, password, receivers, smtp_server, smtp_port):
    """
    Sends an email notification with the given subject and body.
    Requires all email configuration parameters to be set.
    If any email credentials are missing, it will print a warning and skip sending.
    """
    if not all([sender, password, receivers, smtp_server, smtp_port]):
        print(f"[{datetime.utcnow()}] Email credentials (sender, password, receivers, SMTP server, port) not fully set. Skipping email notification.")
        return

    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = receivers # Can handle comma-separated string for multiple recipients
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls() # Enable TLS encryption (recommended)
        server.login(sender, password)
        server.send_message(msg)
        server.quit()
        print(f"[{datetime.utcnow()}] Email notification sent successfully to {receivers}.")
    except Exception as e:
        print(f"[{datetime.utcnow()}] ERROR: Failed to send email notification: {e}")

# ==============================================================================
# MAIN SCRIPT EXECUTION LOGIC
# ==============================================================================
critical_error_occurred = False
error_details = ""

print(f"[{datetime.utcnow()}] KoboToolbox Project Auto-Updater Script Started.")
print(f"[{datetime.utcnow()}] Current working directory: {os.getcwd()}")
# Print length of token (not actual token) to confirm it's loaded
print(f"[{datetime.utcnow()}] KOBO_TOKEN loaded (length: {len(TOKEN) if TOKEN else 0}).")
print(f"[{datetime.utcnow()}] Project Title Filter set to: '{FILTER_TITLE_SUBSTRING}'" if FILTER_TITLE_SUBSTRING else f"[{datetime.utcnow()}] No Project Title Filter applied (all projects considered).")

# --- Step 1: Fetch all projects from KoboToolbox API ---
print(f"[{datetime.utcnow()}] Fetching all projects from KoboToolbox API...")
try:
    response = requests.get(BASE_URL, headers=HEADERS)
    response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
    projects = response.json()['results']
    print(f"[{datetime.utcnow()}] Successfully retrieved {len(projects)} projects.")
except requests.exceptions.RequestException as e:
    critical_error_occurred = True
    error_details = f"Failed to fetch projects from KoboToolbox API. Error: {e}"
    print(f"[{datetime.utcnow()}] ERROR: {error_details}")
    # Send immediate email notification for critical API fetch failure
    send_email_notification(
        subject="KoboToolbox Project Update Failed: Critical API Fetch Error",
        body=f"The script encountered a critical error and failed to fetch projects from KoboToolbox API.\nError: {error_details}",
        sender=EMAIL_SENDER,
        password=EMAIL_PASSWORD,
        receivers=EMAIL_RECEIVERS,
        smtp_server=SMTP_SERVER,
        smtp_port=SMTP_PORT
    )
    exit(1) # Exit the script as we cannot proceed without project data.

# Initialize tracking lists for reporting
recent_projects_found = [] # To store actual project objects if needed, or just names
updated_projects_names = []
skipped_projects_names = []
filtered_out_projects_names = []

# Define the time window for "recent" projects (last 24 hours)
now_utc = datetime.utcnow()
twenty_four_hours_ago = now_utc - timedelta(days=1)
print(f"[{datetime.utcnow()}] Checking for projects created after: {twenty_four_hours_ago.strftime('%Y-%m-%d %H:%M:%S UTC')}")

# --- Step 2: Process each project (only if initial fetch was successful) ---
if not critical_error_occurred:
    print(f"[{datetime.utcnow()}] Starting individual project processing loop...")
    for project in projects:
        current_name = project.get('name', 'N/A') # Safely get project name
        project_uid = project.get('uid', 'N/A')   # Safely get project UID

        # Apply optional title filter
        if FILTER_TITLE_SUBSTRING:
            if FILTER_TITLE_SUBSTRING.lower() not in current_name.lower():
                # print(f"[{datetime.utcnow()}] → Filtered out: '{current_name}' (does not contain '{FILTER_TITLE_SUBSTRING}')")
                filtered_out_projects_names.append(current_name)
                continue # Skip to the next project if it doesn't match the filter

        # Check project creation date
        date_created_str = project.get('date_created')
        if not date_created_str:
            print(f"[{datetime.utcnow()}] WARNING: 'date_created' field missing for project '{current_name}' (UID: {project_uid}). Skipping date check.")
            continue

        try:
            date_created = datetime.strptime(date_created_str, '%Y-%m-%dT%H:%M:%S.%fZ')
        except ValueError:
            print(f"[{datetime.utcnow()}] WARNING: Could not parse date_created '{date_created_str}' for project '{current_name}' (UID: {project_uid}). Skipping date check.")
            continue # Skip this project if date parsing fails

        # Check if the project is recent (created within the last 24 hours)
        if date_created > twenty_four_hours_ago:
            recent_projects_found.append(project) # Add the full project object
            
            # Check if project name already has the suffix
            if not current_name.endswith(PROJECT_NAME_SUFFIX):
                new_name = current_name + PROJECT_NAME_SUFFIX
                print(f"[{datetime.utcnow()}] → Updating project: '{current_name}' (UID: {project_uid}) → '{new_name}'")
                update_data = {'name': new_name}
                update_url = BASE_URL + f"{project_uid}/"
                
                # Attempt to patch the project name via API
                try:
                    update_response = requests.patch(update_url, headers=HEADERS, json=update_data)
                    update_response.raise_for_status() # Raise error for bad responses
                    updated_projects_names.append(new_name)
                except requests.exceptions.RequestException as e:
                    print(f"[{datetime.utcnow()}] ERROR: Failed to update project '{current_name}' (UID: {project_uid}): {e}")
                    # Log individual update failures, but continue processing other projects.
            else:
                print(f"[{datetime.utcnow()}] → Skipped (already named correctly): '{current_name}'")
                skipped_projects_names.append(current_name)
        # else:
        #     print(f"[{datetime.utcnow()}] → Skipped (old): '{current_name}' created on {date_created.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"[{datetime.utcnow()}] Finished individual project processing loop.")

# ==============================================================================
# SUMMARY GENERATION & CONSOLE OUTPUT
# ==============================================================================
summary_message_lines = []
summary_message_lines.append("===== KoboToolbox Project Update Summary =====")
summary_message_lines.append(f"Run Timestamp (UTC): {now_utc.isoformat()}")
summary_message_lines.append(f"Status: {'Success' if not critical_error_occurred else 'Failed Initial Fetch'}")

if FILTER_TITLE_SUBSTRING:
    summary_message_lines.append(f"Project Title Filter Applied: '{FILTER_TITLE_SUBSTRING}' (case-insensitive)")
    summary_message_lines.append(f"Projects Filtered Out by Title: {len(filtered_out_projects_names)}")
else:
    summary_message_lines.append("Project Title Filter: None (all projects considered)")

summary_message_lines.append(f"Projects created in the last 24h (after title filter): {len(recent_projects_found)}")
summary_message_lines.append(f"Projects Successfully Updated: {len(updated_projects_names)}")
summary_message_lines.append(f"Projects Skipped (already named correctly): {len(skipped_projects_names)}")
summary_message_lines.append("==============================================")
summary_message_lines.append("Script Execution Completed.")

full_console_summary = "\n".join(summary_message_lines)
print(full_console_summary)

# ==============================================================================
# CSV LOGGING
# ==============================================================================
print(f"[{datetime.utcnow()}] Attempting to write CSV log...")
log_dir = "logs"
log_file_path = os.path.join(log_dir, "project_update_log.csv")

# Ensure the 'logs' directory exists
try:
    os.makedirs(log_dir, exist_ok=True)
    print(f"[{datetime.utcnow()}] Directory '{log_dir}' ensured.")
except OSError as e:
    print(f"[{datetime.utcnow()}] ERROR: Failed to create directory '{log_dir}': {e}")
    # Continue script; if directory creation fails, CSV write will also fail, but print more context.

# Define CSV headers for the tabular log
csv_headers = [
    "Timestamp (UTC)",
    "Status",
    "Filter Applied",
    "Projects Filtered Out by Title",
    "Projects Created Last 24h",
    "Projects Updated",
    "Projects Skipped"
]

# Prepare data for the CSV row
csv_row_data = {
    "Timestamp (UTC)": now_utc.isoformat(),
    "Status": "Success" if not critical_error_occurred else "Failed Initial Fetch",
    "Filter Applied": FILTER_TITLE_SUBSTRING if FILTER_TITLE_SUBSTRING else "None",
    "Projects Filtered Out by Title": len(filtered_out_projects_names),
    "Projects Created Last 24h": len(recent_projects_found),
    "Projects Updated": len(updated_projects_names),
    "Projects Skipped": len(skipped_projects_names)
}

# Write to CSV log file
file_exists = os.path.exists(log_file_path)
print(f"[{datetime.utcnow()}] Log file '{log_file_path}' exists: {file_exists}")

try:
    with open(log_file_path, "a", newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=csv_headers)
        
        if not file_exists:
            writer.writeheader() # Write header only if file is new
            print(f"[{datetime.utcnow()}] CSV header written to new file.")
        
        writer.writerow(csv_row_data)
        print(f"[{datetime.utcnow()}] CSV row data written successfully.")
    print(f"[{datetime.utcnow()}] CSV log updated at {log_file_path}")
except IOError as e:
    print(f"[{datetime.utcnow()}] ERROR: Failed to write to CSV file '{log_file_path}': {e}")
    # This might indicate permissions issue with the file itself or parent directory.

# ==============================================================================
# EMAIL NOTIFICATION
# ==============================================================================
email_subject = "KoboToolbox Project Update Summary"
email_body = f"KoboToolbox Project Update script has finished running.\n\n{full_console_summary}"

# Add detailed project names to the email body for better context
if updated_projects_names:
    email_body += "\n\nUpdated Projects:\n" + "\n".join([f"- {name}" for name in updated_projects_names])
if skipped_projects_names:
    email_body += "\n\nSkipped Projects (already correctly named):\n" + "\n".join([f"- {name}" for name in skipped_projects_names])
if filtered_out_projects_names and FILTER_TITLE_SUBSTRING:
    email_body += f"\n\nProjects Filtered Out by Title ('{FILTER_TITLE_SUBSTRING}'):\n" + "\n".join([f"- {name}" for name in filtered_out_projects_names[:20]]) # Limit for email to avoid too long emails
    if len(filtered_out_projects_names) > 20:
        email_body += "\n- ... (and more)" # Indicate if list is truncated

print(f"[{datetime.utcnow()}] Sending email notification...")
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
