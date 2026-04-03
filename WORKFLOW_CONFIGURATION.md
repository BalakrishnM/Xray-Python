# Workflow Status Configuration Guide

This guide explains how to configure test workflow statuses for different Jira projects.

## Overview

Different Jira projects may have different workflow configurations. The Xray integration needs to know which statuses allow test execution and which statuses block it.

## Configuration Variables

Add these to your `.env` file or environment variables:

### TEST_TARGET_STATUS
**The ideal status for tests before execution**

- This should be the **last status before "Completed"** in your workflow
- Tests will be automatically transitioned to this status when created
- Default: `Non GXP`

### TEST_EXECUTION_READY_STATUSES
**Comma-separated list of acceptable statuses for test execution**

- Fallback statuses if the target status cannot be reached
- Listed in priority order (first = most preferred)
- Default: `In Progress,Open`

### TEST_BLOCKED_STATUSES
**Comma-separated list of statuses that prevent test execution**

- Tests in these statuses **cannot** be included in Test Executions
- Typically includes completion statuses
- Default: `Completed,Done,Closed,Finished`

---

## Common Workflow Examples

### Example 1: Standard Xray Workflow
**Workflow:** `To Do → In Progress → Ready → Done`

```bash
TEST_TARGET_STATUS=Ready
TEST_EXECUTION_READY_STATUSES=In Progress,To Do
TEST_BLOCKED_STATUSES=Done,Closed
```

### Example 2: GXP Workflow (4-stage)
**Workflow:** `Open → In Progress → Non GXP → Completed`

```bash
TEST_TARGET_STATUS=Non GXP
TEST_EXECUTION_READY_STATUSES=In Progress,Open
TEST_BLOCKED_STATUSES=Completed,Done,Closed,Finished
```

### Example 3: Approval-Based Workflow
**Workflow:** `Draft → Review → Approved → Closed`

```bash
TEST_TARGET_STATUS=Approved
TEST_EXECUTION_READY_STATUSES=Review,Draft
TEST_BLOCKED_STATUSES=Closed,Archived,Cancelled
```

### Example 4: Simple 3-Stage Workflow
**Workflow:** `Open → Ready → Done`

```bash
TEST_TARGET_STATUS=Ready
TEST_EXECUTION_READY_STATUSES=Open
TEST_BLOCKED_STATUSES=Done,Completed,Closed
```

---

## How It Works

### 1. Test Creation
When a new test is created, the system will:
1. Create the test in the default status (usually "Open")
2. Attempt to transition it to `TEST_TARGET_STATUS`
3. If that fails, try to reach any status in `TEST_EXECUTION_READY_STATUSES`
4. Stop at the highest reachable status

### 2. Status Checking
Before creating a Test Execution, the system checks:
- ✅ Test is in `TEST_TARGET_STATUS` or any `TEST_EXECUTION_READY_STATUSES` → **Allowed**
- ❌ Test is in any `TEST_BLOCKED_STATUSES` → **Blocked** (error will occur)

### 3. Multi-Step Transitions
If your workflow requires multiple steps to reach the target status, the system will:
1. Get all available transitions from current status
2. Try to move toward the target status
3. Repeat up to 5 times (prevents infinite loops)
4. Stop when target status or execution-ready status is reached

---

## Troubleshooting

### Error: "Issues not allowed to be executed due to their workflow status"

**Cause:** Tests are in a blocked status (e.g., "Completed", "Done")

**Solution:**
1. Check your workflow: What statuses exist?
2. Identify the last status **before** completion
3. Set `TEST_TARGET_STATUS` to that status
4. Add intermediate statuses to `TEST_EXECUTION_READY_STATUSES`

**Example:**
```bash
# Your workflow: Open → Testing → Completed
TEST_TARGET_STATUS=Testing
TEST_EXECUTION_READY_STATUSES=Open
TEST_BLOCKED_STATUSES=Completed,Done
```

### Error: "Could not transition test to target status"

**Cause:** Workflow permissions or missing transitions

**Solution:**
1. Verify the status exists in your project
2. Check transition permissions (can tests move from "Open" to "Ready"?)
3. Add intermediate statuses to help the transition path
4. Check Jira logs for specific transition errors

### Tests Not Being Created

**Cause:** Invalid `TEST_TARGET_STATUS` value

**Solution:**
1. Use exact status name (case-insensitive, but should match)
2. Check for typos: "Non GXP" vs "NonGXP" vs "Non-GXP"
3. Verify status exists in your Jira project settings

---

## Finding Your Workflow Statuses

### Method 1: Jira UI
1. Go to your Jira project
2. Navigate to **Project Settings** → **Workflows**
3. Click on the workflow for "Test" issue type
4. Note all status names and transitions

### Method 2: Create a Test Manually
1. Create a test manually in Jira
2. Click on the status dropdown
3. Note all available statuses
4. The second-to-last status is usually your `TEST_TARGET_STATUS`

### Method 3: Check Logs
Run your automation and check the output:
```
Available transitions from 'Open':
  - Start Progress → In Progress
  - Move to Non GXP → Non GXP
  - Complete → Completed
```

Choose "Non GXP" as `TEST_TARGET_STATUS` in this case.

---

## Best Practices

1. **Always set TEST_TARGET_STATUS** to the last status before completion
2. **Include intermediate statuses** in `TEST_EXECUTION_READY_STATUSES` for flexibility
3. **Test the configuration** with a single test first
4. **Document your workflow** in your project README
5. **Use .env file** instead of hardcoding values

---

## Example .env File

```bash
# Xray Cloud API Credentials
XRAY_CLIENT_ID=your-client-id-here
XRAY_CLIENT_SECRET=your-client-secret-here

# Jira Cloud Configuration
JIRA_BASE_URL=https://yourcompany.atlassian.net
JIRA_USER_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-jira-api-token-here

# Xray Project Configuration
XRAY_PROJECT_KEY=ABC

# Workflow Status Configuration
# For workflow: Open > In Progress > Non GXP > Completed
TEST_TARGET_STATUS=Non GXP
TEST_EXECUTION_READY_STATUSES=In Progress,Open
TEST_BLOCKED_STATUSES=Completed,Done,Closed,Finished
```

---

## Need Help?

If you're still having issues:
1. Check the console output for detailed transition logs
2. Verify your Jira workflow configuration
3. Ensure you have permissions to transition tests
4. Review the Xray documentation for your specific workflow requirements
