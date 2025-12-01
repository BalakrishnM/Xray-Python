"""
Example CI execution script for Robot Framework with Xray Cloud integration.

This script demonstrates how to run Robot Framework tests with Xray integration
for automated test management and execution reporting.
"""

import os
import sys
from pathlib import Path
from robot import run as robot_run

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_file = project_root / '.env'
    if env_file.exists():
        load_dotenv(env_file)
        print(f"Loaded environment variables from {env_file}")
except ImportError:
    print("WARNING: python-dotenv not installed. Install with: pip install python-dotenv")
except Exception as e:
    print(f"WARNING: Could not load .env file: {e}")


def setup_environment():
    """
    Set up environment variables for Xray integration.
    
    In production, these should be set in your CI/CD pipeline or environment.
    """
    # Only set if not already configured
    if not os.getenv("XRAY_CLIENT_ID"):
        print("WARNING: Xray environment variables not set. Please configure:")
        print("  - XRAY_CLIENT_ID")
        print("  - XRAY_CLIENT_SECRET")
        print("  - JIRA_BASE_URL")
        print("  - JIRA_USER_EMAIL")
        print("  - JIRA_API_TOKEN")
        print("  - XRAY_PROJECT_KEY")
        print("\nTests will run but results won't be uploaded to Xray.")
    
    # Example (for local testing only - use secure methods in production):
    # os.environ["XRAY_CLIENT_ID"] = "your-client-id"
    # os.environ["XRAY_CLIENT_SECRET"] = "your-client-secret"
    # os.environ["JIRA_BASE_URL"] = "https://yourcompany.atlassian.net"
    # os.environ["JIRA_USER_EMAIL"] = "your-email@company.com"
    # os.environ["JIRA_API_TOKEN"] = "your-jira-api-token"
    # os.environ["XRAY_PROJECT_KEY"] = "ABC"


def run_tests_with_xray(test_path="tests", output_dir="output", tags=None):
    """
    Run Robot Framework tests with Xray listener.
    
    Args:
        test_path: Path to test files or directory
        output_dir: Output directory for test results
        tags: Optional list of tags to filter tests
        
    Returns:
        int: Exit code (0 = all tests passed, non-zero = failures)
    """
    print("="*80)
    print("Starting Robot Framework test execution with Xray Cloud integration")
    print("="*80)
    
    # Prepare Robot Framework arguments as keyword arguments
    robot_kwargs = {
        'outputdir': output_dir,
        'listener': 'integrations.xray.XrayListener',
        'loglevel': 'INFO'
    }
    
    # Add tag filtering if specified
    if tags:
        robot_kwargs['include'] = tags
    
    # Run tests
    try:
        exit_code = robot_run(test_path, **robot_kwargs)
        
        print("\n" + "="*80)
        if exit_code == 0:
            print("All tests PASSED")
        else:
            print(f"Tests completed with exit code: {exit_code}")
        print("="*80)
        
        return exit_code
        
    except Exception as e:
        print(f"\nERROR: Test execution failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    """Main entry point for CI execution."""
    # Set up environment
    setup_environment()
    
    # Determine test path from command line or use default
    test_path = sys.argv[1] if len(sys.argv) > 1 else "tests"
    
    # Run tests with Xray integration
    exit_code = run_tests_with_xray(test_path=test_path)
    
    # Exit with appropriate code for CI/CD
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
