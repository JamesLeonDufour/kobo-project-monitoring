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

# --- Project Title Filter (Directly in Code) ---
# Set this variable to the substring that project titles must contain to be processed.
# The comparison is case-insensitive.
# If you leave it as an empty string (''), no title filtering will be applied.
# Example: FILTER_TITLE_SUBSTRING = "Annual Survey"
# Example: FILTER_TITLE_SUBSTRING = "Round 2 Data"
# Example: FILTER_TITLE_SUBSTRING = "" (No filtering)
FILTER_TITLE_SUBSTRING = "RMNA" # <--- SET YOUR FILTER STRING HERE

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
BASE_API_URL = 'https://eu.kobotoolbox.org/api/v2/assets/' # Renamed for clarity

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

    msg.attach(MIMEText(body, 'plain')) # Plain text for broader compatibility

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
total_projects_fetched_from_api = 0 # Track total count reported by API after filters

print(f"[{datetime.utcnow()}] KoboToolbox Project Auto-Updater Script Started.")
print(f"[{datetime.utcnow()}] Current working directory: {os.getcwd()}")
print(f"[{datetime.utcnow()}] KOBO_TOKEN loaded (length: {len(TOKEN) if TOKEN else 0}).")
print(f"[{datetime.utcnow()}] Project Title Filter set to: '{FILTER_TITLE_SUBSTRING}'" if FILTER_TITLE_SUBSTRING else f"[{datetime.utcnow()}] No Project Title Filter applied (all projects considered).")

# --- Step 1: Construct API URL with asset_type filter and Fetch ALL projects with pagination ---
initial_api_url = f"{BASE_API_URL}?asset_type=survey" # Filter by asset_type=survey directly in the URL
print(f"[{datetime.utcnow()}] Fetching all 'survey' projects from KoboToolbox API (handling pagination)...")
all_survey_projects = [] # Store projects that are already filtered by asset_type
next_page_url = initial_api_url # Start with the base URL including asset_type filter

try:
    while next_page_url:
        print(f"[{datetime.utcnow()}] Fetching page: {next_page_url}")
        response = requests.get(next_page_url, headers=HEADERS)
        response.raise_for_status()
        page_data = response.json()
        
        total_projects_fetched_from_api = page_data.get('count', 0) # Update total count from API (this will be the total 'survey' count)
        all_survey_projects.extend(page_data['results']) # Extend with results for the current page
        next_page_url = page_data['next'] # Get URL for the next page, or None if last page
        
        print(f"[{datetime.utcnow()}] Fetched {len(page_data['results'])} 'survey' projects on this page. Total collected: {len(all_survey_projects)}.")

    print(f"[{datetime.utcnow()}] Successfully retrieved {len(all_survey_projects)} 'survey' projects from KoboToolbox across all pages (API reported total 'survey' count: {total_projects_fetched_from_api}).")

except requests.exceptions.RequestException as e:
    critical_error_occurred = True
    error_details = f"Failed to fetch 'survey' projects from KoboToolbox API during pagination. Error: {e}"
    print(f"[{datetime.utcnow()}] ERROR: {error_details}")
    send_email_notification(
        subject="KoboToolbox Project Update Failed: Critical API Fetch Error",
        body=f"The script encountered a critical error and failed to fetch 'survey' projects from KoboToolbox API.\nError: {error_details}",
        sender=EMAIL_SENDER,
        password=EMAIL_PASSWORD,
        receivers=EMAIL_RECEIVERS,
        smtp_server=SMTP_SERVER,
        smtp_port=SMTP_PORT
    )
    exit(1)

# Initialize tracking lists for reporting (these now operate on the already-filtered 'survey' projects)
recent_projects_found = []
updated_projects_names = []
skipped_projects_names = []
filtered_out_by_title_projects_names = []

# Define the time window for "recent" projects (last 24 hours)
now_utc = datetime.utcnow()
twenty_four_hours_ago = now_utc - timedelta(days=1)
print(f"[{datetime.utcnow()}] Checking for projects created after: {twenty_four_hours_ago.strftime('%Y-%m-%d %H:%M:%S UTC')}")

