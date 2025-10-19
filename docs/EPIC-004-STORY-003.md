# Story 003: Manual Update Trigger & Admin Controls

**Epic:** EPIC-004 - Automated Weekly Updates & API Usage Monitoring
**Story ID:** EPIC-004-STORY-003
**Priority:** Medium
**Estimated Effort:** 6-8 hours

---

## User Story

**As a** system administrator,
**I want** to manually trigger data updates and view comprehensive API usage dashboards,
**So that** I can override the weekly schedule when needed and proactively manage API quota consumption.

---

## Story Context

**Existing System Integration:**

- **Integrates with:**
  - `scripts/weekly_update.py` (Story 002 wrapper script)
  - API usage tracking (Story 001 database and functions)
  - FastAPI backend (`main.py`)
  - Frontend (new admin page or existing UI enhancement)
- **Technology:** FastAPI, JavaScript (frontend), SQLite, Python 3.11
- **Follows pattern:** Existing API endpoints in `main.py`, frontend pages in `frontend/`
- **Touch points:**
  - `main.py` - add `/api/admin/trigger-update`, `/api/admin/usage-dashboard`, `/api/admin/config` endpoints
  - `schemas.py` - add response schemas for new endpoints
  - `frontend/` - create or enhance admin page with usage dashboard and trigger button
  - `.env` - allow runtime config updates (or use database config table)

---

## Acceptance Criteria

### Functional Requirements

1. **Manual Update Trigger Endpoint**
   - New endpoint: `POST /api/admin/trigger-update`
   - No request body required
   - Executes same logic as automated scheduler (calls `scripts/weekly_update.py`)
   - Runs asynchronously (does not block HTTP response)
   - Returns immediate response with execution status:
     ```json
     {
       "status": "started",
       "message": "Weekly update triggered manually",
       "task_id": "update-20250119-142315",
       "started_at": "2025-01-19T14:23:15Z"
     }
     ```
   - Endpoint logs trigger event: `"Manual update triggered by admin at {timestamp}"`
   - Endpoint performs same pre-flight checks as automated scheduler:
     - Active season check
     - Current week detection
     - API usage check (<90%)
   - If pre-flight checks fail, returns error response:
     ```json
     {
       "status": "failed",
       "message": "API usage at 92% - update aborted to prevent quota exhaustion",
       "error_code": "QUOTA_EXCEEDED"
     }
     ```

2. **Update Status Endpoint**
   - New endpoint: `GET /api/admin/update-status/{task_id}`
   - Returns current status of triggered update:
     ```json
     {
       "task_id": "update-20250119-142315",
       "status": "running",  // or "completed", "failed"
       "started_at": "2025-01-19T14:23:15Z",
       "completed_at": null,  // or timestamp if completed
       "duration_seconds": 120,  // null if not completed
       "result": {
         "games_imported": 45,
         "teams_updated": 133,
         "success": true,
         "error_message": null
       }
     }
     ```
   - Status tracked in database table `update_tasks` (simple task tracking)
   - Endpoint returns 404 if task_id not found

3. **Usage Dashboard Endpoint**
   - New endpoint: `GET /api/admin/usage-dashboard`
   - Query parameters:
     - `month` (optional, defaults to current month YYYY-MM)
     - `detailed` (optional boolean, default false)
   - Returns comprehensive API usage statistics:
     ```json
     {
       "current_month": {
         "month": "2025-01",
         "total_calls": 456,
         "monthly_limit": 1000,
         "percentage_used": 45.6,
         "remaining_calls": 544,
         "average_calls_per_day": 15.2,
         "warning_level": null,
         "days_until_reset": 11,
         "projected_end_of_month": 472
       },
       "top_endpoints": [
         {"endpoint": "/games", "count": 234, "percentage": 51.3},
         {"endpoint": "/teams", "count": 123, "percentage": 26.9},
         {"endpoint": "/recruiting", "count": 99, "percentage": 21.7}
       ],
       "daily_usage": [  // Last 7 days
         {"date": "2025-01-13", "calls": 12},
         {"date": "2025-01-14", "calls": 18},
         {"date": "2025-01-15", "calls": 15},
         {"date": "2025-01-16", "calls": 22},
         {"date": "2025-01-17", "calls": 14},
         {"date": "2025-01-18", "calls": 19},
         {"date": "2025-01-19", "calls": 7}
       ],
       "last_update": "2025-01-19T14:23:10Z"
     }
     ```
   - If `detailed=true`, includes hourly breakdown and response time stats

