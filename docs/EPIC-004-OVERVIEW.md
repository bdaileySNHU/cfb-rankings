# EPIC-004: Automated Weekly Updates & API Usage Monitoring

**Epic ID:** EPIC-004
**Epic Status:** Ready for Development
**Priority:** High
**Created:** 2025-01-19
**Target Completion:** 3-4 weeks (20-26 development hours)

---

## 📋 Executive Summary

Enable automated weekly data updates every Sunday evening during the active college football season (August-January) while providing comprehensive API usage monitoring to prevent exceeding CFBD API monthly limits. This epic ensures the ranking system stays current without manual intervention while giving administrators visibility and control over API quota consumption.

---

## 🎯 Epic Goal

**As a** system administrator,
**I want** the ranking system to automatically update every Sunday evening with comprehensive API usage monitoring,
**So that** rankings stay current without manual intervention and I can proactively manage API quota to prevent service disruptions.

---

## 💼 Business Value

### Problems Solved

1. **Manual Update Burden:** Currently requires SSH access and manual script execution every week
2. **Stale Data Risk:** Rankings can become outdated if admin forgets weekly update
3. **API Quota Blindness:** No visibility into CFBD API usage, risk of unexpected quota exhaustion
4. **No Override Capability:** Can't trigger updates outside weekly schedule when needed

### Benefits

- **Reduced Admin Workload:** ~15 minutes saved per week (no manual SSH + script execution)
- **Always Current Data:** Automated updates ensure rankings reflect latest games
- **Proactive Quota Management:** Dashboard alerts prevent unexpected API limit violations
- **Operational Flexibility:** Manual trigger allows immediate updates for special circumstances
- **System Reliability:** Automated monitoring reduces service disruption risk

### Success Metrics

- ✅ 100% automated weekly updates during active season (Aug-Jan)
- ✅ Zero API quota violations due to monitoring alerts
- ✅ <5 minute admin intervention time per month (vs current ~60 minutes)
- ✅ 100% uptime during automated update window

---

## 📦 Deliverables

### Story 001: API Usage Tracking Infrastructure
**Effort:** 6-8 hours | **Priority:** Critical (Foundation)

**Delivers:**
- `api_usage` database table tracking all CFBD API calls
- Decorator-based tracking on all API client methods
- `/api/admin/api-usage` endpoint with monthly stats
- Configurable monthly limit (via `.env`)
- Warning logs at 80%, 90%, 95% usage thresholds

**Value:** Provides visibility into API consumption, prevents quota exhaustion

### Story 002: Automated Weekly Update Scheduler
**Effort:** 8-10 hours | **Priority:** High

**Delivers:**
- `scripts/weekly_update.py` wrapper with pre-flight checks
- systemd timer triggering Sundays at 8 PM ET during active season
- Auto-detection of current week from CFBD API
- API usage pre-flight check (aborts if >90% used)
- Comprehensive logging to `/var/log/cfb-rankings/weekly-update.log`

**Value:** Eliminates manual update burden, ensures data currency

### Story 003: Manual Update Trigger & Admin Controls
**Effort:** 6-8 hours | **Priority:** Medium

**Delivers:**
- `/api/admin/trigger-update` endpoint for manual updates
- `/api/admin/usage-dashboard` with comprehensive API metrics
- `/api/admin/config` for runtime limit configuration
- `frontend/admin.html` dashboard page with usage visualization
- Real-time update status polling

**Value:** Provides admin control, visibility, and override capability

---

## 🏗️ Technical Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Admin Dashboard (Web UI)                  │
│  ┌────────────────┬──────────────────┬───────────────────┐ │
│  │ Usage Stats    │ Trigger Update   │ Config Management │ │
│  │ - Current %    │ - Manual Button  │ - Monthly Limit   │ │
│  │ - Daily Chart  │ - Status Poll    │ - Thresholds      │ │
│  └────────────────┴──────────────────┴───────────────────┘ │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTPS/JSON
┌───────────────────────────▼─────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Admin API Endpoints                                 │   │
│  │  - /api/admin/api-usage                              │   │
│  │  - /api/admin/trigger-update                         │   │
│  │  - /api/admin/usage-dashboard                        │   │
│  │  - /api/admin/config                                 │   │
│  └────────────────────┬─────────────────────────────────┘   │
│  ┌────────────────────▼─────────────────────────────────┐   │
│  │  API Usage Tracking (@track_api_usage decorator)    │   │
│  └────────────────────┬─────────────────────────────────┘   │
└───────────────────────┼─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                  CFBD API Client                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Tracked Methods:                                    │   │
│  │  - get_games()        [logged to api_usage table]   │   │
│  │  - get_teams()        [logged to api_usage table]   │   │
│  │  - get_recruiting()   [logged to api_usage table]   │   │
│  │  - get_calendar()     [logged to api_usage table]   │   │
│  └────────────────────┬─────────────────────────────────┘   │
└───────────────────────┼─────────────────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────┐
        │  CollegeFootballData.com API  │
        │  (1000 calls/month limit)     │
        └───────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                  Systemd Timer (Automation)                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  cfb-weekly-update.timer                             │   │
