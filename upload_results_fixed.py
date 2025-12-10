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
import xml.etree.ElementTree as ET
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional


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
        tree = ET.parse(output_xml_path)
        root = tree.getroot()
        
        test_results = []
        story_id = None
        output_dir = str(Path(output_xml_path).parent)
        
        # Status mapping
        status_map = {
            'PASS': 'PASS',
            'FAIL': 'FAIL',
            'SKIP': 'ABORTED'
        }
        
        # Find all test cases
        for suite in root.findall('.//suite'):
            # Try to extract Story ID from suite documentation
            if not story_id:
                doc = suite.find('doc')
                if doc is not None and doc.text:
                    # Look for "Jira-Id: TP-XXXX" pattern
                    match = re.search(r'Jira-Id:\s*(TP-\d+)', doc.text)
                    if match:
                        story_id = match.group(1)
                        print(f"✓ Found Story ID: {story_id}")
            
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
                    if tag_text and tag_text.startswith('xray:'):
                        # Strip "xray:" prefix
                        test_key = tag_text[5:]
                        break
                
                if not test_key:
                    print(f"⚠ Warning: Test '{test_name}' has no xray:TP-XXXX tag - skipping")
                    continue
                
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
                screenshot_dir = os.path.join(output_dir, 'screenshots')
                
                if os.path.exists(screenshot_dir):
                    # Look for screenshots matching test name or test key
                    test_name_normalized = test_name.replace(' ', '_').replace('/', '_')
                    
                    for filename in os.listdir(screenshot_dir):
                        if test_name_normalized in filename or test_key in filename:
                            screenshot_path = os.path.join(screenshot_dir, filename)
                            screenshots.append({
                                'path': screenshot_path,
                                'step_index': None  # Will be distributed by execution_manager
                            })
                    
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


def upload_results_to_xray(output_dir: str, story_id: Optional[str] = None) -> bool:
    """
    Upload test results to Xray using execution_manager.update_execution_results().
    
    This matches the behavior of XrayListener.end_suite().
    
    Args:
        output_dir: Directory containing output.xml
        story_id: Optional Story ID to link to Test Execution
        
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
        print("\n⚠ No tests with xray:TP-XXXX tags found - nothing to upload")
        return False
    
    print(f"\n✓ Found {len(test_results)} test(s) with Xray tags")
    
    # Use extracted story ID if not provided
    if not story_id and extracted_story_id:
        story_id = extracted_story_id
        print(f"✓ Using extracted Story ID: {story_id}")
    elif story_id:
        print(f"✓ Using provided Story ID: {story_id}")
    
    # Import execution manager
    try:
        from integrations.xray import execution_manager
    except ImportError as e:
        print(f"✗ ERROR: Could not import execution_manager: {e}")
        return False
    
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
    print(f"   Tests: {len(test_results)}")
    print(f"   Total Steps: {sum(len(tr['step_results']) for tr in test_results)}")
    print(f"   Screenshots: {sum(len(tr['screenshots']) for tr in test_results)}")
    print(f"   Attachments: {len(attachments)}")
    
    try:
        test_exec_key = execution_manager.update_execution_results(
            test_results=test_results,
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
    
    # Upload and link to Story
    python upload_results_fixed.py --output tests/Web/Output --story TP-8071
        """
    )
    
    parser.add_argument(
        '--output',
        default='tests/Web/Output',
        help='Output directory containing output.xml (default: tests/Web/Output)'
    )
    
    parser.add_argument(
        '--story',
        help='Story ID to link Test Execution to (e.g., TP-8071)'
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*80)
    print("XRAY TEST RESULTS UPLOADER")
    print("="*80)
    print(f"Output Directory: {args.output}")
    if args.story:
        print(f"Story ID: {args.story}")
    
    # Upload results
    success = upload_results_to_xray(args.output, args.story)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
