# KoboToolbox Project Monitoring 🤖

This repository contains a Python script and a GitHub Actions workflow designed to automate the process of identifying newly created KoboToolbox survey projects and updating their names to indicate they are "To Be Verified." It efficiently fetches data, provides structured logs, and sends email notifications for each run.

## ✨ How It Works

The system operates daily to ensure new projects are promptly flagged for review and to keep you informed of the automation's activities.

1.  **Scheduled Execution**: Every day at midnight UTC, a GitHub Actions workflow is triggered. It can also be triggered manually from the GitHub UI for immediate runs.
2.  **Efficient API Fetching**: The Python script connects to the KoboToolbox API to retrieve **only `survey` type projects**. It handles API pagination automatically to ensure all relevant projects are fetched without unnecessary data transfer.
3.  **Optional Title Filtering (In-Script)**: After fetching survey projects, an additional filter can be applied. If configured directly within `script.py`, the script will **only process projects whose names contain a specific substring** (case-insensitive). Projects not matching this substring are identified and skipped from further processing steps.
4.  **Identify New Projects**: It then checks the creation date of each filtered project. If a project was created within the last 24 hours, it's considered "recent" and eligible for naming updates.
5.  **Update Project Names**: For recent and eligible projects, the script verifies if their name already ends with " - To Be Verified".
    * If the suffix is missing, it appends " - To Be Verified" to the project's current name and updates the project via the KoboToolbox API.
    * If the project name already includes the suffix, it's skipped to avoid redundant updates.
6.  **Tabular Logging**: All key actions and statistics (total surveys fetched, projects filtered by title, updated, skipped) are meticulously logged in a structured CSV file (`logs/project_update_log.csv`). A new row is appended for each run, providing a clear, tabular historical record of the automation's activities.
7.  **Commit Changes**: The GitHub Actions workflow automatically commits and pushes the updated CSV log file back to the repository, ensuring your operational logs are persistently saved and version-controlled.
8.  **Email Notification**: A concise summary email is sent to configured recipients after each execution, detailing the run's success/failure status and key processing counts. In case of critical failures (e.g., inability to connect to the KoboToolbox API), an immediate error email is dispatched.

## 🛠️ Setup Guide

To get this automation running, follow these steps:

### Prerequisites

* A KoboToolbox account with API access and an API Token that has permissions to read and update project (asset) names.
* An email account capable of sending mail via SMTP (e.g., Gmail, Outlook).
    * **Important for Gmail/Outlook**: If you use 2-Factor Authentication, you will likely need to generate an "App Password" specifically for this script instead of using your main account password.
* A GitHub repository to host this codebase.

### Configuration Steps

1.  **Generate KoboToolbox API Token**:
    * Log in to your KoboToolbox account.
    * Navigate to your account settings (usually accessible via your profile icon).
    * Generate a new API token. **Keep this token confidential.**

2.  **Gather Email Credentials**:
    * **Sender Email Address**: The full email address from which notifications will be sent (e.g., `your.email@example.com`).
    * **Sender Email Password**: The password for your sender email account (or the App Password if required).
    * **Recipient Email Addresses**: A comma-separated list of email addresses that should receive notifications (e.g., `recipient1@example.com,team@example.com`).
    * **SMTP Server Address**: The SMTP server hostname for your email provider (e.g., `smtp.gmail.com` for Gmail, `smtp.office365.com` for Outlook/Microsoft 365).
    * **SMTP Port**: The port number for your SMTP server (commonly `587` for TLS encryption, or `465` for SSL).

3.  **Add GitHub Secrets**:
    * In your GitHub repository, go to `Settings` > `Secrets and variables` > `Actions`.
    * Click on `New repository secret` for each of the following, and enter their corresponding values obtained in step 2:
        * `KOBO_TOKEN`
        * `EMAIL_SENDER`
        * `EMAIL_PASSWORD`
        * `EMAIL_RECEIVERS`
        * `SMTP_SERVER`
        * `SMTP_PORT`

4.  **Configure Project Title Filter (in `script.py`)**:
    * Open the `script.py` file within your GitHub repository (or locally and push changes).
    * Locate the `FILTER_TITLE_SUBSTRING` variable definition (it's clearly marked under `SCRIPT CONFIGURATION` near the top).
    * **To enable filtering**: Assign the specific substring you want to match to this variable. For example, if you only want to process projects with "RMNA" in their title:
        ```python
        FILTER_TITLE_SUBSTRING = "RMNA"
        ```
    * **To disable filtering**: Set the variable to an empty string:
        ```python
        FILTER_TITLE_SUBSTRING = ""
        ```
    * **Important**: Remember to commit and push any changes to `script.py` to apply your filter settings. Also, ensure you have **removed** `KOBO_PROJECT_FILTER_TITLE` from your `auto_update.yml`'s `env` block, as it is now solely configured within `script.py`.

5.  **Verify Repository Structure**:
    Ensure your repository is organized as follows:

    ```
    your-repo/
    ├── .github/
    │   └── workflows/
    │       └── auto_update.yml  # The GitHub Actions workflow definition
    ├── script.py              # The main Python script
    ├── README.md              # This README file
    └── logs/                  # Directory for log files (will be created automatically)
        └── project_update_log.csv # The tabular CSV log file (will be created automatically)
    ```

    * The `logs` directory and the `project_update_log.csv` file will be created by the script on its first successful run if they don't already exist.

## 📄 Files Overview

* **`.github/workflows/auto_update.yml`**:
    This YAML file configures the GitHub Actions workflow. It defines the trigger (daily schedule, manual dispatch), sets up the Python environment, installs dependencies, executes `script.py`, and handles the commit and push of the updated log file back to the repository.

* **`script.py`**:
    This is the core Python script containing all the automation logic. It handles API authentication, efficient fetching of paginated survey data, applying the in-script title filter, identifying recent projects, updating project names, generating console output summaries, writing to the CSV log, and sending email notifications.

* **`logs/project_update_log.csv`**:
    This automatically generated CSV file serves as a detailed and historical log of every script execution. Each row represents a run and includes metrics such as the timestamp, overall status, total 'survey' projects fetched from the API, whether a title filter was applied, number of 'survey' projects not matching the title filter, number of projects created in the last 24 hours (after all filters), number of projects successfully updated, and number of projects skipped (already had the suffix).

---

## License

This project is open-source and available under the [MIT License](LICENSE).
