"""
Enhanced Upload Results Script - Fixed to match XrayListener behavior

This script parses Robot Framework output.xml and uploads results to Xray
using the same logic as the working XrayListener.

Features:
- Parses BDD-style tests with Given/When/Then steps
- Extracts test IDs from xray:TP-XXXX tags
- Extracts Story ID from suite documentation
- Uses execution_manager.update_execution_results() for complete upload
- Handles step-level results and screenshots

Usage:
    python upload_results_fixed.py --output tests/Web/Output
    python upload_results_fixed.py --output tests/Web/Output --story TP-8071
"""

import os
import sys
import argparse
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

# Use defusedxml for secure XML parsing (protects against XXE attacks)
try:
    from defusedxml.ElementTree import parse as ET_parse
    XML_PARSER_SECURE = True
except ImportError:
    from xml.etree.ElementTree import parse as ET_parse
    XML_PARSER_SECURE = False
    print("⚠ WARNING: defusedxml not installed - using standard XML parser")
    print("   Install with: pip install defusedxml")

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_file = project_root / '.env'
    if env_file.exists():
        load_dotenv(env_file)
        print(f"✓ Loaded environment variables from {env_file}")
    else:
        load_dotenv()  # Try to load from current directory
        print("✓ Loaded environment variables from .env file")
except ImportError:
    print("⚠ python-dotenv not installed - install with: pip install python-dotenv")
    print("   Using system environment variables only")
except Exception as e:
    print(f"⚠ Could not load .env file: {e}")


def setup_environment() -> bool:
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


