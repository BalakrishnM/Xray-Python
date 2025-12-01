# Quick Start Guide - Xray Cloud Integration

## 🚀 Get Started in 5 Minutes

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Configure Xray Credentials

1. **Get Xray API Credentials**:
   - Log in to Jira Cloud
   - Go to Xray Cloud → Settings → API Keys
   - Click "Create API Key"
   - Save the Client ID and Client Secret

2. **Create Jira API Token**:
   - Visit: https://id.atlassian.com/manage-profile/security/api-tokens
   - Click "Create API token"
   - Copy the token

3. **Set Environment Variables**:

**Windows PowerShell**:
```powershell
$env:XRAY_CLIENT_ID = "your-client-id"
$env:XRAY_CLIENT_SECRET = "your-client-secret"
$env:JIRA_BASE_URL = "https://yourcompany.atlassian.net"
$env:JIRA_USER_EMAIL = "your-email@company.com"
$env:JIRA_API_TOKEN = "your-jira-api-token"
$env:XRAY_PROJECT_KEY = "ABC"
```

**Linux/Mac**:
```bash
export XRAY_CLIENT_ID="your-client-id"
export XRAY_CLIENT_SECRET="your-client-secret"
export JIRA_BASE_URL="https://yourcompany.atlassian.net"
export JIRA_USER_EMAIL="your-email@company.com"
export JIRA_API_TOKEN="your-jira-api-token"
export XRAY_PROJECT_KEY="ABC"
```

**Or use .env file** (with python-dotenv):
```bash
cp .env.template .env
# Edit .env and add your credentials
```

### Step 3: Add Story ID to Your Test

Edit your Robot Framework test file:

```robot
*** Settings ***
Documentation    @Story: ABC-123
...              Your test description here

*** Test Cases ***
Your Test Case Name
    Given some precondition
    When some action
    Then some expected result
```

### Step 4: Run Tests

```bash
# Using the provided script
python run.py tests/

# Or directly with robot command
robot --listener integrations.xray.XrayListener --outputdir output tests/
```

### Step 5: Verify in Jira

1. Go to your Jira project
2. Search for "Automation | Your Test Case Name"
3. You should see:
   - ✅ New Xray Test created
   - ✅ Test Steps uploaded
   - ✅ Test linked to your Story
   - ✅ Test Execution with results
   - ✅ Attachments (logs, screenshots)

---

## 🎯 Example Test Run

```bash
# Run the example test
python run.py tests/example_login.robot
```

Expected output:
```
================================================================================
Starting Robot Framework test execution with Xray Cloud integration
================================================================================
Xray Cloud integration enabled
Xray Listener: Found Story ID: ABC-123

Xray Listener: Processing test: User Can Login With Valid Credentials
Creating new Xray Test: Automation | User Can Login With Valid Credentials
Created Xray Test: ABC-456
Uploading 3 test steps to ABC-456...
Successfully uploaded test steps to ABC-456
Linking Test ABC-456 to Story ABC-123...
Successfully linked ABC-456 to ABC-123

================================================================================
Xray Listener: Uploading execution results to Xray Cloud
================================================================================
Uploading Robot Framework execution results from: output/output.xml
Successfully uploaded execution results. Test Execution: ABC-789
Attaching log.html to ABC-789...
Successfully attached log.html
Attaching report.html to ABC-789...
Successfully attached report.html

================================================================================
Xray Listener: Successfully uploaded execution to Test Execution: ABC-789
================================================================================
```

---

## 📚 Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Customize test summary format in `integrations/xray/config.py`
- Add more test cases with `@Story:` tags
- Integrate into your CI/CD pipeline

---

## ❓ Troubleshooting

**Problem**: "Xray integration is not properly configured"
- **Solution**: Check all environment variables are set correctly

**Problem**: "Authentication failed: 401"
- **Solution**: Verify your Xray Client ID and Secret are correct

**Problem**: "Failed to create test: 400"
- **Solution**: Ensure your project has the "Test" issue type and Xray is installed

**Problem**: Tests run but no results in Xray
- **Solution**: Make sure `@Story:` tag is in the suite documentation

For more help, see [README.md](README.md#troubleshooting)
