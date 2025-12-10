"""
XML Structure Diagnostic Tool
Shows exactly what tags and structure exist in your output.xml
"""
import sys
from pathlib import Path
from defusedxml.ElementTree import parse as ET_parse

def diagnose_xml(xml_path: str):
    """Diagnose XML structure and show all tags"""
    print(f"\n{'='*80}")
    print(f"DIAGNOSING: {xml_path}")
    print(f"{'='*80}\n")
    
    xml_file = Path(xml_path)
    if not xml_file.exists():
        print(f"❌ File not found: {xml_path}")
        return
    
    tree = ET_parse(str(xml_file))
    root = tree.getroot()
    
    print(f"Root element: <{root.tag}>")
    print(f"Root attributes: {root.attrib}\n")
    
    # Find all suites
    all_suites = [root] if root.tag == 'suite' else []
    all_suites.extend(root.findall('.//suite'))
    
    print(f"Found {len(all_suites)} suite(s)\n")
    
    for suite_idx, suite in enumerate(all_suites, 1):
        suite_name = suite.get('name', 'Unknown')
        print(f"\n{'─'*80}")
        print(f"SUITE {suite_idx}: {suite_name}")
        print(f"{'─'*80}")
        
        # Check for suite-level tags
        suite_tags = suite.findall('tag')
        if suite_tags:
            print(f"\n  Suite-level tags:")
            for tag in suite_tags:
                print(f"    • {tag.text}")
        
        # Find all tests in this suite
        tests = suite.findall('.//test')
        print(f"\n  Found {len(tests)} test(s) in this suite:\n")
        
        for test_idx, test in enumerate(tests, 1):
            test_name = test.get('name', 'Unknown')
            test_id = test.get('id', 'Unknown')
            
            print(f"  TEST {test_idx}: {test_name}")
            print(f"    ID: {test_id}")
            
            # Get test status
            status_elem = test.find('status')
            if status_elem is not None:
                status = status_elem.get('status', 'UNKNOWN')
                print(f"    Status: {status}")
            
            # Get all tags
            tags = test.findall('tag')
            print(f"    Tags ({len(tags)}):")
            if tags:
                for tag in tags:
                    tag_text = tag.text if tag.text else '(empty)'
                    is_xray = tag_text.startswith('xray:') if tag.text else False
                    marker = "✓ XRAY TAG" if is_xray else ""
                    print(f"      • '{tag_text}' {marker}")
                    
                    if is_xray:
                        extracted = tag_text[5:]
                        print(f"        → Would extract: '{extracted}'")
            else:
                print(f"      (no tags found)")
            
            # Check for metadata/kw elements
            metadata = test.findall('kw')
            if metadata:
                print(f"    Keywords: {len(metadata)} found")
            
            print()
    
    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    
    total_tests = len(root.findall('.//test'))
    total_tags = len(root.findall('.//test/tag'))
    xray_tags = [tag for tag in root.findall('.//test/tag') if tag.text and tag.text.startswith('xray:')]
    
    print(f"Total tests: {total_tests}")
    print(f"Total tags: {total_tags}")
    print(f"Xray tags: {len(xray_tags)}")
    
    if xray_tags:
        print(f"\nXray test IDs found:")
        for tag in xray_tags:
            print(f"  • {tag.text[5:]}")
    else:
        print(f"\n⚠ NO XRAY TAGS FOUND!")
        print(f"\nPossible reasons:")
        print(f"  1. Tags might be at suite level instead of test level")
        print(f"  2. Tags might not have 'xray:' prefix")
        print(f"  3. Tests might not have tags at all")
        
        # Check suite-level tags
        suite_tags_all = root.findall('.//suite/tag')
        if suite_tags_all:
            print(f"\n  Found {len(suite_tags_all)} suite-level tags:")
            for tag in suite_tags_all[:5]:  # Show first 5
                print(f"    • {tag.text}")
        
        # Check all tags regardless of xray prefix
        all_test_tags = root.findall('.//test/tag')
        if all_test_tags:
            print(f"\n  All test tags found (first 10):")
            for tag in all_test_tags[:10]:
                print(f"    • {tag.text if tag.text else '(empty)'}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python diagnose_xml.py <path_to_output.xml>")
        print("\nExample:")
        print("  python diagnose_xml.py output/output.xml")
        print("  python diagnose_xml.py C:/path/to/other/project/output.xml")
        sys.exit(1)
    
    xml_path = sys.argv[1]
    diagnose_xml(xml_path)
