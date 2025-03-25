import os
import time
import logging
import json
from datetime import datetime
from app.jira_board import JiraBoard
from app.jira_assets import JiraAssets
from dotenv import load_dotenv
from app.config import (
    UPDATE_WARNING_SECONDS,
    TASK_SUMMARY_TEMPLATE,
    TASK_DESCRIPTION_TEMPLATE,
    COMMENT_REMINDER,
    COMMENT_REQUEST_UPDATE,
    COMMENT_FUTURE_STUCK,
    ASSIGNEE_MAPPING,
)
from app.helpres import (
    get_task_cached,
    clear_task_cache,
    extract_update_date,
    extract_assignee_name,
    filter_update_issues,
)

logging.basicConfig(level=logging.INFO)
load_dotenv()

# Initialize Jira API Wrappers
jira_assets = JiraAssets(
    workspace_id=os.getenv("JIRA_WORKSPACE_ID"),
    auth={
        "url": os.getenv("JIRA_URL"),
        "username": os.getenv("JIRA_USERNAME"),
        "password": os.getenv("JIRA_APIKEY"),
    },
)

jira_board = JiraBoard(
    url=os.getenv("JIRA_URL"),
    username=os.getenv("JIRA_USERNAME"),
    apikey=os.getenv("JIRA_APIKEY"),
)

# Load asset attribute mapping
ATTRIBUTES_PATH = os.path.join("app", "attributes.json")
try:
    if not os.path.exists(ATTRIBUTES_PATH):
        logging.info(f"{ATTRIBUTES_PATH} not found. Creating default mapping file.")
        asset_attributes = jira_assets.get_attribute_dict(
            os.getenv("JIRA_ASSETS_OBJECT_TYPE_ID")
        )
        if not isinstance(asset_attributes, dict):
            raise ValueError("Default asset attributes is not a dictionary.")
        with open(ATTRIBUTES_PATH, "w") as f:
            json.dump(asset_attributes, f, indent=4)
        attribute_map = asset_attributes
    else:
        with open(ATTRIBUTES_PATH, "r") as f:
            attribute_map = json.load(f)
except Exception as e:
    logging.error(f"Error handling attributes file: {e}")
    attribute_map = {}

# Global cache for task details (to reduce duplicate API calls)
# The cache will be cleared at the beginning of each processing iteration.
task_cache = {}


def process_linked_update_issue(issue, asset, attributes):
    """
    Processes a single linked update issue:
      - If the task is not Done and the update date has passed, adds a reminder comment and transitions to "In Progress".
      - If the task is Done and the update date is outdated, adds a comment to request update.
      - Otherwise (if update date is in the future), logs that the task is stuck.
    """
    issue_key = issue["key"]
    task = get_task_cached(issue_key, jira_board)
    if not task:
        logging.warning(f"[Task ID: {issue_key}] Task not found!")
        return

    status = task.get("fields", {}).get("status", {}).get("name", "")
    update_date_str = attributes.get("Update", [None])[0]
    if not update_date_str:
        logging.error("Asset 'Update' property is missing in attributes.")
        return

    try:
        update_date = datetime.strptime(update_date_str, "%Y-%m-%d")
    except Exception as e:
        logging.error(f"[Task ID: {issue_key}] Error parsing update date: {e}")
        return

    now = datetime.now()
    if status != "Done":
        if update_date <= now:
            if status != "In Progress":
                logging.info(
                    f"[Asset ID: {asset.get('id')}] Task {issue_key} is overdue. Transitioning to In Progress."
                )
                jira_board.add_comment(
                    issue_key, COMMENT_REMINDER.format(update_date=update_date_str)
                )
                jira_board.transition_task_by_name(issue_key, "In Progress")
            else:
                logging.info(
                    f"[Asset ID: {asset.get('id')}] Task {issue_key} is already in In Progress."
                )
        else:
            logging.info(
                f"[Asset ID: {asset.get('id')}] Task {issue_key} is not Done and the update date ({update_date_str}) is in the future. {COMMENT_FUTURE_STUCK.format(update_date=update_date_str)}"
            )
    else:
        if update_date <= now:
            logging.info(
                f"[Asset ID: {asset.get('id')}] Task {issue_key} is Done but update date is outdated. Requesting update."
            )
            jira_board.add_comment(issue_key, COMMENT_REQUEST_UPDATE)
        else:
            logging.info(
                f"[Asset ID: {asset.get('id')}] Task {issue_key} is Done and update date is up-to-date."
            )


