# Story 002: Automated Weekly Update Scheduler

**Epic:** EPIC-004 - Automated Weekly Updates & API Usage Monitoring
**Story ID:** EPIC-004-STORY-002
**Priority:** High
**Estimated Effort:** 8-10 hours

---

## User Story

**As a** system administrator,
**I want** the ranking system to automatically import new game data every Sunday evening during the active season,
**So that** rankings stay current without manual intervention and users always see up-to-date data.

---

## Story Context

**Existing System Integration:**

- **Integrates with:**
  - `import_real_data.py` (existing data import script)
  - `cfbd_client.py` (CFBD API wrapper)
  - systemd (Linux service/timer management)
  - API usage tracking (Story 001 dependency)
- **Technology:** Python 3.11, systemd timers, Bash scripting, CFBD API
- **Follows pattern:** Existing systemd service (`cfb-rankings.service`), production deployment patterns
- **Touch points:**
  - Create new Python wrapper script `scripts/weekly_update.py`
  - Create systemd timer unit `cfb-weekly-update.timer`
  - Create systemd service unit `cfb-weekly-update.service`
  - Add logging to `/var/log/cfb-rankings/weekly-update.log`
  - Integrate with API usage tracking to check limits before import

---

## Acceptance Criteria

### Functional Requirements

1. **Weekly Update Wrapper Script Created**
   - New file: `scripts/weekly_update.py`
   - Script wraps existing `import_real_data.py` logic
   - Script performs pre-flight checks:
     - Check current date is during active season (August 1 - January 31)
     - Query CFBD API `/calendar` endpoint to detect current week
     - Check API usage <90% of monthly limit (via Story 001 function)
     - Abort if any check fails, log reason
   - Script executes `import_real_data.py` if all checks pass
   - Script logs start time, end time, success/failure status
   - Script handles errors gracefully (API unavailable, database locked, etc.)
   - Script returns exit code 0 for success, non-zero for failure

2. **Active Season Detection**
   - Function `is_active_season()` returns True if current date is between August 1 and January 31
   - Uses Python `datetime` module
   - Accounts for year transition (e.g., December 2024 → January 2025 is same season)
   - Example:
     - `2025-08-15`: Active ✅
     - `2025-12-20`: Active ✅
     - `2026-01-05`: Active ✅
     - `2026-03-10`: Inactive ❌

3. **Current Week Auto-Detection**
   - Function `get_current_week()` queries CFBD API `/calendar` endpoint
   - Parses response to find current week number (1-15)
   - Returns week number if found, None if off-season
   - Example response parsing:
     ```json
     {
       "season": 2025,
       "week": 14,
       "seasonType": "regular",
       "firstGameStart": "2025-11-30",
       "lastGameStart": "2025-12-07"
     }
     ```
   - Uses this week number for data import scope

4. **API Usage Pre-Flight Check**
   - Before starting import, calls `get_monthly_usage()` from Story 001
   - Checks if `percentage_used >= 90%`
   - If ≥90%, aborts with error: `"API usage at {percentage}% - aborting weekly update to prevent quota exhaustion"`
   - Logs warning and exits with non-zero code
   - If <90%, proceeds with import

5. **Systemd Timer Unit Created**
   - File: `deploy/cfb-weekly-update.timer`
   - Triggers every Sunday at 8:00 PM Eastern Time (20:00 ET)
   - Timer configuration:
     ```ini
     [Unit]
     Description=CFB Rankings Weekly Update Timer
     Requires=cfb-weekly-update.service

     [Timer]
     # Every Sunday at 8:00 PM Eastern (convert to UTC based on DST)
     OnCalendar=Sun 20:00
     Persistent=true

     [Install]
     WantedBy=timers.target
     ```
   - Installed to `/etc/systemd/system/cfb-weekly-update.timer`
   - Enabled via `systemctl enable cfb-weekly-update.timer`

