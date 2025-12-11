"""
Quick check: What tags are actually in your output.xml?
"""
import sys
from pathlib import Path
from defusedxml.ElementTree import parse as ET_parse

if len(sys.argv) < 2:
    print("Usage: python quick_check.py <path_to_output.xml>")
    sys.exit(1)

xml_path = Path(sys.argv[1])
if not xml_path.exists():
    print(f"File not found: {xml_path}")
    sys.exit(1)

print(f"\n{'='*80}")
print(f"CHECKING: {xml_path}")
print(f"{'='*80}\n")

tree = ET_parse(str(xml_path))
root = tree.getroot()

# Find all tests
all_tests = root.findall('.//test')
print(f"Found {len(all_tests)} test(s)\n")

for idx, test in enumerate(all_tests, 1):
    test_name = test.get('name', 'Unknown')
    print(f"{idx}. Test: {test_name}")
    
    # Find all tags
    tags = test.findall('tag')
    print(f"   Tags found: {len(tags)}")
    
    if tags:
        for tag in tags:
            tag_text = tag.text if tag.text else '(empty)'
            is_xray = tag_text.lower().startswith('xray:') if tag.text else False
            
            if is_xray:
                colon_pos = tag_text.find(':')
                extracted = tag_text[colon_pos+1:]
                print(f"   ✓ '{tag_text}' -> Will extract: {extracted}")
            else:
                print(f"   • '{tag_text}'")
    else:
        print(f"   ⚠ NO TAGS FOUND - This will become AUTO_CREATE_{test_name.replace(' ', '_')}")
    
    print()

print(f"\n{'='*80}")
print("SUMMARY")
print(f"{'='*80}")

xray_tags = [tag for tag in root.findall('.//test/tag') if tag.text and tag.text.lower().startswith('xray:')]
print(f"Total tests with xray tags: {len(xray_tags)}")

if xray_tags:
    print("\nXray test IDs that SHOULD be found:")
    for tag in xray_tags:
        colon_pos = tag.text.find(':')
        extracted = tag.text[colon_pos+1:]
        print(f"  • {extracted}")
else:
    print("\n⚠ NO XRAY TAGS FOUND IN ANY TEST!")
    print("\nThis means:")
    print("  1. Your Robot Framework test might not be generating tags in output.xml")
    print("  2. The tags might be at suite level instead of test level")
    print("  3. The output.xml might be from an old run without the tags")
    print("\nSolution:")
    print("  • Re-run your Robot Framework tests to generate fresh output.xml")
    print("  • Make sure [Tags] are in the test case, not in suite settings")
