"""Configuration module for Xray Cloud integration."""

import os
from typing import Optional


class XrayConfig:
    """Configuration container for Xray Cloud API settings."""
    
    # Xray Cloud API endpoints
    XRAY_AUTH_URL = "https://xray.cloud.getxray.app/api/v2/authenticate"
    XRAY_API_BASE_URL = "https://xray.cloud.getxray.app/api/v2"
    
    # Jira Cloud API endpoint
    JIRA_BASE_URL = os.getenv("JIRA_BASE_URL", "")  # e.g., https://yourcompany.atlassian.net
    
    # Authentication credentials
    XRAY_CLIENT_ID = os.getenv("XRAY_CLIENT_ID", "")
    XRAY_CLIENT_SECRET = os.getenv("XRAY_CLIENT_SECRET", "")
    
    # Jira credentials (for linking tests to stories)
    JIRA_USER_EMAIL = os.getenv("JIRA_USER_EMAIL", "")
    JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN", "")
    
    # Xray project configuration
    XRAY_PROJECT_KEY = os.getenv("XRAY_PROJECT_KEY", "")  # e.g., "ABC"
    
    # Test configuration
    TEST_SUMMARY_PREFIX = "Automation | "
    
    # Workflow status configuration
    TEST_TARGET_STATUS = os.getenv("TEST_TARGET_STATUS", "Non GXP")
    TEST_EXECUTION_READY_STATUSES = os.getenv("TEST_EXECUTION_READY_STATUSES", "In Progress,Open")
    TEST_BLOCKED_STATUSES = os.getenv("TEST_BLOCKED_STATUSES", "Completed,Done,Closed,Finished")
    
    @classmethod
    def get_execution_ready_statuses(cls) -> list:
        """Get list of execution-ready statuses including target status."""
        statuses = [cls.TEST_TARGET_STATUS]
        if cls.TEST_EXECUTION_READY_STATUSES:
            statuses.extend([s.strip() for s in cls.TEST_EXECUTION_READY_STATUSES.split(',')])
        return [s.lower() for s in statuses if s]
    
    @classmethod
    def get_blocked_statuses(cls) -> list:
        """Get list of blocked statuses that prevent execution."""
        if cls.TEST_BLOCKED_STATUSES:
            return [s.strip().lower() for s in cls.TEST_BLOCKED_STATUSES.split(',') if s.strip()]
        return []
    
    @classmethod
    def validate(cls) -> bool:
        """
        Validate that all required configuration values are set.
        
        Returns:
            bool: True if all required values are present, False otherwise
        """
        required_fields = [
            ("XRAY_CLIENT_ID", cls.XRAY_CLIENT_ID),
            ("XRAY_CLIENT_SECRET", cls.XRAY_CLIENT_SECRET),
            ("JIRA_BASE_URL", cls.JIRA_BASE_URL),
            ("JIRA_USER_EMAIL", cls.JIRA_USER_EMAIL),
            ("JIRA_API_TOKEN", cls.JIRA_API_TOKEN),
            ("XRAY_PROJECT_KEY", cls.XRAY_PROJECT_KEY)
        ]
        
        missing_fields = [name for name, value in required_fields if not value]
        
        if missing_fields:
            print(f"ERROR: Missing required environment variables: {', '.join(missing_fields)}")
            return False
        
        return True
    
    @classmethod
    def get_jira_url(cls, path: str) -> str:
        """
        Construct full Jira API URL.
        
        Args:
            path: API endpoint path
            
        Returns:
            str: Full URL
        """
        return f"{cls.JIRA_BASE_URL.rstrip('/')}/rest/api/2/{path.lstrip('/')}"
    
    @classmethod
    def get_xray_url(cls, path: str) -> str:
        """
        Construct full Xray API URL.
        
        Args:
            path: API endpoint path
            
        Returns:
            str: Full URL
        """
        return f"{cls.XRAY_API_BASE_URL.rstrip('/')}/{path.lstrip('/')}"
