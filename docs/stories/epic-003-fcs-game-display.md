# EPIC-003: FCS Game Display for Schedule Completeness

## Epic Goal

Enable users to view complete team schedules including FCS opponent games on the frontend, while maintaining the existing exclusion of FCS games from ELO ranking calculations. This provides schedule completeness and transparency without compromising ranking integrity.

## Epic Description

### Existing System Context

- **Current Functionality**: The system imports and displays only FBS vs FBS games. FCS opponents (e.g., Ohio State vs Grambling, Georgia vs Austin Peay) are intentionally excluded from the database to prevent artificial ELO rating inflation.
- **Technology Stack**:
  - Backend: FastAPI + SQLAlchemy (SQLite)
  - Data Source: CFBD API (`cfbd_client.py`)
  - Frontend: Vanilla JS (`team.js`)
  - Import Logic: `import_real_data.py`
- **Integration Points**:
  - CFBD API game import (`get_games()`)
  - Database models (`Game`, `Team`)
  - API endpoint (`/api/teams/{id}/schedule`)
  - Frontend team schedule display (`team.js` - `createScheduleRow()`)

### Enhancement Details

**What's being added:**
- Store FCS games in database with `excluded_from_rankings=True` flag
- API returns both ranked (FBS) and non-ranked (FCS) games in team schedules
- Frontend displays FCS games with visual distinction (grayed out, marked "Non-conference" or "FCS")
- Team records (W-L) continue to reflect only FBS games

**How it integrates:**
- Extends existing `Game` model with optional flag
- Modifies `import_real_data.py` to import FCS games separately
- Updates team schedule API to include both game types
- Frontend `team.js` applies conditional styling

**Success Criteria:**
1. Ohio State's schedule shows all 5 weeks (including Week 2 vs Grambling)
2. FCS games are visually distinct (different styling/labeling)
3. Team records (wins/losses) only count FBS games
4. ELO calculations remain unchanged (FCS games excluded)
5. All existing functionality continues to work

## Stories

### Story 1: Database Schema & Model Updates
**Goal**: Extend `Game` model to support FCS games without affecting ranking logic

**Key Tasks:**
- Add `excluded_from_rankings` boolean field to `Game` model (default: False)
- Add database migration
- Update `RankingService` to explicitly filter `excluded_from_rankings=False`
- Add tests to verify FCS games don't affect ELO calculations

**Acceptance Criteria:**
- Database supports FCS game storage
- Existing ranking logic explicitly ignores excluded games
- All 270+ existing tests still pass

### Story 2: Backend Import & API Updates
**Goal**: Import FCS games and expose them via team schedule API

**Key Tasks:**
- Modify `import_real_data.py` to import FCS games with `excluded_from_rankings=True`
- Update team schedule endpoint to return all games (FBS + FCS)
- Add field in API response indicating if game is excluded from rankings
- Update API documentation

**Acceptance Criteria:**
- Import script successfully imports FCS games
- Team schedule API returns complete schedules
- FCS games are clearly marked in API response
- Team win/loss counts only reflect FBS games

### Story 3: Frontend Schedule Display
**Goal**: Display complete team schedules with FCS games visually distinguished

**Key Tasks:**
- Update `team.js` `createScheduleRow()` to handle FCS games
- Apply distinct styling for FCS games (grayed text, "FCS" badge)
- Ensure team record display only counts FBS games
- Update schedule table to show game type (FBS/FCS)

**Acceptance Criteria:**
- Team schedules show all games (FBS + FCS)
- FCS games are visually distinct (grayed, labeled)
- Team records match FBS-only counts
- UI is intuitive and clear

## Compatibility Requirements

- ✅ Existing ranking calculations remain unchanged
- ✅ Database schema change is additive (new field with default)
- ✅ API adds data but doesn't break existing clients
- ✅ Frontend changes are backward compatible
- ✅ Performance impact negligible (minimal additional data)

## Risk Mitigation

**Primary Risk:** FCS games accidentally included in ELO calculations

**Mitigation:**
- Explicit `excluded_from_rankings=False` filter in `RankingService`
- Comprehensive test coverage for ranking logic
- Story 1 completes before Story 2 (schema/safety first)

**Rollback Plan:**
- Story 1: Database migration can be reverted
- Story 2: Disable FCS import with feature flag
- Story 3: Frontend change can be reverted via git

## Definition of Done

- ✅ All 3 stories completed with acceptance criteria met
- ✅ Team schedules show complete game lists (FBS + FCS)
- ✅ FCS games visually distinguished in UI
- ✅ Team records reflect FBS games only
- ✅ ELO calculations unchanged (verified by tests)
- ✅ No regression in existing features
- ✅ Production deployment successful

## Dependencies

- CFBD API must return FCS opponent data (already confirmed working)
- Existing test suite must pass before starting
- Database backup before migration

## Success Metrics

- Ohio State shows 5 games (Week 1, 2-FCS, 3, 5, 6)
- Georgia shows 5 games (Week 1, 2-FCS, 3, 5, 6)
- All FCS games clearly marked in UI
- Zero ranking calculation changes
- User feedback positive on schedule completeness

---

## Story Manager Handoff

"Please develop detailed user stories for this brownfield epic. Key considerations:

- This is an enhancement to an existing College Football Ranking System running FastAPI + SQLAlchemy + Vanilla JS
- Integration points:
  - `import_real_data.py` game import logic
  - `RankingService` ELO calculation (must NOT change)
  - `/api/teams/{id}/schedule` endpoint
  - `team.js` schedule display component
- Existing patterns to follow:
  - Database migrations with backward compatibility
  - API endpoint extensions (additive changes)
  - Frontend styling conventions (see `team.css`)
- Critical compatibility requirements:
  - **ZERO changes to ELO ranking calculations**
  - FCS games MUST be excluded from all ranking logic
  - Team W-L records reflect FBS games only
- Each story must include verification that existing ranking functionality remains intact

The epic should maintain ranking system integrity while delivering complete schedule transparency for users."

---

**Created by**: John (PM Agent)
**Date**: 2025-10-18
**Epic Type**: Brownfield Enhancement
**Estimated Effort**: 2-3 development sessions
