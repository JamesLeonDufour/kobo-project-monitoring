KoboToolbox Project Auto-Updater
This repository automates the process of identifying newly created KoboToolbox survey projects and updating their names. It efficiently fetches and processes data, provides structured logs, and sends email notifications for each run.

🚀 Key Features
Automated Project Naming: Automatically appends " - To Be Verified" to new survey projects created in the last 24 hours.
Efficient API Filtering: Fetches only survey type projects directly from the KoboToolbox API, significantly reducing data transfer and processing time.
Customizable Title Filtering: Further refines project selection by allowing you to specify a substring (directly in script.py) that project titles must contain.
Structured Logging: Maintains a clear logs/project_update_log.csv file, appending a new row for each run with key metrics.
Email Notifications: Sends a concise summary email after each execution, including success/failure status and processed counts.
GitHub Actions Workflow: Runs daily at midnight UTC via GitHub Actions, and can also be triggered manually.
🛠️ Setup
To use this automation:

KoboToolbox API Token: Generate an API token from your KoboToolbox account.
Email Credentials: Gather your sender email address, an App Password (recommended for Gmail/Outlook), recipient email addresses, and your SMTP server details (address and port).
GitHub Secrets: In your GitHub repository, go to Settings > Secrets and variables > Actions and add the following secrets:
KOBO_TOKEN
EMAIL_SENDER
EMAIL_PASSWORD
EMAIL_RECEIVERS
SMTP_SERVER
SMTP_PORT
Configure Filter (in script.py): Open script.py and directly set the FILTER_TITLE_SUBSTRING variable if you wish to enable title-based filtering. Set it to "" to disable.
📁 Repository Files
.github/workflows/auto_update.yml: Defines the GitHub Actions workflow for scheduling, environment setup, and script execution.
script.py: Contains the core Python logic for API interaction, project processing, logging, and email notifications.
logs/project_update_log.csv: The automatically generated CSV log file, updated with each run.
License
This project is open-source and available under the MIT License.
