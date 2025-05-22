KoboToolbox Project Auto-Updater
This repository contains a Python script and a GitHub Actions workflow designed to automate the process of identifying newly created KoboToolbox survey projects and updating their names to indicate they are "To Be Verified." It also provides detailed logging and email notifications for each run.

🚀 How It Works
The system operates daily to ensure new projects are promptly flagged for review and to keep you informed of the automation's activities.

Scheduled Execution: Every day at midnight UTC, a GitHub Actions workflow is triggered. It can also be triggered manually from the GitHub UI.
Efficient API Fetching: The Python script connects to the KoboToolbox API to retrieve only survey type projects, handling pagination automatically to ensure all relevant projects are fetched without unnecessary data transfer.
Optional Title Filtering (In-Script): After fetching, the script can apply an additional filter. If configured (directly within script.py), it will only process projects whose names contain a specific substring (case-insensitive). Projects not matching this substring are skipped.
Identify New Projects: It then checks each filtered project's creation date. If a project was created within the last 24 hours, it's considered "recent."
Update Project Names: For recent projects that pass all filters, the script checks if their name already ends with " - To Be Verified".
If not, it appends " - To Be Verified" to the project's current name and updates the project via the KoboToolbox API.
If it already has the suffix, the project is skipped.
Tabular Logging: All actions (total projects fetched, projects filtered by type/title, updated, skipped) are logged in a structured CSV file (logs/project_update_log.csv) within the repository. Each run appends a new row to this file, providing a clear, tabular historical record.
Commit Changes: The GitHub Actions workflow automatically commits and pushes the updated CSV log file back to the repository, ensuring your logs are persistently saved.
Email Notification: After each run, a concise summary email is sent to configured recipients, detailing the results of the script's execution. In case of critical failures (e.g., inability to connect to KoboToolbox API), an immediate error email is sent.
🛠️ Setup
To use this automation, you need a KoboToolbox API token, email sending credentials, and to set up GitHub Actions secrets.

Prerequisites
A KoboToolbox account and access to its API.
A KoboToolbox API Token with sufficient permissions to read and update project (asset) names.
An email account (e.g., Gmail, Outlook) to send notifications. For Gmail/Outlook, you will likely need to generate an "App Password" if you have 2-Factor Authentication enabled, rather than using your regular account password.
A GitHub repository to host this code.
Configuration Steps
Generate KoboToolbox API Token:

Go to your KoboToolbox account settings (usually under your profile).
Generate a new API token. Keep this token secure.
Gather Email Credentials:

Sender Email Address: The full email address that will send the notifications.
Sender Email Password: The password for the sender email account. As mentioned, an "App Password" is highly recommended and often required.
Recipient Email Addresses: A comma-separated list of email addresses that should receive notifications.
SMTP Server Address: The SMTP server for your sender email (e.g., smtp.gmail.com for Gmail, smtp.office365.com for Outlook/Microsoft 365).
SMTP Port: The port for your SMTP server (commonly 587 for TLS, or 465 for SSL).
Add GitHub Secrets:

In your GitHub repository, navigate to Settings > Secrets and variables > Actions.
Click on New repository secret and add the following secrets with their corresponding values:
KOBO_TOKEN: Your KoboToolbox API Token.
EMAIL_SENDER: Your sender email address.
EMAIL_PASSWORD: Your sender email password (App Password).
EMAIL_RECEIVERS: Comma-separated recipient email addresses.
SMTP_SERVER: Your SMTP server address.
SMTP_PORT: Your SMTP port (e.g., 587).
Configure Project Title Filter (Directly in script.py):

Open the script.py file in your repository.
Locate the FILTER_TITLE_SUBSTRING variable (around line 25-30).
To enable filtering: Set its value to the specific substring you want to match in project titles. For example:
Python

FILTER_TITLE_SUBSTRING = "RMNA" # Only process projects with "RMNA" in their title
The comparison is case-insensitive, so "RMNA" will match "RMNA Assessment", "rmna_data", etc.
To disable filtering: Set its value to an empty string:
Python

FILTER_TITLE_SUBSTRING = "" # Process all 'survey' projects
Remember to commit and push changes to script.py to apply the filter.
Repository Structure:
Ensure your repository has the following file structure:

your-repo/
├── .github/
│   └── workflows/
│       └── auto_update.yml  # The GitHub Actions workflow
├── script.py              # The Python script
├── README.md              # This README file
└── logs/                  # Directory for log files (will be created by script)
    └── project_update_log.csv # The tabular CSV log file
The logs directory and project_update_log.csv file will be created automatically by the script on its first run if they don't exist.
📜 Files
.github/workflows/auto_update.yml:
This YAML file defines the GitHub Actions workflow. It specifies:

When the workflow runs (daily schedule, manual trigger).
The environment setup (Python 3.9).
Installation of Python dependencies (requests).
Execution of the script.py.
The passing of all necessary API tokens and email credentials as environment variables from GitHub Secrets to the Python script.
The process for committing the logs/project_update_log.csv back to the repository.
script.py:
This Python script contains the core logic:

Reads configuration (KoboToolbox token, filter title, email settings) from environment variables or directly from the script.
Efficiently fetches only 'survey' type projects from the KoboToolbox API, handling pagination.
Applies an optional title filter (defined in the script).
Identifies projects created in the last 24 hours.
Updates the name of eligible projects by appending " - To Be Verified".
Includes robust error handling for API calls and email sending.
Generates a structured, tabular (CSV) log of the run's summary.
Sends a comprehensive email notification detailing the run's outcome.
logs/project_update_log.csv:
This file is automatically created and updated by the script. It records a tabular summary of each run, including:

Timestamp of the run.
Overall Status of the run.
Total 'survey' projects fetched from the API.
Whether a title filter was applied.
Number of 'survey' projects not matching the title filter.
Number of projects created in the last 24 hours (after all filters).
Number of projects successfully updated.
Number of projects skipped (already had the suffix).
License
This project is open-source and available under the MIT License.
