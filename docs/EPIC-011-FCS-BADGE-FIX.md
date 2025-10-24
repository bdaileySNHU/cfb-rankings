# EPIC-011: Fix FCS Badge Display on Future Games

**Status:** Planning
**Priority:** Medium
**Complexity:** Low
**Estimated Effort:** 1-2 hours

---

## Problem Statement

The FCS badge incorrectly appears on ALL future games, even when the opponent is an FBS team. This happens because future games are marked with `excluded_from_rankings=True` (since they haven't been played yet), and the frontend displays the FCS badge for any game with this flag.

### Current Behavior (Incorrect)
- Ohio State vs Michigan (future game) → Shows "FCS" badge ❌
- Alabama vs Tennessee (future game) → Shows "FCS" badge ❌
- Oregon vs Washington (future game) → Shows "FCS" badge ❌

### Expected Behavior
- Ohio State vs Michigan (future game) → No badge ✅
- Alabama vs Tennessee (future game) → No badge ✅
- Ohio State vs North Dakota State (FCS opponent) → Shows "FCS" badge ✅

---

## Root Cause Analysis

The `excluded_from_rankings` flag serves TWO different purposes:

1. **Marking FCS games** - games against FCS opponents (should show badge)
2. **Marking unprocessed games** - future games that haven't been played yet (should NOT show badge)

The frontend currently shows FCS badge for ANY game with `excluded_from_rankings=True`, causing false positives.

### Code Location
**File:** `frontend/js/team.js`

The logic likely checks:
```javascript
if (game.excluded_from_rankings) {
  // Show FCS badge
}
```

---

## Solution Design

### Option 1: Use `is_processed` Flag (Recommended)
Only show FCS badge if the game is BOTH excluded AND unprocessed (or completed):

```javascript
// Show FCS badge only for actual FCS games, not future games
if (game.excluded_from_rankings && game.is_processed) {
  // Show FCS badge
}
```

**Pros:**
- Minimal change (1 line)
- Uses existing database fields
- No migration required

**Cons:**
- Logic is slightly less explicit

### Option 2: Check Opponent's `is_fcs` Flag
Look up the opponent team and check their `is_fcs` flag:

```javascript
// Show FCS badge if opponent is actually an FCS team
if (opponent.is_fcs) {
  // Show FCS badge
}
```

**Pros:**
- Most explicit and correct
- Future-proof

**Cons:**
- Requires loading opponent team data
- More API calls or data joins

### Option 3: New Database Field
Add `is_fcs_game` boolean field to `games` table, set during import:

**Pros:**
- Explicit separation of concerns
- Clearest intent

**Cons:**
- Requires database migration
- More complex implementation

---

## Recommended Approach

**Use Option 1** - it's the quickest fix with minimal risk.

---

## Implementation Stories

### Story 001: Frontend Badge Logic Fix

**Acceptance Criteria:**
- [ ] FCS badge only appears on games against actual FCS opponents
- [ ] FCS badge does NOT appear on future FBS vs FBS games
- [ ] Past FCS games still show badge correctly
- [ ] No database migration required

**Files to Modify:**
- `frontend/js/team.js` - Update badge display logic

**Implementation:**
```javascript
// BEFORE (incorrect):
if (game.excluded_from_rankings) {
  scheduleHtml += '<span class="fcs-badge">FCS</span>';
}

// AFTER (correct):
if (game.excluded_from_rankings && (game.is_processed || game.home_score > 0 || game.away_score > 0)) {
  scheduleHtml += '<span class="fcs-badge">FCS</span>';
}
```

**Testing:**
1. View team schedule with future FBS games → No FCS badge
2. View team schedule with completed FCS games → FCS badge appears
3. View team schedule with future FCS games → No badge (until game is processed)

---

## Testing Plan

### Manual Testing
1. Navigate to a team page with future games (e.g., Ohio State)
2. Verify future FBS games do NOT show FCS badge
3. Navigate to a team that played an FCS opponent
4. Verify completed FCS game DOES show FCS badge
5. Check multiple teams to ensure consistency

### Edge Cases
- Team with no games yet
- Team with only FCS games
- Team with mix of FBS and FCS games
- Future FCS games (shouldn't show badge until processed)

---

## Deployment

**Risk Level:** 🟢 Low

**Deployment Steps:**
1. Modify `frontend/js/team.js`
2. Test locally
3. Git commit
4. Push to production
5. Clear browser cache and verify

**No backend restart required** - frontend-only change.

**Rollback:** Simple `git revert` if issues occur.

---

## Success Metrics

- ✅ Zero FCS badges on future FBS vs FBS games
- ✅ FCS badges appear on all actual FCS games
- ✅ No user reports of incorrect badges
- ✅ Manual testing passes all scenarios

---

## Related Work

- **EPIC-003:** Initial FCS game display implementation
- **EPIC-012:** Conference display (separate epic)
