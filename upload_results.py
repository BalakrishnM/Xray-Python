"""
Upload existing Robot Framework test results to Xray without re-running tests.

This script allows you to upload test execution results from a previous test run
to Xray Cloud, useful for:
- Re-uploading results after a failed upload
- Uploading results from a different environment
- Batch processing of multiple test result files

Usage:
    python upload_results.py [output_dir] [--story STORY-ID]
    
Examples:
    # Upload results from default output directory
    python upload_results.py
    
    # Upload results from specific directory
    python upload_results.py output/
    
    # Upload with specific story ID (overrides story in test files)
    python upload_results.py output/ --story XSP-100
    
    # Upload from custom output directory with story
    python upload_results.py build/test-results/ --story XSP-200
"""

import os
import sys
from pathlib import Path
import argparse

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


def validate_output_directory(output_dir: str) -> bool:
    """
    Validate that output directory contains Robot Framework results.
    
    Args:
        output_dir: Path to output directory
        
    Returns:
        bool: True if valid, False otherwise
    """
    output_path = Path(output_dir)
    
    if not output_path.exists():
        print(f"ERROR: Directory '{output_dir}' does not exist")
        return False
    
    if not output_path.is_dir():
        print(f"ERROR: '{output_dir}' is not a directory")
        return False
    
    # Check for output.xml (required for Robot Framework results)
    output_xml = output_path / "output.xml"
    if not output_xml.exists():
        print(f"ERROR: 'output.xml' not found in '{output_dir}'")
        print("This directory does not appear to contain Robot Framework test results")
        return False
    
    print(f"✓ Found Robot Framework results in '{output_dir}'")
    return True


def extract_story_id_from_results(output_dir: str) -> str:
    """
    Extract Jira ID from test result files.
    
    Args:
        output_dir: Path to output directory
        
    Returns:
        str: Jira ID if found, None otherwise
    """
    import xml.etree.ElementTree as ET
    
    output_xml = Path(output_dir) / "output.xml"
    
    try:
        tree = ET.parse(output_xml)
        root = tree.getroot()
        
        # Look for Jira-Id: in suite documentation
        for suite in root.iter('suite'):
            doc = suite.find('doc')
            if doc is not None and doc.text:
                # Search for Jira-Id: pattern
                import re
                match = re.search(r'Jira-Id:\s*([A-Z]+-\d+)', doc.text)
                if match:
                    story_id = match.group(1)
                    print(f"✓ Found Jira ID in results: {story_id}")
                    return story_id
        
        print("WARNING: No Jira ID found in test results")
        return None
        
    except Exception as e:
        print(f"WARNING: Could not parse output.xml: {e}")
        return None


def upload_results_to_xray(output_dir: str, story_id: str = None) -> bool:
    """
    Upload test results from output directory to Xray.
    
    Args:
        output_dir: Path to output directory containing test results
        story_id: Optional Story ID (overrides story in test files)
        
    Returns:
        bool: True if upload successful, False otherwise
    """
    from integrations.xray.config import XrayConfig
    from integrations.xray.execution import upload_execution_results
    
    print("\n" + "="*80)
    print("UPLOADING TEST RESULTS TO XRAY")
    print("="*80)
    
    # Validate configuration
    if not XrayConfig.validate():
        print("\nERROR: Xray configuration is not properly set up.")
        print("Please configure the following environment variables:")
        print("  - XRAY_CLIENT_ID")
        print("  - XRAY_CLIENT_SECRET")
        print("  - JIRA_BASE_URL")
        print("  - JIRA_USER_EMAIL")
        print("  - JIRA_API_TOKEN")
        print("  - XRAY_PROJECT_KEY")
        return False
    
    # Get or validate Jira ID
    if not story_id:
        story_id = extract_story_id_from_results(output_dir)
        if not story_id:
            print("\nERROR: No Jira ID provided and none found in test results")
            print("Please provide Jira ID using --story option:")
            print("  python upload_results.py output/ --story XSP-100")
            return False
    
    print(f"\nJira ID: {story_id}")
    
    # Check that output.xml exists
    output_xml = Path(output_dir) / "output.xml"
    if not output_xml.exists():
        print(f"\nERROR: output.xml not found in {output_dir}")
        return False
    
    # Collect attachments
    attachments = []
    output_path = Path(output_dir)
    
    # Add log and report files if they exist
    for filename in ['log.html', 'report.html', 'output.xml']:
        file_path = output_path / filename
        if file_path.exists():
            attachments.append(str(file_path))
    
    # Add screenshots if they exist
    screenshots_dir = output_path / 'screenshots'
    if screenshots_dir.exists():
        for screenshot in screenshots_dir.glob('*.png'):
            attachments.append(str(screenshot))
        for screenshot in screenshots_dir.glob('*.jpg'):
            attachments.append(str(screenshot))
    
    print(f"\nFound {len(attachments)} files to upload")
    
    try:
        # Upload results using execution module
        print("\nUploading results to Xray...")
        
        info = {
            "summary": f"Test Execution for {story_id}",
            "description": f"Automated test execution results uploaded from {output_dir}"
        }
        
        result = upload_execution_results(
            robot_output_xml=str(output_xml),
            attachments=attachments,
            info=info
        )
        
        print(f"\n{'='*80}")
        print(f"✓ SUCCESS: Test results uploaded to Xray")
        print(f"Story: {story_id}")
        print(f"Attachments: {len(attachments)} files")
        print(f"{'='*80}\n")
        return True
            
    except Exception as e:
        print(f"\nERROR: Failed to upload results: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point for result upload script."""
    parser = argparse.ArgumentParser(
        description='Upload existing Robot Framework test results to Xray Cloud',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Upload results from default output directory
  python upload_results.py
  
  # Upload results from specific directory
  python upload_results.py output/
  
  # Upload with specific story ID
  python upload_results.py output/ --story XSP-100
  
  # Upload from custom directory with story
  python upload_results.py build/test-results/ --story XSP-200
        """
    )
    
    parser.add_argument(
        'output_dir',
        nargs='?',
        default='output',
        help='Path to directory containing test results (default: output)'
    )
    
    parser.add_argument(
        '--story',
        '-s',
        help='Story ID to link test execution to (e.g., XSP-100). If not provided, will extract from test results.'
    )
    
    args = parser.parse_args()
    
    # Validate output directory
    if not validate_output_directory(args.output_dir):
        sys.exit(1)
    
    # Upload results
    success = upload_results_to_xray(args.output_dir, args.story)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
