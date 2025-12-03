# EPIC-026: Transfer Portal Team Rankings

**Status:** 📋 Planning
**Priority:** Medium
**Created:** 2025-12-02
**Updated:** 2025-12-02
**Target Release:** Q1 2026

---

## Problem Statement

Transfer portal rank is currently hardcoded to 999 (N/A) for all teams because CFBD API only provides player-level transfer data, not team-level rankings. To properly factor transfer portal strength into preseason ELO calculations, we need to aggregate player data into team rankings.

### Current Behavior
- **All teams:** `transfer_rank = 999` (N/A)
- **Code:** Hardcoded in `import_real_data.py:179`
- **Reason:** CFBD doesn't provide team-level transfer portal rankings

### Desired Behavior
- Calculate team transfer portal rankings based on incoming transfers
- Use aggregated metrics (total ratings, average stars, quantity)
- Factor into preseason ELO calculations

### Impact
- Missing factor in preseason strength assessment
- Teams with strong transfer portal classes not properly credited
- Less accurate preseason rankings for teams rebuilding via portal

---

## Technical Background

### Current Implementation
`import_real_data.py`, line 179:
```python
transfer_rank = 999  # CFBD doesn't have transfer portal rankings easily accessible
```

### Data Source Available
- **CFBD Endpoint:** `GET /player/portal`
- **Parameters:** `year` (required)
- **Returns:** Player-level transfer data

### Actual Data Structure (Verified 2024 API)
```json
[
  {
    "season": 2024,
    "firstName": "Decamerion",
    "lastName": "Richardson",
    "position": "CB",
    "origin": "Mississippi State",
    "destination": "Ole Miss",
    "transferDate": "2023-12-13T17:23:00.000Z",
    "rating": 0.91,
    "stars": 4,
    "eligibility": "Immediate"
  }
]
```

**Data Quality (2024 Season):**
- **Total transfers:** 3,378
- **With destination:** 2,654 (78.6%) - ✅ Good
- **With rating:** 1,852 (54.8%) - ❌ Too sparse
- **With stars:** 2,996 (88.7%) - ✅ Excellent

**Key Finding:** Use **stars** as primary metric, not ratings.

**Transfer Volume:**
- **297 teams** received transfers
- **Top team:** Colorado (41 transfers)
- **Average:** ~9 transfers per team
- **Range:** 1-41 transfers per team

---

## Recommended Approach

Based on API analysis, use **star-based scoring** system:

### Algorithm: Star Points System

**Point Values:**
- 5-star transfer: **100 points**
- 4-star transfer: **80 points**
- 3-star transfer: **60 points**
- 2-star transfer: **40 points**
- 1-star or unrated: **20 points**

**Team Score Calculation:**
```python
team_score = sum(star_points for all incoming transfers)
team_rank = rank teams by team_score (highest = #1)
```

**Example:**
- Colorado: 41 transfers
  - 5x 4-star (400 pts) + 36x 3-star (2,160 pts) = **2,560 points** → Rank #1
- Indiana: 30 transfers
  - 2x 4-star (160 pts) + 28x 3-star (1,680 pts) = **1,840 points** → Rank #15

**Why This Algorithm:**
1. ✅ **Simple** - Easy to understand and implement
2. ✅ **Data Available** - 88.7% coverage for stars
3. ✅ **Balanced** - Rewards both quality (stars) and quantity (count)
4. ✅ **Comparable** - Can validate against 247Sports/On3 rankings

### Implementation Phases

#### Phase 1: Data Collection & Storage
1. Add CFBD client method: `get_transfer_portal(year)`
2. Filter for transfers with `destination != null`
3. Group by destination team
4. Calculate total points per team

#### Phase 2: Database Integration
1. Add fields to Team model:
   - `transfer_portal_points` (Integer)
   - `transfer_portal_rank` (Integer)
   - `transfer_count` (Integer)
2. Create migration for new fields
3. Update import logic to populate fields

#### Phase 3: Ranking & Display
1. Calculate rankings (1-N) based on points
2. Add to Team API responses
3. Update frontend to display transfer rank
4. Add to preseason ELO calculation

#### Phase 4: Validation & Tuning
1. Compare with 247Sports transfer rankings
2. Adjust point values if needed
3. Test preseason ELO impact

---

## Stories

### Story 26.1: API Client Implementation ✅ Complete (Research)
**Goal:** Verify CFBD API and understand data structure