# --- Step 2: Process each 'survey' project (after API-side filtering) ---
if not critical_error_occurred:
    print(f"[{datetime.utcnow()}] Starting individual project processing loop and applying title filter...")
    for project in all_survey_projects: # Iterate over only the survey projects
        current_name = project.get('name', 'N/A')
        project_uid = project.get('uid', 'N/A')

        # --- Filter 1: By optional project title substring (Python-side filter) ---
        if FILTER_TITLE_SUBSTRING:
            if FILTER_TITLE_SUBSTRING.lower() not in current_name.lower():
                # This project does NOT match the title filter. It will be skipped.
                filtered_out_by_title_projects_names.append(current_name)
                continue # Skip to the next project, do not process it further.

        # --- Filter 2: Check project creation date for projects that passed title filter ---
        date_created_str = project.get('date_created')
        if not date_created_str:
            print(f"[{datetime.utcnow()}] WARNING: 'date_created' field missing for project '{current_name}' (UID: {project_uid}). Skipping date check.")
            continue

        try:
            date_created = datetime.strptime(date_created_str, '%Y-%m-%dT%H:%M:%S.%fZ')
        except ValueError:
            print(f"[{datetime.utcnow()}] WARNING: Could not parse date_created '{date_created_str}' for project '{current_name}' (UID: {project_uid}). Skipping date check.")
            continue

        # Check if the project is recent (created within the last 24 hours)
        if date_created > twenty_four_hours_ago:
            recent_projects_found.append(project)
            
            # Check if project name already has the suffix
            if not current_name.endswith(PROJECT_NAME_SUFFIX):
                new_name = current_name + PROJECT_NAME_SUFFIX
                print(f"[{datetime.utcnow()}] → Updating project: '{current_name}' (UID: {project_uid}) → '{new_name}'")
                update_data = {'name': new_name}
                update_url = BASE_API_URL + f"{project_uid}/" # Use BASE_API_URL
                
                # Attempt to patch the project name via API
                try:
                    update_response = requests.patch(update_url, headers=HEADERS, json=update_data)
                    update_response.raise_for_status()
                    updated_projects_names.append(new_name)
                except requests.exceptions.RequestException as e:
                    print(f"[{datetime.utcnow()}] ERROR: Failed to update project '{current_name}' (UID: {project_uid}): {e}")
            else:
                print(f"[{datetime.utcnow()}] → Skipped (already named correctly): '{current_name}'")
                skipped_projects_names.append(current_name)
    print(f"[{datetime.utcnow()}] Finished individual project processing loop.")

# ==============================================================================
# SUMMARY GENERATION & CONSOLE OUTPUT
# ==============================================================================
summary_message_lines = []
summary_message_lines.append("===== KoboToolbox Project Update Summary =====")
summary_message_lines.append(f"Run Timestamp (UTC): {now_utc.isoformat()}")
summary_message_lines.append(f"Overall Status: **{'SUCCESS' if not critical_error_occurred else 'FAILED'}**")

# Clarified summary output after API-side filtering
summary_message_lines.append(f"Total 'survey' Projects Fetched from API: {total_projects_fetched_from_api}")

if FILTER_TITLE_SUBSTRING:
    summary_message_lines.append(f"Project Title Filter Applied: '{FILTER_TITLE_SUBSTRING}' (case-insensitive)")
    summary_message_lines.append(f" 'survey' Projects NOT Matching Title Filter: {len(filtered_out_by_title_projects_names)}")
else:
    summary_message_lines.append("Project Title Filter: None applied")

summary_message_lines.append(f"Projects created in Last 24h (after all filters): {len(recent_projects_found)}")
summary_message_lines.append(f"Projects Successfully Updated: {len(updated_projects_names)}")
summary_message_lines.append(f"Projects Skipped (already named correctly): {len(skipped_projects_names)}")
summary_message_lines.append("==============================================")
summary_message_lines.append("Script Execution Completed.")

full_console_summary = "\n".join(summary_message_lines)
print(full_console_summary)

# ==============================================================================
# CSV LOGGING
# ==============================================================================
# Note: The CSV log will still contain all columns for comprehensive data,
# even if some are not displayed in the console/email summary for brevity.

print(f"[{datetime.utcnow()}] Attempting to write CSV log...")
log_dir = "logs"
log_file_path = os.path.join(log_dir, "project_update_log.csv")

