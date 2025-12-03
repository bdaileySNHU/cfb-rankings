# EPIC-026: Transfer Portal Team Rankings

**Status:** 📋 Placeholder / Future Work
**Priority:** Low
**Created:** 2025-12-02
**Target Release:** TBD

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

### Sample Data Structure (Expected)
```json
[
  {
    "season": 2024,
    "firstName": "John",
    "lastName": "Doe",
    "position": "QB",
    "origin": "Previous School",
    "destination": "New School",
    "transferDate": "2024-01-15",
    "rating": 0.95,
    "stars": 4,
    "eligibility": "Immediate"
  }
]
```

---

## Proposed Approach

### Phase 1: Data Collection
1. Call CFBD `/player/portal` endpoint for target season
2. Filter for incoming transfers only (ignore outgoing)
3. Group transfers by destination team
4. Store raw player transfer data

### Phase 2: Ranking Algorithm
Multiple options for calculating team transfer rankings:

#### Option A: Total Transfer Rating
- Sum all incoming transfer ratings
- Higher total = better transfer portal class
- Pro: Rewards quantity and quality
- Con: Favors teams with many transfers

#### Option B: Average Transfer Rating
- Average rating of incoming transfers
- Pro: Quality over quantity
- Con: One 5-star = same as multiple 4-stars

#### Option C: Weighted Composite
- Combine total rating, average rating, and count
- Formula: `score = (total_rating * 0.5) + (avg_rating * 0.3) + (count * 0.2)`
- Pro: Balanced approach
- Con: More complex, needs tuning

#### Option D: Position-Weighted
- Weight transfers by position value (QB > RB > WR, etc.)
- Pro: Recognizes impact positions
- Con: Subjective position values

### Phase 3: Integration
1. Add new field to Team model: `calculated_transfer_score`
2. Update import logic to calculate and store rankings
3. Integrate into preseason ELO calculation
4. Add to API responses

---

## Stories (Placeholder)

### Story 26.1: Research Transfer Portal API
**Goal:** Understand CFBD player portal data structure

**Tasks:**
- [ ] Make test API calls to `/player/portal?year=2024`
- [ ] Document actual response structure
- [ ] Analyze data completeness (ratings, stars, positions)
- [ ] Check historical data availability (2020-2024)
- [ ] Identify any data quality issues

---

### Story 26.2: Design Ranking Algorithm
**Goal:** Decide on methodology for team transfer rankings

**Tasks:**
- [ ] Evaluate ranking algorithm options (A-D above)
- [ ] Research how 247Sports/Rivals calculate transfer rankings
- [ ] Prototype algorithms with 2023 data
- [ ] Compare results with expert assessments
- [ ] Choose final approach

---

### Story 26.3: Implement Data Aggregation
**Goal:** Build system to aggregate player transfers into team rankings

**Tasks:**
- [ ] Add `get_transfer_portal()` method to CFBDClient
- [ ] Create transfer aggregation service
- [ ] Group transfers by destination team
- [ ] Calculate team transfer scores
- [ ] Generate rankings (1-N) based on scores

---

### Story 26.4: Database Schema Updates
**Goal:** Add fields to store calculated transfer data

**Tasks:**
- [ ] Add `calculated_transfer_score` to Team model
- [ ] Add `calculated_transfer_rank` to Team model
- [ ] Create migration script
- [ ] Update API serializers
- [ ] Update frontend display

---

### Story 26.5: Integration Testing
**Goal:** Validate transfer rankings accuracy

**Tasks:**
- [ ] Import 2023 transfer data
- [ ] Calculate team rankings
- [ ] Compare with 247Sports transfer portal rankings
- [ ] Adjust algorithm if needed
- [ ] Test with 2024 data

---

### Story 26.6: ELO Integration
**Goal:** Factor transfer rankings into preseason ELO

**Tasks:**
- [ ] Update preseason ELO calculation formula
- [ ] Weight transfer rank appropriately vs recruiting/returning production
- [ ] Test impact on preseason rankings
- [ ] Validate against actual season outcomes

---

## Open Questions

1. **Weighting:** How much should transfers count vs recruiting rank and returning production?
2. **Timing:** When to run calculation (portal windows: December/spring)?
3. **Quality Thresholds:** Should we filter low-rated transfers?
4. **FCS Transfers:** Include or exclude FCS-to-FBS transfers?
5. **Historical Data:** Do we backfill for previous seasons?

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