**Status:** ✅ Research Complete (2025-12-02)

**Findings:**
- API endpoint: `/player/portal?year=YYYY`
- 3,378 transfers in 2024
- 78.6% have destinations (usable)
- 88.7% have star ratings (primary metric)
- 297 teams received transfers
- Colorado leads with 41 transfers

**Next:** Proceed to Story 26.2

---

### Story 26.2: Add CFBD Transfer Portal Method
**Goal:** Add API client method to fetch transfer data

**Priority:** High
**Effort:** Small (1-2 hours)

**Tasks:**
- [ ] Add `get_transfer_portal(year)` method to `cfbd_client.py`
- [ ] Handle pagination if needed (check API limits)
- [ ] Add error handling for missing data
- [ ] Add unit test for method
- [ ] Document method parameters and return format

**Acceptance Criteria:**
- Method returns list of player transfers for given year
- Filters out invalid data (null destination)
- Handles API errors gracefully
- Unit tests pass

**Files to Modify:**
- `cfbd_client.py` (add method ~line 458)
- `tests/test_cfbd_client.py` (add tests)

---

### Story 26.3: Implement Transfer Scoring Algorithm
**Goal:** Create service to calculate team transfer portal scores

**Priority:** High
**Effort:** Medium (4-6 hours)

**Tasks:**
- [ ] Create `services/transfer_portal_service.py`
- [ ] Implement star-to-points conversion
- [ ] Group transfers by destination team
- [ ] Calculate total points per team
- [ ] Generate rankings (1-N) based on points
- [ ] Handle edge cases (teams with no transfers)
- [ ] Add comprehensive unit tests

**Algorithm:**
```python
STAR_POINTS = {5: 100, 4: 80, 3: 60, 2: 40, 1: 20, None: 20}

def calculate_team_scores(transfers):
    team_scores = {}
    for transfer in transfers:
        if transfer['destination']:
            team = transfer['destination']
            stars = transfer.get('stars', 1)
            points = STAR_POINTS.get(stars, 20)
            team_scores[team] = team_scores.get(team, 0) + points
    return team_scores

def rank_teams(team_scores):
    sorted_teams = sorted(team_scores.items(),
                         key=lambda x: x[1],
                         reverse=True)
    return {team: rank+1 for rank, (team, _) in enumerate(sorted_teams)}
```

**Acceptance Criteria:**
- Correctly calculates points for all star levels
- Handles null/missing star values
- Ranks teams correctly (highest score = rank 1)
- Edge cases handled (0 transfers, ties)
- Unit tests cover all scenarios

**Files to Create:**
- `services/transfer_portal_service.py`
- `tests/test_transfer_portal_service.py`

---

### Story 26.4: Database Schema Changes
**Goal:** Add transfer portal fields to Team model

**Priority:** Medium
**Effort:** Small (2-3 hours)

**Tasks:**
- [ ] Add fields to Team model in `models.py`:
  - `transfer_portal_points` (Integer, default=0)
  - `transfer_portal_rank` (Integer, default=999)
  - `transfer_count` (Integer, default=0)
- [ ] Create Alembic migration script
- [ ] Test migration on dev database
- [ ] Update Team schema in `schemas.py`
- [ ] Document new fields

**Migration Command:**
```bash
alembic revision -m "Add transfer portal fields to teams"
```

**Acceptance Criteria:**
- Migration runs without errors
- Fields have correct types and defaults
- Backwards compatible (existing teams get default values)
- Schema documentation updated

**Files to Modify:**
- `models.py` (Team model, ~line 50)
- `schemas.py` (TeamResponse schema)
- `alembic/versions/XXXX_add_transfer_portal_fields.py` (new)

---

### Story 26.5: Import Logic Integration
**Goal:** Calculate and store transfer rankings during import

**Priority:** Medium
**Effort:** Medium (3-4 hours)

**Tasks:**
- [ ] Update `import_real_data.py` to fetch transfer data
- [ ] Call transfer portal service to calculate scores
- [ ] Update Team records with calculated values
- [ ] Add logging for transfer portal import
- [ ] Handle teams with no transfers gracefully
- [ ] Add transfer data to import output

