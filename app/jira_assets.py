import requests
import logging
from atlassian.rest_client import AtlassianRestAPI

logging.basicConfig(level=logging.INFO)


class JiraAssets(AtlassianRestAPI):
    """
    Jira Service Management Assets API wrapper.
    """

    def __init__(self, workspace_id, auth):
        """
        Initialize the API client.
        :param workspace_id: Workspace ID for Jira Assets.
        :param auth: Dictionary containing 'url', 'username', and 'password' for authentication.
        """
        self.workspace_id = workspace_id
        self.auth = auth
        api_url = f"{auth['url']}gateway/api/jsm/assets/workspace/{workspace_id}/v1"
        super().__init__(**{**auth, "url": api_url})

    def _request(self, method, endpoint, **kwargs):
        """
        Make a generic API request.
        :param method: HTTP method (GET, POST, PUT, DELETE).
        :param endpoint: API endpoint.
        :param kwargs: Additional parameters (params, json, etc.)
        :return: JSON response or error message.
        """
        url = f"{self.url}/{endpoint.lstrip('/')}"
        try:
            response = requests.request(
                method,
                url,
                auth=(self.auth["username"], self.auth["password"]),
                headers=self.experimental_headers,
                **kwargs,
            )
            response.raise_for_status()
            return response.json() if response.text else None
        except requests.exceptions.HTTPError as err:
            logging.error(f"HTTP error: {err} - {response.text}")
            return {"error": str(err), "response": response.text}
        except Exception as err:
            logging.error(f"Request failed: {err}")
            return {"error": str(err)}

    def build_aql_query(self, filters):
        """
        Build an AQL query string based on filters.
        :param filters: Dictionary of field-value pairs for filtering.
        :return: AQL query string.
        """
        conditions = []
        for field, value in filters.items():
            if isinstance(value, (list, tuple)):
                formatted_values = ", ".join([str(v) for v in value])
                conditions.append(f"{field} IN ({formatted_values})")
            else:
                formatted_value = f"'{value}'" if isinstance(value, str) else value
                conditions.append(f"{field} = {formatted_value}")
        return " AND ".join(conditions)

    def get_assets_by_filter(self, filters):
        """
        Retrieve assets filtered by given parameters.
        :param filters: Dictionary of filters for AQL query.
        :return: JSON response with assets.
        """
        query = self.build_aql_query(filters)
        return self.post_object_aql(query)

    def extract_attribute_values(self, object_data, attribute_map):
        """
        Extract attribute values from an object using a predefined attribute map.
        :param object_data: Object data containing attributes.
        :param attribute_map: Dictionary mapping IDs to attribute names.
        :return: Dictionary of extracted attribute values.
        """
        attributes = {}

        for attr in object_data.get("attributes", []):
            attr_name = attribute_map.get(attr["objectTypeAttributeId"])
            if attr_name:
                values = []
                for value in attr.get("objectAttributeValues", []):
                    if "value" in value:
                        values.append(value["value"])
                    elif "referencedObject" in value:
                        values.append(value["referencedObject"].get("label"))
                attributes[attr_name] = values

        return attributes

    def get_object_connected_tickets(self, object_id):
        """
        Retrieve linked tickets of an asset object.
        :param object_id: ID of the object.
        :return: List of linked tickets or an empty list.
        """
        response = self._request("GET", f"/objectconnectedtickets/{object_id}/tickets")
        if response and "tickets" in response:
            return response["tickets"]
        return []

    def get_object_by_id(self, object_id):
        """
        Retrieve an object data based on its id.
        :param object_id: ID of the object.
        :return: A json assets object data.
        """

        return self._request("GET", f"object/{object_id}")

    def post_object_aql(self, query):
        """
        Execute an AQL query to find asset objects.
        :param query: AQL query string.
        :return: JSON response with objects matching the query.
        """
        return self._request("POST", "/object/aql", json={"qlQuery": query})

    def get_attribute_dict(self, objecttype_id):
        """
        Retrieve a dictionary of attribute IDs and their names.
        :param objecttype_id: ID of the object type.
        :return: A dictionary with attribute IDs as keys and names as values.
        """
        attributes = self.get_object_attributes(objecttype_id)
        if not attributes:
            return {}
        return {attr["id"]: attr["name"] for attr in attributes}

    def get_object_attributes(self, object_id):
        """
        Retrieve the attributes of an asset object.
        :param object_id: ID of the object.
        :return: A list of attributes of the object.
        """
        return self._request("GET", f"/objecttype/{object_id}/attributes")

    def update_object_by_id(self, object_id, payload):
        """
        Update an asset object with the given payload.
        :param object_id: ID of the object.
        :param payload: The payload containing the update data (attributes, avatar, etc.).
        :return: JSON response with the updated object.
        """
        return self._request("PUT", f"/object/{object_id}", json=payload)

    def add_linked_issue(self, object_id, issue_key):
        """
        Link a Jira issue to an asset object.
        :param object_id: ID of the object.
        :param issue_key: Jira issue key to link.
        :return: JSON response.
        """
        data = {"issueKey": issue_key}
        return self._request("POST", f"/object/{object_id}/link", json=data)

    def remove_linked_issue(self, object_id, issue_key):
        """
        Unlink a Jira issue from an asset object.
        :param object_id: ID of the object.
        :param issue_key: Jira issue key to unlink.
        :return: JSON response.
        """
        return self._request("DELETE", f"/object/{object_id}/unlink/{issue_key}")