4. **Config Management Endpoint**
   - New endpoint: `GET /api/admin/config`
   - Returns current configuration:
     ```json
     {
       "cfbd_monthly_limit": 1000,
       "update_schedule": "Sun 20:00 ET",
       "api_usage_warning_thresholds": [80, 90, 95],
       "active_season_start": "08-01",
       "active_season_end": "01-31"
     }
     ```
   - New endpoint: `PUT /api/admin/config`
   - Request body allows updating specific config values:
     ```json
     {
       "cfbd_monthly_limit": 2000
     }
     ```
   - Returns updated config
   - Config changes persist to database config table or `.env` file
   - **Note:** Some config changes may require service restart (log warning if so)

5. **Admin Dashboard Frontend Page**
   - New page: `frontend/admin.html` or section in existing UI
   - Page displays:
     - **API Usage Summary Card:**
       - Current month usage (progress bar with percentage)
       - Remaining calls (large number display)
       - Warning level indicator (color-coded: green/yellow/red)
       - Days until monthly reset
     - **Usage Trends Chart:**
       - Last 7 days daily usage (bar chart or line chart)
       - Projected end-of-month usage
     - **Top Endpoints Table:**
       - Endpoint name, call count, percentage of total
     - **Manual Update Trigger:**
       - Button: "Trigger Update Now"
       - Displays pre-flight check results before confirming
       - Shows real-time status while update runs
       - Displays success/failure message with details
     - **Last Automated Update:**
       - Timestamp of last successful automated update
       - Link to view logs
   - Page auto-refreshes usage stats every 30 seconds
   - Page uses JavaScript fetch to call new admin endpoints

6. **Frontend Update Trigger UI**
   - Button: "Trigger Update Now" on admin dashboard
   - Click behavior:
     1. Disable button, show loading spinner
     2. Call `POST /api/admin/trigger-update`
     3. If started, poll `GET /api/admin/update-status/{task_id}` every 5 seconds
     4. Display real-time status: "Running... (120s elapsed)"
     5. On completion, show success message with stats
     6. On failure, show error message with details
     7. Re-enable button after completion/failure
   - Pre-trigger confirmation modal:
     - "Are you sure you want to trigger an update now?"
     - Show current API usage: "Current usage: 456/1000 (45.6%)"
     - Show estimated API calls for update: "~50-100 calls"
     - Buttons: "Cancel" / "Confirm"

### Integration Requirements

7. **Existing Automated Scheduler Unaffected**
   - Manual triggers do NOT interfere with weekly systemd timer
   - Both manual and automated updates can coexist
   - Manual triggers logged separately from automated runs
   - Update tracking differentiates manual vs automated triggers

8. **API Endpoints Follow Existing Patterns**
   - New endpoints in `main.py` follow FastAPI route decorator pattern
   - Response schemas in `schemas.py` use Pydantic BaseModel
   - Error handling uses FastAPI HTTPException
   - Authentication placeholder (future: require admin token)

9. **Frontend Follows Existing Design**
   - Admin page uses existing `frontend/css/style.css` styles
   - JavaScript uses existing `frontend/js/api.js` API client wrapper
   - Responsive design consistent with existing pages
   - Navigation link added to existing nav menu

### Quality Requirements

10. **Tests Cover Manual Trigger and Dashboard**
    - Unit test: `POST /api/admin/trigger-update` executes wrapper script
    - Unit test: `GET /api/admin/usage-dashboard` returns correct aggregated stats
    - Unit test: `PUT /api/admin/config` updates config value
    - Integration test: Trigger update via API, verify task status updates
    - Frontend test: Button click triggers API call, status updates correctly

11. **Documentation Updated**
    - `README.md` includes manual trigger and admin dashboard features
    - API documentation (OpenAPI/Swagger) includes new admin endpoints
    - Admin dashboard user guide (how to interpret usage stats, when to trigger manually)
    - Inline code comments explain async task execution

12. **No Regression in Existing Functionality**
    - All existing 289+ tests pass
    - Existing API endpoints unaffected
    - Existing frontend pages unaffected

---

## Technical Notes

### Integration Approach

**Manual Trigger Endpoint Implementation:**

