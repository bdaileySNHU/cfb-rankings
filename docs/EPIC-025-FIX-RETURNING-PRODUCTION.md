# EPIC-025: Fix Returning Production Import

**Status:** ✅ Complete
**Priority:** High
**Created:** 2025-12-02
**Completed:** 2025-12-02
**Target Release:** Production Ready

---

## Problem Statement

All teams in the system are showing 50% (0.5) returning production instead of their actual values from CFBD. This affects the accuracy of preseason ELO calculations and team strength assessments.

### Current Behavior
- **All teams:** `returning_production = 0.5` (default value)
- **Expected:** Actual percentages based on returning starters/production
- **Example:** Ohio State, Georgia, all teams show 50%

### Impact
- Preseason ELO ratings less accurate
- No differentiation between teams with high/low returning production
- Missing key factor in team strength assessment

---

## Root Cause Analysis

### Code Location
`import_real_data.py`, lines 143-149:
```python
# Fetch returning production
returning_data = cfbd.get_returning_production(year) or []
returning_map = {}
for r in returning_data:
    if 'team' in r and 'returningProduction' in r:
        returning_map[r['team']] = r['team_name']['returningProduction']
```

### Data Source
- **CFBD Endpoint:** `GET /player/returning`
- **Method:** `cfbd_client.py:get_returning_production(year)`
- **Status:** API endpoint exists and is being called

### Hypothesis
One or more of the following issues:
1. **API response format mismatch** - Field names don't match our expectations
2. **Empty/null data** - CFBD may not have data for the requested year
3. **Data parsing error** - Logic error in mapping construction
4. **Team name mismatch** - Team names in API don't match our database names

---

## Technical Details

### Database Schema
`models.py`, Team model:
```python
returning_production = Column(Float, default=0.5)
```

### Import Logic Flow
1. Call `cfbd.get_returning_production(year)`
2. Build `returning_map` dictionary: `{team_name: production_value}`
3. Look up each team in map: `returning_map.get(team_name, 0.5)`
4. Store in database

### Current Test Results
```bash
# Ohio State (team_id: 82)
curl -s "https://cfb.bdailey.com/api/teams/82" | jq '.returning_production'
# Output: 0.5

# Georgia (team_id: 35)
curl -s "https://cfb.bdailey.com/api/teams/35" | jq '.returning_production'
# Output: 0.5
```

---

## Stories

### Story 25.1: Investigate CFBD API Response Format
**Goal:** Understand the actual data structure returned by CFBD

**Tasks:**
- [ ] Make test API call to `/player/returning?year=2024`
- [ ] Document actual response structure
- [ ] Compare with expected structure in code
- [ ] Check for field name differences
- [ ] Verify data availability for target years (2024, 2025)

**Acceptance Criteria:**
- Document exact JSON structure from CFBD
- Identify any field name mismatches
- Confirm data exists for current season

---

### Story 25.2: Fix Import Logic
**Goal:** Correct the data parsing to properly import returning production

**Tasks:**
- [ ] Update field names in `import_real_data.py` to match CFBD response
- [ ] Add error handling for missing data
- [ ] Add logging to track import success/failure
- [ ] Handle team name normalization if needed
- [ ] Add data validation (0.0 <= value <= 1.0)

**Acceptance Criteria:**
- Import script successfully parses CFBD response
- Teams get actual returning production values (not 0.5)
- Logging shows how many teams were updated
- Handle edge cases gracefully

**Files to Modify:**
- `import_real_data.py` (lines 143-149, 180)

---

### Story 25.3: Test and Verify Import
**Goal:** Validate that returning production data is correctly imported

**Tasks:**
- [ ] Run import for 2024 season
- [ ] Query database to verify varying values
- [ ] Test with known teams (e.g., Ohio State, Georgia)
- [ ] Compare values with CFBD website if available
- [ ] Re-run preseason ELO calculation

**Acceptance Criteria:**
- At least 50% of FBS teams have non-default values
- Values are distributed (not all the same)
- Spot-check 5 teams matches CFBD data
- Preseason ELO rankings reflect new data

**Test Commands:**
```bash
# Import with fixes
python import_real_data.py --season 2024

# Verify varying values
python -c "
from database import SessionLocal
from models import Team
db = SessionLocal()
teams = db.query(Team).filter(Team.returning_production != 0.5).count()
print(f'Teams with non-default returning production: {teams}')
"

# Check specific teams
curl -s "https://cfb.bdailey.com/api/teams/82" | jq '.returning_production'
```

---

### Story 25.4: Document Returning Production
**Goal:** Add documentation about returning production data

**Tasks:**
- [ ] Add comments to import code explaining data source
- [ ] Document expected value range (0.0-1.0)
- [ ] Add to system documentation
- [ ] Note any limitations or caveats

**Acceptance Criteria:**
- Code comments explain CFBD data structure
- Documentation includes example values
- Future maintainers understand the metric

---

## Success Metrics

- **Primary:** Teams show varying returning production values (not all 0.5)
- **Data Quality:** At least 80% of FBS teams have valid data
- **Accuracy:** Spot-check of 10 teams matches CFBD source
- **ELO Impact:** Preseason rankings show impact of returning production

---

## Dependencies

- **CFBD API:** Must have returning production data for target season
- **Team Names:** Team name normalization may be required
- **Preseason ELO:** May need to recalculate after fix

---

## Testing Plan

### Unit Tests
- Test parsing of sample CFBD response
- Test team name normalization
- Test value validation (0.0-1.0 range)

### Integration Tests
- Full import for 2024 season
- Verify database values
- Check API responses

### Manual Verification
- Compare 5 teams with CFBD website
- Verify preseason rankings change appropriately

---

## Rollout Plan

1. **Development:** Fix and test locally
2. **Staging:** Import 2024 data, verify results
3. **Production:**
   - Backup database
   - Re-run import for current season
   - Verify rankings update
   - Monitor for issues

---

## Related Documentation

- [SEASON-MANAGEMENT.md](SEASON-MANAGEMENT.md) - Season initialization process
- [WEEKLY-WORKFLOW.md](WEEKLY-WORKFLOW.md) - Data import procedures
- [EPIC-024](EPIC-024-SEASON-SPECIFIC-RECORDS.md) - Season data management

---

## Notes

- **Recruiting Rank:** Already working correctly ✅
- **Transfer Portal Rank:** Separate issue (see EPIC-026)
- **Data Freshness:** CFBD updates returning production after spring practices

---

**Last Updated:** 2025-12-02
**Owner:** Development Team
**EPIC:** EPIC-025
