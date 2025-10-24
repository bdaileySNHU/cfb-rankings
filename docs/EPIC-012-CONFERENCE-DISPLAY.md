# EPIC-012: Add Actual Conference Display

**Status:** Planning
**Priority:** Medium
**Complexity:** Medium
**Estimated Effort:** 3-4 hours

---

## Problem Statement

The system currently displays only conference TIER (P5/G5/FCS) instead of actual conference names. Users want to see the actual conference (Big Ten, SEC, ACC, etc.) while still maintaining the tier system for ranking exclusion logic.

### Current Behavior
- Ohio State → "P5"
- Alabama → "P5"
- Toledo → "G5"

### Desired Behavior
- Ohio State → "Big Ten" (P5)
- Alabama → "SEC" (P5)
- Toledo → "Mid-American" (G5)

---

## Business Requirements

### Keep Tier System
The P5/G5/FCS tier system must remain because:
1. FCS games are excluded from ELO calculations
2. Conference tier affects preseason rating calculations
3. Filtering/grouping by tier is valuable

### Add Conference Names
Users want to see actual conference affiliations:
- **Power 5:** SEC, Big Ten, ACC, Big 12, Pac-12
- **Group of 5:** American Athletic, Mountain West, Conference USA, Mid-American, Sun Belt
- **Independents:** FBS Independents, FCS

---

## Technical Investigation

### CFBD API Data Available ✅

The CFBD API **already provides** conference names in team data:

```json
{
  "school": "Alabama",
  "conference": "SEC",
  "classification": "fbs"
}
```

**Sample conferences in API:**
- "SEC"
- "Big Ten"
- "ACC"
- "Big 12"
- "Pac-12"
- "Mountain West"
- "Mid-American"
- "American Athletic"
- "Conference USA"
- "Sun Belt"
- "FBS Independents"

### Current Implementation Issue

The import script currently:
1. Fetches conference name from API: `conference_name = team_data.get('conference')`
2. Maps it to tier enum: `conference = CONFERENCE_MAP.get(conference_name, ConferenceType.GROUP_5)`
3. Stores ONLY the tier: `Team(conference=conference)`
4. **Discards the actual conference name** ❌

### Database Schema Current State

```python
class Team(Base):
    conference = Column(Enum(ConferenceType), nullable=False)  # Only stores P5/G5/FCS
```

---

## Solution Design

### Database Changes

Add new field to store actual conference name alongside tier:

```python
class Team(Base):
    # Existing fields
    conference = Column(Enum(ConferenceType), nullable=False)  # P5/G5/FCS (keep for logic)

    # NEW field
    conference_name = Column(String(50), nullable=True)  # "SEC", "Big Ten", etc.
```

### Import Script Changes

Modify `import_real_data.py` to save both values:

```python
# Get conference data from API
conference_name = team_data.get('conference', 'FBS Independents')

# Map to tier (for logic)
conference_tier = CONFERENCE_MAP.get(conference_name, ConferenceType.GROUP_5)

# Create team with BOTH values
team = Team(
    name=team_name,
    conference=conference_tier,           # P5/G5/FCS
    conference_name=conference_name,      # "SEC", "Big Ten", etc.
    # ... other fields
)
```

### Frontend Changes

Display conference name with tier in parentheses:

```html
<!-- Team page -->
<div class="stat">
  <div class="stat-label">Conference</div>
  <div class="stat-value">SEC (P5)</div>
</div>

<!-- Rankings page -->
<td>Alabama - SEC (P5)</td>
```

---

## Implementation Stories

### Story 001: Database Migration

**Acceptance Criteria:**
- [ ] New `conference_name` field added to `teams` table
- [ ] Migration script creates field as nullable
- [ ] Migration runs without errors on production

**Deliverables:**
- `migrate_add_conference_name.py` script

**Implementation:**
```python
"""
Add conference_name field to teams table
EPIC-012: Conference Display
"""
import sqlite3

def migrate():
    conn = sqlite3.connect('cfb_rankings.db')
    cursor = conn.cursor()

    # Add conference_name column
    cursor.execute("""
        ALTER TABLE teams
        ADD COLUMN conference_name VARCHAR(50) NULL
    """)

    conn.commit()
    conn.close()
    print("✓ Added conference_name field")

if __name__ == "__main__":
    migrate()
```

---

### Story 002: Update Import Script

**Acceptance Criteria:**
- [ ] Import script saves both conference tier AND name
- [ ] Existing tier logic unchanged (for FCS exclusion)
- [ ] All teams get correct conference name on next import
- [ ] No API changes needed (uses existing data)

**Files to Modify:**
- `import_real_data.py`
- `models.py`

**Implementation:**

**models.py:**
```python
class Team(Base):
    __tablename__ = "teams"

    # ... existing fields ...
    conference = Column(Enum(ConferenceType), nullable=False)
    conference_name = Column(String(50), nullable=True)  # NEW
```

