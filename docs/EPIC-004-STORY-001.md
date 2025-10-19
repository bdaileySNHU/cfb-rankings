# Story 001: API Usage Tracking Infrastructure

**Epic:** EPIC-004 - Automated Weekly Updates & API Usage Monitoring
**Story ID:** EPIC-004-STORY-001
**Priority:** High (Foundation for other stories)
**Estimated Effort:** 6-8 hours

---

## User Story

**As a** system administrator,
**I want** to track all CFBD API usage and see current monthly consumption,
**So that** I can monitor approaching API limits and avoid unexpected quota exhaustion.

---

## Story Context

**Existing System Integration:**

- **Integrates with:** `cfbd_client.py` (CFBD API wrapper), SQLite database via SQLAlchemy
- **Technology:** Python 3.11, SQLAlchemy ORM, FastAPI, SQLite
- **Follows pattern:** Existing database models in `models.py`, API endpoints in `main.py`, Pydantic schemas in `schemas.py`
- **Touch points:**
  - `cfbd_client.py` - add tracking decorator to all API methods
  - `models.py` - add new `APIUsage` model
  - `schemas.py` - add `APIUsageResponse` schema
  - `main.py` - add `/api/admin/api-usage` endpoint
  - `.env` - add `CFBD_MONTHLY_LIMIT` configuration

---

## Acceptance Criteria

### Functional Requirements

1. **API Usage Database Table Created**
   - New `api_usage` table with columns:
     - `id` (INTEGER PRIMARY KEY)
     - `endpoint` (VARCHAR - CFBD API endpoint called, e.g., "/games", "/teams")
     - `timestamp` (DATETIME - when API call was made)
     - `status_code` (INTEGER - HTTP response code, e.g., 200, 404, 500)
     - `response_time_ms` (FLOAT - API response time in milliseconds)
     - `month` (VARCHAR - YYYY-MM format for aggregation, e.g., "2025-01")
     - `created_at` (DATETIME - record creation timestamp)
   - SQLAlchemy model created in `models.py`
   - Table created via migration or automatic creation

2. **CFBD Client Tracking Decorator**
   - Python decorator `@track_api_usage` added to `cfbd_client.py`
   - Decorator wraps all CFBD API methods (e.g., `get_games()`, `get_teams()`, `get_recruiting()`)
   - Decorator captures:
     - Endpoint URL
     - Response status code
     - Response time
     - Current month (YYYY-MM)
   - Decorator inserts record into `api_usage` table after each API call
   - Decorator does NOT block or fail API call if tracking insert fails (graceful degradation)
   - Decorator adds <5ms overhead to API calls

3. **Monthly Usage Aggregation Query**
   - Function `get_monthly_usage(month: str)` returns:
     - Total API calls for specified month
     - Configured monthly limit (from `.env`)
     - Percentage of limit used
     - Remaining calls
     - Average calls per day
     - Breakdown by endpoint (top 5 most-called endpoints)
   - Function located in `cfbd_client.py` or new `api_usage_service.py`

4. **API Usage Dashboard Endpoint**
   - New endpoint: `GET /api/admin/api-usage`
   - Query parameters:
     - `month` (optional, defaults to current month YYYY-MM)
   - Returns JSON response (Pydantic schema `APIUsageResponse`):
     ```json
     {
       "month": "2025-01",
       "total_calls": 456,
       "monthly_limit": 1000,
       "percentage_used": 45.6,
       "remaining_calls": 544,
       "average_calls_per_day": 15.2,
       "warning_level": null,  // or "80%", "90%", "95%"
       "top_endpoints": [
         {"endpoint": "/games", "count": 234},
         {"endpoint": "/teams", "count": 123},
         {"endpoint": "/recruiting", "count": 99}
       ],
       "last_updated": "2025-01-30T14:23:10Z"
     }
     ```

5. **Configurable Monthly Limit**
   - Environment variable `CFBD_MONTHLY_LIMIT` added to `.env` file (default: 1000)
   - Limit read from environment on application startup
   - Limit used in usage percentage calculations
   - Limit easily changeable by editing `.env` and restarting service

6. **Warning Threshold Logging**
   - Warning logs generated when usage crosses thresholds:
     - 80% of limit: `WARNING: CFBD API usage at 80% (800/1000 calls)`
     - 90% of limit: `WARNING: CFBD API usage at 90% (900/1000 calls)`
     - 95% of limit: `CRITICAL: CFBD API usage at 95% (950/1000 calls)`
   - Warnings logged to application log (via Python `logging` module)
   - Warnings checked on each API call (after usage tracking)
   - Warnings only logged ONCE per threshold per month (no spam)

### Integration Requirements

7. **Existing CFBD API Functionality Unchanged**
   - All existing `cfbd_client.py` methods work identically
   - API call behavior unchanged (same parameters, same return values)
   - No breaking changes to method signatures
   - Tracking is transparent to callers

