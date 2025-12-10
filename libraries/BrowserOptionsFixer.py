"""
Browser Options Fixer - Monkey patches SeleniumLibrary to handle string options correctly.

This module fixes the common issue where string values are passed to the options parameter
instead of proper ChromeOptions/FirefoxOptions objects.
"""

import sys
from selenium import webdriver


def patch_selenium_library():
    """
    Patches SeleniumLibrary.open_browser to handle string options gracefully.
    This prevents the 'str object has no attribute add_argument' error.
    """
    try:
        from SeleniumLibrary import SeleniumLibrary
        
        # Store original open_browser method
        original_open_browser = SeleniumLibrary.open_browser
        
        def patched_open_browser(self, url, browser='Firefox', alias=None, 
                                remote_url=False, desired_capabilities=None, 
                                ff_profile_dir=None, options=None, service_log_path=None,
                                executable_path=None):
            """
            Patched version that converts string options to proper objects.
            """
            # If options is a string, convert it to proper options object
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
                    # If we can't determine browser, set options to None
                    options = None
                
                print(f"[BrowserOptionsFixer] Converted string options to proper {browser} options object")
            
            # Call original method with fixed options
            return original_open_browser(self, url, browser, alias, remote_url, 
                                       desired_capabilities, ff_profile_dir, options,
                                       service_log_path, executable_path)
        
        # Replace the method
        SeleniumLibrary.open_browser = patched_open_browser
        print("[BrowserOptionsFixer] Successfully patched SeleniumLibrary.open_browser")
        
    except ImportError:
        print("[BrowserOptionsFixer] Warning: SeleniumLibrary not found, skipping patch")
    except Exception as e:
        print(f"[BrowserOptionsFixer] Warning: Failed to patch SeleniumLibrary: {e}")


# Auto-patch when module is imported
patch_selenium_library()
