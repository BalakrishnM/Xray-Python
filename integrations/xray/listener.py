"""Robot Framework listener for Xray Cloud integration."""

import os
import re
from typing import Dict, List, Optional, Any
from pathlib import Path
from robot.libraries.BuiltIn import BuiltIn
from .test_manager import create_or_get_test, upload_test_steps, link_test_to_story, get_test_by_key
from .execution import upload_execution_results
from .execution_manager import update_execution_results
from .config import XrayConfig


class XrayListener:
    """
    Robot Framework listener that integrates with Xray Cloud.
    
    This listener:
    - Extracts Story ID from feature file descriptions (@Story: ABC-123)
    - Creates or retrieves Xray Tests for each scenario
    - Uploads BDD test steps to Xray
    - Links tests to stories
    - Collects execution results during test run
    - Uploads execution results and attachments at the end of the suite
    
    Usage in Robot Framework:
        robot --listener integrations.xray.XrayListener test_suite.robot
        
    Or programmatically:
        from integrations.xray import XrayListener
        # When running tests via Python
    """
    
    ROBOT_LISTENER_API_VERSION = 3
    
    def __init__(self):
        """Initialize the Xray listener."""
        self.story_id: Optional[str] = None
        self.current_test_key: Optional[str] = None
        self.current_test_name: Optional[str] = None
        self.current_test_file: Optional[str] = None
        self.current_test_steps: List[Dict[str, Any]] = []
        self.current_step_index: int = 0
        self.current_test_screenshots: List[str] = []  # Screenshots for current test
        self.test_results: List[Dict[str, Any]] = []
        self.suite_metadata: Dict[str, Any] = {}
        self.output_dir: str = "output"
        self.screenshots: List[str] = []
        self.test_xray_mapping: Dict[str, str] = {}  # test_name -> xray_key
        
        # Validate configuration
        if not XrayConfig.validate():
            print("WARNING: Xray integration is not properly configured. "
                  "Tests will run but results won't be uploaded to Xray.")
            self.enabled = False
        else:
            self.enabled = True
            print("Xray Cloud integration enabled")
    
    def start_suite(self, data, result):
        """
        Called when a test suite starts.
        
        Extracts Story ID from suite documentation/metadata.
        
        Args:
            data: Suite data object
            result: Suite result object
        """
        if not self.enabled:
            return
        
        # Extract Story ID from suite documentation
        # Format: @Story: ABC-123
        doc = data.doc if hasattr(data, 'doc') else ""
        
        self.story_id = self._extract_story_id(doc)
        
        if self.story_id:
            print(f"Xray Listener: Found Story ID: {self.story_id}")
        else:
            print("Xray Listener: No Story ID found in suite documentation")
        
        # Store suite metadata
        self.suite_metadata = {
            'name': data.name,
            'doc': doc,
            'source': str(data.source) if hasattr(data, 'source') else ""
        }
        
        # Store test file path for later updates
        if hasattr(data, 'source'):
            self.current_test_file = str(data.source)
    
    def start_test(self, data, result):
        """
        Called when a test case starts.
        
        Creates or retrieves Xray Test for this scenario and uploads test steps.
        
        Args:
            data: Test data object
            result: Test result object
        """
        if not self.enabled or not self.story_id:
            return
        
        scenario_name = data.name
        self.current_test_name = scenario_name
        print(f"\nXray Listener: Processing test: {scenario_name}")
        
        # Reset step tracking
        self.current_test_steps = []
        self.current_step_index = 0
        self.current_test_screenshots = []  # Clear screenshots for new test
        
        try:
            # Check if test already has Xray ID in tags
            xray_key = self._get_xray_id_from_tags(data.tags)
            
            if xray_key:
                # Verify the test exists in Xray
                if self._verify_test_exists(xray_key):
                    print(f"Using existing Xray Test from tags: {xray_key}")
                    self.current_test_key = xray_key
                    self.test_xray_mapping[scenario_name] = xray_key
                else:
                    print(f"WARNING: Test {xray_key} from tags not found in Xray, creating new test")
                    xray_key = None
            
            if not xray_key:
                # Create or get Xray Test
                self.current_test_key = create_or_get_test(scenario_name, self.story_id)
                self.test_xray_mapping[scenario_name] = self.current_test_key
                
                # Update test file with Xray ID
                if self.current_test_file:
                    self._add_xray_tag_to_test(self.current_test_file, scenario_name, self.current_test_key)
                
                # Extract and upload test steps from keywords (only for new tests)
                steps = self._extract_bdd_steps(data)
                self.current_test_steps = steps
                
                if steps:
                    upload_test_steps(self.current_test_key, steps)
                    print(f"✓ Uploaded {len(steps)} test steps to {self.current_test_key}")
            else:
                # For existing tests, just extract steps for result mapping
                steps = self._extract_bdd_steps(data)
                self.current_test_steps = steps
                print(f"ℹ Skipping test steps upload for existing test {xray_key}")
            
        except Exception as e:
            print(f"ERROR: Failed to process test in Xray: {str(e)}")
            self.current_test_key = None
    
    def end_test(self, data, result):
        """
        Called when a test case ends.
        
        Collects test execution results for later upload.
        
        Args:
            data: Test data object
            result: Test result object
        """
        if not self.enabled or not self.current_test_key:
            return
        
        # Map Robot Framework status to Xray status
        status_map = {
            'PASS': 'PASS',
            'FAIL': 'FAIL',
            'SKIP': 'ABORTED'
        }
        
        xray_status = status_map.get(result.status, 'FAIL')
        
        # Create step results based on overall test status
        # All steps get the same status as the test
        step_results = []
        for idx, step in enumerate(self.current_test_steps):
            step_result = {
                'status': xray_status,
                'actual_result': f"Step {idx + 1}: {step['action']} - {result.status}"
            }
            step_results.append(step_result)
        
        # Try to get screenshots from ScreenshotLibrary if available
        try:
            builtin = BuiltIn()
            screenshot_lib = builtin.get_library_instance('ScreenshotLibrary')
            test_screenshots = screenshot_lib.get_test_screenshots()
            
            # Map screenshots to steps based on order captured
            # Distribute screenshots evenly across steps if we have more screenshots than steps
            screenshots_with_steps = []
            num_steps = len(self.current_test_steps)
            
            if num_steps > 0 and test_screenshots:
                screenshots_per_step = len(test_screenshots) / num_steps
                for idx, screenshot in enumerate(test_screenshots):
                    # Assign to step based on proportional position
                    step_index = min(int(idx / screenshots_per_step), num_steps - 1)
                    screenshots_with_steps.append({
                        'path': screenshot,
                        'step_index': step_index
                    })
            else:
                # No steps, attach to test run directly
                for screenshot in test_screenshots:
                    screenshots_with_steps.append({
                        'path': screenshot,
                        'step_index': None
                    })
            
            self.current_test_screenshots = screenshots_with_steps
            screenshot_lib.clear_test_screenshots()
        except:
            # ScreenshotLibrary not available or no screenshots
            pass
        
        # Collect test result
        test_result = {
            'test_key': self.current_test_key,
            'scenario_name': data.name,
            'status': xray_status,
            'actual_result': result.message if result.message else f"Test {result.status}",
            'step_results': step_results,
            'execution_time': result.elapsedtime,  # milliseconds
            'start_time': result.starttime,
            'end_time': result.endtime,
            'screenshots': self.current_test_screenshots[:]  # Screenshots with step mapping
        }
        
        self.test_results.append(test_result)
        
        print(f"Xray Listener: Test {self.current_test_key} completed with status: {xray_status}")
    
    def end_suite(self, data, result):
        """
        Called when a test suite ends.
        
        Uploads execution results and attachments to Xray.
        
        Args:
            data: Suite data object
            result: Suite result object
        """
        if not self.enabled or not self.test_results:
            return
        
        print("\n" + "="*80)
        print("Xray Listener: Uploading execution results to Xray Cloud")
        print("="*80)
        
        try:
            # Determine output directory
            try:
                builtin = BuiltIn()
                self.output_dir = builtin.get_variable_value("${OUTPUT_DIR}", "output")
            except:
                self.output_dir = os.getenv("ROBOT_OUTPUT_DIR", "output")
            
            # Collect attachments
            attachments = self._collect_attachments()
            
            # Upload execution results using GraphQL API
            test_exec_key = update_execution_results(
                test_results=self.test_results,
                attachments=attachments
            )
            
            if test_exec_key:
                print(f"\n{'='*80}")
                print(f"Xray Listener: Successfully uploaded execution to Test Execution: {test_exec_key}")
                print(f"{'='*80}\n")
            else:
                print(f"\nWARNING: Failed to create Test Execution\n")
            
        except Exception as e:
            print(f"\nERROR: Failed to upload execution results to Xray: {str(e)}\n")
    
    def _extract_story_id(self, text: str) -> Optional[str]:
        """
        Extract Story ID from text in format @Story: ABC-123.
        
        Args:
            text: Text to search for Story ID
            
        Returns:
            Optional[str]: Story ID if found, None otherwise
        """
        if not text:
            return None
        
        # Pattern: @Story: ABC-123 or @Story:ABC-123
        pattern = r'@Story:\s*([A-Z]+-\d+)'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            return match.group(1)
        
        return None
    
    def _extract_bdd_steps(self, test_data) -> List[Dict[str, str]]:
        """
        Extract BDD steps from Robot Framework test keywords.
        
        Args:
            test_data: Robot Framework test data object
            
        Returns:
            List[Dict[str, str]]: List of step dictionaries
        """
        steps = []
        
        if not hasattr(test_data, 'body'):
            return steps
        
        for item in test_data.body:
            # Check if it's a keyword
            if hasattr(item, 'name'):
                keyword_name = item.name
                
                # Check if it's a BDD keyword (Given, When, Then, And, But)
                bdd_keywords = ['Given', 'When', 'Then', 'And', 'But']
                
                is_bdd = False
                step_text = keyword_name
                
                for bdd_kw in bdd_keywords:
                    if keyword_name.startswith(bdd_kw + ' '):
                        is_bdd = True
                        break
                
                if is_bdd or len(steps) == 0:  # Include first keyword even if not BDD
                    # Extract arguments if present
                    args = []
                    if hasattr(item, 'args'):
                        args = [str(arg) for arg in item.args]
                    
                    step_data = ""
                    if args:
                        step_data = " | ".join(args)
                    
                    step = {
                        "action": step_text,
                        "data": step_data,
                        "result": ""
                    }
                    
                    steps.append(step)
        
        return steps
    
    def _collect_attachments(self) -> List[str]:
        """
        Collect attachment files from output directory.
        
        Returns:
            List[str]: List of file paths to attach
        """
        attachments = []
        
        # Common Robot Framework output files
        standard_files = ['log.html', 'report.html']
        
        for filename in standard_files:
            filepath = os.path.join(self.output_dir, filename)
            if os.path.exists(filepath):
                attachments.append(filepath)
        
        # Look for screenshots
        screenshot_patterns = ['*.png', '*.jpg', '*.jpeg']
        
        output_path = Path(self.output_dir)
        for pattern in screenshot_patterns:
            for screenshot in output_path.glob(pattern):
                attachments.append(str(screenshot))
        
        # Look for PDF reports
        for pdf in output_path.glob('*.pdf'):
            attachments.append(str(pdf))
        
        return attachments
    
    def _update_test_result(self, test_key: str, status: str, message: str):
        """
        Update test result by adding a comment with execution status.
        
        Args:
            test_key: Test issue key
            status: Execution status (PASSED/FAILED/ABORTED)
            message: Result message
        """
        import base64
        from .config import XrayConfig
        
        try:
            comment_url = XrayConfig.get_jira_url(f"issue/{test_key}/comment")
            
            auth = base64.b64encode(
                f"{XrayConfig.JIRA_USER_EMAIL}:{XrayConfig.JIRA_API_TOKEN}".encode()
            ).decode()
            
            headers = {
                "Authorization": f"Basic {auth}",
                "Content-Type": "application/json"
            }
            
            status_emoji = "✅" if status == "PASSED" else ("❌" if status == "FAILED" else "⚠️")
            result_text = f"Test Execution Result: {status_emoji} {status}\\n\\n"
            if message:
                result_text += f"Message: {message}\\n"
            result_text += f"\\nExecuted on: {os.getenv('COMPUTERNAME', 'Unknown')}"
            
            payload = {
                "body": result_text
            }
            
            import requests
            import json
            response = requests.post(
                comment_url,
                headers=headers,
                data=json.dumps(payload),
                timeout=30
            )
            
            if response.ok:
                print(f"  ✓ Updated test result in {test_key}")
            
        except Exception as e:
            print(f"  WARNING: Could not update test result: {str(e)}")
    
    def log_message(self, message):
        """
        Called when a log message is emitted.
        
        Can be used to capture screenshot paths or other evidence.
        
        Args:
            message: Log message object
        """
        # Could be extended to capture specific evidence during test execution
        pass
    
    def _get_xray_id_from_tags(self, tags) -> Optional[str]:
        """
        Extract Xray test ID from test tags.
        
        Looks for tags in format: xray:XSP-123 or xray-XSP-123
        
        Args:
            tags: Test tags list
            
        Returns:
            Xray test key if found, None otherwise
        """
        if not tags:
            return None
        
        for tag in tags:
            tag_str = str(tag)
            # Match xray:XSP-123 or xray-XSP-123
            match = re.match(r'xray[:-]([A-Z]+-\d+)', tag_str, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _verify_test_exists(self, test_key: str) -> bool:
        """
        Verify that a test exists in Xray.
        
        Args:
            test_key: Xray test key (e.g., XSP-123)
            
        Returns:
            True if test exists, False otherwise
        """
        try:
            from .test_manager import get_test_by_key
            test = get_test_by_key(test_key)
            return test is not None
        except Exception as e:
            print(f"WARNING: Error verifying test {test_key}: {str(e)}")
            return False
    
    def _add_xray_tag_to_test(self, file_path: str, test_name: str, xray_key: str):
        """
        Add Xray test ID tag to the test case in the Robot Framework file.
        
        Args:
            file_path: Path to the .robot file
            test_name: Name of the test case
            xray_key: Xray test key (e.g., XSP-123)
        """
        try:
            if not os.path.exists(file_path):
                print(f"WARNING: Test file not found: {file_path}")
                return
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find the test case and add xray tag
            # Pattern: test_name followed by optional [Documentation] or [Tags] on next lines
            pattern = rf'^({re.escape(test_name)})\s*$'
            
            lines = content.split('\n')
            updated = False
            
            for i, line in enumerate(lines):
                if re.match(pattern, line.strip()):
                    # Found the test case
                    # Look ahead to find [Documentation] and/or [Tags]
                    j = i + 1
                    doc_end = -1
                    tags_line = -1
                    
                    # Scan next few lines for [Documentation] and [Tags]
                    while j < len(lines) and j < i + 10:
                        stripped = lines[j].strip()
                        if stripped.startswith('[Documentation]'):
                            doc_end = j
                            # Continue scanning for continuation lines
                            while j + 1 < len(lines) and lines[j + 1].strip().startswith('...'):
                                j += 1
                                doc_end = j
                        elif stripped.startswith('[Tags]'):
                            tags_line = j
                            break
                        elif stripped and not stripped.startswith('...') and not stripped.startswith('['):
                            # Hit a keyword, stop scanning
                            break
                        j += 1
                    
                    # Now update based on what we found
                    if tags_line != -1:
                        # Found existing [Tags] line - append xray tag
                        if f'xray:{xray_key}' not in lines[tags_line] and f'xray-{xray_key}' not in lines[tags_line]:
                            lines[tags_line] = lines[tags_line].rstrip() + f'    xray:{xray_key}'
                            updated = True
                    elif doc_end != -1:
                        # Has documentation but no tags - insert [Tags] after doc
                        indent = '    '
                        lines.insert(doc_end + 1, f'{indent}[Tags]    xray:{xray_key}')
                        updated = True
                    else:
                        # No [Documentation] or [Tags], add [Tags] after test name
                        indent = '    '
                        lines.insert(i + 1, f'{indent}[Tags]    xray:{xray_key}')
                        updated = True
                    break
            
            if updated:
                # Write back to file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
                print(f"✓ Updated test file with Xray ID: {xray_key}")
            else:
                print(f"WARNING: Could not find test case '{test_name}' in file to add Xray tag")
                
        except Exception as e:
            print(f"WARNING: Error updating test file with Xray tag: {str(e)}")
