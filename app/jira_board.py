import requests
import logging

logging.basicConfig(level=logging.INFO)


class JiraBoard:
    """
    Jira Board/Task Management API wrapper.
    """

    def __init__(self, url, username, apikey):
        self.url = url.rstrip("/")
        self.username = username
        self.apikey = apikey
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _request(self, method, endpoint, **kwargs):
        url = f"{self.url}/{endpoint.lstrip('/')}"
        auth = (self.username, self.apikey)

        try:
            response = requests.request(
                method, url, auth=auth, headers=self.headers, **kwargs
            )
            response.raise_for_status()
            if response.text:
                return response.json()
            return None
        except requests.exceptions.HTTPError as err:
            logging.error(f"HTTP error: {err}")
            return {"error": str(err), "response": response.text}
        except Exception as err:
            logging.error(f"Request failed: {err}")
            return {"error": str(err)}

    def get_users_from_group(self, group_id):
        return self._request(
            "GET", f"rest/api/2/groups/picker", params={"groupId": group_id}
        )

    def get_all_users(self):
        return self._request("GET", f"/rest/api/2/users/search")

    def create_task(
        self, project_key, summary, description, issue_type="Task", **kwargs
    ):

        if not project_key or not summary or not description:
            raise ValueError(
                "project_key, summary, and description are required fields."
            )

        fields = {
            "project": {"key": project_key},
            "summary": summary,
            "description": description,
            "issuetype": {"name": issue_type},
        }

        if assignee_id := kwargs.get("assignee_id"):
            fields["assignee"] = {"id": assignee_id}
        if duedate := kwargs.get("duedate"):
            fields["duedate"] = duedate
        if labels := kwargs.get("task_labels"):
            fields["labels"] = labels

        if custom_fields := kwargs.get("custom_fields"):
            fields.update(custom_fields)

        payload = {"fields": fields}

        return self._request("POST", "rest/api/2/issue", json=payload)

    def get_task(self, issue_key):
        return self._request("GET", f"rest/api/2/issue/{issue_key}")

    def update_task(self, issue_key, **fields):
        payload = {"fields": fields}
        return self._request("PUT", f"rest/api/2/issue/{issue_key}", json=payload)

    def add_comment(self, issue_key, comment):
        payload = {"body": comment}
        return self._request(
            "POST", f"rest/api/2/issue/{issue_key}/comment", json=payload
        )

    def get_transitions(self, issue_key):
        return self._request("GET", f"rest/api/2/issue/{issue_key}/transitions")

    def transition_task(self, issue_key, transition_id):
        payload = {"transition": {"id": transition_id}}
        return self._request(
            "POST", f"rest/api/2/issue/{issue_key}/transitions", json=payload
        )

    def is_task_done(self, issue_key):
        """
        Check if a task is in the 'Done' status.
        """
        task = self.get_task(issue_key)
        if task:
            return task.get("fields", {}).get("status", {}).get("name") == "Done"
        return False

    def find_transition_by_name(self, issue_key, transition_name):
        """
        Find a transition ID by its name for a given issue.
        """
        transitions = self.get_transitions(issue_key)
        for transition in transitions.get("transitions", []):
            if transition["name"] == transition_name:
                return transition["id"]
        return None

    def transition_task_by_name(self, issue_key, transition_name):
        """
        Transition a task to a new status by its name.
        """
        transition_id = self.find_transition_by_name(issue_key, transition_name)
        if not transition_id:
            raise ValueError(
                f"Transition '{transition_name}' not found for issue {issue_key}"
            )
        return self.transition_task(issue_key, transition_id)
