*** Settings ***
Documentation    Common browser configuration and setup keywords
Library          SeleniumLibrary

*** Variables ***
# Browser Configuration
${DEFAULT_BROWSER}       Chrome
${HEADLESS}              False
${BROWSER_WIDTH}         1920
${BROWSER_HEIGHT}        1080

# Browser Options (for headless, performance, etc.)
${CHROME_OPTIONS}        add_argument("--disable-gpu");add_argument("--no-sandbox");add_argument("--disable-dev-shm-usage")
${FIREFOX_OPTIONS}       add_argument("--headless")

# Timeouts
${DEFAULT_TIMEOUT}       10s
${PAGE_LOAD_TIMEOUT}     30s

*** Keywords ***
Open Browser With Options
    [Arguments]    ${url}    ${browser}=${DEFAULT_BROWSER}    ${headless}=${HEADLESS}
    [Documentation]    Opens browser with common options
    ...                Action: Open browser with specified configuration
    ...                Data: URL=${url}, Browser=${browser}, Headless=${headless}
    ...                Expected Result: Browser opens and navigates to URL
    
    # Set browser options based on browser type
    ${options}=    Create Browser Options    ${browser}    ${headless}
    
    # Open browser
    Run Keyword If    '${options}' != 'NONE'
    ...    Open Browser    ${url}    ${browser}    options=${options}
    ...    ELSE
    ...    Open Browser    ${url}    ${browser}
    
    # Set window size
    Set Window Size    ${BROWSER_WIDTH}    ${BROWSER_HEIGHT}
    
    # Set timeouts
    Set Selenium Timeout    ${DEFAULT_TIMEOUT}
    Set Selenium Page Load Timeout    ${PAGE_LOAD_TIMEOUT}

Create Browser Options
    [Arguments]    ${browser}    ${headless}
    [Documentation]    Creates browser-specific options
    
    ${options}=    Set Variable    NONE
    
    # Chrome options
    Run Keyword If    '${browser}' == 'Chrome' or '${browser}' == 'chrome'
    ...    Set Variable    ${CHROME_OPTIONS}
    
    # Firefox options
    Run Keyword If    '${browser}' == 'Firefox' or '${browser}' == 'firefox'
    ...    Set Variable    ${FIREFOX_OPTIONS}
    
    # Add headless mode if enabled
    ${options}=    Run Keyword If    '${headless}' == 'True'
    ...    Set Variable    ${options};add_argument("--headless")
    ...    ELSE
    ...    Set Variable    ${options}
    
    [Return]    ${options}

Open Chrome Browser
    [Arguments]    ${url}
    [Documentation]    Opens Chrome browser with default settings
    ...                Action: Open Chrome browser
    ...                Data: URL = ${url}
    ...                Expected Result: Chrome browser opens to URL
    Open Browser    ${url}    Chrome
    Maximize Browser Window
    Set Selenium Timeout    ${DEFAULT_TIMEOUT}

Open Firefox Browser
    [Arguments]    ${url}
    [Documentation]    Opens Firefox browser with default settings
    ...                Action: Open Firefox browser
    ...                Data: URL = ${url}
    ...                Expected Result: Firefox browser opens to URL
    Open Browser    ${url}    Firefox
    Maximize Browser Window
    Set Selenium Timeout    ${DEFAULT_TIMEOUT}

Open Headless Chrome
    [Arguments]    ${url}
    [Documentation]    Opens Chrome in headless mode (no UI)
    ...                Action: Open Chrome in headless mode
    ...                Data: URL = ${url}
    ...                Expected Result: Chrome opens without UI
    ${chrome_options}=    Evaluate    sys.modules['selenium.webdriver'].ChromeOptions()    sys, selenium.webdriver
    Call Method    ${chrome_options}    add_argument    --headless
    Call Method    ${chrome_options}    add_argument    --disable-gpu
    Call Method    ${chrome_options}    add_argument    --no-sandbox
    Create Webdriver    Chrome    options=${chrome_options}
    Go To    ${url}
    Set Selenium Timeout    ${DEFAULT_TIMEOUT}
