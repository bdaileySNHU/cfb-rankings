# Returning Production Guide

**EPIC-025** - Understanding and using returning production in the CFB Rankings system

---

## Overview

**Returning Production** measures the percentage of a team's previous season's production (Predicted Points Added, or PPA) that returns for the current season. This metric is a key factor in preseason team strength assessment.

### Why It Matters

- **High returning production (80%+):** Veteran team with experience and continuity
- **Medium returning production (40-60%):** Balanced roster turnover
- **Low returning production (<20%):** Major roster changes (NFL departures, transfers out)

---

## Data Source

### CFBD API Endpoint
```
GET https://api.collegefootballdata.com/player/returning
```

**Parameters:**
- `year` (required): Season year (e.g., 2024)
- `team` (optional): Filter by specific team

### Response Structure
```json
{
  "season": 2024,
  "team": "Ohio State",
  "conference": "Big Ten",
  "percentPPA": 0.224,           // Overall returning production (22.4%)
  "percentPassingPPA": 0.024,    // Passing production (2.4%)
  "percentReceivingPPA": 0.288,  // Receiving production (28.8%)
  "percentRushingPPA": 0.626,    // Rushing production (62.6%)
  "usage": 0.318,                // Overall usage returning (31.8%)
  "passingUsage": 0.138,
  "receivingUsage": 0.382,
  "rushingUsage": 0.45
}
```

**Key Field:** `percentPPA`
- Represents overall team returning production
- Value range: 0.0 - 1.0 (decimal, not percentage)
- Example: 0.224 = 22.4% returning production

---

## Implementation

### Database Schema

`models.py` - Team model:
```python
class Team(Base):
    __tablename__ = "teams"

    # Preseason factors
    returning_production = Column(Float, default=0.5)
```

