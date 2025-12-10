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

# Import browser options fixer to prevent 'add_argument' errors
try:
    from libraries import BrowserOptionsFixer
except ImportError:
    print("Note: BrowserOptionsFixer not available")

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


def run_tests_with_xray(test_path="tests", output_dir="output", tags=None, skip_xray=False, browser=None, browser_library=None):
    """
    Run Robot Framework tests with optional Xray listener.
    
    Args:
        test_path: Path to test files or directory
        output_dir: Output directory for test results
        tags: Optional list of tags to filter tests (e.g., ['smoke', 'regression'])
        skip_xray: If True, skip Xray integration (only run tests)
        browser: Browser to use for tests (e.g., 'chrome', 'firefox', 'edge')
        browser_library: Path to custom browser support library (e.g., 'tests/Web/Library/BrowserSupport.py')
        
    Returns:
        int: Exit code (0 = all tests passed, non-zero = failures)
        
    Examples:
        # Run all tests with Xray
        run_tests_with_xray()
        
        # Run only smoke tests with Xray
        run_tests_with_xray(tags=['smoke'])
        
        # Run tests in Firefox
        run_tests_with_xray(browser='firefox')
        
        # Run tests without Xray integration
        run_tests_with_xray(skip_xray=True)
        
        # Run regression tests in Edge without Xray
        run_tests_with_xray(tags=['regression'], browser='edge', skip_xray=True)
        
        # Run with custom browser library
        run_tests_with_xray(browser='chrome', browser_library='tests/Web/Library/BrowserSupport.py')
    """
    print("="*80)
    if skip_xray:
        print("Starting Robot Framework test execution (Xray integration disabled)")
    else:
        print("Starting Robot Framework test execution with Xray Cloud integration")
    
    if browser:
        print(f"Browser: {browser.capitalize()}")
    
    if browser_library:
        print(f"Using browser library: {browser_library}")
    
    print("="*80)
    
    # Set environment variable to skip Xray if requested
    if skip_xray:
        os.environ["SKIP_XRAY"] = "true"
    
    # Prepare Robot Framework arguments as keyword arguments
    robot_kwargs = {
        'outputdir': output_dir,
        'loglevel': 'INFO'
    }
    
    # Add custom browser library if specified
    if browser_library:
        # Add the library path to Python path for imports
        library_dir = Path(browser_library).parent
        if library_dir not in sys.path:
            sys.path.insert(0, str(library_dir))
        
        # Add as library to Robot Framework
        robot_kwargs['pythonpath'] = str(library_dir)
    
    # Build listener list
    listeners = []
    
    # Add BrowserOptionsFixer listener to fix string options issues
    listeners.append('libraries.BrowserOptionsFixer.BrowserOptionsFixer')
    
    # Add Xray listener unless skip_xray is True
    if not skip_xray:
        listeners.append('integrations.xray.XrayListener')
    
    # Set listeners
    if listeners:
        robot_kwargs['listener'] = listeners
    
    # Add tag filtering if specified
    if tags:
        if isinstance(tags, list):
            robot_kwargs['include'] = tags
        else:
            robot_kwargs['include'] = [tags]
    
    # Add browser variables - always set defaults or use specified browser
    if browser:
        # Capitalize browser name for Robot Framework
        browser_value = browser.capitalize()
    else:
        browser_value = 'Chrome'
    
    robot_kwargs['variable'] = [
        f'BROWSER:{browser_value}',
        f'global_browser_options:{browser_value}',
        f'DEFAULT_BROWSER:{browser_value}'
    ]
    
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
    """
    Main entry point for CI execution.
    
    Command line arguments:
        python run.py [test_path] [--tags tag1,tag2] [--skip-xray] [--browser chrome]
        
    Examples:
        python run.py tests/
        python run.py tests/ --tags smoke
        python run.py tests/ --browser firefox
        python run.py tests/ -b chrome -t smoke
        python run.py tests/ --tags smoke,regression --skip-xray
        python run.py tests/ -b edge --skip-xray
    """
    # Set up environment
    setup_environment()
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Run Robot Framework tests with optional Xray integration')
    parser.add_argument('test_path', nargs='?', default='tests', help='Path to test files or directory (default: tests)')
    parser.add_argument('--tags', '-t', help='Comma-separated list of tags to include (e.g., smoke,regression)')
    parser.add_argument('--browser', '-b', help='Browser to use (e.g., chrome, firefox, edge, safari)')
    parser.add_argument('--browser-library', '-l', help='Path to custom browser support library (e.g., tests/Web/Library/BrowserSupport.py)')
    parser.add_argument('--skip-xray', action='store_true', help='Skip Xray integration (only run tests)')
    parser.add_argument('--output', '-o', default='output', help='Output directory (default: output)')
    
    args = parser.parse_args()
    
    # Parse tags if provided
    tags = None
    if args.tags:
        tags = [tag.strip() for tag in args.tags.split(',')]
        print(f"Running tests with tags: {', '.join(tags)}")
    
    # Run tests with Xray integration
    exit_code = run_tests_with_xray(
        test_path=args.test_path,
        output_dir=args.output,
        tags=tags,
        browser=args.browser,
        browser_library=args.browser_library,
        skip_xray=args.skip_xray
    )
    
    # Exit with appropriate code for CI/CD
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