│  │  - Triggers: Sunday 8:00 PM ET                       │   │
│  │  - During: Aug 1 - Jan 31                            │   │
│  └────────────────────┬─────────────────────────────────┘   │
│  ┌────────────────────▼─────────────────────────────────┐   │
│  │  cfb-weekly-update.service                           │   │
│  │  - Runs: scripts/weekly_update.py                    │   │
│  │  - Pre-flight: Season check, week detect, usage check│  │
│  │  - Executes: import_real_data.py                     │   │
│  │  - Logs: /var/log/cfb-rankings/weekly-update.log    │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    SQLite Database                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  NEW: api_usage table                                │   │
│  │  - id, endpoint, timestamp, status_code,             │   │
│  │    response_time_ms, month, created_at               │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  NEW: update_tasks table                             │   │
│  │  - task_id, status, trigger_type, started_at,        │   │
│  │    completed_at, duration_seconds, result            │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  EXISTING: teams, games, ranking_history, seasons    │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow: Automated Weekly Update

```
┌──────────────────────┐
│ Sunday 8:00 PM ET    │
│ systemd timer fires  │
└──────────┬───────────┘
           │
           ▼
┌─────────────────────────────┐
│ cfb-weekly-update.service   │
│ executes weekly_update.py   │
└──────────┬──────────────────┘
           │
           ├─► Check 1: is_active_season()
           │   ✓ Aug 1 - Jan 31? → Continue
           │   ✗ Off-season? → Exit gracefully
           │
           ├─► Check 2: get_current_week()
           │   ✓ Week 1-15 detected → Continue
           │   ✗ No week found → Abort with error
           │
           ├─► Check 3: check_api_usage()
           │   ✓ <90% used → Continue
           │   ✗ ≥90% used → Abort with warning
           │
           ▼
┌─────────────────────────────┐
│ Execute import_real_data.py │
│ - Import new games          │
│ - Update team records       │
│ - Recalculate rankings      │
│ - Log progress              │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ Log completion status       │
│ - Success: Exit code 0      │
│ - Failure: Exit code 1      │
│ - Duration logged           │
└─────────────────────────────┘
```

### Data Flow: API Usage Tracking

```
┌──────────────────────────┐
│ CFBD API call initiated  │
│ (e.g., get_games())      │
└──────────┬───────────────┘
           │
           ▼
┌────────────────────────────────┐
│ @track_api_usage decorator     │
│ - Start timer                  │
│ - Execute actual API call      │
│ - Capture response time        │
│ - Capture status code          │
└──────────┬─────────────────────┘
           │
           ▼
┌────────────────────────────────┐
│ Insert api_usage record        │
│ - endpoint: "get_games"        │
│ - timestamp: 2025-01-19 14:23  │
│ - status_code: 200             │
│ - response_time_ms: 234.5      │
│ - month: "2025-01"             │
└──────────┬─────────────────────┘
           │
           ▼
┌────────────────────────────────┐
│ Check usage thresholds         │
│ - Calculate % of monthly limit │
│ - If ≥80%: Log WARNING         │
│ - If ≥90%: Log WARNING         │
│ - If ≥95%: Log CRITICAL        │
└──────────┬─────────────────────┘
           │
           ▼
┌────────────────────────────────┐
│ Return API call result         │
│ (tracking transparent)         │
└────────────────────────────────┘
```

---

## 🔗 Dependencies

### External Dependencies

- **CFBD API:** CollegeFootballData.com API (free tier: 1000 calls/month)
- **systemd:** Linux service/timer management (already in production)
- **SQLite:** Database (already in production)

