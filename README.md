# Xray Cloud Integration for Robot Framework

Complete integration module for automatically managing Xray Tests and uploading Robot Framework execution results to Jira Xray Cloud.

## Features

✅ **Automatic Test Creation**: Creates Xray Tests automatically if they don't exist  
✅ **BDD Step Upload**: Uploads BDD scenario steps as Xray Test Steps  
✅ **Story Linking**: Links Xray Tests to predefined Jira Stories  
✅ **Execution Results**: Uploads test execution results with pass/fail status  
✅ **Evidence Attachment**: Attaches logs, screenshots, PDFs, and other evidence  
✅ **Client Credentials Auth**: Uses Xray Cloud Client ID and Client Secret  
✅ **Duplicate Prevention**: Reuses existing tests instead of creating duplicates  

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [Quick Start](#quick-start)
  - [Feature File Format](#feature-file-format)
  - [CI/CD Integration](#cicd-integration)
- [Architecture](#architecture)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

1. **Jira Cloud** instance with **Xray Cloud** installed
2. **Xray API credentials**:
   - Client ID
   - Client Secret
   - Get from: Xray Cloud → Settings → API Keys → Create API Key
3. **Jira API credentials**:
   - User email address
   - Jira API Token (create at: https://id.atlassian.com/manage-profile/security/api-tokens)
4. Python 3.7+ with `requests` library

---

## Installation

1. **Install required Python packages**:

```bash
pip install requests robotframework
```

2. **Project structure** (already created):

```
python_automation_framework/
├── integrations/
│   └── xray/
│       ├── __init__.py
│       ├── auth.py              # Authentication module
│       ├── config.py            # Configuration management
│       ├── test_manager.py      # Test creation and management
│       ├── execution.py         # Execution results upload
│       ├── listener.py          # Robot Framework listener
│       └── utils.py             # Utility functions
├── tests/                       # Your Robot Framework tests
├── run.py                       # CI execution script
└── README.md
```

---

## Configuration

### Environment Variables

Set these environment variables in your system or CI/CD pipeline:

| Variable | Description | Example |
|----------|-------------|---------|
| `XRAY_CLIENT_ID` | Xray Cloud API Client ID | `A1B2C3D4E5F6` |
| `XRAY_CLIENT_SECRET` | Xray Cloud API Client Secret | `secret-key-here` |
| `JIRA_BASE_URL` | Your Jira Cloud instance URL | `https://yourcompany.atlassian.net` |
| `JIRA_USER_EMAIL` | Jira user email address | `user@company.com` |
| `JIRA_API_TOKEN` | Jira API Token | `your-api-token` |
| `XRAY_PROJECT_KEY` | Jira project key for Xray Tests | `ABC` |

#### Workflow Status Configuration (Optional)

Configure workflow statuses to match your project's Jira workflow:

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `TEST_TARGET_STATUS` | Target status for tests to be execution-ready | `Non GXP` | `Ready`, `Approved`, `To Do` |
| `TEST_EXECUTION_READY_STATUSES` | Alternative execution-ready statuses (comma-separated) | `In Progress,Open` | `Ready,Approved,Open` |
| `TEST_BLOCKED_STATUSES` | Statuses that prevent test execution (comma-separated) | `Completed,Done,Closed,Finished` | `Closed,Cancelled` |

**Example workflow configurations:**

**Standard Xray workflow:**
```bash
TEST_TARGET_STATUS=Ready
TEST_EXECUTION_READY_STATUSES=Approved,To Do,Open
TEST_BLOCKED_STATUSES=Completed,Done,Closed
```

**Custom GXP workflow (Open > In Progress > Non GXP > Completed):**
```bash
TEST_TARGET_STATUS=Non GXP
TEST_EXECUTION_READY_STATUSES=In Progress,Open
TEST_BLOCKED_STATUSES=Completed,Done,Closed,Finished
```

> **Important:** The `TEST_TARGET_STATUS` should be the **last status before Completed** in your workflow. Tests in "Completed" or "Done" status cannot be executed.

### Windows PowerShell Setup

```powershell
$env:XRAY_CLIENT_ID = "your-client-id"
$env:XRAY_CLIENT_SECRET = "your-client-secret"
$env:JIRA_BASE_URL = "https://yourcompany.atlassian.net"
$env:JIRA_USER_EMAIL = "user@company.com"
$env:JIRA_API_TOKEN = "your-api-token"
$env:XRAY_PROJECT_KEY = "ABC"

# Optional: Workflow configuration
$env:TEST_TARGET_STATUS = "Non GXP"
$env:TEST_EXECUTION_READY_STATUSES = "In Progress,Open"
$env:TEST_BLOCKED_STATUSES = "Completed,Done,Closed,Finished"
```

### Linux/Mac Setup

```bash
export XRAY_CLIENT_ID="your-client-id"
export XRAY_CLIENT_SECRET="your-client-secret"
export JIRA_BASE_URL="https://yourcompany.atlassian.net"
export JIRA_USER_EMAIL="user@company.com"
export JIRA_API_TOKEN="your-api-token"
export XRAY_PROJECT_KEY="ABC"

# Optional: Workflow configuration
export TEST_TARGET_STATUS="Non GXP"
export TEST_EXECUTION_READY_STATUSES="In Progress,Open"
export TEST_BLOCKED_STATUSES="Completed,Done,Closed,Finished"
```

### Using .env File (Recommended)

Create a `.env` file in your project root:

```bash
# Copy the template
cp .env.template .env

# Edit .env with your credentials and workflow settings
```

Then use a tool like `python-dotenv` to load environment variables:

```bash
pip install python-dotenv
```

### CI/CD Setup (GitHub Actions Example)

```yaml
env:
  XRAY_CLIENT_ID: ${{ secrets.XRAY_CLIENT_ID }}
  XRAY_CLIENT_SECRET: ${{ secrets.XRAY_CLIENT_SECRET }}
  JIRA_BASE_URL: ${{ secrets.JIRA_BASE_URL }}
  JIRA_USER_EMAIL: ${{ secrets.JIRA_USER_EMAIL }}
  JIRA_API_TOKEN: ${{ secrets.JIRA_API_TOKEN }}
  XRAY_PROJECT_KEY: "ABC"
```

---

## Usage

### Quick Start

1. **Add Story ID to your feature file**:

```robot
*** Settings ***
Documentation    @Story: ABC-123
...              This suite tests the login functionality

*** Test Cases ***
User Can Login With Valid Credentials
    Given user is on login page
    When user enters valid credentials
    Then user is logged in successfully
```

2. **Run tests with Xray listener**:

```bash
# Using the provided run.py script (recommended)
python run.py tests/

# Or directly with robot command
robot --listener integrations.xray.XrayListener --outputdir output tests/
```

### Running Tests with Tags

Filter tests by tags to run specific test subsets:

```bash
# Run only smoke tests
python run.py tests/ --tags smoke

# Run multiple tags (smoke OR regression)
python run.py tests/ --tags smoke,regression

# Using robot command directly
robot --listener integrations.xray.XrayListener --include smoke --outputdir output tests/
```

**Example test file with tags:**

```robot
*** Settings ***
Documentation    @Story: ABC-123

*** Test Cases ***
User Can Login
    [Tags]    smoke    login
    Given user is on login page
    When user enters valid credentials
    Then user is logged in

Admin Can Manage Users
    [Tags]    regression    admin
    Given admin is logged in
    When admin creates new user
    Then user appears in list
```

### Running Tests Without Xray Integration

Skip Xray integration to run tests locally without uploading results:

```bash
# Using run.py script
python run.py tests/ --skip-xray

# Or set environment variable
export SKIP_XRAY=true  # Linux/Mac
$env:SKIP_XRAY = "true"  # Windows PowerShell

python run.py tests/

# Using robot command directly (without Xray listener)
robot --outputdir output tests/
```

**Use cases for skipping Xray:**
- Local development and debugging
- Running tests in non-CI environments
- Testing without Xray credentials configured
- Running quick smoke tests without reporting

### Advanced Examples

```bash
# Run smoke tests without Xray
python run.py tests/ --tags smoke --skip-xray

# Run specific test file with custom output directory
python run.py tests/login_tests.robot --output results/

# Run regression tests with Xray integration
python run.py tests/ --tags regression

# Run all tests with Xray in specific output folder
python run.py tests/ --output build/test-results/
```

3. **Check results**:
   - Xray Test created/updated in Jira: `ABC-456` (example)
   - Test Steps uploaded from BDD scenario
   - Test linked to Story: `ABC-123`
   - Execution results uploaded with attachments

### Feature File Format

The Story ID must be in the suite documentation using the `@Story:` tag:

```robot
*** Settings ***
Documentation    @Story: ABC-123
...              Additional documentation can go here
...              Multiple lines are supported

Library          SeleniumLibrary

*** Test Cases ***
Scenario 1: User Login
    [Documentation]    Test user login functionality
    Given user is on login page
    When user enters "username" and "password"
    Then user should see dashboard
```

**Important Notes**:
- Format: `@Story: PROJECT-NUMBER` (e.g., `@Story: ABC-123`)
- Must be in the `*** Settings ***` section under `Documentation`
- Case-insensitive
- Supports variations: `@Story:ABC-123` (no space)

### CI/CD Integration

#### Example run.py Usage

```python
from integrations.xray import XrayListener
from robot import run as robot_run

# Run with Xray integration
exit_code = robot_run(
    '--outputdir', 'output',
    '--listener', 'integrations.xray.XrayListener',
    'tests/'
)
```

#### Jenkins Pipeline Example

```groovy
pipeline {
    agent any
    
    environment {
        XRAY_CLIENT_ID = credentials('xray-client-id')
        XRAY_CLIENT_SECRET = credentials('xray-client-secret')
        JIRA_BASE_URL = 'https://yourcompany.atlassian.net'
        JIRA_USER_EMAIL = credentials('jira-user-email')
        JIRA_API_TOKEN = credentials('jira-api-token')
        XRAY_PROJECT_KEY = 'ABC'
    }
    
    stages {
        stage('Run Tests') {
            steps {
                sh 'python run.py tests/'
            }
        }
    }
    
    post {
        always {
            archiveArtifacts artifacts: 'output/**/*', allowEmptyArchive: true
        }
    }
}
```

---

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────┐
│                  Robot Framework                        │
│                   (Test Execution)                      │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                  XrayListener                           │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 1. Extract @Story: ABC-123 from suite doc       │   │
│  │ 2. Create/get Xray Test for each scenario       │   │
│  │ 3. Upload BDD steps as Test Steps               │   │
│  │ 4. Link Test to Story                           │   │
│  │ 5. Collect execution results                    │   │
│  │ 6. Upload results + attachments at end          │   │
│  └─────────────────────────────────────────────────┘   │
└──────┬──────────────────┬──────────────────┬───────────┘
       │                  │                  │
       ▼                  ▼                  ▼
┌────────────┐    ┌──────────────┐   ┌──────────────┐
│    Auth    │    │ Test Manager │   │  Execution   │
│            │    │              │   │              │
│ • Client   │    │ • Create Test│   │ • Upload XML │
│   ID/Secret│    │ • Upload     │   │ • Attach     │
│ • Bearer   │    │   Steps      │   │   Evidence   │
│   Token    │    │ • Link Story │   │              │
└──────┬─────┘    └──────┬───────┘   └──────┬───────┘
       │                 │                  │
       └────────┬────────┴──────────────────┘
                ▼
    ┌───────────────────────────┐
    │   Xray Cloud REST API     │
    │  + Jira Cloud REST API    │
    └───────────────────────────┘
```

### Workflow

1. **Suite Start**:
   - Extract `@Story: ABC-123` from suite documentation
   - Validate Xray configuration

2. **Test Start** (per scenario):
   - Create or retrieve Xray Test: `"Automation | Scenario Name"`
   - Extract BDD steps from test keywords
   - Upload steps to Xray Test
   - Link Test to Story using Jira issue links

3. **Test End** (per scenario):
   - Collect execution status (PASSED/FAILED/ABORTED)
   - Store actual result message
   - Record execution time

4. **Suite End**:
   - Upload `output.xml` to Xray using Robot Framework import API
   - Attach evidence files (logs, screenshots, PDFs)
   - Create Test Execution in Xray with all results

---

## API Reference

### Authentication

#### `authenticate_xray(client_id, client_secret)`

Authenticate with Xray Cloud and obtain Bearer token.

```python
from integrations.xray import authenticate_xray

token = authenticate_xray(
    client_id="your-client-id",
    client_secret="your-client-secret"
)
# Returns: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Test Management

#### `create_or_get_test(scenario_name, story_id)`

Create new Xray Test or retrieve existing one.

```python
from integrations.xray import create_or_get_test

test_key = create_or_get_test(
    scenario_name="User can login",
    story_id="ABC-123"
)
# Returns: "ABC-456"
```

#### `upload_test_steps(test_key, steps)`

Upload BDD scenario steps to Xray Test.

```python
from integrations.xray import upload_test_steps

steps = [
    {"action": "Given user is on login page", "data": "", "result": ""},
    {"action": "When user enters valid credentials", "data": "", "result": ""},
    {"action": "Then user is logged in", "data": "", "result": "User sees dashboard"}
]

upload_test_steps("ABC-456", steps)
# Returns: True if successful
```

#### `link_test_to_story(test_key, story_id)`

Link Xray Test to Jira Story.

```python
from integrations.xray import link_test_to_story

link_test_to_story("ABC-456", "ABC-123")
# Returns: True if successful
```

### Execution Results

#### `upload_execution_results(robot_output_xml, attachments, info)`

Upload Robot Framework execution results to Xray.

```python
from integrations.xray import upload_execution_results

result = upload_execution_results(
    robot_output_xml="output/output.xml",
    attachments=[
        "output/log.html",
        "output/report.html",
        "screenshots/error.png",
        "reports/test_report.pdf"
    ],
    info={
        "summary": "Nightly regression run",
        "description": "Automated test execution"
    }
)
# Returns: {"testExecIssue": {"key": "ABC-789"}, ...}
```

---

## Troubleshooting

### Common Issues

#### 1. "Xray integration is not properly configured"

**Cause**: Missing environment variables

**Solution**: Verify all required environment variables are set:
```powershell
# Check variables
echo $env:XRAY_CLIENT_ID
echo $env:JIRA_BASE_URL
```

#### 2. "Authentication failed: 401"

**Cause**: Invalid Client ID or Client Secret

**Solution**: 
- Verify credentials in Xray Cloud → Settings → API Keys
- Generate new API key if necessary
- Ensure no extra spaces in credentials

#### 3. "Failed to create test: 400"

**Cause**: Invalid project key or missing Test issue type

**Solution**:
- Verify `XRAY_PROJECT_KEY` matches your Jira project
- Ensure "Test" issue type exists in your project
- Check Xray app is installed and licensed

#### 4. "Failed to link test to story: 400"

**Cause**: Link type "Tests" doesn't exist

**Solution**:
- Create "Tests" link type in Jira settings
- Or use existing link type by modifying `test_manager.py`

#### 5. "output.xml not found"

**Cause**: Test execution finished but output.xml not generated

**Solution**:
- Ensure Robot Framework completes successfully
- Check output directory path is correct
- Verify file permissions

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Then run tests
```

### Manual Testing

Test individual components:

```python
# Test authentication
from integrations.xray import authenticate_xray
token = authenticate_xray()
print(f"Token: {token[:20]}...")

# Test test creation
from integrations.xray import create_or_get_test
test_key = create_or_get_test("Test Scenario", "ABC-123")
print(f"Test Key: {test_key}")
```

---

## Advanced Configuration

### Custom Test Summary Format

Modify `integrations/xray/config.py`:

```python
TEST_SUMMARY_PREFIX = "E2E | "  # Instead of "Automation | "
```

### Token Caching

Tokens are automatically cached for 55 minutes. To force refresh:

```python
from integrations.xray.auth import XrayAuth
XrayAuth.clear_token()
```

### Custom Attachment Collection

Modify `listener.py` `_collect_attachments()` method to add custom files.

---

## Support

For issues or questions:
1. Check [Xray Cloud API Documentation](https://docs.getxray.app/display/XRAYCLOUD/REST+API)
2. Verify [Jira Cloud REST API](https://developer.atlassian.com/cloud/jira/platform/rest/v3/)
3. Review logs in `output/log.html`

---

## License

Internal use only - adapt as needed for your organization.
