# Epic 021: Quarter-Weighted ELO with Garbage Time Adjustment

**Epic Number**: EPIC-021
**Created**: 2025-11-16
**Status**: Planning

## Epic Goal

Enhance the ELO ranking algorithm to process games quarter-by-quarter with reduced weighting for 4th quarter scoring in high-differential games, producing more accurate rankings by accounting for garbage time touchdowns.

## Epic Description

**Existing System Context:**

- **Current functionality**: ELO ratings are calculated using full-game scores with a margin of victory (MOV) multiplier based on final point differential
- **Technology stack**:
  - Backend: Python 3.x, FastAPI, SQLAlchemy
  - Database: PostgreSQL
  - External API: College Football Data API (CFBD)
  - Core algorithm: `RankingService.process_game()` in `ranking_service.py`
- **Integration points**:
  - `Game` model in `models.py` (stores home_score, away_score)
  - `calculate_mov_multiplier()` method (line 102 in ranking_service.py)
  - CFBD API client for game data import
  - Database migration system for schema changes

**Enhancement Details:**

- **What's being added/changed**:
  1. Quarter-by-quarter score storage in `Game` model (8 new fields: q1-q4 for home/away)
  2. CFBD API integration to fetch quarter scores during import
  3. Modified ELO calculation that:
     - Processes each quarter as a mini-game with weighted contribution
     - Detects "garbage time" (4th quarter with score differential > threshold)
     - Applies reduced weight (e.g., 25-50%) to 4th quarter MOV in blowouts
  4. Data migration to backfill quarter scores for existing games

- **How it integrates**:
  - Extends `Game` model with optional quarter score fields (nullable for backward compatibility)
  - Replaces single `calculate_mov_multiplier()` call with quarter-weighted calculation
  - Updates `cfbd_client.py` to fetch additional quarter score data
  - Maintains existing API contract - no frontend changes required initially

- **Success criteria**:
  - Rankings correctly discount garbage time touchdowns (e.g., 35-0 game with late TD ranks better than 35-7)
  - All existing games backfilled with quarter data (where available from CFBD)
  - No regression in existing ELO calculation logic
  - Performance impact < 10% on ranking calculation time

## Stories

### Story 21.1: Quarter Score Data Model and API Integration

**Goal**: Add database support for quarter scores and fetch them from CFBD API

**Tasks**:
- Add 8 new nullable fields to `Game` model: `q1_home`, `q1_away`, `q2_home`, `q2_away`, `q3_home`, `q3_away`, `q4_home`, `q4_away`
- Create Alembic migration for schema change
- Update `cfbd_client.py` to fetch quarter scores from CFBD API (line score endpoint)
- Modify import scripts (`import_real_data.py`, `scripts/update_games.py`) to populate quarter fields
- Add validation to ensure quarter scores sum to final score

**Acceptance Criteria**:
- Migration runs successfully on dev and production databases
- New games imported include quarter scores when available from CFBD
- Existing games remain functional with NULL quarter scores
- Quarter score validation prevents data integrity issues

**Integration Verification**:
- IV1: Existing games without quarter data still process correctly
- IV2: API imports complete successfully with new quarter fields
- IV3: Database queries perform within acceptable thresholds (no index degradation)

---

### Story 21.2: Quarter-Weighted ELO Algorithm Implementation

**Goal**: Implement quarter-by-quarter ELO calculation with garbage time detection

**Tasks**:
- Create new method `calculate_quarter_weighted_mov()` in `RankingService`
- Implement garbage time detection logic:
  - Threshold: Score differential > 21 points entering 4th quarter
  - 4th quarter weight: 0.25 (25%) when garbage time detected, 1.0 otherwise
- Modify `process_game()` to use quarter-weighted calculation when quarter data available
- Add configuration constants: `GARBAGE_TIME_THRESHOLD`, `GARBAGE_TIME_Q4_WEIGHT`
- Maintain backward compatibility: fall back to current MOV calculation if quarters unavailable

**Acceptance Criteria**:
- Quarter-weighted algorithm correctly processes games with quarter data
- Garbage time detection activates when differential > threshold
- Games without quarter data fall back to legacy MOV calculation
- Unit tests cover garbage time, close games, and missing data scenarios

**Integration Verification**:
- IV1: Rankings for existing games (no quarter data) remain unchanged
- IV2: New rankings with quarter data show expected adjustments for blowouts
- IV3: Performance benchmarks show < 10% overhead for quarter processing

---

### Story 21.3: Historical Data Backfill and Validation

**Goal**: Backfill quarter scores for existing games and validate ranking accuracy

**Tasks**:
- Create backfill script `scripts/backfill_quarter_scores.py`
- Fetch quarter data from CFBD API for all existing games in database
- Update `Game` records with quarter scores where available
- Generate before/after ranking comparison report
- Document games where quarter data unavailable from CFBD

**Acceptance Criteria**:
- 90%+ of existing games have quarter scores backfilled
- Ranking changes documented and validated (spot-check top 25)
- Script handles API rate limits and failures gracefully
- Report shows ranking impact of quarter-weighted algorithm

**Integration Verification**:
- IV1: All existing API endpoints return correct data after backfill
- IV2: Frontend displays rankings correctly with new algorithm
- IV3: Historical ranking queries show consistent results

---

## Compatibility Requirements

- ✓ **Existing APIs remain unchanged**: All current endpoints maintain same contract
- ✓ **Database schema changes are backward compatible**: Quarter fields are nullable, legacy queries unaffected
- ✓ **UI changes follow existing patterns**: No frontend changes required initially (future enhancement)
- ✓ **Performance impact is minimal**: < 10% overhead on ranking calculations, indexes maintained

## Risk Mitigation

**Primary Risk**: Algorithm changes produce unexpected ranking shifts that undermine user trust

**Mitigation**:
- Generate comprehensive before/after comparison report
- Provide configuration flag to toggle between legacy and quarter-weighted algorithms
- Implement gradual rollout: test on historical seasons before applying to current season
- Document expected ranking changes with rationale (e.g., "Team X drops 3 spots due to garbage time TDs")

**Rollback Plan**:
- Feature flag `USE_QUARTER_WEIGHTED_ELO` defaults to `False` initially
- Database migration is additive (new columns), rollback drops columns if needed
- Alembic downgrade script provided for schema rollback
- Rankings can be recalculated using legacy algorithm from same game data

## Definition of Done

- ✓ All 3 stories completed with acceptance criteria met
- ✓ Existing functionality verified: legacy MOV calculation still works for games without quarter data
- ✓ Integration points working: CFBD API fetches quarter scores, database stores them correctly
- ✓ Documentation updated: Algorithm explanation in `docs/architecture.md`, migration notes in this document
- ✓ No regression in existing features: All tests pass, rankings for non-quarter games unchanged

## References

- **Current ELO Implementation**: `ranking_service.py:102-116` (`calculate_mov_multiplier`)
- **Game Model**: `models.py:60-100`
- **CFBD API Client**: `cfbd_client.py`
- **Architecture Documentation**: `docs/architecture.md`