### Internal Dependencies

- **Story 001 → Story 002:** Usage tracking must exist before scheduler pre-flight checks
- **Story 001 + 002 → Story 003:** Admin endpoints rely on tracking and scheduler wrapper

### Development Sequence

```
Story 001 (API Tracking)
    ↓ (blocks)
Story 002 (Scheduler) + Story 003 (Admin UI) (can run in parallel)
```

**Recommended Approach:** Develop Story 001 first, then parallelize Story 002 and Story 003.

---

## 🧪 Testing Strategy

### Unit Tests (Per Story)

**Story 001:**
- Decorator logs API calls correctly
- Monthly usage aggregation calculates accurately
- Warning thresholds trigger at correct percentages
- Tracking failure doesn't break API calls

**Story 002:**
- `is_active_season()` returns correct boolean for various dates
- `get_current_week()` parses CFBD calendar response
- API usage pre-flight check aborts at 90% threshold
- Wrapper script executes successfully (mocked dependencies)

**Story 003:**
- Manual trigger endpoint starts background task
- Usage dashboard returns aggregated stats
- Config endpoint updates monthly limit
- Frontend button triggers API call correctly

### Integration Tests

**End-to-End Scenarios:**
1. Automated update runs successfully on Sunday evening
2. Manual update triggered via admin UI completes successfully
3. API usage dashboard displays accurate real-time stats
4. Automated update aborts when API usage >90%
5. Warning logs generated at threshold crossings

### Production Smoke Tests

**Post-Deployment Checklist:**
- [ ] systemd timer enabled and scheduled correctly
- [ ] Manual trigger via admin UI works end-to-end
- [ ] Usage dashboard loads and displays current month stats
- [ ] Automated update runs successfully on first Sunday
- [ ] Logs written to `/var/log/cfb-rankings/weekly-update.log`
- [ ] All 289+ existing tests pass (no regressions)

---

## 🚀 Deployment Plan

### Development Environment

1. **Story 001:** Develop locally, test with mock API calls
2. **Story 002:** Develop locally, test timer with `systemd-analyze calendar`
3. **Story 003:** Develop locally, test admin UI with local backend

### Production Deployment

**Prerequisites:**
- All 3 stories completed and tested
- Documentation updated
- Deployment scripts prepared

**Deployment Steps:**

1. **Deploy Story 001 (API Tracking):**
   ```bash
   # SSH into production VPS
   ssh user@production-server

   # Pull latest code
   cd /var/www/cfb-rankings
   git pull origin main

   # Create api_usage table (migration or automatic)
   source venv/bin/activate
   python3 -c "from database import init_db; init_db()"

   # Restart service to load new code
   sudo systemctl restart cfb-rankings
   ```

2. **Deploy Story 002 (Scheduler):**
   ```bash
   # Install systemd units
   sudo cp deploy/cfb-weekly-update.timer /etc/systemd/system/
   sudo cp deploy/cfb-weekly-update.service /etc/systemd/system/

   # Reload systemd
   sudo systemctl daemon-reload

   # Enable and start timer
   sudo systemctl enable cfb-weekly-update.timer
   sudo systemctl start cfb-weekly-update.timer

   # Verify timer scheduled
   sudo systemctl status cfb-weekly-update.timer
   systemctl list-timers | grep cfb-weekly-update
   ```

3. **Deploy Story 003 (Admin UI):**
   ```bash
   # Frontend files already deployed with git pull
   # Restart service to load new admin endpoints
   sudo systemctl restart cfb-rankings

   # Test admin UI
   curl http://localhost:8000/api/admin/api-usage
   ```

4. **Verification:**
   ```bash
   # Test manual trigger
   curl -X POST http://localhost:8000/api/admin/trigger-update

   # View logs
   tail -f /var/log/cfb-rankings/weekly-update.log

   # Check usage dashboard
   curl http://localhost:8000/api/admin/usage-dashboard
   ```

### Rollback Plan

**If issues arise:**

1. **Disable Timer:**
   ```bash
   sudo systemctl disable cfb-weekly-update.timer
   sudo systemctl stop cfb-weekly-update.timer
   ```

2. **Revert Code:**
   ```bash
   git reset --hard <previous-commit>
   sudo systemctl restart cfb-rankings
   ```

