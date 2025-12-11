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
    
    # Check for tags at root level
    print("🔍 Checking for tags at ROOT level...")
    root_tags = root.findall('tag')
    if root_tags:
        print(f"  ✓ Found {len(root_tags)} tag(s) at ROOT level:")
        for tag in root_tags:
            tag_text = tag.text if tag.text else '(empty)'
            if tag.text and 'xray:' in tag.text.lower():
                print(f"    • {tag_text} ⭐ XRAY TAG AT ROOT LEVEL")
            else:
                print(f"    • {tag_text}")
    else:
        print(f"  ✗ No tags at ROOT level")
    print()
    
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
        print(f"\n🔍 Checking for tags at SUITE level...")
        suite_tags = suite.findall('tag')
        if suite_tags:
            print(f"  ✓ Found {len(suite_tags)} tag(s) at SUITE level:")
            for tag in suite_tags:
                tag_text = tag.text if tag.text else '(empty)'
                if tag.text and 'xray:' in tag.text.lower():
                    print(f"    • {tag_text} ⭐ XRAY TAG AT SUITE LEVEL")
                else:
                    print(f"    • {tag_text}")
        else:
            print(f"  ✗ No tags at SUITE level")
        
        # Find direct test children (not nested)
        direct_tests = suite.findall('test')
        # Find all nested tests
        all_tests = suite.findall('.//test')
        
        print(f"\n  Tests: {len(direct_tests)} direct, {len(all_tests)} total (including nested)")
        
        for test_idx, test in enumerate(all_tests, 1):
            test_name = test.get('name', 'Unknown')
            test_id = test.get('id', 'Unknown')
            
            print(f"\n  ┌─ TEST {test_idx}: {test_name}")
            print(f"  │   ID: {test_id}")
            
            # Get test status
            status_elem = test.find('status')
            if status_elem is not None:
                status = status_elem.get('status', 'UNKNOWN')
                print(f"  │   Status: {status}")
            
            # Get all tags
            print(f"  │")
            print(f"  │   🔍 Checking for tags at TEST level...")
            tags = test.findall('tag')
            print(f"  │   Tags ({len(tags)}):")
            if tags:
                for tag in tags:
                    tag_text = tag.text if tag.text else '(empty)'
                    
                    # Debug: Show exact characters
                    if tag.text:
                        tag_repr = repr(tag_text)
                        tag_lower = tag_text.lower()
                        has_xray = 'xray:' in tag_lower
                        starts_xray = tag_lower.startswith('xray:')
                        
                        if starts_xray:
                            print(f"  │     ⭐ XRAY TAG FOUND AT TEST LEVEL!")
                        
                        print(f"  │     • Repr: {tag_repr}")
                        print(f"  │       Text: '{tag_text}'")
                        print(f"  │       Lower: '{tag_lower}'")
                        print(f"  │       Length: {len(tag_text)} chars")
                        print(f"  │       Contains 'xray:': {has_xray}")
                        print(f"  │       Starts with 'xray:': {starts_xray}")
                        
                        if starts_xray:
                            colon_pos = tag_text.find(':')
                            extracted = tag_text[colon_pos+1:]
                            print(f"  │       → Would extract: '{extracted}'")
                        print(f"  │")
            else:
                print(f"  │     ✗ No tags at TEST level")
            
            print(f"  └─")
            
            # Check for metadata/kw elements
            metadata = test.findall('kw')
            if metadata:
                print(f"      Keywords: {len(metadata)} found")
    
    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY - WHERE ARE XRAY TAGS?")
    print(f"{'='*80}")
    
    total_tests = len(root.findall('.//test'))
    total_tags = len(root.findall('.//test/tag'))
    xray_tags = [tag for tag in root.findall('.//test/tag') if tag.text and tag.text.lower().startswith('xray:')]
    
    # Check different levels
    root_xray = [tag for tag in root.findall('tag') if tag.text and 'xray:' in tag.text.lower()]
    suite_xray = [tag for tag in root.findall('.//suite/tag') if tag.text and 'xray:' in tag.text.lower()]
    test_xray = [tag for tag in root.findall('.//test/tag') if tag.text and 'xray:' in tag.text.lower()]
    
    print(f"\nTotal tests: {total_tests}")
    print(f"Total test-level tags: {total_tags}")
    print(f"\n📍 XRAY TAG LOCATIONS:")
    print(f"   • At ROOT level: {len(root_xray)} xray tag(s)")
    print(f"   • At SUITE level: {len(suite_xray)} xray tag(s)")
    print(f"   • At TEST level: {len(test_xray)} xray tag(s)")
    
    if test_xray:
        print(f"\n✓ Xray test IDs found at TEST level:")
        for tag in test_xray:
            colon_pos = tag.text.find(':')
            extracted = tag.text[colon_pos+1:]
            print(f"  • {extracted}")
    
    if suite_xray:
        print(f"\n⚠ Xray tags found at SUITE level (not currently supported):")
        for tag in suite_xray:
            colon_pos = tag.text.find(':')
            extracted = tag.text[colon_pos+1:]
            print(f"  • {extracted}")
        print(f"\n  NOTE: The upload script only reads tags at TEST level.")
        print(f"        You need to move these tags to individual tests.")
    
    if root_xray:
        print(f"\n⚠ Xray tags found at ROOT level (not currently supported):")
        for tag in root_xray:
            colon_pos = tag.text.find(':')
            extracted = tag.text[colon_pos+1:]
            print(f"  • {extracted}")
        print(f"\n  NOTE: The upload script only reads tags at TEST level.")
    
    if not test_xray and not suite_xray and not root_xray:
        print(f"\n❌ NO XRAY TAGS FOUND at any level!")
        print(f"\nPossible reasons:")
        print(f"  1. Tags don't have 'xray:' prefix (case-insensitive)")
        print(f"  2. Tests don't have tags at all")
        print(f"  3. Tags might be in a different format")
        
        # Show all tags found
        all_tags_anywhere = root.findall('.//tag')
        if all_tags_anywhere:
            print(f"\n  All tags found in XML (first 10):")
            for tag in all_tags_anywhere[:10]:
                level = "UNKNOWN"
                if tag in root.findall('tag'):
                    level = "ROOT"
                elif tag in root.findall('.//suite/tag'):
                    level = "SUITE"
                elif tag in root.findall('.//test/tag'):
                    level = "TEST"
                print(f"    [{level}] • {tag.text if tag.text else '(empty)'}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python diagnose_xml.py <path_to_output.xml>")
        print("\nExample:")
        print("  python diagnose_xml.py output/output.xml")
        print("  python diagnose_xml.py C:/path/to/other/project/output.xml")
        sys.exit(1)
    
    xml_path = sys.argv[1]
    diagnose_xml(xml_path)