**import_real_data.py:**
```python
# Line ~155
conference_name = team_data.get('conference', 'FBS Independents')
conference_tier = CONFERENCE_MAP.get(conference_name, ConferenceType.GROUP_5)

# Line ~166
team = Team(
    name=team_name,
    conference=conference_tier,
    conference_name=conference_name,  # NEW - save the actual name
    recruiting_rank=recruiting_rank,
    # ... rest of fields
)
```

---

### Story 003: Update Backend API

**Acceptance Criteria:**
- [ ] Team schemas include conference_name
- [ ] All API endpoints return conference_name
- [ ] Backward compatible (tier still returned)

**Files to Modify:**
- `schemas.py`

**Implementation:**

```python
class TeamSchema(BaseModel):
    id: int
    name: str
    conference: str  # Existing: "P5", "G5", "FCS"
    conference_name: Optional[str]  # NEW: "SEC", "Big Ten", etc.
    elo_rating: float
    # ... other fields
```

---

### Story 004: Update Frontend Display

**Acceptance Criteria:**
- [ ] Team pages show conference name with tier
- [ ] Rankings page shows conference name
- [ ] Schedule tables show conference name
- [ ] Fallback to tier if conference_name missing

**Files to Modify:**
- `frontend/js/team.js`
- `frontend/js/rankings.js`

**Implementation:**

```javascript
// Display conference with tier
function formatConference(conference, conferenceName) {
  if (conferenceName) {
    return `${conferenceName} (${conference})`;
  }
  return conference;  // Fallback to tier only
}

// Usage in team page
const conferenceDisplay = formatConference(
  team.conference,
  team.conference_name
);
```

---

## Data Migration Strategy

### Option 1: Re-import All Teams (Recommended)
- Run import script to populate conference_name for all teams
- Quick and ensures data consistency
- Already have import script ready

### Option 2: Backfill from API
- Create one-time script to fetch conference for existing teams
- More complex, not necessary since import is fast

**Recommendation:** Use Option 1

---

## Testing Plan

### Unit Tests
```python
def test_team_has_conference_name():
    team = create_test_team(
        name="Ohio State",
        conference=ConferenceType.POWER_5,
        conference_name="Big Ten"
    )
    assert team.conference_name == "Big Ten"
    assert team.conference == ConferenceType.POWER_5
```

### Integration Tests
1. Import teams via API
2. Verify conference_name saved correctly
3. Query API endpoint
4. Verify conference_name returned

### Manual Testing
1. Run migration locally
2. Re-import teams
3. Check database: `SELECT name, conference, conference_name FROM teams LIMIT 10;`
4. View frontend and verify display
5. Test all team types (P5, G5, FCS, Independent)

---

## Deployment

**Risk Level:** 🟡 Medium (Database migration required)

**Estimated Time:** 20-25 minutes

### Deployment Steps

#### Step 1: Deploy Code
```bash
cd ~/Stat-urday\ Synthesis
git pull origin main
```

#### Step 2: Run Migration
```bash
sudo -u www-data python3 migrate_add_conference_name.py
```

**Expected output:**
```
✓ Added conference_name field
```

#### Step 3: Re-import Team Data
```bash
# This will populate conference_name for all teams
sudo -u www-data -E env PATH=$PATH python3 import_real_data.py <<< "yes"
```

**Expected output:**
```
Importing teams...
  Added: Ohio State (P5) - Conference: Big Ten
  Added: Alabama (P5) - Conference: SEC
  ...
```

#### Step 4: Restart Backend
```bash
sudo systemctl restart cfb-rankings
```

#### Step 5: Verify Deployment

**Database check:**
```bash
sqlite3 cfb_rankings.db "SELECT name, conference, conference_name FROM teams WHERE conference='P5' LIMIT 5;"
```

**Expected:**
```
Ohio State|P5|Big Ten
Alabama|P5|SEC
Georgia|P5|SEC
Michigan|P5|Big Ten
Clemson|P5|ACC
```

**Frontend check:**
- Visit team page → Should show "SEC (P5)" or "Big Ten (P5)"
- Visit rankings page → Conference names visible

---

## Rollback Plan

If deployment fails:

```bash
# Revert code
git revert HEAD
sudo systemctl restart cfb-rankings

# Remove column (if needed)
sqlite3 cfb_rankings.db "
  CREATE TABLE teams_backup AS SELECT * FROM teams;
  DROP TABLE teams;
  ALTER TABLE teams_backup RENAME TO teams;
"
```

---

## Success Metrics

- ✅ All teams have conference_name populated
- ✅ Frontend displays conference names correctly
- ✅ API returns conference_name in responses
- ✅ Tier logic (P5/G5/FCS) still works for calculations
- ✅ No breaking changes to existing functionality

---

## Future Enhancements

1. **Conference realignment tracking** - Historical conference changes
2. **Conference standings** - Show team's rank within conference
3. **Conference strength metrics** - Average ELO by conference
4. **Filter rankings by conference** - "Show only SEC teams"

---

## Related Work

- **EPIC-003:** FCS game display
- **EPIC-011:** FCS badge fix
