"""Test management module for creating and managing Xray tests."""

import requests
import json
import base64
from typing import Optional, List, Dict, Any
from .auth import XrayAuth
from .config import XrayConfig


def _get_test_issue_type(project_key: str) -> Dict[str, Any]:
    """
    Get the correct Test issue type for the project.
    Tries to find Xray's "Test" issue type, falls back to alternatives.
    
    Args:
        project_key: Jira project key
        
    Returns:
        dict: Issue type object (either {"name": "Test"} or {"id": "12345"})
    """
    # Jira API uses Basic Auth
    auth = base64.b64encode(
        f"{XrayConfig.JIRA_USER_EMAIL}:{XrayConfig.JIRA_API_TOKEN}".encode()
    ).decode()
    
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json"
    }
    
    # Get project metadata to find available issue types
    project_url = f"{XrayConfig.JIRA_BASE_URL}/rest/api/2/project/{project_key}"
    
    try:
        response = requests.get(project_url, headers=headers, timeout=30)
        response.raise_for_status()
        project_data = response.json()
        
        issue_types = project_data.get("issueTypes", [])
        
        # Try to find "Test" issue type (Xray)
        for issue_type in issue_types:
            if issue_type.get("name", "").lower() == "test":
                print(f"Found Xray Test issue type: {issue_type['name']} (ID: {issue_type['id']})")
                return {"id": issue_type["id"]}
        
        # If no Test type found, list available types
        available_types = [f"{it['name']} (ID: {it['id']})" for it in issue_types]
        print(f"WARNING: 'Test' issue type not found in project {project_key}")
        print(f"Available issue types: {', '.join(available_types)}")
        
        # Check if Xray is installed by looking for Test-related types
        for issue_type in issue_types:
            name = issue_type.get("name", "").lower()
            if "test" in name or "xray" in name:
                print(f"Using alternative test type: {issue_type['name']}")
                return {"id": issue_type["id"]}
        
        # If still not found, raise error with helpful message
        raise ValueError(
            f"No 'Test' issue type found in project {project_key}. "
            f"Please ensure Xray is installed or configure a custom test issue type. "
            f"Available types: {', '.join(available_types)}"
        )
        
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to get project issue types: {e}")
        # Fallback to using name (might fail but worth trying)
        return {"name": "Test"}


def _transition_test_to_completed(test_key: str) -> bool:
    """
    Transition a Test issue to 'Completed' or 'Done' status.
    In some Xray workflows, tests must be completed before they can be executed.
    
    Args:
        test_key: Jira Test issue key (e.g., "ABC-456")
        
    Returns:
        bool: True if successful or already in completed status
    """
    # Jira API uses Basic Auth
    auth = base64.b64encode(
        f"{XrayConfig.JIRA_USER_EMAIL}:{XrayConfig.JIRA_API_TOKEN}".encode()
    ).decode()
    
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json"
    }
    
    try:
        # Get current status
        issue_url = f"{XrayConfig.JIRA_BASE_URL}/rest/api/2/issue/{test_key}"
        response = requests.get(issue_url, headers=headers, timeout=30)
        response.raise_for_status()
        issue_data = response.json()
        
        current_status = issue_data.get("fields", {}).get("status", {}).get("name", "")
        print(f"Test {test_key} current status: {current_status}")
        
        # Check if already in completed status
        completed_statuses = ["completed", "done", "closed", "finished"]
        if any(status in current_status.lower() for status in completed_statuses):
            print(f"Test {test_key} already in completed status: {current_status}")
            return True
        
        # Get available transitions
        transitions_url = f"{XrayConfig.JIRA_BASE_URL}/rest/api/2/issue/{test_key}/transitions"
        response = requests.get(transitions_url, headers=headers, timeout=30)
        response.raise_for_status()
        transitions_data = response.json()
        
        available_transitions = transitions_data.get("transitions", [])
        
        # Debug: Print all available transitions
        print(f"Available transitions from '{current_status}':")
        for t in available_transitions:
            print(f"  - {t['name']} -> {t['to']['name']}")
        
        # Find a transition to completed status
        for transition in available_transitions:
            target_status = transition.get("to", {}).get("name", "").lower()
            if any(status in target_status for status in completed_statuses):
                transition_id = transition["id"]
                transition_name = transition["to"]["name"]
                
                print(f"Transitioning {test_key} from '{current_status}' to '{transition_name}'...")
                
                # Perform transition
                payload = {"transition": {"id": transition_id}}
                response = requests.post(
                    transitions_url,
                    headers=headers,
                    data=json.dumps(payload),
                    timeout=30
                )
                response.raise_for_status()
                
                print(f"✓ Test {test_key} transitioned to '{transition_name}'")
                return True
        
        # If current status is already an intermediate status (In Progress, In Review, etc.)
        # but no "Completed" transition found, it might need a different transition name
        # Try common completion transition names
        completion_transition_names = ["complete", "finish", "resolve", "close", "mark as done"]
        
        for transition in available_transitions:
            transition_name_lower = transition.get("name", "").lower()
            if any(name in transition_name_lower for name in completion_transition_names):
                transition_id = transition["id"]
                transition_name = transition["name"]
                target_status = transition["to"]["name"]
                
                print(f"Trying completion transition: '{transition_name}' -> '{target_status}'...")
                
                payload = {"transition": {"id": transition_id}}
                response = requests.post(
                    transitions_url,
                    headers=headers,
                    data=json.dumps(payload),
                    timeout=30
                )
                response.raise_for_status()
                
                print(f"✓ Test {test_key} transitioned via '{transition_name}' to '{target_status}'")
                return True
        
        # List available transitions for debugging
        transition_names = [f"{t['to']['name']}" for t in available_transitions]
        print(f"WARNING: Could not transition {test_key} to 'Completed' status")
        print(f"Current status: {current_status}")
        print(f"Available transitions: {', '.join(transition_names)}")
        print(f"Note: Tests may need to be manually transitioned to 'Completed' before execution")
        
        return False
        
    except requests.exceptions.RequestException as e:
        print(f"WARNING: Failed to transition test {test_key}: {e}")
        return False