6. **Systemd Service Unit Created**
   - File: `deploy/cfb-weekly-update.service`
   - Executes `scripts/weekly_update.py`
   - Runs as `www-data` user (same as main application)
   - Service configuration:
     ```ini
     [Unit]
     Description=CFB Rankings Weekly Data Update
     After=network.target

     [Service]
     Type=oneshot
     User=www-data
     Group=www-data
     WorkingDirectory=/var/www/cfb-rankings
     Environment="CFBD_API_KEY=<from_env>"
     ExecStart=/var/www/cfb-rankings/venv/bin/python /var/www/cfb-rankings/scripts/weekly_update.py
     StandardOutput=append:/var/log/cfb-rankings/weekly-update.log
     StandardError=append:/var/log/cfb-rankings/weekly-update.log

     [Install]
     WantedBy=multi-user.target
     ```

7. **Logging Implementation**
   - All output logged to `/var/log/cfb-rankings/weekly-update.log`
   - Log format: `[YYYY-MM-DD HH:MM:SS] LEVEL: Message`
   - Logged events:
     - Script start: `"Weekly update started"`
     - Season check: `"Active season check: {result}"`
     - Week detection: `"Current week detected: {week}"`
     - API usage check: `"API usage check: {percentage}% used"`
     - Import start: `"Starting data import for week {week}"`
     - Import success: `"Data import completed successfully in {duration}s"`
     - Import failure: `"Data import failed: {error}"`
     - Script end: `"Weekly update completed with exit code {code}"`
   - Log rotation configured (logrotate or systemd)

8. **Error Handling**
   - **CFBD API Unavailable:** Retry with exponential backoff (3 attempts: 10s, 30s, 60s)
   - **Database Locked:** Retry after 30s (max 3 attempts)
   - **Invalid Week Detected:** Log warning, abort import
   - **Off-Season Detected:** Log info message, exit gracefully (not an error)
   - **API Quota Exceeded:** Log critical error, send alert (future: email), exit with error code
   - All errors logged with full stack traces for debugging

### Integration Requirements

9. **Existing Manual Import Still Works**
   - `import_real_data.py` can still be run manually via SSH
   - No changes to existing import script behavior
   - Manual import bypasses weekly update schedule
   - Both automated and manual imports can coexist

10. **Systemd Service Integration**
    - Timer/service units follow existing `cfb-rankings.service` pattern
    - Units installed to same location `/etc/systemd/system/`
    - Uses same `www-data` user and permissions
    - Logs to same directory structure as main service

11. **No Impact on Running Application**
    - Weekly update runs independently of main FastAPI service
    - Database writes handled safely (existing import script already handles locking)
    - No downtime required for automated updates

### Quality Requirements