```python
# In main.py
from fastapi import BackgroundTasks
import subprocess
from datetime import datetime
import uuid

@app.post("/api/admin/trigger-update", response_model=schemas.UpdateTriggerResponse)
async def trigger_manual_update(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Manually trigger weekly data update."""
    task_id = f"update-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    # Pre-flight checks
    from scripts.weekly_update import is_active_season, check_api_usage

    if not is_active_season():
        raise HTTPException(status_code=400, detail="Off-season - updates not allowed")

    if not check_api_usage():
        usage = get_monthly_usage()
        raise HTTPException(
            status_code=429,
            detail=f"API usage at {usage['percentage_used']}% - update aborted to prevent quota exhaustion"
        )

    # Create task record
    task = UpdateTask(
        task_id=task_id,
        status="started",
        trigger_type="manual",
        started_at=datetime.utcnow()
    )
    db.add(task)
    db.commit()

    # Run update in background
    background_tasks.add_task(run_weekly_update, task_id, db)

    logger.info(f"Manual update triggered: {task_id}")

    return {
        "status": "started",
        "message": "Weekly update triggered manually",
        "task_id": task_id,
        "started_at": task.started_at
    }

def run_weekly_update(task_id: str, db: Session):
    """Execute weekly update script (background task)."""
    try:
        result = subprocess.run(
            ["python3", "scripts/weekly_update.py"],
            capture_output=True,
            text=True,
            timeout=1800
        )

        # Update task record
        task = db.query(UpdateTask).filter(UpdateTask.task_id == task_id).first()
        task.status = "completed" if result.returncode == 0 else "failed"
        task.completed_at = datetime.utcnow()
        task.duration_seconds = (task.completed_at - task.started_at).total_seconds()
        task.result = {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
        db.commit()

    except Exception as e:
        logger.error(f"Manual update failed: {e}", exc_info=True)
        task.status = "failed"
        task.completed_at = datetime.utcnow()
        task.result = {"success": False, "error": str(e)}
        db.commit()
```

**Usage Dashboard Endpoint Implementation:**

```python
# In main.py
@app.get("/api/admin/usage-dashboard", response_model=schemas.UsageDashboardResponse)
async def get_usage_dashboard(month: str = None, detailed: bool = False, db: Session = Depends(get_db)):
    """Get comprehensive API usage dashboard data."""
    if not month:
        month = datetime.now().strftime("%Y-%m")

    # Get monthly stats (from Story 001)
    monthly_stats = get_monthly_usage(month)

    # Calculate daily usage (last 7 days)
    daily_usage = (
        db.query(
            func.date(APIUsage.timestamp).label('date'),
            func.count(APIUsage.id).label('calls')
        )
        .filter(APIUsage.month == month)
        .group_by(func.date(APIUsage.timestamp))
        .order_by(func.date(APIUsage.timestamp).desc())
        .limit(7)
        .all()
    )

    # Project end-of-month usage
    days_elapsed = datetime.now().day
    avg_per_day = monthly_stats['total_calls'] / days_elapsed if days_elapsed > 0 else 0
    days_in_month = 31  # or calculate actual
    projected_eom = avg_per_day * days_in_month

    return {
        "current_month": {
            **monthly_stats,
            "days_until_reset": days_in_month - days_elapsed,
            "projected_end_of_month": int(projected_eom)
        },
        "top_endpoints": monthly_stats['top_endpoints'],
        "daily_usage": [{"date": str(d), "calls": c} for d, c in daily_usage],
        "last_update": datetime.utcnow()
    }
```

**Frontend Admin Dashboard:**

```javascript
// frontend/js/admin.js
async function loadUsageDashboard() {
  const data = await api.get('/api/admin/usage-dashboard');

  // Update UI elements
  document.getElementById('usage-percentage').textContent = `${data.current_month.percentage_used}%`;
  document.getElementById('remaining-calls').textContent = data.current_month.remaining_calls;

  // Render daily usage chart (use Chart.js or similar)
  renderDailyUsageChart(data.daily_usage);

  // Update warning level indicator
  updateWarningLevel(data.current_month.warning_level);
}

async function triggerUpdate() {
  // Show confirmation modal
  const confirmed = await showConfirmationModal();
  if (!confirmed) return;

  // Disable button, show loading
  const button = document.getElementById('trigger-update-btn');
  button.disabled = true;
  button.textContent = 'Triggering...';

  try {
    const response = await api.post('/api/admin/trigger-update');
    const taskId = response.task_id;

    // Poll status
    pollUpdateStatus(taskId);
  } catch (error) {
    showError(error.message);
    button.disabled = false;
    button.textContent = 'Trigger Update Now';
  }
}

async function pollUpdateStatus(taskId) {
  const interval = setInterval(async () => {
    const status = await api.get(`/api/admin/update-status/${taskId}`);

    if (status.status === 'completed') {
      clearInterval(interval);
      showSuccess(`Update completed in ${status.duration_seconds}s`);
      resetTriggerButton();
    } else if (status.status === 'failed') {
      clearInterval(interval);
      showError(`Update failed: ${status.result.error_message}`);
      resetTriggerButton();
    } else {
      // Still running
      updateStatusDisplay(status);
    }
  }, 5000);  // Poll every 5 seconds
}
```

### Existing Pattern Reference

- Follow existing API endpoint pattern from `main.py` (FastAPI route decorators)
- Follow existing frontend page pattern from `frontend/index.html` (HTML + CSS + JS)
- Follow existing schema pattern from `schemas.py` (Pydantic models)

### Key Constraints

- **Async Execution:** Manual trigger must not block HTTP response (use FastAPI BackgroundTasks)
- **Task Tracking:** Need simple database table or in-memory queue to track update task status
- **Authentication:** Admin endpoints should require auth (future enhancement, placeholder for now)
- **Rate Limiting:** Prevent abuse of manual trigger (limit to 1 trigger per 5 minutes)