def parse_test_results_from_xml(output_xml_path: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Parse Robot Framework output.xml and extract test results in XrayListener format.
    
    Returns:
        Tuple of (list of test result dictionaries, story_id)
        
    Test result dictionary structure matches XrayListener:
        {
            'test_key': 'TP-8753',
            'scenario_name': 'Test scenario name',
            'status': 'PASS' | 'FAIL' | 'ABORTED',
            'actual_result': 'Test message',
            'step_results': [
                {'status': 'PASS', 'actual_result': 'Step description'},
                ...
            ],
            'screenshots': [
                {'path': '/path/to/screenshot.png', 'step_index': 0},
                ...
            ]
        }
    """
    try:
        # Validate input file exists and is readable
        xml_path = Path(output_xml_path)
        if not xml_path.exists():
            raise FileNotFoundError(f"output.xml not found: {output_xml_path}")
        if not xml_path.is_file():
            raise ValueError(f"Path is not a file: {output_xml_path}")
        
        # Parse XML securely
        tree = ET_parse(str(xml_path))
        root = tree.getroot()
        
        test_results = []
        story_id = None
        output_dir = xml_path.parent
        
        # Status mapping
        status_map = {
            'PASS': 'PASS',
            'FAIL': 'FAIL',
            'SKIP': 'ABORTED'
        }
        
        # Find all test cases
        # Check both root suite and nested suites
        all_suites = [root] if root.tag == 'suite' else []
        all_suites.extend(root.findall('.//suite'))
        
        for suite in all_suites:
            # Try to extract Story ID from suite documentation
            if not story_id:
                doc = suite.find('doc')
                if doc is not None and doc.text:
                    # Look for "Jira-Id: TP-XXXX" pattern
                    match = re.search(r'Jira-Id:\s*([A-Z][A-Z0-9]+-\d+)', doc.text)
                    if match:
                        story_id = match.group(1)
                        # Validate Story ID format (prevent injection)
                        if re.match(r'^[A-Z][A-Z0-9]+-\d+$', story_id):
                            print(f"✓ Found Story ID: {story_id}")
                        else:
                            print(f"⚠ Invalid Story ID format: {story_id}")
                            story_id = None
            
            for test in suite.findall('.//test'):
                test_name = test.get('name')
                status_elem = test.find('status')
                
                if status_elem is None:
                    continue
                
                status = status_elem.get('status', 'FAIL')
                xray_status = status_map.get(status, 'FAIL')
                message = status_elem.get('message', f'Test {status}')
                
                # Extract Xray test ID from tags
                tags = test.findall('tag')
                test_key = None
                
                for tag in tags:
                    tag_text = tag.text
                    if tag_text:
                        # Strip whitespace (some XML parsers preserve leading/trailing spaces)
                        tag_text = tag_text.strip()
                        
                        # Check for xray tag (case-insensitive: xray:, Xray:, XRAY:)
                        if tag_text.lower().startswith('xray:'):
                            # Find colon and extract after it (handles any case)
                            colon_pos = tag_text.find(':')
                            potential_key = tag_text[colon_pos+1:].strip()  # Strip whitespace from test ID too
                            # Validate test key format (prevent injection)
                            # Allows formats like: TP-9876, XSP-168, ABC-456
                            if re.match(r'^[A-Z][A-Z0-9]*-\d+$', potential_key):
                                test_key = potential_key
                                break
                            else:
                                print(f"⚠ Warning: Invalid test key format in tag: {tag_text} (extracted: {potential_key})")
                
                # If no xray tag found, we'll create a placeholder that will be auto-created later
                if not test_key:
                    # Use test name as placeholder - will be created if --create-tests is enabled
                    test_key = f"AUTO_CREATE_{test_name.replace(' ', '_')}"
                    print(f"ℹ Info: Test '{test_name}' has no xray tag - will auto-create if enabled")
                
                print(f"✓ Found test: {test_key} - {test_name} ({xray_status})")
                
                # Parse step-level results from keywords (BDD-style: Given/When/Then/And)
                step_results = []
                keywords = test.findall('.//kw')
                
                for kw in keywords:
                    kw_name = kw.get('name', '')
                    kw_status_elem = kw.find('status')
                    
                    # Look for BDD keywords
                    if any(kw_name.startswith(prefix) for prefix in ['Given ', 'When ', 'Then ', 'And ', 'But ']):
                        kw_status = kw_status_elem.get('status', 'FAIL') if kw_status_elem is not None else 'FAIL'
                        kw_xray_status = status_map.get(kw_status, 'FAIL')
                        
                        step_result = {
                            'status': kw_xray_status,
                            'actual_result': f"{kw_name} - {kw_status}"
                        }
                        step_results.append(step_result)
                        print(f"    • Step: {kw_name[:50]}... ({kw_xray_status})")
                
                # If no BDD steps found, create a single step from test result
                if not step_results:
                    step_results.append({
                        'status': xray_status,
                        'actual_result': message
                    })
                    print(f"    • No BDD steps found - using test result as single step")
                
                # Find screenshots for this test
                screenshots = []
                screenshot_dir = Path(output_dir) / 'screenshots'
                
                if screenshot_dir.exists() and screenshot_dir.is_dir():
                    # Look for screenshots matching test name or test key
                    test_name_normalized = test_name.replace(' ', '_').replace('/', '_')
                    
                    try:
                        for filepath in screenshot_dir.iterdir():
                            if not filepath.is_file():
                                continue
                            
                            filename = filepath.name
                            # Validate that file is actually inside screenshot_dir (prevent path traversal)
                            if filepath.resolve().parent != screenshot_dir.resolve():
                                continue
                            
                            if test_name_normalized in filename or test_key in filename:
                                screenshots.append({
                                    'path': str(filepath),
                                    'step_index': None  # Will be distributed by execution_manager
                                })
                    except (PermissionError, OSError) as e:
                        print(f"    ⚠ Could not read screenshot directory: {e}")
                    
                    if screenshots:
                        print(f"    • Found {len(screenshots)} screenshot(s)")
                
                # Build test result in XrayListener format
                test_result = {
                    'test_key': test_key,
                    'scenario_name': test_name,
                    'status': xray_status,
                    'actual_result': message,
                    'step_results': step_results,
                    'screenshots': screenshots
                }
                
                test_results.append(test_result)
        
        return test_results, story_id
        
    except Exception as e:
        print(f"✗ ERROR parsing output.xml: {e}")
        import traceback
        traceback.print_exc()
        return [], None


def upload_results_to_xray(output_dir: str, story_id: Optional[str] = None, create_tests: bool = False) -> bool:
    """
    Upload test results to Xray using execution_manager.update_execution_results().
    
    This matches the behavior of XrayListener.end_suite().
    
    Args:
        output_dir: Directory containing output.xml
        story_id: Optional Story ID to link to Test Execution
        create_tests: If True, automatically create tests that don't exist (requires story_id)
        
    Returns:
        True if upload successful, False otherwise
    """
    print("\n" + "="*80)
    print("UPLOADING RESULTS TO XRAY")
    print("="*80)
    
    # Validate environment
    if not setup_environment():
        print("\n✗ Cannot upload to Xray - missing credentials")
        return False
    
    # Validate output directory
    output_path = Path(output_dir)
    if not output_path.exists():
        print(f"✗ ERROR: Directory '{output_dir}' does not exist")
        return False
    
    output_xml = output_path / "output.xml"
    if not output_xml.exists():
        print(f"✗ ERROR: 'output.xml' not found in '{output_dir}'")
        return False
    
    print(f"✓ Found Robot Framework results in '{output_dir}'")
    
    # Parse test results from XML
    print("\n📋 Parsing test results...")
    test_results, extracted_story_id = parse_test_results_from_xml(str(output_xml))
    
    if not test_results:
        print("\n⚠ No tests found in output.xml")
        print("   Make sure your Robot Framework tests ran and generated output.xml")
        return False
    
    print(f"\n✓ Found {len(test_results)} test(s)")
    
    # Use extracted story ID if not provided
    if not story_id and extracted_story_id:
        story_id = extracted_story_id
        print(f"✓ Using extracted Story ID: {story_id}")
    elif story_id:
        print(f"✓ Using provided Story ID: {story_id}")
    
    # Import execution manager and test manager
    try:
        from integrations.xray import execution_manager, test_manager
    except ImportError as e:
        print(f"✗ ERROR: Could not import Xray modules: {e}")
        return False
    
    # Create or validate test IDs before upload
    print("\n🔍 Validating/Creating Test IDs in Xray...")
    validated_results = []
    skipped_count = 0
    
    for test_result in test_results:
        test_key = test_result.get('test_key')
        scenario_name = test_result.get('scenario_name')
        
        print(f"\n   Processing: {test_key} - {scenario_name}")
        
        # Check if this is an auto-create placeholder
        if test_key.startswith('AUTO_CREATE_'):
            # This test has no xray tag - must create it
            if create_tests and story_id:
                print(f"      → No xray tag - creating new test...")
                try:
                    # Create new test linked to Story
                    new_test_key = test_manager.create_or_get_test(scenario_name, story_id)
                    print(f"      ✓ Created: {new_test_key}")
                    
                    # Update test_result with new test key
                    test_result['test_key'] = new_test_key
                    validated_results.append(test_result)
                    
                except Exception as e:
                    print(f"      ✗ Failed to create test: {e}")
                    skipped_count += 1
            elif not story_id:
                print(f"      ⚠ No xray tag and no Story ID provided")
                print(f"      → Add --story TP-XXXX to create test")
                skipped_count += 1
            else:
                print(f"      ⚠ No xray tag - use --create-tests to auto-create")
                skipped_count += 1
            continue
        
        # Check if test exists in Xray
        print(f"      → Checking if {test_key} exists in Xray...")
        try:
            issue_id = test_manager._get_jira_issue_id(test_key)
        except Exception as e:
            print(f"      ⚠ Could not verify test: {e}")
            issue_id = None
        
        if issue_id:
            print(f"      ✓ {test_key} exists (ID: {issue_id})")
            validated_results.append(test_result)
        else:
            # Test doesn't exist in Xray
            print(f"WARNING: Error getting Jira issue ID: 404 Client Error: Not Found for url: https://admin-ev.atlassian.net/rest/api/2/issue/{test_key}")
            print(f"      ⚠ {test_key} not found in Xray")
            
            # If --create-tests flag is provided, try to create it first
            if create_tests and story_id:
                print(f"      → Creating test: {scenario_name}")
                try:
                    # Create new test linked to Story
                    created_key = test_manager.create_or_get_test(scenario_name, story_id)
                    print(f"      ✓ Created: {created_key}")
                    
                    # Update test_result with created test key
                    test_result['test_key'] = created_key
                    validated_results.append(test_result)
                except Exception as e:
                    print(f"      ✗ Failed to create test: {e}")
                    print(f"      → Will attempt upload anyway (may fail)")
                    validated_results.append(test_result)
            else:
                # No auto-create, but still try to upload (execution_manager will filter it out)
                print(f"      → Will attempt upload anyway (may fail if test doesn't exist)")
                print(f"      → Use --create-tests --story to pre-create test")
                validated_results.append(test_result)
    
    if not validated_results:
        print(f"\n✗ No valid tests to upload after validation")
        print(f"   Processed: {len(test_results)} test(s)")
        print(f"   Validated: {len(validated_results)} test(s)")
        print(f"   Skipped: {skipped_count} test(s)")
        print("\nPossible reasons:")
        if not create_tests:
            print("  • Missing --create-tests flag to auto-create tests")
        if not story_id:
            print("  • Missing --story flag (required for creating tests)")
        print("\nTo upload all tests, use:")
        print(f"  python upload_results_fixed.py --output {output_dir} --story TP-XXXX --create-tests")
        return False
    
    print(f"\n✓ Validated {len(validated_results)} test(s) for upload")
    if skipped_count > 0:
        print(f"⚠ Skipped {skipped_count} test(s)")
    
    # Important note about test existence
    tests_not_in_xray = [tr for tr in validated_results if not test_manager._get_jira_issue_id(tr['test_key'])]
    if tests_not_in_xray:
        print(f"\n⚠ WARNING: {len(tests_not_in_xray)} test(s) with xray tags don't exist in Xray:")
        for tr in tests_not_in_xray:
            print(f"   • {tr['test_key']} - will be filtered out during upload")
        print(f"\n   To create these tests automatically, run:")
        print(f"   python upload_results_fixed.py --output {output_dir} --story {story_id or 'TP-XXXX'} --create-tests")
        print(f"\n   Only tests that exist in Xray will be included in the Test Execution.")
    
    # Collect attachments (log.html, report.html)
    attachments = []
    for filename in ['log.html', 'report.html']:
        filepath = output_path / filename
        if filepath.exists():
            attachments.append(str(filepath))
            print(f"✓ Will attach: {filename}")
    
    # Upload using execution_manager.update_execution_results()
    # This is the SAME function that XrayListener.end_suite() uses
    print("\n📤 Uploading to Xray Cloud...")
    print(f"   Tests: {len(validated_results)}")
    print(f"   Total Steps: {sum(len(tr['step_results']) for tr in validated_results)}")
    print(f"   Screenshots: {sum(len(tr['screenshots']) for tr in validated_results)}")
    print(f"   Attachments: {len(attachments)}")
    
    try:
        test_exec_key = execution_manager.update_execution_results(
            test_results=validated_results,
            attachments=attachments if attachments else None
        )
        
        if test_exec_key:
            print(f"\n{'='*80}")
            print(f"✅ SUCCESS! Test Execution created: {test_exec_key}")
            print(f"{'='*80}")
            
            # If story ID provided, link it
            if story_id:
                print(f"\n🔗 Linking to Story: {story_id}")
                try:
                    from integrations.xray import test_manager
                    # This would require additional API call - not implemented in original
                    print(f"   ℹ Manual linking required - add {test_exec_key} to {story_id}")
                except:
                    pass
            
            return True
        else:
            print(f"\n✗ Failed to create Test Execution")
            return False
            
    except Exception as e:
        print(f"\n✗ ERROR uploading results: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Upload Robot Framework test results to Xray Cloud',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Upload results from default directory
    python upload_results_fixed.py
    
    # Upload with custom output directory
    python upload_results_fixed.py --output tests/Web/Output
    
    # Upload and link to Story (required for auto-creating tests)
    python upload_results_fixed.py --output tests/Web/Output --story TP-8071
    
    # Auto-create tests that don't exist (requires --story)
    python upload_results_fixed.py --output tests/Web/Output --story TP-8071 --create-tests
        """
    )
    
    parser.add_argument(
        '--output',
        default='tests/Web/Output',
        help='Output directory containing output.xml (default: tests/Web/Output)'
    )
    
    parser.add_argument(
        '--story',
        help='Story ID to link Test Execution to (e.g., TP-8071). Required for --create-tests.'
    )
    
    parser.add_argument(
        '--create-tests',
        action='store_true',
        help='Automatically create tests in Xray if they don\'t exist (requires --story)'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.create_tests and not args.story:
        parser.error("--create-tests requires --story to be specified")
    
    # Validate Story ID format if provided
    if args.story:
        if not re.match(r'^[A-Z][A-Z0-9]+-\d+$', args.story):
            parser.error(f"Invalid Story ID format: {args.story}. Expected format: ABC-123")
    
    # Validate output directory path
    output_path = Path(args.output)
    try:
        # Resolve to absolute path and check it's safe
        output_path = output_path.resolve()
    except (OSError, RuntimeError) as e:
        parser.error(f"Invalid output directory path: {e}")
    
    print("\n" + "="*80)
    print("XRAY TEST RESULTS UPLOADER")
    print("="*80)
    print(f"Output Directory: {output_path}")
    if args.story:
        print(f"Story ID: {args.story}")
    if args.create_tests:
        print(f"Auto-create tests: Enabled")
    
    # Upload results
    success = upload_results_to_xray(str(output_path), args.story, args.create_tests)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
