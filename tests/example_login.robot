"""Example Robot Framework feature file with Xray integration."""

*** Settings ***
Documentation    Jira-Id: XSP-23
...              This is an example test suite that demonstrates Xray Cloud integration.
...              The Jira-Id tag links all tests in this suite to the specified Jira Story.
...              
...              When executed with the XrayListener, this suite will:
...              1. Create/retrieve Xray Tests for each scenario
...              2. Upload BDD steps as Test Steps
...              3. Link each Test to Story ABC-123
...              4. Upload execution results with attachments

Library          Collections
Library          String
Library          ../libraries/ScreenshotLibrary.py

*** Variables ***
${USERNAME}      testuser
${PASSWORD}      password123
${EXPECTED_MSG}  Login successful

*** Test Cases ***
User Can Login With Valid Credentials
    [Documentation]    Verify that a user can successfully login with valid credentials
    [Tags]    login    smoke    regression    xray:XSP-145
    Given user is on login page
    When user enters valid credentials
    Then user should see success message
    And user should be redirected to dashboard

User Cannot Login With Invalid Password
    [Documentation]    Verify that login fails with incorrect password
    [Tags]    login    negative    regression    xray:XSP-129
    Given user is on login page
    When user enters username "${USERNAME}" and password "wrongpassword"
    Then user should see error message "Invalid credentials"
    And user should remain on login page

User Can Logout Successfully
    [Documentation]    Verify that logged in user can logout
    [Tags]    logout    smoke    xray:XSP-130
    Given user is logged in
    When user clicks logout button
    Then user should see login page
    And session should be terminated

Password Reset Email Is Sent
    [Documentation]    Verify password reset functionality
    [Tags]    password_reset    xray:XSP-131
    Given user is on login page
    When user clicks "Forgot Password" link
    And user enters email "${USERNAME}@example.com"
    And user submits password reset request
    Then user should see confirmation message "Password reset email sent"

*** Keywords ***
User Is On Login Page
    [Documentation]    Navigate to login page
    Log    Navigating to login page
    Capture Page Screenshot    Login Page
    Set Test Variable    ${CURRENT_PAGE}    login

User Enters Valid Credentials
    [Documentation]    Enter valid username and password
    Log    Entering username: ${USERNAME}
    Log    Entering password: ****
    Capture Screenshot    Credentials Entered
    Set Test Variable    ${CREDENTIALS_ENTERED}    True

User Enters Username "${username}" And Password "${password}"
    [Documentation]    Enter specific credentials
    Log    Entering username: ${username}
    Log    Entering password: ${password}
    Capture Screenshot    Invalid Credentials Entry
    Set Test Variable    ${ENTERED_USERNAME}    ${username}
    Set Test Variable    ${ENTERED_PASSWORD}    ${password}

User Should See Success Message
    [Documentation]    Verify success message is displayed
    Log    Verifying success message
    Capture Element Screenshot    Success Message
    Should Be Equal As Strings    ${EXPECTED_MSG}    Login successful

User Should Be Redirected To Dashboard
    [Documentation]    Verify redirection to dashboard
    Log    Verifying redirect to dashboard
    Capture Page Screenshot    Dashboard
    Set Test Variable    ${CURRENT_PAGE}    dashboard

User Should See Error Message "${message}"
    [Documentation]    Verify error message is displayed
    Log    Verifying error message: ${message}
    Capture Element Screenshot    Error Message - Invalid Credentials
    Should Contain    ${message}    Invalid

User Should Remain On Login Page
    [Documentation]    Verify still on login page
    Log    Verifying user is still on login page
    Should Be Equal As Strings    ${CURRENT_PAGE}    login

User Is Logged In
    [Documentation]    Precondition: User is already logged in
    User Is On Login Page
    User Enters Valid Credentials
    Log    User logged in successfully

User Clicks Logout Button
    [Documentation]    Click the logout button
    Log    Clicking logout button
    Capture Screenshot    Logout Button Clicked
    Set Test Variable    ${LOGOUT_CLICKED}    True

User Should See Login Page
    [Documentation]    Verify login page is displayed
    Log    Verifying login page is displayed
    Set Test Variable    ${CURRENT_PAGE}    login

Session Should Be Terminated
    [Documentation]    Verify user session is terminated
    Log    Verifying session is terminated
    Set Test Variable    ${SESSION_ACTIVE}    False

User Clicks "${link}" Link
    [Documentation]    Click a specific link
    Log    Clicking link: ${link}

User Enters Email "${email}"
    [Documentation]    Enter email address
    Log    Entering email: ${email}

User Submits Password Reset Request
    [Documentation]    Submit password reset form
    Log    Submitting password reset request

User Should See Confirmation Message "${message}"
    [Documentation]    Verify confirmation message
    Log    Verifying confirmation: ${message}
    Capture Element Screenshot    Password Reset Confirmation
    Should Contain    ${message}    sent