**Integration Points:**
```python
# In import_real_data.py, after recruiting/returning production
print("Fetching transfer portal data...")
transfer_data = cfbd.get_transfer_portal(year)

print("Calculating transfer portal rankings...")
from services.transfer_portal_service import TransferPortalService
tp_service = TransferPortalService()
team_scores = tp_service.calculate_scores(transfer_data)
team_ranks = tp_service.rank_teams(team_scores)

# Update teams
for team_name, team_obj in team_objects.items():
    team_obj.transfer_portal_points = team_scores.get(team_name, 0)
    team_obj.transfer_portal_rank = team_ranks.get(team_name, 999)
    # Count transfers manually from transfer_data
```

**Acceptance Criteria:**
- Transfer data imported without errors
- All teams have valid transfer_portal_rank
- Teams with no transfers: rank=999, points=0
- Import logging shows transfer stats
- Print statement: "Loaded transfer data for X teams"

**Files to Modify:**
- `import_real_data.py` (~line 156, after returning production)

---

### Story 26.6: API Response Updates
**Goal:** Expose transfer portal data via API

**Priority:** Low
**Effort:** Small (1 hour)

**Tasks:**
- [ ] Add fields to TeamResponse schema
- [ ] Update `/api/teams/{id}` endpoint
- [ ] Update `/api/rankings` endpoint
- [ ] Test API responses with Postman/curl
- [ ] Update API documentation

**Expected Response:**
```json
{
  "team_id": 82,
  "name": "Ohio State",
  "recruiting_rank": 5,
  "transfer_portal_rank": 23,
  "transfer_portal_points": 1240,
  "transfer_count": 18,
  "returning_production": 0.308
}
```

**Acceptance Criteria:**
- New fields appear in API responses
- Values are accurate
- Swagger/API docs updated

**Files to Modify:**
- `schemas.py` (TeamResponse)
- `main.py` (if needed for endpoint logic)

---

### Story 26.7: Frontend Display
**Goal:** Show transfer portal rank on team pages

**Priority:** Low
**Effort:** Small (2 hours)

**Tasks:**
- [ ] Add transfer portal rank to team detail page
- [ ] Add to rankings table (optional column)
- [ ] Add tooltip explaining metric
- [ ] Style badge/indicator
- [ ] Test responsive design

**Acceptance Criteria:**
- Transfer rank visible on team page
- "N/A" or "999" displays as "--"
- Tooltip explains calculation
- Mobile-friendly display

**Files to Modify:**
- `frontend/team.html`
- `frontend/js/team.js`
- `frontend/css/style.css` (if styling needed)

---

### Story 26.8: Validation & Comparison
**Goal:** Validate rankings against 247Sports

**Priority:** Medium
**Effort:** Medium (3-4 hours)

**Tasks:**
- [ ] Scrape or manually collect 247Sports 2024 transfer rankings
- [ ] Compare top 25 teams from our rankings vs 247Sports
- [ ] Calculate correlation coefficient
- [ ] Identify major discrepancies
- [ ] Document comparison results
- [ ] Adjust algorithm if needed (point values)

**Acceptance Criteria:**
- Correlation coefficient > 0.70 (good alignment)
- Top 10 teams have at least 6/10 overlap
- Discrepancies explained (different methodology)
- Report documented

**Deliverable:**
- `docs/stories/26.8.story.md` with comparison results

---

### Story 26.9: Preseason ELO Integration
**Goal:** Factor transfer rank into preseason ELO

**Priority:** Low (after validation)
**Effort:** Medium (4-5 hours)

**Tasks:**
- [ ] Review current preseason ELO formula
- [ ] Determine weighting for transfer rank
- [ ] Update `ranking_service.py` initialization
- [ ] Test impact on preseason rankings
- [ ] Validate against actual season performance
- [ ] Document formula changes

**Proposed Weighting:**
- Recruiting Rank: 40%
- Returning Production: 35%
- Transfer Portal Rank: 25%

**Acceptance Criteria:**
- Transfer rank affects preseason ELO
- Top transfer teams get appropriate boost
- Formula documented
- Test results show improvement in prediction accuracy

**Files to Modify:**
- `ranking_service.py` (initialize_team_rating method)

---

## Implementation Summary

### Effort Estimate
- **Total Stories:** 9
- **Story 26.1:** ✅ Complete (research)
- **Story 26.2-26.9:** ~20-25 hours total
- **Critical Path:** Stories 26.2 → 26.3 → 26.4 → 26.5

### Story Priorities
**Phase 1 (Must Have):**
- 26.2: CFBD Client Method (2h)
- 26.3: Scoring Algorithm (5h)
- 26.4: Database Schema (3h)
- 26.5: Import Integration (4h)