**Storage Format:**
- Stored as decimal (0.0 - 1.0)
- Default value: 0.5 (50%) for teams without data
- FCS teams: Default to 0.5 (CFBD doesn't provide FCS data)

### Import Logic

`import_real_data.py:141-156`:
```python
# Fetch returning production (EPIC-025)
# API returns percentPPA (decimal 0.0-1.0) for overall returning production
print("Fetching returning production...")
returning_data = cfbd.get_returning_production(year) or []
returning_map = {}
for r in returning_data:
    if 'team' in r and 'percentPPA' in r:
        team = r['team']
        prod = r['percentPPA']
        # Validate and store (API returns decimal, no conversion needed)
        if isinstance(prod, (int, float)) and 0.0 <= prod <= 1.0:
            returning_map[team] = prod
        else:
            print(f"  Warning: Invalid returning production for {team}: {prod}")

print(f"  Loaded returning production for {len(returning_map)} teams")
```

**Key Points:**
1. Use `percentPPA` field (not `returningProduction`)
2. Values are already decimals - no `/100` conversion needed
3. Validate range: 0.0 <= value <= 1.0
4. Default to 0.5 if team not found in API data

### API Client

`cfbd_client.py:441-456`:
```python
def get_returning_production(self, year: int, team: Optional[str] = None) -> List[Dict]:
    """
    Get returning production percentages

    Args:
        year: Season year
        team: Optional team filter

    Returns:
        List of returning production data with percentPPA values
    """
    params = {'year': year}
    if team:
        params['team'] = team

    return self._get('/player/returning', params=params)
```

---

## Usage in System

### Preseason ELO Calculation

Returning production is one of three preseason factors:

1. **Recruiting Rank** - Quality of incoming talent
2. **Returning Production** - Experience and continuity
3. **Transfer Portal Rank** - Portal additions (future: EPIC-026)

**Example:**
```python
# High recruiting + Low returning production = Talented but inexperienced
# Low recruiting + High returning production = Veteran but less talented
# High recruiting + High returning production = Elite veteran team
```

### API Responses

**GET /api/teams/{id}**
```json
{
  "team_id": 82,
  "name": "Ohio State",
  "recruiting_rank": 5,
  "returning_production": 0.224,  // 22.4%
  "elo_rating": 1856.32
}
```

**GET /api/rankings**
```json
{
  "rankings": [
    {
      "rank": 1,
      "team_name": "Georgia",
      "recruiting_rank": 1,
      "returning_production": 0.604,  // 60.4%
      "elo_rating": 1923.15
    }
  ]
}
```

---

## Data Quality

### Expected Values

**Typical Range:** 0.025 - 0.924 (2.5% - 92.4%)

**Distribution Examples (2024 Season):**

**High Returning Production (>80%):**
- SMU: 92.4%
- Iowa State: 90.1%
- Hawai'i: 89.6%
- West Virginia: 88.3%
- Boston College: 88.2%

**Medium Returning Production (40-60%):**
- Alabama: 60.2%
- Georgia: 60.4%
- Arizona: 61.6%
- Arizona State: 61.5%

**Low Returning Production (<20%):**
- Washington: 2.5%
- Florida Atlantic: 2.7%
- James Madison: 3.7%
- Oregon State: 7.0%

### Coverage

- **FBS Teams:** 133 teams (100% coverage)
- **FCS Teams:** Default to 0.5 (CFBD doesn't provide FCS data)
- **Data Freshness:** Updated by CFBD after spring practices

---

## Validation

### Data Checks

Run these checks after import:

```bash
# Check specific team
python3 -c "
from database import SessionLocal
from models import Team

db = SessionLocal()
team = db.query(Team).filter(Team.name == 'Ohio State').first()
print(f'Ohio State returning production: {team.returning_production*100:.1f}%')
"

# Check distribution
python3 test_returning_production.py
```

**Expected Output:**
```
Ohio State returning production: 22.4%

Database Verification:
============================================================
Teams with non-default returning production: 132/230
Success rate: 57.4%
```

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| **All teams 50%** | Wrong field name | Use `percentPPA` not `returningProduction` |
| **Values too high (>100)** | Not dividing by 100 | Don't divide - values already decimal |
| **Missing data** | API error or FCS team | Check API response, FCS defaults OK |
| **Team name mismatch** | Name difference | Check CFBD team names vs database |

---

## Maintenance

### Updating Data

**When to update:**
- Before each season starts (August)
- After spring practices (May-June)
- When CFBD updates data

**How to update:**
```bash
# Re-import for current season
python3 import_real_data.py --season 2025

# Or reset and full re-import
python3 import_real_data.py --season 2025 --reset
```

### Monitoring

```bash
# Check data freshness
python3 -c "
from database import SessionLocal
from models import Team
from sqlalchemy import func

db = SessionLocal()

# Count non-default values
non_default = db.query(Team).filter(Team.returning_production != 0.5).count()
total = db.query(Team).count()

print(f'Teams with returning production data: {non_default}/{total}')

# Check average
avg = db.query(func.avg(Team.returning_production)).scalar()
print(f'Average returning production: {avg*100:.1f}%')
"
```

**Expected:**
- 132+ teams with non-default values
- Average around 50-60%

---

## Related Metrics

### Comparison with Other Factors

| Metric | What It Measures | Data Source | Range |
|--------|------------------|-------------|-------|
| **Recruiting Rank** | Incoming talent quality | CFBD recruiting | 1-130 (rank) |
| **Returning Production** | Experience/continuity | CFBD player returning | 0.0-1.0 (%) |
| **Transfer Portal Rank** | Portal additions | Not yet implemented | TBD |

### Correlation with Performance

**High returning production + High recruiting:**
- Elite veteran teams (Georgia, Alabama when loaded)
- Strong preseason favorites

**Low returning production + High recruiting:**
- Reloading elite programs (Ohio State 2024)
- High ceiling but unproven

**High returning production + Low recruiting:**
- Experienced mid-major teams
- Strong early season, may plateau

---

## Examples

### Case Study: Ohio State 2024

**Data:**
- Recruiting Rank: #5 (elite incoming class)
- Returning Production: 22.4% (major turnover)
- Context: Many NFL departures (Marvin Harrison Jr., etc.)

**Impact on Preseason ELO:**
- High recruiting rank: +adjustment for talent
- Low returning production: -adjustment for inexperience
- Net result: Still high ELO but tempered expectations

### Case Study: SMU 2024

**Data:**
- Recruiting Rank: #94 (lower-tier FBS)
- Returning Production: 92.4% (highest in FBS)
- Context: Veteran team with continuity

**Impact on Preseason ELO:**
- Lower recruiting rank: Limited talent boost
- Very high returning production: +adjustment for experience
- Net result: Strong mid-tier team with proven roster

---

## Troubleshooting

### Debug Import

```bash
# Enable verbose logging
python3 import_real_data.py --season 2024 --reset 2>&1 | grep -i "returning"
```

**Expected Output:**
```
Fetching returning production...
  Loaded returning production for 133 teams
  Added: Ohio State - Big Ten (P5) - Recruiting: #5, Returning: 22%
```

### Verify API Call

```bash
# Direct API test
curl "https://api.collegefootballdata.com/player/returning?year=2024" \
  -H "Authorization: Bearer YOUR_API_KEY" | \
  python3 -m json.tool | head -50
```

### Check Database

```bash
# Query specific team
sqlite3 cfb_rankings.db "
  SELECT name, returning_production, recruiting_rank
  FROM teams
  WHERE name = 'Ohio State';
"
```

---

## References

- [CFBD API Documentation](https://api.collegefootballdata.com/api/docs/)
- [EPIC-025: Fix Returning Production](EPIC-025-FIX-RETURNING-PRODUCTION.md)
- [Story 25.1: API Investigation](stories/25.1.story.md)
- [Story 25.2: Fix Implementation](stories/25.2.story.md)
- [Story 25.3: Testing](stories/25.3.story.md)

---

**Last Updated:** 2025-12-02
**EPIC:** EPIC-025
**Status:** ✅ Complete
**Maintained By:** Development Team