3. **Database Rollback:**
   - `api_usage` and `update_tasks` tables can remain (no harm, just unused)
   - Or drop tables if needed: `DROP TABLE api_usage; DROP TABLE update_tasks;`

4. **Resume Manual Updates:**
   - Fallback to SSH + `import_real_data.py` manual execution

---

## 📊 Success Criteria

### Epic Completion Criteria

- ✅ All 3 stories completed with acceptance criteria met
- ✅ All automated tests passing (unit + integration)
- ✅ All 289+ existing tests passing (no regressions)
- ✅ Documentation updated (README, DEPLOYMENT, API docs)
- ✅ Production deployment successful
- ✅ First automated Sunday update runs successfully
- ✅ Admin dashboard accessible and displays accurate stats
- ✅ Manual trigger endpoint works end-to-end

### Post-Deployment Success Indicators (1 month)

- 📈 100% automated weekly updates during active season (4/4 Sundays)
- 📈 Zero API quota violations
- 📈 Zero service disruptions due to stale data
- 📈 <5 minutes admin time spent on updates (vs 60 minutes/month manual)
- 📈 API usage dashboard accessed regularly by admin
- 📈 Zero failed automated updates (or failures quickly resolved)

---

## 🔐 Security & Compliance

### Authentication (Future Enhancement)

**Current State:**
- Admin endpoints have no authentication (placeholder)
- Anyone with server access can trigger updates or view usage

**Future Enhancement:**
- Add API key or JWT authentication to `/api/admin/*` endpoints
- Implement role-based access control (RBAC)
- Audit log all admin actions

### Data Privacy

- **API usage table:** Contains only metadata (endpoint, timestamp, status code)
- **No sensitive data:** API responses not logged, only call metadata
- **CFBD API key:** Stored in `.env` file (not in git, not exposed via API)

### Rate Limiting

- **Manual trigger:** Limit to 1 trigger per 5 minutes (prevent abuse)
- **API usage endpoints:** No rate limiting needed (admin-only, low volume)

---

## 📝 Configuration

### Environment Variables

**New Variables (Story 001):**
```bash
# .env file
CFBD_MONTHLY_LIMIT=1000  # Monthly API call limit
```

**Existing Variables:**
```bash
CFBD_API_KEY=your_api_key_here  # Already exists
DATABASE_URL=sqlite:///./cfb_rankings.db  # Already exists
```

### Configuration Files

**New Files:**
- `deploy/cfb-weekly-update.timer` - systemd timer unit
- `deploy/cfb-weekly-update.service` - systemd service unit
- `scripts/weekly_update.py` - wrapper script for automated updates

**Modified Files:**
- `main.py` - new admin endpoints
- `models.py` - new `APIUsage` and `UpdateTask` models
- `schemas.py` - new response schemas
- `cfbd_client.py` - add `@track_api_usage` decorator
- `frontend/admin.html` - new admin dashboard page
- `frontend/js/admin.js` - admin UI logic

---

## 🛠️ Troubleshooting Guide

### Common Issues

**Issue 1: Automated update not running on Sunday**

**Symptoms:**
- Timer scheduled but service never executes
- No logs in `/var/log/cfb-rankings/weekly-update.log`

**Diagnosis:**
```bash
# Check timer status
systemctl status cfb-weekly-update.timer

# Check timer schedule
systemctl list-timers | grep cfb-weekly-update

# Check service status
journalctl -u cfb-weekly-update.service -n 50
```

**Solutions:**
- Verify timer enabled: `systemctl enable cfb-weekly-update.timer`
- Check timer schedule: `systemd-analyze calendar "Mon 00:00"`
- Verify service executes manually: `systemctl start cfb-weekly-update.service`

---

**Issue 2: API usage tracking not recording calls**

**Symptoms:**
- `/api/admin/api-usage` returns 0 total calls
- `api_usage` table empty despite API calls being made

**Diagnosis:**
```bash
# Check database table exists
sqlite3 cfb_rankings.db ".schema api_usage"

# Check decorator applied to methods
grep -n "@track_api_usage" cfbd_client.py

# Check application logs for tracking errors
journalctl -u cfb-rankings | grep "track_api_usage"
```

**Solutions:**
- Verify `@track_api_usage` decorator applied to all CFBD client methods
- Check database permissions (www-data can write)
- Review error logs for tracking failures
- Verify `CFBD_MONTHLY_LIMIT` set in `.env`

---

**Issue 3: Manual trigger hangs or times out**