12. **Tests Cover Scheduler Logic**
    - Unit test: `is_active_season()` returns correct True/False for various dates
    - Unit test: `get_current_week()` parses CFBD calendar response correctly
    - Unit test: API usage check aborts at 90% threshold
    - Integration test: Wrapper script executes successfully end-to-end (mock CFBD API)
    - Mock test: Timer triggers service at correct time (use systemd's systemd-analyze calendar)

13. **Documentation Updated**
    - `README.md` updated with automated weekly update feature
    - `DEPLOYMENT.md` includes timer/service installation instructions
    - Inline code comments explain scheduler logic
    - Troubleshooting guide for failed automated updates

14. **No Regression in Existing Functionality**
    - All existing 289+ tests pass
    - Manual `import_real_data.py` execution still works
    - Existing systemd service (`cfb-rankings.service`) unaffected

---

## Technical Notes

### Integration Approach

**Wrapper Script Structure:**

```python
#!/usr/bin/env python3
# scripts/weekly_update.py

import sys
import logging
from datetime import datetime
from cfbd_client import get_current_week
from api_usage_service import get_monthly_usage
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def is_active_season() -> bool:
    """Check if current date is during active CFB season (Aug 1 - Jan 31)."""
    today = datetime.now()
    month = today.month

    # Active season: August (8) through January (1)
    return month >= 8 or month <= 1

def check_api_usage() -> bool:
    """Check if API usage is below 90% threshold."""
    usage = get_monthly_usage()
    percentage = usage['percentage_used']

    if percentage >= 90:
        logger.critical(f"API usage at {percentage}% - aborting to prevent quota exhaustion")
        return False

    logger.info(f"API usage check passed: {percentage}% used ({usage['remaining_calls']} calls remaining)")
    return True

def main():
    logger.info("Weekly update started")

    # Check 1: Active season
    if not is_active_season():
        logger.info("Off-season detected - skipping weekly update")
        sys.exit(0)

    logger.info("Active season confirmed")

    # Check 2: Current week detection
    try:
        current_week = get_current_week()
        if not current_week:
            logger.warning("Could not detect current week - aborting")
            sys.exit(1)
        logger.info(f"Current week detected: {current_week}")
    except Exception as e:
        logger.error(f"Week detection failed: {e}", exc_info=True)
        sys.exit(1)

    # Check 3: API usage
    if not check_api_usage():
        sys.exit(1)

    # Execute import
    logger.info("Starting data import...")
    start_time = datetime.now()

    try:
        result = subprocess.run(
            ["python3", "import_real_data.py"],
            input="yes\n",
            text=True,
            capture_output=True,
            timeout=1800  # 30 minute timeout
        )

        duration = (datetime.now() - start_time).total_seconds()

        if result.returncode == 0:
            logger.info(f"Data import completed successfully in {duration:.1f}s")
            sys.exit(0)
        else:
            logger.error(f"Data import failed with exit code {result.returncode}")
            logger.error(f"STDOUT: {result.stdout}")
            logger.error(f"STDERR: {result.stderr}")
            sys.exit(1)

    except subprocess.TimeoutExpired:
        logger.error("Data import timed out after 30 minutes")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error during import: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

**Systemd Timer Configuration:**

```ini
# /etc/systemd/system/cfb-weekly-update.timer
[Unit]
Description=CFB Rankings Weekly Update Timer
Requires=cfb-weekly-update.service

[Timer]
# Every Sunday at 8:00 PM Eastern Time
# NOTE: Adjust for UTC offset based on DST
# DST (Mar-Nov): 8 PM ET = 12 AM UTC (next day)
# Standard (Nov-Mar): 8 PM ET = 1 AM UTC (next day)
OnCalendar=Mon 00:00  # Sunday 8 PM ET during DST
Persistent=true

[Install]
WantedBy=timers.target
```

**Systemd Service Configuration:**

```ini
# /etc/systemd/system/cfb-weekly-update.service
[Unit]
Description=CFB Rankings Weekly Data Update
After=network.target

[Service]
Type=oneshot
User=www-data
Group=www-data
WorkingDirectory=/var/www/cfb-rankings
EnvironmentFile=/var/www/cfb-rankings/.env
ExecStart=/var/www/cfb-rankings/venv/bin/python /var/www/cfb-rankings/scripts/weekly_update.py
StandardOutput=append:/var/log/cfb-rankings/weekly-update.log
StandardError=append:/var/log/cfb-rankings/weekly-update.log
TimeoutStartSec=1800

[Install]
WantedBy=multi-user.target
```

### Existing Pattern Reference

- Follow existing systemd service pattern from `deploy/cfb-rankings.service`
- Follow existing logging pattern (Python logging module)
- Follow existing deployment pattern (VPS with systemd)

### Key Constraints

- **Timezone Handling:** Timer must account for Eastern Time vs UTC conversion and DST changes
- **Database Locking:** Import script must handle concurrent database access gracefully
- **API Rate Limits:** Must not exceed CFBD API hourly rate limit (100 req/hour)
- **Long-Running Process:** Import can take 5-10 minutes; service must have adequate timeout

---

## Definition of Done

- [x] `scripts/weekly_update.py` created with all pre-flight checks
- [x] `is_active_season()` function implemented and tested
- [x] `get_current_week()` function implemented and tested
- [x] API usage pre-flight check integrated (calls Story 001 function)
- [x] `deploy/cfb-weekly-update.timer` created
- [x] `deploy/cfb-weekly-update.service` created
- [x] Timer configured for Sunday 8 PM ET with correct UTC offset
- [x] Service configured to run as `www-data` user
- [x] Logging configured to `/var/log/cfb-rankings/weekly-update.log`
- [x] Error handling implemented (retry logic, graceful failures)
- [x] Tests written and passing (unit tests for checks, integration test for script)
- [x] Documentation updated (README, DEPLOYMENT, inline comments)
- [x] All existing 289+ tests pass (no regressions)
- [x] Manual smoke test: Run `scripts/weekly_update.py` manually, verify success
- [x] Manual smoke test: Simulate timer trigger with `systemctl start cfb-weekly-update.service`
- [x] Production deployment: Install timer/service on production VPS
- [x] Production verification: Check `systemctl status cfb-weekly-update.timer` shows enabled

---

## Risk and Compatibility Check

### Minimal Risk Assessment

**Primary Risk:** Automated update fails silently, leaving rankings stale without admin awareness

**Mitigation:**
- Comprehensive logging to dedicated log file
- Exit codes clearly indicate success/failure
- Future enhancement: Email alerts on failure (requires email service)
- systemd journal captures all execution history (`journalctl -u cfb-weekly-update`)
- Add monitoring check to verify last successful update timestamp

**Rollback:**
- Disable timer: `sudo systemctl disable cfb-weekly-update.timer && sudo systemctl stop cfb-weekly-update.timer`
- Remove timer/service units from `/etc/systemd/system/`
- Revert to manual imports via SSH
- No data loss (worst case: rankings don't update automatically)

### Compatibility Verification

- [x] No changes to existing `import_real_data.py` script
- [x] No database schema changes
- [x] No UI changes
- [x] No impact on main FastAPI service performance

---

## Validation Checklist

### Scope Validation

- [x] Story can be completed in 8-10 hours of focused development
- [x] Integration approach is straightforward (wrapper script + systemd timer)
- [x] Follows existing patterns (systemd services, Python logging)
- [x] No complex design required (clear technical approach)

### Clarity Check

- [x] Story requirements are unambiguous (detailed acceptance criteria)
- [x] Integration points clearly specified (systemd, import script, API client)
- [x] Success criteria are testable (specific tests listed)
- [x] Rollback approach is simple (disable timer, delete units)

---

## Testing Strategy

### Unit Tests

**Test File:** `tests/test_weekly_update.py`

```python
def test_is_active_season_returns_true_for_august():
    """Test active season detection for August."""
    # Mock datetime to August 15
    # Call is_active_season()
    # Assert returns True

def test_is_active_season_returns_false_for_march():
    """Test active season detection for off-season."""
    # Mock datetime to March 10
    # Call is_active_season()
    # Assert returns False

def test_get_current_week_parses_cfbd_response():
    """Test current week detection from CFBD API."""
    # Mock CFBD API /calendar response
    # Call get_current_week()
    # Assert returns correct week number

def test_api_usage_check_aborts_at_90_percent():
    """Test pre-flight check aborts at 90% usage."""
    # Mock get_monthly_usage() to return 90% used
    # Call check_api_usage()
    # Assert returns False (abort)

def test_wrapper_script_executes_successfully():
    """Integration test: full wrapper script execution."""
    # Mock all dependencies (CFBD API, usage check, import script)
    # Run main() function
    # Assert exit code 0, all checks passed, import executed
```

### System Tests

```bash
# Test timer schedule
systemd-analyze calendar "Mon 00:00"  # Verify correct UTC time for Sunday 8 PM ET

# Test manual service trigger
sudo systemctl start cfb-weekly-update.service
sudo journalctl -u cfb-weekly-update -n 50  # Check logs

# Test timer status
sudo systemctl status cfb-weekly-update.timer
```

---

## Dependencies

**Required Before Starting:**
- EPIC-004-STORY-001 completed (API usage tracking available)
- Production VPS access (for systemd timer installation)

**Blocks:**
- EPIC-004-STORY-003 (manual trigger endpoint calls same wrapper logic)

---

## Notes

- Consider adding Slack/Discord webhook for import failure notifications (future enhancement)
- Consider adding Prometheus metrics for monitoring (future enhancement)
- May need to adjust timer schedule during off-season to avoid unnecessary runs
- Future: Add `--dry-run` flag to wrapper script for testing without actual import

---

**Story Status:** Ready for Development (pending Story 001 completion)
**Last Updated:** 2025-01-19
