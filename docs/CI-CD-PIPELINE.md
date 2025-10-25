# CI/CD Pipeline Documentation

## Overview

This project uses **GitHub Actions** for continuous integration and continuous deployment (CI/CD). The pipeline automatically runs tests, checks code quality, and validates changes on every push and pull request.

**Workflow File:** `.github/workflows/tests.yml`

---

## Pipeline Triggers

The CI/CD pipeline runs automatically on:

### 1. Push Events
```yaml
on:
  push:
    branches: [ main, develop ]
```

Triggers when code is pushed to:
- `main` branch (production)
- `develop` branch (development)

### 2. Pull Request Events
```yaml
on:
  pull_request:
    branches: [ main, develop ]
```

Triggers when a pull request is opened or updated targeting:
- `main` branch
- `develop` branch

### 3. Manual Trigger
You can also manually trigger the workflow from the GitHub Actions tab.

---

## Pipeline Jobs

The pipeline consists of two main jobs that run in sequence:

```
┌─────────────────┐
│   test job      │  ← Runs unit + integration tests
│   (required)    │
└────────┬────────┘
         │
         │ (only if test passes)
         ▼
┌─────────────────┐
│  e2e-test job   │  ← Runs end-to-end tests
│   (optional)    │
└─────────────────┘
```

---

## Job 1: Test (Unit + Integration Tests)

### Purpose
Run fast unit and integration tests to validate code changes.

### Steps Breakdown

#### 1. Checkout Repository
```yaml
- name: Checkout repository
  uses: actions/checkout@v4
```

**What it does:** Downloads your code from GitHub so the workflow can access it.

#### 2. Set up Python
```yaml
- name: Set up Python ${{ matrix.python-version }}
  uses: actions/setup-python@v4
  with:
    python-version: ${{ matrix.python-version }}
```

**What it does:** Installs Python 3.11 (defined in strategy.matrix).

**Why:** Ensures consistent Python version across all test runs.

#### 3. Cache pip Dependencies
```yaml
- name: Cache pip dependencies
  uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('requirements-dev.txt') }}
```

**What it does:** Caches Python packages to speed up future runs.

**Why:** Installing dependencies can take 1-2 minutes. Caching reduces this to seconds.

**Cache Key:** Based on OS and `requirements-dev.txt` content. Cache invalidates when dependencies change.

#### 4. Install Dependencies
```yaml
- name: Install dependencies
  run: |
    python -m pip install --upgrade pip
    pip install -r requirements-dev.txt
```

**What it does:**
- Upgrades pip to latest version
- Installs all development dependencies (pytest, playwright, coverage, etc.)

**Dependencies include:**
- pytest, pytest-cov, pytest-asyncio, pytest-mock
- playwright (for E2E tests)
- fastapi, uvicorn
- sqlalchemy, pydantic
- All production dependencies

#### 5. Install Playwright Browsers
```yaml
- name: Install Playwright browsers
  run: |
    python -m playwright install chromium
```

**What it does:** Downloads Chromium browser for E2E testing.

**Why:** Playwright needs a real browser to run E2E tests.

#### 6. Run Unit Tests
```yaml
- name: Run unit tests
  run: |
    pytest -m unit -v --tb=short
```

**What it does:** Runs only tests marked with `@pytest.mark.unit`.

**Flags:**
- `-m unit`: Run only unit tests
- `-v`: Verbose output
- `--tb=short`: Short traceback on failures

#### 7. Run Integration Tests
```yaml
- name: Run integration tests
  run: |
    pytest -m integration -v --tb=short
```

**What it does:** Runs tests marked with `@pytest.mark.integration`.

**Why separate?** Allows you to see which category failed.

#### 8. Run All Tests with Coverage
```yaml
- name: Run tests with coverage
  run: |
    pytest -m "not e2e" --cov=. --cov-report=xml --cov-report=term-missing
```

**What it does:**
- Runs all tests except E2E (E2E runs in separate job)
- Generates coverage report in XML format
- Shows coverage in terminal with missing lines

**Output:**
```
---------- coverage: platform darwin, python 3.11.13 -----------
Name                          Stmts   Miss  Cover   Missing
-----------------------------------------------------------
cfbd_client.py                  145     12    92%   89-95, 203
ranking_service.py              234      8    97%   156, 245-251
main.py                         312     15    95%   89, 234-245
-----------------------------------------------------------
TOTAL                          1245     67    95%
```

#### 9. Upload Coverage to Codecov
```yaml
- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v4
  with:
    file: ./coverage.xml
    fail_ci_if_error: false
```

**What it does:** Uploads coverage data to Codecov.io for tracking over time.