**Symptoms:**
- POST `/api/admin/trigger-update` times out
- UI shows "Running..." indefinitely
- No completion status returned

**Diagnosis:**
```bash
# Check background task status
ps aux | grep weekly_update.py

# Check update task records
sqlite3 cfb_rankings.db "SELECT * FROM update_tasks ORDER BY started_at DESC LIMIT 5;"

# Check logs
tail -f /var/log/cfb-rankings/weekly-update.log
```

**Solutions:**
- Increase timeout in service config (default: 1800s / 30 min)
- Check database not locked (stop main service if needed)
- Verify CFBD API accessible (curl test)
- Kill hung process: `pkill -f weekly_update.py`

---

**Issue 4: API usage >90%, automated update aborted**

**Symptoms:**
- Warning log: "API usage at 92% - update aborted"
- Rankings not updated despite Sunday timer execution

**Diagnosis:**
```bash
# Check current usage
curl http://localhost:8000/api/admin/api-usage

# Check monthly call count
sqlite3 cfb_rankings.db "SELECT COUNT(*) FROM api_usage WHERE month = '2025-01';"
```

**Solutions:**
- **Short-term:** Increase monthly limit in `.env` (if upgraded to paid tier)
- **Short-term:** Manually trigger update on 1st of next month (resets quota)
- **Long-term:** Optimize import script to reduce API calls
- **Long-term:** Cache team/conference data to reduce redundant calls

---

## 📚 Documentation Updates

### README.md Updates

**New Section:**
```markdown
## Automated Weekly Updates

The system automatically imports new game data every Sunday at 8:00 PM ET during the active college football season (August 1 - January 31).

### How It Works

- **Scheduler:** systemd timer triggers weekly updates
- **Pre-flight Checks:** Validates active season, detects current week, checks API usage
- **Execution:** Runs data import automatically
- **Logging:** All updates logged to `/var/log/cfb-rankings/weekly-update.log`

### Manual Trigger

Administrators can manually trigger updates via the admin dashboard:

1. Navigate to `/frontend/admin.html`
2. Click "Trigger Update Now"
3. Monitor real-time status

### API Usage Monitoring

View current API usage stats at `/api/admin/api-usage` or the admin dashboard. The system tracks all CFBD API calls and warns when approaching the monthly limit (default: 1000 calls/month).
```

### Deployment Guide Updates

**New Section:**
```markdown
## EPIC-004: Automated Updates Deployment

### Install systemd Timer

```bash
sudo cp deploy/cfb-weekly-update.timer /etc/systemd/system/
sudo cp deploy/cfb-weekly-update.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable cfb-weekly-update.timer
sudo systemctl start cfb-weekly-update.timer
```

### Verify Installation

```bash
systemctl status cfb-weekly-update.timer
systemctl list-timers | grep cfb-weekly-update
```

### Environment Configuration

Add to `.env`:
```
CFBD_MONTHLY_LIMIT=1000
```
```

---

## 🎉 Summary

This epic delivers comprehensive automation and monitoring for the College Football Ranking System:

✅ **Automated Weekly Updates** - No more manual SSH + script execution
✅ **API Usage Tracking** - Full visibility into CFBD API consumption
✅ **Proactive Alerts** - Warnings prevent quota exhaustion
✅ **Admin Dashboard** - Real-time usage stats and control
✅ **Manual Override** - Trigger updates on-demand when needed
✅ **Robust Error Handling** - Graceful failures with comprehensive logging

**Estimated ROI:**
- **Time Saved:** ~15 min/week × 22 weeks/season = **5.5 hours/season**
- **Risk Reduction:** Prevents stale data, quota violations, service disruptions
- **Operational Efficiency:** Automated monitoring reduces reactive troubleshooting

---

## 📅 Story Development Order

1. **EPIC-004-STORY-001** (6-8 hours) - API Usage Tracking Infrastructure
2. **EPIC-004-STORY-002** (8-10 hours) - Automated Weekly Update Scheduler
3. **EPIC-004-STORY-003** (6-8 hours) - Manual Update Trigger & Admin Controls

**Total Effort:** 20-26 hours (~3-4 weeks at 6-8 hours/week)

---

**Epic Status:** ✅ Ready for Development
**Documentation:** ✅ Complete
**Stories:** ✅ Detailed and Ready
**Last Updated:** 2025-01-19
