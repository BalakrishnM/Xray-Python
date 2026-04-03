"""
Browser Options Fixer - Robot Framework listener that patches SeleniumLibrary.

This module fixes the common issue where string values are passed to the options parameter
instead of proper ChromeOptions/FirefoxOptions objects.
"""

from robot.libraries.BuiltIn import BuiltIn
from selenium import webdriver


class BrowserOptionsFixer:
    """Robot Framework listener to fix browser options issues."""
    
    ROBOT_LISTENER_API_VERSION = 3
    
    def __init__(self):
        self.ROBOT_LIBRARY_SCOPE = 'GLOBAL'
        self._patched = False
    
    def start_suite(self, data, result):
        """Called when a test suite starts. Patch SeleniumLibrary here."""
        if not self._patched:
            self._patch_selenium_library()
            self._patched = True
    
    def _patch_selenium_library(self):
        """Patches SeleniumLibrary.open_browser to handle string options."""
        try:
            from SeleniumLibrary.keywords import BrowserManagementKeywords
            
            # Store original method
            original_method = BrowserManagementKeywords.open_browser
            
            def patched_open_browser(self, url, browser='Firefox', alias=None, 
                                    remote_url=False, desired_capabilities=None, 
                                    ff_profile_dir=None, options=None, service_log_path=None,
                                    executable_path=None):
                """Patched version that converts string options to proper objects."""
                
                # If options is a string, convert it to proper options object or remove it
                if options is not None and isinstance(options, str):
                    browser_lower = browser.lower() if isinstance(browser, str) else 'chrome'
                    
                    if 'chrome' in browser_lower:
                        options = webdriver.ChromeOptions()
                        options.add_argument('--disable-gpu')
                        options.add_argument('--no-sandbox')
                        options.add_argument('--disable-dev-shm-usage')
                        print(f"[BrowserOptionsFixer] Created ChromeOptions object")
                    elif 'firefox' in browser_lower:
                        options = webdriver.FirefoxOptions()
                        print(f"[BrowserOptionsFixer] Created FirefoxOptions object")
                    elif 'edge' in browser_lower:
                        options = webdriver.EdgeOptions()
                        print(f"[BrowserOptionsFixer] Created EdgeOptions object")
                    else:
                        # If we can't determine browser, remove options parameter
                        options = None
                        print(f"[BrowserOptionsFixer] Removed invalid string options")
                
                # Call original method with fixed options
                return original_method(self, url, browser, alias, remote_url, 
                                     desired_capabilities, ff_profile_dir, options,
                                     service_log_path, executable_path)
            
            # Replace the method
            BrowserManagementKeywords.open_browser = patched_open_browser
            print("[BrowserOptionsFixer] Successfully patched SeleniumLibrary")
            
        except ImportError as e:
            print(f"[BrowserOptionsFixer] SeleniumLibrary not found: {e}")
        except Exception as e:
            print(f"[BrowserOptionsFixer] Failed to patch: {e}")


# For direct import and auto-patching
def patch_now():
    """Immediately patch SeleniumLibrary if it's already imported."""
    try:
        from SeleniumLibrary.keywords import BrowserManagementKeywords
        
        # Check if already patched
        if hasattr(BrowserManagementKeywords.open_browser, '__name__') and \
           'patched' in BrowserManagementKeywords.open_browser.__name__:
            print("[BrowserOptionsFixer] Already patched")
            return
        
        # Store original method
        original_method = BrowserManagementKeywords.open_browser
        
        def patched_open_browser(self, url, browser='Firefox', alias=None, 
                                remote_url=False, desired_capabilities=None, 
                                ff_profile_dir=None, options=None, service_log_path=None,
                                executable_path=None):
            """Patched version that converts string options to proper objects."""
            
            # If options is a string, convert it to proper options object or remove it
            if options is not None and isinstance(options, str):
                browser_lower = browser.lower() if isinstance(browser, str) else 'chrome'
                
                if 'chrome' in browser_lower:
                    options = webdriver.ChromeOptions()
                    options.add_argument('--disable-gpu')
                    options.add_argument('--no-sandbox')
                    options.add_argument('--disable-dev-shm-usage')
                elif 'firefox' in browser_lower:
                    options = webdriver.FirefoxOptions()
                elif 'edge' in browser_lower:
                    options = webdriver.EdgeOptions()
                else:
                    # If we can't determine browser, remove options parameter
                    options = None
            
            # Call original method with fixed options
            return original_method(self, url, browser, alias, remote_url, 
                                 desired_capabilities, ff_profile_dir, options,
                                 service_log_path, executable_path)
        
        # Replace the method
        BrowserManagementKeywords.open_browser = patched_open_browser
        print("[BrowserOptionsFixer] Successfully patched SeleniumLibrary")
        
    except ImportError:
        print("[BrowserOptionsFixer] SeleniumLibrary not yet loaded")
    except Exception as e:
        print(f"[BrowserOptionsFixer] Failed to patch: {e}")


# Auto-patch when module is imported
patch_now()
