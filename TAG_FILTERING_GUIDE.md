# Tag Filtering and Xray Control Guide

This guide explains how to run specific tests using tags and how to control Xray integration.

---

## Running Tests with Tags

### Basic Tag Filtering

Use tags to organize and run specific subsets of tests:

```bash
# Run only smoke tests
python run.py tests/ --tags smoke

# Run multiple tags (OR logic - smoke OR regression)
python run.py tests/ --tags smoke,regression

# Run from specific directory with tags
python run.py tests/login/ --tags smoke
```

### Using Robot Framework Directly

```bash
# Include tests with specific tag
robot --include smoke --outputdir output tests/

# Include multiple tags (OR logic)
robot --include smokeORregression --outputdir output tests/

# Exclude specific tags
robot --exclude slow --outputdir output tests/

# Combine include and exclude
robot --include smoke --exclude wip --outputdir output tests/
```

---

## Common Tag Strategies

### By Priority/Importance

```robot
*** Test Cases ***
Critical User Login
    [Tags]    critical    smoke
    ...

Important Data Validation  
    [Tags]    important    regression
    ...

Nice To Have Feature
    [Tags]    low-priority
    ...
```

Run critical tests:
```bash
python run.py tests/ --tags critical
```

### By Feature Area

```robot
*** Test Cases ***
Login Functionality
    [Tags]    login    authentication
    ...

User Profile Management
    [Tags]    profile    user-management
    ...

Payment Processing
    [Tags]    payment    checkout
    ...
```

Run all login tests:
```bash
python run.py tests/ --tags login
```

### By Test Type

```robot
*** Test Cases ***
API Endpoint Test
    [Tags]    api    smoke
    ...

UI Interaction Test
    [Tags]    ui    regression
    ...

Integration Test
    [Tags]    integration    slow
    ...
```

Run only API tests:
```bash
python run.py tests/ --tags api
```

### By Environment

```robot
*** Test Cases ***
Production Safe Test
    [Tags]    prod-safe    smoke
    ...

Test Environment Only
    [Tags]    test-only    destructive
    ...
```

Run production-safe tests:
```bash
python run.py tests/ --tags prod-safe
```

---

## Skipping Xray Integration

### Use Cases

- **Local development**: Test your Robot Framework code without Xray overhead
- **Debugging**: Focus on test logic without external integrations
- **No credentials**: Run tests when Xray credentials aren't available
- **Quick feedback**: Faster test execution without API calls

### Methods to Skip Xray

#### Method 1: Command Line Flag (Recommended)

```bash
# Skip Xray using --skip-xray flag
python run.py tests/ --skip-xray

# Combine with tags
python run.py tests/ --tags smoke --skip-xray
```

#### Method 2: Environment Variable

```bash
# Linux/Mac
export SKIP_XRAY=true
python run.py tests/

# Windows PowerShell
$env:SKIP_XRAY = "true"
python run.py tests/

# Windows CMD
set SKIP_XRAY=true
python run.py tests/
```

#### Method 3: .env File

Edit `.env`:
```bash
SKIP_XRAY=true
```

Then run normally:
```bash
python run.py tests/
```

#### Method 4: Robot Framework Without Listener

```bash
# Simply don't use the Xray listener
robot --outputdir output tests/
```

---

## Practical Examples

### Development Workflow

```bash
# 1. Local development - run smoke tests quickly
python run.py tests/ --tags smoke --skip-xray

# 2. Debug specific test without Xray
python run.py tests/login_test.robot --skip-xray

# 3. Full local regression
python run.py tests/ --tags regression --skip-xray

# 4. Ready for CI - run with Xray integration
python run.py tests/ --tags smoke
```

### CI/CD Pipeline

```yaml
# GitHub Actions example
jobs:
  smoke-tests:
    runs-on: ubuntu-latest
    steps:
      - name: Run smoke tests
        run: python run.py tests/ --tags smoke
        env:
          XRAY_CLIENT_ID: ${{ secrets.XRAY_CLIENT_ID }}
          # ... other Xray credentials

  local-validation:
    runs-on: ubuntu-latest
    steps:
      - name: Quick validation (no Xray)
        run: python run.py tests/ --tags smoke --skip-xray
```

### Team Scenarios

**QA Engineer (needs Xray reporting):**
```bash
python run.py tests/ --tags regression
```

**Developer (local testing):**
```bash
python run.py tests/ --tags smoke --skip-xray
```

**CI System (full test suite):**
```bash
python run.py tests/
```

---

## Tag Naming Conventions

### Recommended Tags

| Tag | Purpose | Example |
|-----|---------|---------|
| `smoke` | Critical path tests | Login, basic navigation |
| `regression` | Full feature coverage | All functionality |
| `api` | API/backend tests | REST endpoints |
| `ui` | User interface tests | Button clicks, forms |
| `integration` | Multi-system tests | Database + API |
| `slow` | Long-running tests | Performance tests |
| `wip` | Work in progress | Tests under development |
| `bug-{id}` | Bug reproduction | `bug-123`, `bug-456` |

### Example Test Organization

```robot
*** Settings ***
Documentation    Login functionality tests
...              @Story: PRJ-123

*** Test Cases ***
Valid Login Works
    [Tags]    smoke    login    critical
    [Documentation]    Critical user login path
    Given user is on login page
    When user enters valid credentials
    Then user is logged in

Invalid Password Shows Error
    [Tags]    regression    login    negative
    [Documentation]    Error handling test
    Given user is on login page
    When user enters invalid password
    Then error message is displayed

SSO Login Integration
    [Tags]    integration    login    slow
    [Documentation]    Third-party SSO integration
    Given user clicks SSO login
    When user authenticates with provider
    Then user is logged in via SSO
```

Run different test sets:
```bash
# Critical tests only
python run.py tests/ --tags critical

# All login tests
python run.py tests/ --tags login

# Everything except slow tests
robot --exclude slow --outputdir output tests/
```

---

## Quick Reference

```bash
# Common Commands

# Run all tests with Xray
python run.py tests/

# Run smoke tests with Xray
python run.py tests/ --tags smoke

# Run smoke tests WITHOUT Xray (local dev)
python run.py tests/ --tags smoke --skip-xray

# Run regression tests
python run.py tests/ --tags regression

# Run multiple tags
python run.py tests/ --tags smoke,critical

# Custom output directory
python run.py tests/ --output build/results/

# Combine everything
python run.py tests/login/ --tags smoke --skip-xray --output results/
```

---

## Tips and Best Practices

1. **Keep tags simple**: Use short, descriptive tag names
2. **Be consistent**: Agree on tag naming with your team
3. **Don't over-tag**: 2-4 tags per test is usually enough
4. **Use smoke for CI**: Fast, critical path tests
5. **Skip Xray locally**: Faster feedback during development
6. **Document tag meanings**: Add to project README

---

## Troubleshooting

### Tags not working?

**Check your test file:**
```robot
*** Test Cases ***
My Test
    [Tags]    smoke    # <-- Tags must be in [Tags] section
    Test steps here
```

**Verify command:**
```bash
# Correct
python run.py tests/ --tags smoke

# Incorrect (old syntax)
python run.py tests/ -t smoke  # Won't work
```

### Xray not being skipped?

**Check environment variable:**
```bash
# PowerShell
$env:SKIP_XRAY

# Linux/Mac
echo $SKIP_XRAY
```

Should show `true` when set.

**Or use the flag:**
```bash
python run.py tests/ --skip-xray  # Most reliable
```
