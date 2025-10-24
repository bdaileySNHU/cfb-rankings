# Two New Epics: FCS Badge Fix & Conference Display

This document summarizes the investigation and planning for two new improvement areas identified after EPIC-010 deployment.

---

## Epic Overview

| Epic | Priority | Complexity | Effort | Risk |
|------|----------|------------|--------|------|
| **EPIC-011: FCS Badge Fix** | Medium | Low | 1-2 hours | 🟢 Low |
| **EPIC-012: Conference Display** | Medium | Medium | 3-4 hours | 🟡 Medium |

---

## EPIC-011: FCS Badge Fix

### Problem
Future FBS vs FBS games incorrectly show "FCS" badge because they're marked `excluded_from_rankings=True` (since they're unprocessed).

### Root Cause
The `excluded_from_rankings` flag serves TWO purposes:
1. Marking actual FCS games ✅
2. Marking future/unprocessed games ❌

The frontend shows FCS badge for ANY game with this flag = false positives.

### Solution (Frontend-only, no migration)
Change badge logic from:
```javascript
if (game.excluded_from_rankings) {
  // Show FCS badge
}
```

To:
```javascript
if (game.excluded_from_rankings && game.is_processed) {
  // Show FCS badge - only for completed excluded games
}
```

### Files to Change
- `frontend/js/team.js` - 1 line change

### Deployment
- 🟢 **Low risk** - frontend only, no backend restart
- ⏱️ **5 minutes** - change + test + deploy

---

## EPIC-012: Conference Display

### Problem
System shows only tier (P5/G5/FCS) instead of actual conference names (Big Ten, SEC, etc.)

**Current:** Ohio State → "P5"
**Desired:** Ohio State → "Big Ten (P5)"

### Key Requirement
**Keep tier system** for:
- FCS exclusion logic
- Preseason rating calculations
- Filtering/grouping

**Add conference names** for user display.

### Technical Investigation Results ✅

**Good news:** CFBD API already provides conference names!

```json
{
  "school": "Alabama",
  "conference": "SEC",    // ← Already available!
  "classification": "fbs"
}
```

**Current issue:** Import script fetches conference name but discards it, only saving the tier enum.

### Solution

**1. Database Migration**
Add `conference_name` field to teams table:
```python
conference_name = Column(String(50), nullable=True)
```

**2. Import Script Update**
Save BOTH tier and name:
```python
team = Team(
    conference=ConferenceType.POWER_5,  # Keep for logic
    conference_name="Big Ten"            # NEW - for display
)
```

**3. Frontend Display**
```javascript
// Show: "Big Ten (P5)"
formatConference(team.conference, team.conference_name)
```

### Files to Change
1. `models.py` - Add field to Team model
2. `migrate_add_conference_name.py` - New migration script
3. `import_real_data.py` - Save conference name
4. `schemas.py` - Add field to API response
5. `frontend/js/team.js` - Display conference name
6. `frontend/js/rankings.js` - Display conference name

### Deployment
- 🟡 **Medium risk** - database migration + re-import required
- ⏱️ **20-25 minutes** - migration + re-import + restart

---

## Implementation Recommendation

### Option A: Do Both Separately (Recommended)
1. **Week 1:** Complete EPIC-011 (FCS badge fix)
   - Quick win, immediate value
   - Low risk, frontend-only
   - Can deploy in 5 minutes

2. **Week 2:** Complete EPIC-012 (Conference display)
   - Requires migration planning
   - More testing needed
   - Schedule maintenance window

### Option B: Combine Them
- Do both in one deployment session
- Advantage: One maintenance window
- Disadvantage: Higher risk, more to test

**Recommendation:** Option A - do EPIC-011 first as a quick win.

---

## Detailed Documentation

Full epic documentation available at:
- `docs/EPIC-011-FCS-BADGE-FIX.md` - Complete specs, implementation guide, testing
- `docs/EPIC-012-CONFERENCE-DISPLAY.md` - Complete specs, migration plan, deployment

---

## Next Steps

1. **Review** these epic documents
2. **Choose** implementation approach (Option A or B)
3. **Start** with EPIC-011 (quick win) or both together
4. **Let me know** which you'd like to implement first!

---

## Questions?

- Want to see current frontend code where badge logic lives?
- Need help prioritizing which epic to do first?
- Want to see sample data from CFBD API?
- Any concerns about the migration strategy?

Just ask! I'm ready to implement whichever you choose. 🚀
