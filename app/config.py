# app/config.py

import os
import json
import logging

# Time thresholds
ONE_DAY_SECONDS = 86400  # 24 hours in seconds
UPDATE_WARNING_DAYS = 5
UPDATE_WARNING_SECONDS = UPDATE_WARNING_DAYS * ONE_DAY_SECONDS

# Task and comment message templates
TASK_SUMMARY_TEMPLATE = "Update {asset_name}"
TASK_DESCRIPTION_TEMPLATE = (
    "Please update the asset '{asset_name}'.\n\n"
    "Required steps:\n"
    "1. Update the app\n"
    "2. Update the 'Update' property in Asset\n"
    "3. Move task to -> DONE"
)

COMMENT_REMINDER = "Reminder: The asset update is overdue (Update date: {update_date}). Please update the asset."
COMMENT_REQUEST_UPDATE = (
    "The Update date is outdated. Please update the asset accordingly."
)
COMMENT_FUTURE_STUCK = (
    "Task is not Done and the update date ({update_date}) is in the future. "
    "Task is stuck and needs review."
)
USER_MAPPING_PATH = os.path.join("app", "user_mapping.json")

try:
    with open(USER_MAPPING_PATH, "r") as f:
        ASSIGNEE_MAPPING = json.load(f)
except Exception as e:
    logging.error(f"Error loading user mapping from {USER_MAPPING_PATH}: {e}")
    ASSIGNEE_MAPPING = {}