**Why:** Provides visual coverage reports and tracks coverage trends.

**Note:** `fail_ci_if_error: false` means upload failures won't fail the build.

#### 10. Archive Test Results
```yaml
- name: Archive test results
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: test-results
    path: |
      htmlcov/
      .coverage
    retention-days: 7
```

**What it does:** Saves coverage HTML report and raw coverage data as downloadable artifacts.

**Why:** Allows you to download and view full HTML coverage report after CI runs.

**Retention:** Artifacts are kept for 7 days.

---

## Job 2: E2E Test (End-to-End Tests)

### Purpose
Run browser-based E2E tests to validate complete user workflows.

### Dependencies
```yaml
needs: test
```

**What it does:** Only runs if the `test` job passes.

**Why:** No point running slow E2E tests if unit tests are failing.

### Steps Breakdown

#### 1-3. Setup (Same as Test Job)
- Checkout repository
- Set up Python
- Install dependencies
- Install Playwright browsers

#### 4. Start FastAPI Server
```yaml
- name: Start FastAPI server
  run: |
    python3 main.py &
    sleep 5
  env:
    PYTHONUNBUFFERED: 1
```

**What it does:**
- Starts FastAPI server in background (`&`)
- Waits 5 seconds for server to be ready

**Environment:**
- `PYTHONUNBUFFERED: 1` - Ensures logs are immediately visible

**Why needed:** E2E tests require a running server to test against.

#### 5. Run E2E Tests
```yaml
- name: Run E2E tests
  run: |
    pytest -m e2e -v --tb=short
```

**What it does:** Runs all tests marked with `@pytest.mark.e2e`.

**Tests include:**
- Rankings page workflow (11 tests)
- Team detail page workflow (10 tests)
- Predictions page workflow (12 tests)
- AP Poll comparison workflow (13 tests)

**Total:** 46 E2E tests

#### 6. Archive Screenshots on Failure
```yaml
- name: Archive E2E screenshots
  if: failure()
  uses: actions/upload-artifact@v4
  with:
    name: e2e-screenshots
    path: screenshots/
    retention-days: 7
```

**What it does:** If E2E tests fail, uploads screenshots for debugging.

**Why:** Visual debugging is crucial for E2E test failures.

**Note:** Only runs if E2E tests fail (`if: failure()`).

---

## Viewing Test Results

### In GitHub UI

1. **Navigate to Actions Tab**
   - Go to your repository on GitHub
   - Click "Actions" tab at the top

2. **View Workflow Runs**
   - See list of all workflow runs
   - Green ✓ = passed
   - Red ✗ = failed
   - Yellow ● = running

3. **Click on a Run**
   - See detailed logs for each job
   - Expand steps to see output
   - View test results and failures

### Download Artifacts

1. **Scroll to bottom of workflow run**
2. **Click "Artifacts" section**
3. **Download:**
   - `test-results` - Coverage reports
   - `e2e-screenshots` - Screenshots from failed E2E tests

### View Coverage Report

1. Download `test-results` artifact
2. Extract ZIP file
3. Open `htmlcov/index.html` in browser
4. Browse line-by-line coverage

---

## Workflow File Location

```
.github/
└── workflows/
    └── tests.yml    ← CI/CD configuration
```

### Full Workflow Structure

```yaml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:                    # Job 1: Unit + Integration
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.11']
    steps:
      - Checkout
      - Setup Python
      - Cache dependencies
      - Install dependencies
      - Install Playwright
      - Run unit tests
      - Run integration tests
      - Run tests with coverage
      - Upload coverage
      - Archive results

  e2e-test:               # Job 2: E2E Tests
    runs-on: ubuntu-latest
    needs: test
    steps:
      - Checkout
      - Setup Python
      - Install dependencies
      - Install Playwright
      - Start server
      - Run E2E tests
      - Archive screenshots
```

---

## Test Execution Timeline

Typical execution times (on GitHub Actions):

| Step                        | Duration  |
|----------------------------|-----------|
| Checkout & Setup           | ~10s      |
| Install dependencies (cached) | ~20s   |
| Install Playwright         | ~30s      |
| Run unit tests            | ~5s       |
| Run integration tests     | ~10s      |
| Run coverage              | ~15s      |
| Upload artifacts          | ~5s       |
| **Total (test job)**      | **~1.5 min** |
|                           |           |
| Start server              | ~5s       |
| Run E2E tests            | ~2-3 min  |
| **Total (e2e-test job)**  | **~2.5-3.5 min** |
|                           |           |
| **Grand Total**           | **~4-5 min** |

---

## Badge Integration

