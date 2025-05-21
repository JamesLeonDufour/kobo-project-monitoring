# KoboToolbox Project Auto-Updater

This repository contains a Python script and a GitHub Actions workflow designed to automate the process of identifying newly created KoboToolbox projects and updating their names to indicate they are "To Be Verified."

## 🚀 How It Works

The system operates daily to ensure new projects are promptly flagged for review.

1.  **Scheduled Execution**: Every day at midnight UTC, a GitHub Actions workflow is triggered. It can also be triggered manually.
2.  **Fetch Projects**: The Python script connects to the KoboToolbox API to retrieve a list of all available projects.
3.  **Identify New Projects**: It then checks each project's creation date. If a project was created within the last 24 hours, it's considered "recent."
4.  **Update Project Names**: For recent projects, the script checks if their name already ends with " - To Be Verified".
    * If not, it appends " - To Be Verified" to the project's current name and updates the project via the KoboToolbox API.
    * If it already has the suffix, the project is skipped.
5.  **Logging**: All actions (projects found, updated, or skipped) are logged to a file (`logs/project_update_log.txt`) within the repository.
6.  **Commit Changes**: The GitHub Actions workflow automatically commits and pushes the updated log file back to the repository, providing a persistent record of operations.

## 🛠️ Setup

To use this automation, you need a KoboToolbox API token and to set up a GitHub Actions secret.

### Prerequisites

* A KoboToolbox account and access to its API.
* A KoboToolbox API Token with sufficient permissions to read and update project (asset) names.
* A GitHub repository to host this code.

### Configuration Steps

1.  **Generate KoboToolbox API Token**:
    * Go to your KoboToolbox account settings (usually under your profile).
    * Generate a new API token. **Keep this token secure.**

2.  **Add GitHub Secret**:
    * In your GitHub repository, navigate to `Settings` > `Secrets and variables` > `Actions`.
    * Click on `New repository secret`.
    * Name the secret `KOBO_TOKEN`.
    * Paste your KoboToolbox API token as the value.

3.  **Repository Structure**:
    Ensure your repository has the following file structure:

    ```
    your-repo/
    ├── .github/
    │   └── workflows/
    │       └── auto_update.yml  # The GitHub Actions workflow
    ├── script.py              # The Python script
    ├── README.md              # This README file
    └── logs/                  # Directory for log files (will be created by script)
        └── project_update_log.txt
    ```

    * The `logs` directory will be created automatically by the script if it doesn't exist.

## 📜 Files

* **`.github/workflows/auto_update.yml`**:
    This YAML file defines the GitHub Actions workflow. It specifies:
    * When the workflow runs (daily schedule, manual trigger).
    * The environment setup (Python 3.9).
    * Installation of Python dependencies (`requests`).
    * Execution of the `script.py`.
    * The process for committing the `project_update_log.txt` back to the repository.

* **`script.py`**:
    This Python script contains the core logic:
    * Reads the KoboToolbox API token from environment variables.
    * Fetches all projects from the KoboToolbox API.
    * Identifies projects created in the last 24 hours.
    * Updates the name of eligible projects by appending " - To Be Verified".
    * Logs the actions performed.

* **`logs/project_update_log.txt`**:
    This file is automatically created and updated by the script. It records a summary of each run, including:
    * Timestamp of the run.
    * Number of projects created in the last 24 hours.
    * Number of projects successfully updated.
    * Number of projects skipped (already had the suffix).

## License

This project is open-source and available under the [MIT License](LICENSE).
