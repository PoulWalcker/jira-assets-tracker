# Jira Assets Tracker

This project automates asset tracking and task management in Jira. It processes asset data, extracts key attributes, and creates or updates Jira tasks accordingly.

## 1. Environment Variables

Create a `.env` file in the project root with the following variables (adjust them as needed):

```
JIRA_APIKEY=YOUR_API_KEY
JIRA_URL=https://your-jira-instance.atlassian.net/
JIRA_PROJECT_KEY=TST  # Use ITINF for production, TST for testing
JIRA_USERNAME=your-email@example.com
JIRA_WORKSPACE_ID=your-workspace-id

# For production use 53, for test use 54
JIRA_ASSETS_OBJECT_TYPE_ID=54
SLEEP_TIME_INTERVAL_SECONDS=600
```

## 2. User Mapping File

The project uses a JSON file to map user names to their Jira assignee IDs. Create the file `app/user_mapping.json` with content similar to the following example:

```json
{
  "Name Surname": "000000:00000000-0000-0000-0000-000000000000",
  "Name Surname": "000000:00000000-0000-0000-0000-000000000000"
}
```

The assignee mapping is used to automatically assign tasks based on the asset's "Primary Responsible Employee" attribute.

## 3. Configuration

All configurable parameters such as time thresholds, message templates, and user mappings are stored in the configuration file `app/config.py`. You can adjust these values to match your environment and preferences.

## 4. Project Structure

The project is organized as follows:

```
project_root/
├── app/
│   ├── __init__.py           # Package initializer, optional public API definitions.
│   ├── config.py             # Configuration constants and message templates.
│   ├── jira_board.py         # JiraBoard API wrapper for task management.
│   ├── jira_assets.py        # JiraAssets API wrapper for asset data.
│   ├── helpers.py            # Helper functions (e.g., caching, attribute extraction).
│   ├── updater.py            # Core logic for processing assets and managing tasks.
│   └── main.py               # Application entry point.
├── .dockerignore            # Files to exclude from the Docker build context.
├── .gitignore               # Files and directories to ignore in Git.
├── Dockerfile               # Docker configuration to build the container.
├── requirements.txt         # Python dependencies.
└── README.md                # Project documentation.

P.S.: In the original code, the part with tests exists, but I have decided to hide it in the public version. 
```

## 5. Running the Application

To run the application locally, execute:

```bash
python -m app.main
```

## 6. Docker

To build and run the application in a Docker container, ensure the Dockerfile is in the project root. Then run:

```bash
docker build -t jira-assets-tracker .
docker run --env-file .env jira-assets-tracker
```

## Additional Notes

### Environment Variables:
All sensitive data and environment-specific settings are controlled via environment variables. Adjust the `.env` file as needed.

### User Mapping:
The user mapping file (`app/user_mapping.json`) is used to automatically assign tasks to users based on asset attributes.

### Configuration:
You can customize the configuration in `app/config.py` (e.g., message templates and time thresholds) to suit your workflow.