8. **Database Schema Addition is Non-Breaking**
   - New `api_usage` table does NOT alter existing tables
   - Existing queries and models unaffected
   - Database migration (if used) is additive only

9. **Performance Impact is Minimal**
   - API call overhead <5ms (tracking insert is async or non-blocking if possible)
   - Database inserts batched if volume is high (optional optimization)
   - No impact on existing API endpoint response times

### Quality Requirements

10. **Tests Cover API Usage Tracking**
    - Unit test: Decorator correctly logs API calls
    - Unit test: Monthly usage aggregation calculates correctly
    - Unit test: Warning thresholds trigger at correct percentages
    - Integration test: `/api/admin/api-usage` endpoint returns correct data
    - Test that tracking failure doesn't break API calls

11. **Documentation Updated**
    - `README.md` updated with API usage tracking feature
    - `.env.example` includes `CFBD_MONTHLY_LIMIT=1000`
    - API documentation (OpenAPI/Swagger) includes `/api/admin/api-usage` endpoint
    - Inline code comments explain tracking decorator logic

12. **No Regression in Existing Functionality**
    - All existing 289 tests pass
    - Manual smoke test of data import (`import_real_data.py`) succeeds
    - API calls to CFBD return expected data

---

## Technical Notes

### Integration Approach

**Decorator Pattern for Tracking:**

```python
# In cfbd_client.py
import functools
from datetime import datetime
from sqlalchemy.orm import Session
from database import SessionLocal
from models import APIUsage
import logging

logger = logging.getLogger(__name__)

def track_api_usage(func):
    """Decorator to track CFBD API usage in database."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = datetime.now()

        try:
            # Execute the actual API call
            response = func(*args, **kwargs)
            status_code = 200  # Success
        except Exception as e:
            status_code = getattr(e, 'status_code', 500)
            raise
        finally:
            # Track usage (non-blocking)
            try:
                end_time = datetime.now()
                response_time_ms = (end_time - start_time).total_seconds() * 1000
                month = start_time.strftime("%Y-%m")

                db = SessionLocal()
                usage_record = APIUsage(
                    endpoint=func.__name__,  # or extract from URL
                    timestamp=start_time,
                    status_code=status_code,
                    response_time_ms=response_time_ms,
                    month=month
                )
                db.add(usage_record)
                db.commit()
                db.close()

                # Check warning thresholds
                check_usage_warnings(month)

            except Exception as tracking_error:
                logger.warning(f"Failed to track API usage: {tracking_error}")
                # Don't fail the API call due to tracking failure

        return response
    return wrapper
```

**Database Model:**

```python
# In models.py
class APIUsage(Base):
    __tablename__ = "api_usage"

    id = Column(Integer, primary_key=True, index=True)
    endpoint = Column(String(200), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    status_code = Column(Integer, nullable=False)
    response_time_ms = Column(Float, default=0.0)
    month = Column(String(7), index=True, nullable=False)  # YYYY-MM
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Usage Aggregation Function:**

```python
# In cfbd_client.py or api_usage_service.py
def get_monthly_usage(month: str = None) -> dict:
    """Get API usage stats for specified month."""
    if not month:
        month = datetime.now().strftime("%Y-%m")

    db = SessionLocal()

    # Total calls
    total_calls = db.query(APIUsage).filter(APIUsage.month == month).count()

    # Monthly limit from environment
    monthly_limit = int(os.getenv("CFBD_MONTHLY_LIMIT", "1000"))

    # Calculate metrics
    percentage_used = (total_calls / monthly_limit) * 100 if monthly_limit > 0 else 0
    remaining_calls = monthly_limit - total_calls

    # Top endpoints
    top_endpoints = (
        db.query(APIUsage.endpoint, func.count(APIUsage.id).label('count'))
        .filter(APIUsage.month == month)
        .group_by(APIUsage.endpoint)
        .order_by(func.count(APIUsage.id).desc())
        .limit(5)
        .all()
    )

    db.close()

    return {
        "month": month,
        "total_calls": total_calls,
        "monthly_limit": monthly_limit,
        "percentage_used": round(percentage_used, 2),
        "remaining_calls": remaining_calls,
        "top_endpoints": [{"endpoint": ep, "count": cnt} for ep, cnt in top_endpoints]
    }
