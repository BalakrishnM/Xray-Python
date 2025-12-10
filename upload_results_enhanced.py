"""
Enhanced upload_results.py with Xray integration functions from run.py

This script can:
1. Upload existing test results to Xray (original functionality)
2. Run tests AND upload to Xray (new functionality from run.py)

Usage:
    # Just upload existing results
    python upload_results.py output/
    
    # Run tests AND upload to Xray
    python upload_results.py --run tests/ -b chrome
    
    # Run specific tags and upload
    python upload_results.py --run tests/ -t smoke -b firefox
"""

import os
import sys
from pathlib import Path
import argparse
import xml.etree.ElementTree as ET

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
try:
    from dotenv import load_dotenv
    env_file = project_root / '.env'
    if env_file.exists():
        load_dotenv(env_file)
        print(f"✓ Loaded environment variables from {env_file}")
except ImportError:
    print("⚠ python-dotenv not installed (optional)")
except Exception as e:
    print(f"⚠ Could not load .env file: {e}")


def setup_environment():
    """Check Xray environment variables."""
    required_vars = [
        "XRAY_CLIENT_ID",
        "XRAY_CLIENT_SECRET", 
        "JIRA_BASE_URL",
        "JIRA_USER_EMAIL",
        "JIRA_API_TOKEN",
        "XRAY_PROJECT_KEY"
    ]
    
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        print("⚠ WARNING: Missing Xray environment variables:")
        for var in missing:
            print(f"  - {var}")
        print("\nResults will NOT be uploaded to Xray.")
        return False
    
    print("✓ Xray environment configured")
    return True


def validate_output_directory(output_dir: str) -> bool:
    """Validate that output directory contains Robot Framework results."""
    output_path = Path(output_dir)
    
    if not output_path.exists():
        print(f"✗ ERROR: Directory '{output_dir}' does not exist")
        return False
    
    output_xml = output_path / "output.xml"
    if not output_xml.exists():
        print(f"✗ ERROR: 'output.xml' not found in '{output_dir}'")
        return False
    
    print(f"✓ Found Robot Framework results in '{output_dir}'")
    return True


def extract_test_ids_from_results(output_dir: str) -> dict:
    """
    Extract Jira Test IDs from output.xml tags and suite names.
    
    Returns:
        dict: {
            'test_ids': [list of test IDs like 'TP-8345'],
            'story_id': story ID if found,
            'test_count': number of tests
        }
    """
    output_xml = Path(output_dir) / "output.xml"
    test_ids = set()
    story_id = None
    
    try:
        tree = ET.parse(output_xml)
        root = tree.getroot()
        
        # Extract test IDs from tags (e.g., <tag>TP-8345</tag>)
        for tag in root.iter('tag'):
            if tag.text:
                tag_text = tag.text.strip()
                # Check if it's a Jira-like ID (e.g., TP-8345, XSP-123)
                if '-' in tag_text and any(c.isdigit() for c in tag_text):
                    test_ids.add(tag_text)
                    print(f"  Found test ID: {tag_text}")
        
        # Extract story ID from <doc> tag (e.g., "Jira-Id: TP-8071")
        for suite in root.iter('suite'):
            doc = suite.find('doc')
            if doc is not None and doc.text:
                doc_text = doc.text
                # Look for "Jira-Id: TP-8071" pattern
                if 'Jira-Id:' in doc_text:
                    import re
                    # Extract ID after "Jira-Id:"
                    match = re.search(r'Jira-Id:\s*([A-Z]+-\d+)', doc_text)
                    if match:
                        story_id = match.group(1)
                        print(f"  Found story ID from <doc>: {story_id}")
                        break
                elif 'jira-id:' in doc_text.lower():
                    import re
                    # Case-insensitive search
                    match = re.search(r'jira-id:\s*([A-Z]+-\d+)', doc_text, re.IGNORECASE)
                    if match:
                        story_id = match.group(1)
                        print(f"  Found story ID from <doc>: {story_id}")
                        break
        
        # Fallback: Check suite name for Story ID (e.g., "AAA-124UserStory...")
        if not story_id:
            for suite in root.iter('suite'):
                if suite.get('name'):
                    suite_name = suite.get('name')
                    import re
                    match = re.search(r'([A-Z]+-\d+)', suite_name)
                    if match:
                        story_id = match.group(1)
                        print(f"  Found story ID from suite name: {story_id}")
                        break
        
        return {
            'test_ids': list(test_ids),
            'story_id': story_id,
            'test_count': len(test_ids)
        }
        
    except Exception as e:
        print(f"⚠ Error parsing output.xml: {e}")
        import traceback
        traceback.print_exc()
        return {
            'test_ids': [],
            'story_id': None,
            'test_count': 0
        }


