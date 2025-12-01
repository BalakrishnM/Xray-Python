"""
Execution result management for Xray Cloud using GraphQL API.

This module handles creating Test Executions and updating test run results
with proper step-level details, actual results, and attachments.
"""

import os
import requests
import json
import base64
from typing import List, Dict, Any, Optional
from .auth import authenticate_xray
from .config import XrayConfig
from .test_manager import _get_jira_issue_id


def create_test_execution_graphql(test_issue_ids: List[str], summary: str, description: str = "") -> Optional[Dict]:
    """
    Create a Test Execution using GraphQL API.
    
    Args:
        test_issue_ids: List of test issue IDs (internal Jira IDs, not keys)
        summary: Summary for the Test Execution
        description: Optional description
        
    Returns:
        Dict with testExecutionId and issueKey if successful, None otherwise
    """
    try:
        token = authenticate_xray()
        graphql_url = "https://xray.cloud.getxray.app/api/v2/graphql"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Format test IDs as JSON array
        test_ids_str = json.dumps(test_issue_ids)
        
        mutation = f"""
        mutation {{
            createTestExecution(
                testIssueIds: {test_ids_str}
                jira: {{
                    fields: {{
                        summary: "{summary}"
                        description: "{description}"
                        project: {{ key: "{XrayConfig.XRAY_PROJECT_KEY}" }}
                    }}
                }}
            ) {{
                testExecution {{
                    issueId
                    jira(fields: ["key"])
                }}
                warnings
            }}
        }}
        """
        
        payload = {"query": mutation}
        
        print(f"Creating Test Execution with {len(test_issue_ids)} tests...")
        response = requests.post(graphql_url, headers=headers, data=json.dumps(payload), timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        if 'errors' in result:
            print(f"GraphQL errors: {result['errors']}")
            return None
        
        test_exec = result['data']['createTestExecution']['testExecution']
        test_exec_key = test_exec['jira']['key']
        test_exec_id = test_exec['issueId']
        
        print(f"✓ Created Test Execution: {test_exec_key} (ID: {test_exec_id})")
        
        return {
            'testExecutionId': test_exec_id,
            'issueKey': test_exec_key
        }
        
    except Exception as e:
        print(f"ERROR creating Test Execution: {str(e)}")
        return None


def get_test_runs(test_execution_id: str) -> List[Dict]:
    """
    Get test runs from a Test Execution.
    
    Args:
        test_execution_id: Internal ID of the Test Execution
        
    Returns:
        List of test run dictionaries with id, test info, and steps
    """
    try:
        token = authenticate_xray()
        graphql_url = "https://xray.cloud.getxray.app/api/v2/graphql"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        query = f"""
        query {{
            getTestExecution(issueId: "{test_execution_id}") {{
                issueId
                tests(limit: 100) {{
                    results {{
                        issueId
                        jira(fields: ["key", "summary"])
                        testType {{
                            name
                        }}
                        steps {{
                            id
                            action
                            data
                            result
                        }}
                        testRuns(limit: 1) {{
                            results {{
                                id
                                status {{
                                    name
                                }}
                                steps {{
                                    id
                                    status {{
                                        name
                                    }}
                                    comment
                                }}
                            }}
                        }}
                    }}
                }}
            }}
        }}
        """
        
        payload = {"query": query}
        
        response = requests.post(graphql_url, headers=headers, data=json.dumps(payload), timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        if 'errors' in result:
            print(f"GraphQL errors: {result['errors']}")
            return []
        
        test_runs = []
        tests = result['data']['getTestExecution']['tests']['results']
        
        for test in tests:
            test_run_list = test.get('testRuns', {}).get('results', [])
            if test_run_list:
                test_run = test_run_list[0]
                test_runs.append({
                    'testRunId': test_run['id'],
                    'testKey': test['jira']['key'],
                    'testIssueId': test['issueId'],
                    'testSteps': test.get('steps', []),
                    'testRunSteps': test_run.get('steps', []),
                    'currentStatus': test_run['status']['name']
                })
        
        return test_runs
        
    except Exception as e:
        print(f"ERROR getting test runs: {str(e)}")
        return []


def update_test_run_status(test_run_id: str, status: str, comment: str = "") -> bool:
    """
    Update the overall status of a test run.
    
    Args:
        test_run_id: Test run ID
        status: Status (PASS, FAIL, EXECUTING, TODO, ABORTED)
        comment: Optional comment
        
    Returns:
        True if successful
    """
    try:
        token = authenticate_xray()
        graphql_url = "https://xray.cloud.getxray.app/api/v2/graphql"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        comment_escaped = comment.replace('"', '\\"').replace('\n', '\\n')
        
        mutation = f"""
        mutation {{
            updateTestRunStatus(
                id: "{test_run_id}"
                status: "{status}"
            )
        }}
        """
        
        # Also update comment if provided
        if comment:
            comment_mutation = f"""
            mutation {{
                updateTestRunComment(
                    id: "{test_run_id}"
                    comment: "{comment_escaped}"
                )
            }}
            """
            
            payload = {"query": comment_mutation}
            requests.post(graphql_url, headers=headers, data=json.dumps(payload), timeout=30)
        
        payload = {"query": mutation}
        response = requests.post(graphql_url, headers=headers, data=json.dumps(payload), timeout=30)
        response.raise_for_status()
        
        return True
        
    except Exception as e:
        print(f"WARNING: Failed to update test run status: {str(e)}")
        return False


def update_test_run_step(test_run_id: str, step_id: str, status: str, actual_result: str = "") -> bool:
    """
    Update a specific test run step with status and actual result.
    
    Args:
        test_run_id: Test run ID  
        step_id: Test run step ID
        status: Status (PASSED, FAILED, EXECUTING, TODO)
        actual_result: Actual result text
        
    Returns:
        True if successful
    """
    try:
        token = authenticate_xray()
        graphql_url = "https://xray.cloud.getxray.app/api/v2/graphql"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Map common status values to Xray step status values
        status_map = {
            'PASS': 'PASSED',
            'PASSED': 'PASSED',
            'FAIL': 'FAILED',
            'FAILED': 'FAILED',
            'TODO': 'TODO',
            'EXECUTING': 'EXECUTING'
        }
        
        # Normalize status
        normalized_status = status_map.get(status, status)
        
        actual_escaped = actual_result.replace('"', '\\"').replace('\n', '\\n')
        
        mutation = f"""
        mutation {{
            updateTestRunStep(
                testRunId: "{test_run_id}"
                stepId: "{step_id}"
                updateData: {{
                    status: "{normalized_status}"
                    actualResult: "{actual_escaped}"
                }}
            ) {{
                warnings
            }}
        }}
        """
        
        payload = {"query": mutation}
        response = requests.post(graphql_url, headers=headers, data=json.dumps(payload), timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        if 'errors' in result:
            print(f"  WARNING: Error updating step {step_id}: {result['errors']}")
            return False
            
        return True
        
    except Exception as e:
        print(f"WARNING: Failed to update test run step: {str(e)}")
        return False
        response.raise_for_status()
        
        result = response.json()
        
        if 'errors' in result:
            print(f"  WARNING: Error updating step: {result['errors']}")
            return False
            
        return True
        
    except Exception as e:
        print(f"  WARNING: Failed to update test run step: {str(e)}")
        return False


def add_evidence_to_test_run_step_batch(test_run_id: str, step_id: str, file_paths: list) -> bool:
    """
    Add multiple evidence/attachments to a specific test run step in a single API call.
    
    Args:
        test_run_id: Test run ID
        step_id: Test run step ID
        file_paths: List of file paths to attach
        
    Returns:
        True if successful
    """
    try:
        token = authenticate_xray()
        graphql_url = "https://xray.cloud.getxray.app/api/v2/graphql"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        import mimetypes
        
        # Build evidence array for all files
        evidence_items = []
        for file_path in file_paths:
            # Read file and encode to base64
            with open(file_path, 'rb') as f:
                file_data = base64.b64encode(f.read()).decode()
            
            filename = os.path.basename(file_path)
            filename_escaped = filename.replace('"', '\\\\"').replace('\\n', ' ')
            
            # Determine MIME type
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = "application/octet-stream"
            
            evidence_obj = '''{{
                filename: "{}"
                mimeType: "{}"
                data: "{}"
            }}'''.format(filename_escaped, mime_type, file_data)
            evidence_items.append(evidence_obj)
        
        evidence_array = ',\\n'.join(evidence_items)
        
        mutation = """
        mutation {{
            addEvidenceToTestRunStep(
                testRunId: "{}"
                stepId: "{}"
                evidence: [
                    {}
                ]
            ) {{
                addedEvidence
                warnings
            }}
        }}
        """.format(test_run_id, step_id, evidence_array)
        
        payload = {"query": mutation}
        response = requests.post(graphql_url, headers=headers, data=json.dumps(payload), timeout=120)
        response.raise_for_status()
        
        result = response.json()
        
        if 'errors' in result:
            print(f"  WARNING: Error adding step evidence: {result['errors']}")
            return False
            
        return True
        
    except Exception as e:
        print(f"  WARNING: Failed to add step evidence: {str(e)}")
        return False


def add_evidence_to_test_run_step(test_run_id: str, step_id: str, file_path: str) -> bool:
    """
    Add evidence/attachment to a specific test run step.
    
    Args:
        test_run_id: Test run ID
        step_id: Test run step ID
        file_path: Path to the file to attach
        
    Returns:
        True if successful
    """
    # Use batch function with single file
    return add_evidence_to_test_run_step_batch(test_run_id, step_id, [file_path])


def add_attachment_to_test_run(test_run_id: str, file_path: str) -> bool:
    """
    Add an attachment/evidence to a test run.
    
    Args:
        test_run_id: Test run ID
        file_path: Path to the file to attach
        
    Returns:
        True if successful
    """
    try:
        token = authenticate_xray()
        graphql_url = "https://xray.cloud.getxray.app/api/v2/graphql"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Read file and encode to base64
        with open(file_path, 'rb') as f:
            file_data = base64.b64encode(f.read()).decode()
        
        import os
        import mimetypes
        filename = os.path.basename(file_path)
        filename_escaped = filename.replace('"', '\\"')
        
        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = "application/octet-stream"
        
        mutation = f"""
        mutation {{
            addEvidenceToTestRun(
                id: "{test_run_id}"
                evidence: [{{
                    filename: "{filename_escaped}"
                    mimeType: "{mime_type}"
                    data: "{file_data}"
                }}]
            ) {{
                addedEvidence
                warnings
            }}
        }}
        """
        
        payload = {"query": mutation}
        response = requests.post(graphql_url, headers=headers, data=json.dumps(payload), timeout=60)
        response.raise_for_status()
        
        result = response.json()
        
        if 'errors' in result:
            print(f"  WARNING: Error adding attachment: {result['errors']}")
            return False
            
        return True
        
    except Exception as e:
        print(f"  WARNING: Failed to add attachment: {str(e)}")
        return False


def update_execution_results(test_results: List[Dict], attachments: List[str] = None) -> Optional[str]:
    """
    Update test execution results with proper step-level details.
    
    Args:
        test_results: List of test result dictionaries with:
            - test_key: Test issue key
            - status: Overall status (PASSED/FAILED/ABORTED)
            - actual_result: Actual result message
            - step_results: Optional list of step results
        attachments: Optional list of file paths to attach
        
    Returns:
        Test Execution key if successful, None otherwise
    """
    if not test_results:
        print("No test results to upload")
        return None
    
    try:
        # Get internal IDs for all tests
        test_issue_ids = []
        test_key_to_id = {}
        
        for test_result in test_results:
            test_key = test_result['test_key']
            issue_id = _get_jira_issue_id(test_key)
            if issue_id:
                test_issue_ids.append(issue_id)
                test_key_to_id[test_key] = issue_id
        
        if not test_issue_ids:
            print("ERROR: Could not get issue IDs for tests")
            return None
        
        # Create Test Execution
        summary = f"Automated Test Execution - {len(test_results)} tests"
        description = f"Execution of {len(test_results)} automated tests"
        
        test_exec_result = create_test_execution_graphql(test_issue_ids, summary, description)
        
        if not test_exec_result:
            print("ERROR: Failed to create Test Execution")
            return None
        
        test_exec_id = test_exec_result['testExecutionId']
        test_exec_key = test_exec_result['issueKey']
        
        # Get test runs
        print(f"\nRetrieving test runs from {test_exec_key}...")
        test_runs = get_test_runs(test_exec_id)
        
        if not test_runs:
            print("WARNING: No test runs found")
            return test_exec_key
        
        # Update each test run with results
        print(f"\nUpdating {len(test_runs)} test run results...")
        
        for test_run in test_runs:
            test_key = test_run['testKey']
            test_run_id = test_run['testRunId']
            
            # Find matching test result
            test_result = next((tr for tr in test_results if tr['test_key'] == test_key), None)
            
            if not test_result:
                print(f"  ⚠️  No result found for {test_key}")
                continue
            
            status = test_result['status']
            actual_result = test_result.get('actual_result', f'Test {status}')
            
            print(f"\n  Updating {test_key} (Status: {status})...")
            
            # Update overall test run status
            update_test_run_status(test_run_id, status, actual_result)
            
            # Update each test step if step results are provided
            step_results = test_result.get('step_results', [])
            test_run_steps = test_run.get('testRunSteps', [])
            
            if step_results and test_run_steps:
                print(f"    Updating {len(test_run_steps)} step results...")
                
                for idx, test_run_step in enumerate(test_run_steps):
                    step_id = test_run_step['id']
                    
                    # Get corresponding step result (if available)
                    if idx < len(step_results):
                        step_result = step_results[idx]
                        step_status = step_result.get('status', status)
                        step_actual = step_result.get('actual_result', 'Step executed')
                    else:
                        # Default to overall test status
                        step_status = status
                        step_actual = f'Step {idx + 1} - {status}'
                    
                    update_test_run_step(test_run_id, step_id, step_status, step_actual)
            
            # Add test-specific screenshots to steps if provided
            test_screenshots = test_result.get('screenshots', [])
            if test_screenshots:
                print(f"    Adding {len(test_screenshots)} screenshots to {test_key}...")
                
                # Group screenshots by step_index for batch upload
                screenshots_by_step = {}
                screenshots_no_step = []
                
                for screenshot_info in test_screenshots:
                    screenshot_path = screenshot_info.get('path') if isinstance(screenshot_info, dict) else screenshot_info
                    step_index = screenshot_info.get('step_index') if isinstance(screenshot_info, dict) else None
                    
                    if not os.path.exists(screenshot_path):
                        print(f"      WARNING: Screenshot not found: {screenshot_path}")
                        continue
                    
                    if step_index is not None and step_index < len(test_run_steps):
                        if step_index not in screenshots_by_step:
                            screenshots_by_step[step_index] = []
                        screenshots_by_step[step_index].append(screenshot_path)
                    else:
                        screenshots_no_step.append(screenshot_path)
                
                # Batch upload screenshots per step
                for step_index, screenshot_paths in screenshots_by_step.items():
                    step_id = test_run_steps[step_index]['id']
                    if add_evidence_to_test_run_step_batch(test_run_id, step_id, screenshot_paths):
                        print(f"      ✓ Attached {len(screenshot_paths)} screenshot(s) to step {step_index + 1}")
                
                # Upload screenshots without step mapping to test run
                for screenshot_path in screenshots_no_step:
                    if add_attachment_to_test_run(test_run_id, screenshot_path):
                        print(f"      ✓ Attached to test run")
            
            print(f"    ✓ Updated {test_key}")
        
        # Add attachments if provided
        if attachments and test_runs:
            print(f"\n  Adding {len(attachments)} attachments...")
            
            # Add attachments to the first test run as an example
            # In practice, you might want to add to all or specific test runs
            first_test_run_id = test_runs[0]['testRunId']
            
            for attachment in attachments:
                add_attachment_to_test_run(first_test_run_id, attachment)
        
        print(f"\n✓ Successfully updated execution results in {test_exec_key}")
        return test_exec_key
        
    except Exception as e:
        print(f"\nERROR updating execution results: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