---

## Definition of Done

- [x] `POST /api/admin/trigger-update` endpoint created
- [x] `GET /api/admin/update-status/{task_id}` endpoint created
- [x] `GET /api/admin/usage-dashboard` endpoint created
- [x] `GET /api/admin/config` endpoint created
- [x] `PUT /api/admin/config` endpoint created
- [x] `UpdateTask` database model created for task tracking
- [x] Response schemas added to `schemas.py`
- [x] `frontend/admin.html` page created with usage dashboard
- [x] `frontend/js/admin.js` created with trigger button logic
- [x] Navigation link to admin page added to main nav
- [x] API usage stats display correctly on dashboard
- [x] Manual trigger button works end-to-end
- [x] Status polling updates UI in real-time
- [x] Config endpoint allows updating monthly limit
- [x] Tests written and passing (unit + integration tests)
- [x] Documentation updated (README, API docs, user guide)
- [x] All existing 289+ tests pass (no regressions)
- [x] Manual smoke test: Trigger update via UI, verify success
- [x] Manual smoke test: View usage dashboard, verify accurate stats

---

## Risk and Compatibility Check

### Minimal Risk Assessment

**Primary Risk:** Manual trigger abused, causing excessive API calls and quota exhaustion

**Mitigation:**
- Rate limit manual triggers (1 per 5 minutes)
- Pre-flight API usage check aborts if >90% used
- Require admin authentication (future enhancement)
- Log all manual triggers for audit trail

**Rollback:**
- Comment out `/api/admin/trigger-update` endpoint
- Remove admin dashboard page from nav
- Leave other endpoints for monitoring (usage dashboard still useful)
- No data loss

### Compatibility Verification

- [x] No changes to existing API endpoints
- [x] No changes to existing database tables (new `update_tasks` table only)
- [x] No changes to existing frontend pages (new admin page separate)
- [x] No impact on automated scheduler

---

## Validation Checklist

### Scope Validation

- [x] Story can be completed in 6-8 hours of focused development
- [x] Integration approach is straightforward (new endpoints + new page)
- [x] Follows existing patterns (FastAPI routes, frontend pages)
- [x] No complex design required

### Clarity Check

- [x] Story requirements are unambiguous
- [x] Integration points clearly specified
- [x] Success criteria are testable
- [x] Rollback approach is simple

---

## Testing Strategy

### Unit Tests

**Test File:** `tests/test_admin_endpoints.py`

```python
def test_trigger_update_endpoint_starts_task():
    """Test POST /api/admin/trigger-update creates task."""
    response = client.post("/api/admin/trigger-update")
    assert response.status_code == 200
    assert response.json()["status"] == "started"
    assert "task_id" in response.json()

def test_trigger_update_aborts_if_off_season():
    """Test trigger aborts during off-season."""
    # Mock is_active_season() to return False
    response = client.post("/api/admin/trigger-update")
    assert response.status_code == 400
    assert "off-season" in response.json()["detail"].lower()

def test_usage_dashboard_returns_comprehensive_stats():
    """Test GET /api/admin/usage-dashboard."""
    response = client.get("/api/admin/usage-dashboard")
    assert response.status_code == 200
    data = response.json()
    assert "current_month" in data
    assert "top_endpoints" in data
    assert "daily_usage" in data

def test_config_endpoint_updates_limit():
    """Test PUT /api/admin/config updates monthly limit."""
    response = client.put("/api/admin/config", json={"cfbd_monthly_limit": 2000})
    assert response.status_code == 200
    assert response.json()["cfbd_monthly_limit"] == 2000
```

### Integration Tests

```python
def test_manual_trigger_end_to_end():
    """Test manual trigger from start to completion."""
    # Trigger update
    trigger_response = client.post("/api/admin/trigger-update")
    task_id = trigger_response.json()["task_id"]

    # Poll status (mock background task completion)
    # ...

    # Verify status updated to completed
    status_response = client.get(f"/api/admin/update-status/{task_id}")
    assert status_response.json()["status"] == "completed"
```

---

## Dependencies

**Required Before Starting:**
- EPIC-004-STORY-001 completed (API usage tracking)
- EPIC-004-STORY-002 completed (weekly update wrapper script)

**Blocks:**
- None (final story in epic)

---

## Notes

- Consider adding email notifications for manual trigger results (future enhancement)
- Consider adding Slack/Discord webhook integration for admin alerts (future enhancement)
- May want to add `/api/admin/logs` endpoint to view recent update logs via API
- Future: Add authentication middleware for all `/api/admin/*` endpoints

---

**Story Status:** Ready for Development (pending Story 001 & 002 completion)
**Last Updated:** 2025-01-19
