# app/helpers.py

import logging
from datetime import datetime

# Global cache for task details to reduce duplicate API calls.
# This cache is shared among functions in this module.
task_cache = {}


def get_task_cached(issue_key, jira_board):
    """
    Returns task details for a given issue key using caching.
    """
    if issue_key not in task_cache:
        task_cache[issue_key] = jira_board.get_task(issue_key)
    return task_cache[issue_key]


def clear_task_cache():
    """
    Clears the global task cache.
    """
    global task_cache
    task_cache = {}


def extract_update_date(attributes):
    """
    Extracts and parses the 'Update' date from asset attributes.
    """
    update_date_str = attributes.get("Update", [None])[0]
    if update_date_str:
        try:
            return datetime.strptime(update_date_str, "%Y-%m-%d")
        except Exception as e:
            logging.error(f"Error parsing update date: {e}")
    return None


def extract_assignee_name(attributes):
    """
    Extracts the assignee's name from the asset attributes dictionary.
    """
    return attributes.get("Primary Responsible Employee", [None])[0]


def is_task_for_update(task):
    """
    Checks if the provided task has the 'AssetUpdate' label.
    """
    if not task:
        return False
    fields = task.get("fields", {})
    labels = fields.get("labels", [])
    return "AssetUpdate" in labels


def filter_update_issues(linked_issues, jira_board):
    """
    Filters the list of linked issues to only include update tasks.
    """
    filtered = []
    for linked_issue in linked_issues:
        issue_key = linked_issue.get("key")
        task = get_task_cached(issue_key, jira_board)
        if is_task_for_update(task):
            filtered.append(linked_issue)
    return filtered