def create_or_get_test(scenario_name: str, story_id: str) -> str:
    """
    Create a new Xray Test or retrieve existing one if it already exists.
    
    The test summary follows the format: "Automation | <Scenario Name>".
    If a test with this summary already exists in the project, it will be reused.
    
    Args:
        scenario_name: Name of the BDD scenario
        story_id: Jira Story ID (e.g., "ABC-123")
        
    Returns:
        str: Jira Test issue key (e.g., "ABC-456")
        
    Raises:
        requests.HTTPError: If API request fails
        
    Example:
        >>> test_key = create_or_get_test("User can login", "ABC-123")
        >>> print(test_key)  # "ABC-456"
    """
    test_summary = f"{XrayConfig.TEST_SUMMARY_PREFIX}{scenario_name}"
    
    # Search for existing test with this summary
    existing_test = _search_test_by_summary(test_summary)
    
    if existing_test:
        print(f"Found existing Xray Test: {existing_test}")
        return existing_test
    
    # Create new test if it doesn't exist
    print(f"Creating new Xray Test: {test_summary}")
    test_key = _create_test(test_summary, scenario_name, story_id)
    print(f"Created Xray Test: {test_key}")
    
    return test_key


def _search_test_by_summary(summary: str) -> Optional[str]:
    """
    Search for an existing test by summary using Jira JQL.
    
    Args:
        summary: Test summary to search for
        
    Returns:
        Optional[str]: Test issue key if found, None otherwise
    """
    jql = f'project = "{XrayConfig.XRAY_PROJECT_KEY}" AND issuetype = Test AND summary ~ "{summary}"'
    
    search_url = XrayConfig.get_jira_url("search")
    
    # Jira API uses Basic Auth with email and API token
    auth = base64.b64encode(
        f"{XrayConfig.JIRA_USER_EMAIL}:{XrayConfig.JIRA_API_TOKEN}".encode()
    ).decode()
    
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "jql": jql,
        "fields": ["key", "summary"],
        "maxResults": 1
    }
    
    try:
        response = requests.post(
            search_url,
            headers=headers,
            data=json.dumps(payload),
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        issues = data.get("issues", [])
        
        if issues:
            return issues[0]["key"]
        
        return None
        
    except requests.exceptions.RequestException as e:
        print(f"WARNING: Error searching for existing test: {str(e)}")
        return None


def _create_test(summary: str, scenario_name: str, story_id: str) -> str:
    """
    Create a new Xray Test issue in Jira.
    
    Args:
        summary: Test summary
        scenario_name: Scenario name for description
        story_id: Story ID to link to
        
    Returns:
        str: Created test issue key
    """
    create_url = XrayConfig.get_jira_url("issue")
    
    # Jira API uses Basic Auth
    auth = base64.b64encode(
        f"{XrayConfig.JIRA_USER_EMAIL}:{XrayConfig.JIRA_API_TOKEN}".encode()
    ).decode()
    
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json"
    }
    
    # Get the correct issue type for the project
    issue_type = _get_test_issue_type(XrayConfig.XRAY_PROJECT_KEY)
    
    payload = {
        "fields": {
            "project": {
                "key": XrayConfig.XRAY_PROJECT_KEY
            },
            "summary": summary,
            "description": f"Automated test for scenario: {scenario_name}",
            "issuetype": issue_type  # Use dynamically detected issue type
        }
    }
    
    try:
        response = requests.post(
            create_url,
            headers=headers,
            data=json.dumps(payload),
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        test_key = data["key"]
        
        print(f"Created test: {test_key}")
        
        # Transition test to completed status (required for test execution in some workflows)
        _transition_test_to_completed(test_key)
        
        # Link the test to the story
        if story_id:
            link_test_to_story(test_key, story_id)
        
        return test_key
        
    except requests.exceptions.HTTPError as e:
        error_msg = f"Failed to create test: {e.response.status_code}"
        try:
            error_detail = e.response.json()
            error_msg += f" - {error_detail}"
        except:
            error_msg += f" - {e.response.text}"
        
        print(f"ERROR: {error_msg}")
        raise


def upload_test_steps(test_key: str, steps: List[Dict[str, Any]]) -> bool:
    """
    Upload BDD scenario steps to an Xray Test using GraphQL API.
    
    Args:
        test_key: Jira Test issue key (e.g., "ABC-456")
        steps: List of step dictionaries with 'action', 'data', and 'result' fields
               For BDD steps: action = "Given/When/Then <step text>"
               
    Returns:
        bool: True if successful, False otherwise
        
    Example:
        >>> steps = [
        ...     {"action": "Given user is on login page", "data": "", "result": ""},
        ...     {"action": "When user enters valid credentials", "data": "", "result": ""},
        ...     {"action": "Then user is logged in", "data": "", "result": "User sees dashboard"}
        ... ]
        >>> upload_test_steps("ABC-456", steps)
    """
    try:
        from integrations.xray.auth import authenticate_xray
        
        # Get the Jira internal issue ID (not the key)
        issue_id = _get_jira_issue_id(test_key)
        if not issue_id:
            print(f"WARNING: Could not get internal ID for {test_key}")
            return False
        
        # Get authentication token
        token = authenticate_xray()
        
        # Xray GraphQL endpoint
        graphql_url = "https://xray.cloud.getxray.app/api/v2/graphql"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        print(f"Uploading {len(steps)} test steps to {test_key} (ID: {issue_id}) via GraphQL...")
        
        # Step 1: Set test type to Manual (required for manual test steps)
        update_type_mutation = """
        mutation {
            updateTestType(issueId: "%s", testType: {name: "Manual"}) {
                issueId
            }
        }
        """ % issue_id
        
        response = requests.post(
            graphql_url,
            headers=headers,
            data=json.dumps({"query": update_type_mutation}),
            timeout=30
        )
        response.raise_for_status()
        
        # Step 2: Remove all existing test steps
        remove_steps_mutation = """
        mutation {
            removeAllTestSteps(issueId: "%s") {
                issueId
            }
        }
        """ % issue_id
        
        response = requests.post(
            graphql_url,
            headers=headers,
            data=json.dumps({"query": remove_steps_mutation}),
            timeout=30
        )
        # Ignore errors if no steps exist
        
        # Step 3: Add each test step
        for step in steps:
            action = step.get('action', '').replace('"', '\\"').replace('\n', '\\n')
            data = step.get('data', '').replace('"', '\\"').replace('\n', '\\n')
            result = step.get('result', '').replace('"', '\\"').replace('\n', '\\n')
            
            add_step_mutation = """
            mutation {
                addTestStep(
                    issueId: "%s",
                    step: {
                        action: "%s"
                        data: "%s"
                        result: "%s"
                    }
                ) {
                    id
                }
            }
            """ % (issue_id, action, data, result)
            
            response = requests.post(
                graphql_url,
                headers=headers,
                data=json.dumps({"query": add_step_mutation}),
                timeout=30
            )
            response.raise_for_status()
            
            result_data = response.json()
            if 'errors' in result_data:
                error_msg = result_data['errors'][0].get('message', 'Unknown error')
                print(f"WARNING: Failed to add step: {error_msg}")
                return False
        
        print(f"Successfully uploaded {len(steps)} test steps to {test_key}")
        return True
        
    except requests.exceptions.HTTPError as e:
        error_msg = f"Failed to upload test steps: {e.response.status_code}"
        try:
            error_detail = e.response.json()
            error_msg += f" - {error_detail}"
        except:
            error_msg += f" - {e.response.text}"
        
        print(f"WARNING: {error_msg}")
        return False
        
    except requests.exceptions.RequestException as e:
        print(f"WARNING: Network error uploading test steps: {str(e)}")
        return False


def _get_jira_issue_id(test_key: str) -> Optional[str]:
    """
    Get the internal Jira issue ID from the issue key.
    
    Args:
        test_key: Jira Test issue key (e.g., "ABC-456")
        
    Returns:
        Optional[str]: Internal issue ID or None if not found
    """
    issue_url = XrayConfig.get_jira_url(f"issue/{test_key}")
    
    # Jira API uses Basic Auth
    auth = base64.b64encode(
        f"{XrayConfig.JIRA_USER_EMAIL}:{XrayConfig.JIRA_API_TOKEN}".encode()
    ).decode()
    
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(issue_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        return data.get("id")
        
    except requests.exceptions.RequestException as e:
        print(f"WARNING: Error getting Jira issue ID: {str(e)}")
        return None


def _get_test_internal_id(test_key: str) -> Optional[str]:
    """
    Get the internal Xray test ID from the issue key.
    
    Args:
        test_key: Jira Test issue key (e.g., "ABC-456")
        
    Returns:
        Optional[str]: Internal test ID or None if not found
    """
    # Use Xray API to get test details
    test_url = XrayConfig.get_xray_url(f"test?keys={test_key}")
    
    headers = XrayAuth.get_auth_headers()
    
    try:
        response = requests.get(test_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if isinstance(data, list) and len(data) > 0:
            return data[0].get("id")
        elif isinstance(data, dict):
            return data.get("id")
        
        return None
        
    except requests.exceptions.RequestException as e:
        print(f"WARNING: Error getting test internal ID: {str(e)}")
        return None


def link_test_to_story(test_key: str, story_id: str) -> bool:
    """
    Link an Xray Test to a Jira Story using 'tests' relationship.
    
    The link type is "Tests" where the Test "tests" the Story.
    
    Args:
        test_key: Jira Test issue key (e.g., "ABC-456")
        story_id: Jira Story issue key (e.g., "ABC-123")
        
    Returns:
        bool: True if successful, False otherwise
        
    Example:
        >>> link_test_to_story("ABC-456", "ABC-123")
    """
    link_url = XrayConfig.get_jira_url("issueLink")
    
    # Jira API uses Basic Auth
    auth = base64.b64encode(
        f"{XrayConfig.JIRA_USER_EMAIL}:{XrayConfig.JIRA_API_TOKEN}".encode()
    ).decode()
    
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "type": {
            "name": "Test"
        },
        "inwardIssue": {
            "key": story_id  # Story is tested by Test
        },
        "outwardIssue": {
            "key": test_key  # Test tests the Story
        }
    }
    
    try:
        print(f"Linking Test {test_key} to Story {story_id}...")
        response = requests.post(
            link_url,
            headers=headers,
            data=json.dumps(payload),
            timeout=30
        )
        response.raise_for_status()
        
        print(f"Successfully linked {test_key} to {story_id}")
        return True
        
    except requests.exceptions.HTTPError as e:
        # Check if link already exists (400 error with specific message)
        if e.response.status_code == 400:
            try:
                error_detail = e.response.json()
                if "already exists" in str(error_detail).lower():
                    print(f"Link between {test_key} and {story_id} already exists")
                    return True
            except:
                pass
        
        error_msg = f"Failed to link test to story: {e.response.status_code}"
        try:
            error_detail = e.response.json()
            error_msg += f" - {error_detail}"
        except:
            error_msg += f" - {e.response.text}"
        
        print(f"ERROR: {error_msg}")
        return False
        
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Network error linking test to story: {str(e)}")
        return False


def get_test_by_key(test_key: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve an Xray test by its key.
    
    Args:
        test_key: Test issue key (e.g., "XSP-123")
        
    Returns:
        Dict with test details if found, None otherwise
    """
    try:
        test_url = XrayConfig.get_jira_url(f"issue/{test_key}")
        
        # Jira API uses Basic Auth
        auth = base64.b64encode(
            f"{XrayConfig.JIRA_USER_EMAIL}:{XrayConfig.JIRA_API_TOKEN}".encode()
        ).decode()
        
        headers = {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(
            test_url,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return None
        else:
            response.raise_for_status()
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"WARNING: Error retrieving test {test_key}: {str(e)}")
        return None