```

### Existing Pattern Reference

- Follow existing database model pattern in `models.py` (Team, Game, RankingHistory models)
- Follow existing endpoint pattern in `main.py` (FastAPI route with Pydantic response)
- Follow existing schema pattern in `schemas.py` (Pydantic BaseModel with field validation)

### Key Constraints

- **Non-blocking tracking**: API usage tracking MUST NOT slow down or block CFBD API calls
- **Graceful degradation**: If tracking fails, API call should still succeed
- **Privacy**: No sensitive data logged (API responses not stored, only metadata)
- **Storage**: API usage records grow over time; consider archival strategy for old months (future enhancement)

---

## Definition of Done

- [x] `api_usage` table created in SQLite database with correct schema
- [x] `APIUsage` model added to `models.py`
- [x] `APIUsageResponse` Pydantic schema added to `schemas.py`
- [x] `@track_api_usage` decorator implemented in `cfbd_client.py`
- [x] All CFBD API client methods decorated with `@track_api_usage`
- [x] `get_monthly_usage()` function implemented and tested
- [x] `GET /api/admin/api-usage` endpoint created in `main.py`
- [x] `CFBD_MONTHLY_LIMIT` environment variable added to `.env` and `.env.example`
- [x] Warning threshold logging implemented (80%, 90%, 95%)
- [x] Tests written and passing (unit + integration tests)
- [x] Documentation updated (README, API docs, inline comments)
- [x] All 289+ existing tests pass (no regressions)
- [x] Manual smoke test: Run `import_real_data.py`, verify usage tracked correctly
- [x] Manual smoke test: Call `/api/admin/api-usage`, verify accurate stats returned

---

## Risk and Compatibility Check

### Minimal Risk Assessment

**Primary Risk:** Tracking database inserts fail or slow down CFBD API calls, impacting data import performance

**Mitigation:**
- Wrap tracking logic in try-except to prevent failures from bubbling up
- Use asynchronous database inserts if possible (or separate thread)
- Add timeout to tracking insert (max 100ms)
- Log tracking failures but don't raise exceptions

**Rollback:**
- Remove `@track_api_usage` decorator from all methods
- Leave `api_usage` table in place (no data loss, just stop tracking)
- Comment out `/api/admin/api-usage` endpoint
- Remove `CFBD_MONTHLY_LIMIT` from `.env` (or leave for future use)

### Compatibility Verification

- [x] No breaking changes to existing CFBD API client methods
- [x] Database change is additive only (new table, no alterations)
- [x] No UI changes (admin endpoint only, no frontend impact yet)
- [x] Performance impact <5ms per API call (tested with timing decorator)

---

## Validation Checklist

### Scope Validation

- [x] Story can be completed in 6-8 hours of focused development
- [x] Integration approach is straightforward (decorator pattern + new table)
- [x] Follows existing patterns (models, endpoints, schemas)
- [x] No design or architecture work required (clear technical approach)

### Clarity Check

- [x] Story requirements are unambiguous (detailed acceptance criteria)
- [x] Integration points are clearly specified (decorator on client, new endpoint)
- [x] Success criteria are testable (specific tests listed in DoD)
- [x] Rollback approach is simple (remove decorator, disable endpoint)

---

## Testing Strategy

### Unit Tests

**Test File:** `tests/test_api_usage_tracking.py`

```python
def test_track_api_usage_decorator_logs_call():
    """Test that decorator creates APIUsage record."""
    # Mock CFBD API call
    # Apply decorator
    # Execute function
    # Assert APIUsage record created with correct fields

def test_get_monthly_usage_calculates_correctly():
    """Test monthly usage aggregation logic."""
    # Seed api_usage table with test data
    # Call get_monthly_usage()
    # Assert total_calls, percentage_used, remaining_calls correct

def test_warning_threshold_triggers_at_80_percent():
    """Test warning logged at 80% usage."""
    # Seed usage data to 80% of limit
    # Trigger API call
    # Assert warning logged

def test_tracking_failure_does_not_break_api_call():
    """Test graceful degradation if tracking fails."""
    # Mock database insert to raise exception
    # Execute API call
    # Assert API call succeeds despite tracking failure
```

### Integration Tests

**Test File:** `tests/test_api_usage_endpoint.py`

```python
def test_api_usage_endpoint_returns_current_month_stats():
    """Test GET /api/admin/api-usage returns correct data."""
    # Seed api_usage table with current month data
    # Call GET /api/admin/api-usage
    # Assert response matches expected structure
    # Assert total_calls, percentage_used accurate

def test_api_usage_endpoint_with_month_parameter():
    """Test endpoint with specific month query param."""
    # Seed multiple months of data
    # Call GET /api/admin/api-usage?month=2024-12
    # Assert only December 2024 data returned
```

---

## Dependencies

**Required Before Starting:**
- EPIC-004 epic approved
- Development environment set up with SQLite database

**Blocks:**
- EPIC-004-STORY-002 (scheduler needs usage checking before import)
- EPIC-004-STORY-003 (admin dashboard displays usage stats)

---

## Notes

- Consider adding index on `api_usage.month` column for faster aggregation queries
- Future enhancement: Archive old usage data (>6 months) to separate table to keep queries fast
- Future enhancement: Add daily/weekly usage trends to dashboard
- Future enhancement: Email alerts when approaching limits (requires email service integration)

---

**Story Status:** Ready for Development
**Last Updated:** 2025-01-19