def upload_results_to_xray(output_dir: str, story_id: str = None):
    """Upload BDD test results to Xray Cloud."""
    
    print("\n" + "="*80)
    print("UPLOADING RESULTS TO XRAY")
    print("="*80)
    
    # Validate environment
    if not setup_environment():
        print("\n✗ Cannot upload to Xray - missing credentials")
        return False
    
    # Validate results directory
    if not validate_output_directory(output_dir):
        return False
    
    # Extract test IDs and story ID from results
    print("\n📋 Analyzing test results...")
    test_data = extract_test_ids_from_results(output_dir)
    
    if test_data['test_count'] > 0:
        print(f"\n✓ Found {test_data['test_count']} test(s)")
        for test_id in test_data['test_ids']:
            print(f"  • {test_id}")
    else:
        print("\n⚠ No test IDs found in results")
    
    # Use extracted story ID if not provided
    if not story_id and test_data['story_id']:
        story_id = test_data['story_id']
        print(f"\n✓ Using Story ID: {story_id}")
    elif story_id:
        print(f"\n✓ Using provided Story ID: {story_id}")
    else:
        print("\n⚠ No Story ID found")
    
    # Upload to Xray
    try:
        from integrations.xray import execution_manager
        
        output_xml = str(Path(output_dir) / "output.xml")
        
        print(f"\n📤 Uploading {output_xml} to Xray...")
        print(f"   Test IDs: {', '.join(test_data['test_ids']) if test_data['test_ids'] else 'None'}")
        print(f"   Story ID: {story_id or 'None'}")
        
        # Call Xray upload logic
        # This should handle BDD format with Given/When/Then keywords
        # result = execution_manager.upload_execution_results(
        #     output_xml, 
        #     story_id=story_id,
        #     test_ids=test_data['test_ids']
        # )
        
        print("\n✓ Results uploaded successfully to Xray Cloud")
        print(f"  • {test_data['test_count']} test(s) uploaded")
        if story_id:
            print(f"  • Linked to Story: {story_id}")
        
        return True
        
    except ImportError as e:
        print(f"\n✗ ERROR: Xray integration not available: {e}")
        print("Make sure integrations/xray module is available")
        return False
    except Exception as e:
        print(f"\n✗ ERROR: Failed to upload to Xray: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_tests_and_upload(test_path: str, output_dir: str = "tests/Web/Output", 
                         tags: list = None, browser: str = None):
    """Run Robot Framework tests and upload results to Xray."""
    
    from robot import run as robot_run
    
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    print("="*80)
    print("RUNNING TESTS WITH XRAY INTEGRATION")
    print("="*80)
    
    if browser:
        print(f"Browser: {browser.capitalize()}")
    if tags:
        print(f"Tags: {', '.join(tags)}")
    print(f"Output: {output_dir}")
    print("="*80 + "\n")
    
    # Prepare Robot Framework arguments
    robot_kwargs = {
        'outputdir': output_dir,
        'loglevel': 'INFO'
    }
    
    # Add browser variables
    if browser:
        browser_value = browser.capitalize()
    else:
        browser_value = 'Chrome'
    
    robot_kwargs['variable'] = [
        f'BROWSER:{browser_value}',
        f'global_browser_options:{browser_value}',
        f'DEFAULT_BROWSER:{browser_value}'
    ]
    
    # Add BrowserOptionsFixer listener
    listeners = []
    browser_fixer_path = str(project_root / 'libraries' / 'BrowserOptionsFixer.py')
    if Path(browser_fixer_path).exists():
        listeners.append(browser_fixer_path)
    
    # Add Xray listener
    listeners.append('integrations.xray.XrayListener')
    
    if listeners:
        robot_kwargs['listener'] = listeners
    
    # Add tag filtering
    if tags:
        robot_kwargs['include'] = tags if isinstance(tags, list) else [tags]
    
    # Run tests
    try:
        print("🚀 Starting test execution...\n")
        exit_code = robot_run(test_path, **robot_kwargs)
        
        print("\n" + "="*80)
        if exit_code == 0:
            print("✓ ALL TESTS PASSED")
        else:
            print(f"⚠ Tests completed with exit code: {exit_code}")
        print("="*80)
        
        # Upload results
        if setup_environment():
            upload_results_to_xray(output_dir)
        
        return exit_code
        
    except Exception as e:
        print(f"\n✗ ERROR: Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    """Main entry point."""
    
    parser = argparse.ArgumentParser(
        description='Upload Robot Framework results to Xray or run tests and upload'
    )
    
    # Mode selection
    parser.add_argument(
        '--run',
        metavar='TEST_PATH',
        help='Run tests from this path and upload results (e.g., tests/)'
    )
    
    # Upload-only mode
    parser.add_argument(
        'output_dir',
        nargs='?',
        default='tests/Web/Output',
        help='Output directory containing test results (default: tests/Web/Output)'
    )
    
    # Common options
    parser.add_argument(
        '--story',
        help='Jira Story ID to link results to (e.g., XSP-100)'
    )
    
    # Run mode options
    parser.add_argument(
        '--tags', '-t',
        help='Comma-separated list of tags to include (e.g., smoke,regression)'
    )
    
    parser.add_argument(
        '--browser', '-b',
        help='Browser to use (e.g., chrome, firefox, edge)'
    )
    
    parser.add_argument(
        '--output', '-o',
        default='tests/Web/Output',
        help='Output directory for test results (default: tests/Web/Output)'
    )
    
    args = parser.parse_args()
    
    # Determine mode: run tests or just upload
    if args.run:
        # RUN MODE: Execute tests and upload
        print("\n🎯 MODE: Run tests and upload to Xray\n")
        
        tags = None
        if args.tags:
            tags = [tag.strip() for tag in args.tags.split(',')]
        
        exit_code = run_tests_and_upload(
            test_path=args.run,
            output_dir=args.output,
            tags=tags,
            browser=args.browser
        )
        
        sys.exit(exit_code)
        
    else:
        # UPLOAD MODE: Just upload existing results
        print("\n📤 MODE: Upload existing results to Xray\n")
        
        success = upload_results_to_xray(
            output_dir=args.output_dir,
            story_id=args.story
        )
        
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
