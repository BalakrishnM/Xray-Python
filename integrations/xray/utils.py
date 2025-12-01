"""Utility functions for Xray integration."""

import re
from typing import Optional


def extract_story_id_from_text(text: str) -> Optional[str]:
    """
    Extract Jira Story ID from text.
    
    Supports formats:
    - @Story: ABC-123
    - @Story:ABC-123
    - Story: ABC-123
    
    Args:
        text: Text to search
        
    Returns:
        Optional[str]: Story ID if found, None otherwise
    """
    if not text:
        return None
    
    pattern = r'@?Story:\s*([A-Z]+-\d+)'
    match = re.search(pattern, text, re.IGNORECASE)
    
    if match:
        return match.group(1)
    
    return None


def format_test_summary(scenario_name: str, prefix: str = "Automation | ") -> str:
    """
    Format test summary for Xray.
    
    Args:
        scenario_name: Scenario name
        prefix: Prefix to add (default: "Automation | ")
        
    Returns:
        str: Formatted summary
    """
    return f"{prefix}{scenario_name}"


def parse_robot_status(robot_status: str) -> str:
    """
    Convert Robot Framework status to Xray status.
    
    Args:
        robot_status: Robot Framework status (PASS, FAIL, SKIP)
        
    Returns:
        str: Xray status (PASSED, FAILED, ABORTED)
    """
    status_map = {
        'PASS': 'PASSED',
        'FAIL': 'FAILED',
        'SKIP': 'ABORTED',
        'NOT RUN': 'TODO'
    }
    
    return status_map.get(robot_status.upper(), 'FAILED')


def validate_issue_key(issue_key: str) -> bool:
    """
    Validate Jira issue key format.
    
    Args:
        issue_key: Issue key to validate (e.g., "ABC-123")
        
    Returns:
        bool: True if valid format
    """
    if not issue_key:
        return False
    
    pattern = r'^[A-Z]+-\d+$'
    return bool(re.match(pattern, issue_key))