**Phase 2 (Should Have):**
- 26.6: API Updates (1h)
- 26.8: Validation (4h)

**Phase 3 (Nice to Have):**
- 26.7: Frontend Display (2h)
- 26.9: Preseason ELO (5h)

### Success Criteria
✅ **Data Collection:** 78.6% transfer coverage
✅ **Algorithm:** Star-based points system
✅ **Rankings:** All FBS teams ranked 1-N
✅ **Validation:** Correlation > 0.70 with 247Sports
✅ **Integration:** Affects preseason ELO appropriately

---

## Open Questions

**Resolved:**
1. ✅ **Algorithm:** Use star-based points (not ratings)
2. ✅ **Data Availability:** 88.7% have stars, good coverage
3. ✅ **Metric Choice:** Simple sum of star points

**Remaining:**
1. **Weighting in ELO:** What % weight for transfer rank? (Proposed: 25%)
2. **Timing:** Update after each portal window? Or once preseason?
3. **FCS Transfers:** Include or exclude? (Recommend: Include all)
4. **Historical Backfill:** Implement for past seasons? (Recommend: 2023-2025 only)
5. **Tie Breaking:** How to handle teams with same points? (Recommend: by transfer count)

---

## Success Metrics (When Implemented)

- **Data Coverage:** Transfer data for 90%+ of FBS teams
- **Ranking Distribution:** Teams ranked 1-130+ (all FBS)
- **Accuracy:** Top 10 transfer classes align with expert rankings
- **ELO Impact:** Measurable improvement in preseason prediction accuracy

---

## Dependencies

- **CFBD API:** Must provide player transfer data with ratings
- **Player Ratings:** Require composite ratings (247/Rivals/ESPN)
- **Team Name Mapping:** Portal destination names → our team names
- **EPIC-025:** Should complete returning production first

---

## Priority Rationale

**Why Low Priority:**
1. Recruiting rank (currently working) is strong proxy for team strength
2. Returning production (EPIC-025) is more impactful metric
3. Transfer portal is newer phenomenon (< 5 years of data)
4. Requires complex aggregation logic
5. Algorithm needs research and validation

**When to Prioritize:**
- After EPIC-025 complete
- When transfer portal becomes more significant factor
- If user demand increases
- During off-season with development time available

---

## Alternative Solutions

### Option 1: Manual Entry
- Manually enter top 25 transfer classes from 247Sports
- Pro: Simple, accurate for top teams
- Con: Labor intensive, incomplete data

### Option 2: Third-Party API
- Find alternative API with team-level transfer rankings
- Pro: Pre-calculated, maintained by others
- Con: May not exist, potential cost

### Option 3: Keep Hardcoded
- Continue using 999 (N/A) for all teams
- Pro: No work required
- Con: Missing data factor in preseason calculations

---

## Research Links

- [CFBD API Docs](https://api.collegefootballdata.com/api/docs/)
- [247Sports Transfer Portal Rankings](https://247sports.com/Season/2024-Football/TransferPortalRankings/)
- [On3 Transfer Portal Rankings](https://www.on3.com/transfer-portal/rankings/)

---

## Related EPICs

- [EPIC-025: Fix Returning Production](EPIC-025-FIX-RETURNING-PRODUCTION.md) - Higher priority preseason metric
- [EPIC-024: Season-Specific Records](EPIC-024-SEASON-SPECIFIC-RECORDS.md) - Data management foundation

---

## Implementation Notes

When this EPIC is prioritized, start with:
1. **Research phase** - Understand data availability and quality
2. **Prototype** - Test algorithm with historical data
3. **Validate** - Compare with expert rankings
4. **Iterate** - Refine based on results

---

## Code Locations (For Future Reference)

### Files to Modify
- `import_real_data.py:179` - Remove hardcoded 999
- `cfbd_client.py` - Add `get_transfer_portal()` method
- `models.py` - Add transfer score/rank fields
- `preseason_elo.py` - Integrate into ELO calculation
- `main.py` - Add transfer data to API responses

### New Files Needed
- `services/transfer_rankings.py` - Transfer aggregation service
- `tests/test_transfer_rankings.py` - Unit tests

---

**Last Updated:** 2025-12-02
**Owner:** Development Team
**EPIC:** EPIC-026
**Status:** Placeholder - No immediate work planned