# Ensure the 'logs' directory exists
try:
    os.makedirs(log_dir, exist_ok=True)
    print(f"[{datetime.utcnow()}] Directory '{log_dir}' ensured.")
except OSError as e:
    print(f"[{datetime.utcnow()}] ERROR: Failed to create directory '{log_dir}': {e}")

# Define CSV headers for the tabular log
csv_headers = [
    "Timestamp (UTC)",
    "Status",
    "Total Surveys Fetched (API)", # New header name
    "Filter Applied (Title Substring)",
    "Surveys Not Matching Title Filter", # Clarified header name
    "Surveys Created Last 24h",
    "Surveys Updated",
    "Surveys Skipped"
]

# Prepare data for the CSV row
csv_row_data = {
    "Timestamp (UTC)": now_utc.isoformat(),
    "Status": "Success" if not critical_error_occurred else "Failed Initial Fetch",
    "Total Surveys Fetched (API)": total_projects_fetched_from_api, # Use the actual API count of surveys
    "Filter Applied (Title Substring)": FILTER_TITLE_SUBSTRING if FILTER_TITLE_SUBSTRING else "None",
    "Surveys Not Matching Title Filter": len(filtered_out_by_title_projects_names),
    "Surveys Created Last 24h": len(recent_projects_found),
    "Surveys Updated": len(updated_projects_names),
    "Surveys Skipped": len(skipped_projects_names)
}

# Write to CSV log file
file_exists = os.path.exists(log_file_path)
print(f"[{datetime.utcnow()}] Log file '{log_file_path}' exists: {file_exists}")

try:
    with open(log_file_path, "a", newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=csv_headers)
        
        if not file_exists:
            writer.writeheader()
            print(f"[{datetime.utcnow()}] CSV header written to new file.")
        
        writer.writerow(csv_row_data)
        print(f"[{datetime.utcnow()}] CSV row data written successfully.")
    print(f"[{datetime.utcnow()}] CSV log updated at {log_file_path}")
except IOError as e:
    print(f"[{datetime.utcnow()}] ERROR: Failed to write to CSV file '{log_file_path}': {e}")

# ==============================================================================
# EMAIL NOTIFICATION
# ==============================================================================
email_subject = "KoboToolbox Project Update Summary"

# Construct a more visually appealing email body
email_body_parts = []

email_body_parts.append("--- KoboToolbox Project Auto-Updater ---")
email_body_parts.append(f"Run Date: {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}")
email_body_parts.append(f"Status: **{'SUCCESS' if not critical_error_occurred else 'FAILED'}**") # Bold status

email_body_parts.append("\n--- Summary of Processing ---")
# Updated this line to reflect API-side filtering
email_body_parts.append(f"- Total 'survey' Projects Fetched from KoboToolbox API: {total_projects_fetched_from_api}")

if FILTER_TITLE_SUBSTRING:
    email_body_parts.append(f"- Project Title Filter Applied: '{FILTER_TITLE_SUBSTRING}' (case-insensitive)")
    email_body_parts.append(f"- 'survey' Projects NOT Matching Title Filter: {len(filtered_out_by_title_projects_names)}")
else:
    email_body_parts.append("- Project Title Filter: None applied")

email_body_parts.append("\n--- Actionable Results ---")
email_body_parts.append(f"- Projects Created in Last 24h (after all filters): {len(recent_projects_found)}")
email_body_parts.append(f"- Projects Successfully Updated: {len(updated_projects_names)}")
email_body_parts.append(f"- Projects Skipped (already named correctly): {len(skipped_projects_names)}")

email_body_parts.append("\n----------------------------------------")
email_body_parts.append("See the updated 'project_update_log.csv' file in your GitHub repository for full details and historical data.")

email_final_body = "\n".join(email_body_parts)


print(f"[{datetime.utcnow()}] Sending email notification...")
send_email_notification(
    subject=email_subject,
    body=email_final_body,
    sender=EMAIL_SENDER,
    password=EMAIL_PASSWORD,
    receivers=EMAIL_RECEIVERS,
    smtp_server=SMTP_SERVER,
    smtp_port=SMTP_PORT
)
print(f"[{datetime.utcnow()}] Script finished.")