def create_update_task(asset, attributes, is_outdated):
    """
    Creates a new update task for the asset if no linked update task exists.
    The 'is_outdated' flag can be used for additional differentiation.
    """
    workspace_id = os.getenv("JIRA_WORKSPACE_ID")
    project_key = os.getenv("JIRA_PROJECT_KEY")
    if not workspace_id or not project_key:
        logging.error(
            "Workspace ID or Project Key is not set in environment variables."
        )
        return

    asset_id = asset.get("id")
    if not asset_id:
        logging.error("Asset ID is missing.")
        return

    linked_issues = jira_assets.get_object_connected_tickets(asset_id)
    update_issues = filter_update_issues(linked_issues, jira_board)
    if update_issues:
        logging.info(
            f"[Asset ID: {asset_id}] Already has linked update issue: {update_issues[0].get('key', '')}"
        )
        return

    custom_field_id = f"{workspace_id}:{asset_id}"
    asset_name = attributes.get("Name", [None])[0]
    if not asset_name:
        logging.error("Asset 'Name' property is missing in attributes.")
        return

    duedate = attributes.get("Update", [None])[0]
    if not duedate:
        logging.error("Asset 'Update' property is missing in attributes.")
        return

    assignee_name = extract_assignee_name(attributes)
    assignee_id = ASSIGNEE_MAPPING.get(assignee_name) if assignee_name else None

    task_payload = {
        "project_key": project_key,
        "summary": TASK_SUMMARY_TEMPLATE.format(asset_name=asset_name),
        "description": TASK_DESCRIPTION_TEMPLATE.format(asset_name=asset_name),
        "issue_type": "Task",
        "duedate": duedate,
        "custom_fields": {
            "customfield_10191": [
                {
                    "workspaceId": workspace_id,
                    "id": custom_field_id,
                    "objectId": asset_id,
                }
            ],
        },
        "task_labels": ["AssetUpdate"],
    }
    if assignee_id and assignee_id != 0:
        task_payload["assignee_id"] = assignee_id

    response = jira_board.create_task(**task_payload)
    if not response or "key" not in response:
        logging.error(
            f"[Asset ID: {asset_id}] Failed to create task. Response: {response}"
        )
        return

    logging.info(f"[Asset ID: {asset_id}] Created new update task: {response['key']}.")


def process_asset_update(asset):
    """
    Processes a single asset:
      - Extracts asset attributes and the Update date.
      - Uses precise time comparison (in seconds) to determine if the asset is overdue,
        scheduled for update, or up-to-date.
    """
    attributes = jira_assets.extract_attribute_values(asset, attribute_map)
    update_date = extract_update_date(attributes)
    if not update_date:
        logging.warning(f"[Asset ID: {asset.get('id')}] No valid Update date.")
        return

    now = datetime.now()
    time_diff = update_date - now
    if time_diff.total_seconds() <= 0:
        logging.info(
            f"[Asset ID: {asset.get('id')}] Requires update (Update: {update_date.strftime('%Y-%m-%d %H:%M:%S')})."
        )
        handle_overdue_asset(asset, attributes)
    elif time_diff.total_seconds() <= UPDATE_WARNING_SECONDS:
        logging.info(
            f"[Asset ID: {asset.get('id')}] Scheduled for update in {time_diff.total_seconds()/3600:.1f} hours."
        )
        handle_future_asset(asset, attributes, update_date)
    else:
        logging.info(
            f"[Asset ID: {asset.get('id')}] Up-to-date (Next update: {update_date.strftime('%Y-%m-%d %H:%M:%S')})."
        )


def handle_overdue_asset(asset, attributes):
    """
    Handles assets with an overdue update date.
    Processes linked update tasks if present; otherwise, creates a new update task.
    """
    asset_id = asset["id"]
    linked_issues = jira_assets.get_object_connected_tickets(asset_id)
    update_issues = filter_update_issues(linked_issues, jira_board)
    if update_issues:
        for issue in update_issues:
            process_linked_update_issue(issue, asset, attributes)
    else:
        create_update_task(asset, attributes, is_outdated=True)
        logging.info(f"[Asset ID: {asset_id}] New update task is being created.")


def handle_future_asset(asset, attributes, update_date):
    """
    Handles assets with an upcoming update date (within the warning interval).
    If an update task exists and is active (e.g., in 'TO DO' or 'In Progress'), do nothing.
    Otherwise, creates a new update task.
    """
    asset_id = asset["id"]
    linked_issues = jira_assets.get_object_connected_tickets(asset_id)
    update_issues = filter_update_issues(linked_issues, jira_board)

    active_issue_found = False
    active_statuses = ["TO DO", "In Progress"]
    for issue in update_issues:
        issue_key = issue["key"]
        task = get_task_cached(issue_key, jira_board)
        if not task:
            logging.warning(f"[Asset ID: {asset_id}] Task {issue_key} not found!")
            continue
        status = task.get("fields", {}).get("status", {}).get("name", "")
        if status in active_statuses:
            logging.info(
                f"[Asset ID: {asset_id}] Task {issue_key} is active with status: {status}."
            )
            active_issue_found = True
            break

    if not active_issue_found:
        create_update_task(asset, attributes, is_outdated=False)
        logging.info(f"[Asset ID: {asset_id}] New update task is being created.")


def process_assets_with_update(assets):
    """Processes all assets in the provided list."""
    for asset in assets:
        process_asset_update(asset)


def run_every_10_minutes():
    """Runs the asset update check every 10 minutes."""
    while True:
        logging.info("> ---------- Running iteration ----------")
        global task_cache
        clear_task_cache()  # Clear the cache for fresh API calls
        assets = jira_assets.post_object_aql(
            f"objectTypeId = {os.getenv('JIRA_ASSETS_OBJECT_TYPE_ID')} AND Update is not EMPTY"
        )
        process_assets_with_update(assets.get("values", []))
        logging.info("> ---------- End of iteration ----------")
        time.sleep(int(os.getenv("SLEEP_TIME_INTERVAL_SECONDS", 600)))


if __name__ == "__main__":
    run_every_10_minutes()