Add CI status badge to README:

```markdown
![Tests](https://github.com/YOUR_USERNAME/REPO_NAME/actions/workflows/tests.yml/badge.svg)
```

Shows:
- ✅ Green "passing" when all tests pass
- ❌ Red "failing" when tests fail
- ⚪ Gray "no status" if never run

---

## Troubleshooting CI Failures

### Tests Pass Locally But Fail in CI

**Possible causes:**
1. **Environment differences**
   - Missing dependencies in `requirements-dev.txt`
   - Different Python version locally
   - Different OS (macOS vs Linux)

**Solution:**
- Check workflow logs for specific errors
- Ensure `requirements-dev.txt` is up to date
- Test with same Python version locally (3.11)

### E2E Tests Timeout

**Possible causes:**
1. Server not starting in time
2. Browser not launching
3. Slow API responses

**Solution:**
- Increase `sleep` time in "Start server" step
- Check server logs in workflow output
- Add more `page.wait_for_timeout()` in tests

### Cache Not Working

**Symptom:** Dependencies install every time

**Cause:** `requirements-dev.txt` changed or cache expired

**Solution:**
- Normal behavior when dependencies change
- Cache auto-expires after 7 days of no use

### Artifacts Not Uploading

**Cause:** Path doesn't exist or permissions issue

**Solution:**
- Check that `htmlcov/` directory is created
- Ensure `if: always()` or `if: failure()` condition is correct

---

## Security Considerations

### Secrets Management

**API Keys:**
- CFBD API key stored in GitHub Secrets
- Access via `${{ secrets.CFBD_API_KEY }}`

**Adding secrets:**
1. Go to repository Settings
2. Click "Secrets and variables" → "Actions"
3. Click "New repository secret"
4. Add name and value

**Usage in workflow:**
```yaml
env:
  CFBD_API_KEY: ${{ secrets.CFBD_API_KEY }}
```

### Branch Protection

Recommended branch protection rules for `main`:

- ✅ Require pull request before merging
- ✅ Require status checks to pass ("test" job)
- ✅ Require branches to be up to date
- ✅ Require linear history

---

## Local vs CI Differences

| Aspect | Local | CI |
|--------|-------|-----|
| OS | macOS/Windows/Linux | Ubuntu Linux |
| Python | Any version | 3.11 |
| Database | SQLite (persistent) | SQLite (in-memory per test) |
| Browser | Visible (headed) | Headless |
| Parallelization | Single thread | Can run parallel jobs |
| Caching | Manual (`pip cache`) | Automatic (GitHub Actions) |

---

## Optimizing CI Performance

### 1. Use Caching Effectively
```yaml
- uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('requirements-dev.txt') }}
```

**Speeds up:** Dependency installation by 80%

### 2. Run Tests in Parallel
```yaml
strategy:
  matrix:
    python-version: ['3.10', '3.11', '3.12']
```

**Note:** Currently testing only Python 3.11. Can add more versions if needed.

### 3. Skip E2E for Draft PRs
```yaml
if: github.event.pull_request.draft == false
```

**Benefit:** Faster feedback loop during development.

### 4. Fail Fast
```yaml
strategy:
  fail-fast: true
```

**Benefit:** Stops other matrix jobs if one fails.

---

## Monitoring and Alerts

### GitHub Notifications

You receive notifications when:
- ✅ Your PR's tests pass
- ❌ Your PR's tests fail
- ✅ Push to main passes tests
- ❌ Push to main fails tests

**Configure in:** GitHub Settings → Notifications

### Codecov Integration

View coverage trends at: `https://codecov.io/gh/YOUR_USERNAME/REPO_NAME`

Features:
- Coverage percentage over time
- Coverage diff on PRs
- File-by-file coverage
- Sunburst visualization

---

## Future Enhancements

Potential improvements to CI/CD:

1. **Deployment Stage**
   - Auto-deploy to staging on `develop` branch
   - Auto-deploy to production on `main` branch

2. **Performance Testing**
   - Add load testing job
   - Track API response times

3. **Security Scanning**
   - Add dependency vulnerability scanning
   - Add code security scanning (Snyk, Bandit)

4. **Lint and Format Checks**
   - Add black/flake8 for code formatting
   - Add mypy for type checking

5. **Docker Integration**
   - Build Docker image in CI
   - Push to container registry

---

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [pytest Documentation](https://docs.pytest.org/)
- [Codecov Documentation](https://docs.codecov.com/)
- [Playwright CI Guide](https://playwright.dev/python/docs/ci)

---

## Questions?

- Check workflow logs first
- Review this documentation
- Open an issue on GitHub
