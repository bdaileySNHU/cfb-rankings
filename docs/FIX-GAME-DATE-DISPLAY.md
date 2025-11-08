# Fix: Game Date Display Issue

**Date:** 2025-11-08
**Issue:** Predictions showing import timestamp instead of actual game date

## Problem

Game predictions were displaying "Tue, Oct 28 at 12:07 PM" for all Week 11 games, which was the timestamp when the data was imported, not the actual game date.

**Root Cause:**
- The `parse_game_date()` function in `import_real_data.py` had a fallback to `datetime.now()` when the CFBD API didn't provide a `start_date` for future games
- This caused unscheduled games to show the import timestamp instead of the actual game date

## Solution

### 1. Updated `parse_game_date()` in `import_real_data.py`

**Before:**
```python
return datetime.now()  # Fallback if date parsing fails
```

**After:**
```python
# Return None for unscheduled games instead of showing wrong date
return None
```

**Why:**
- Returning `None` for unscheduled games prevents showing incorrect import timestamps
- The Game model already allows `nullable=True` for `game_date`
- Frontend can now properly detect and handle unscheduled games

### 2. Updated Frontend to Show "TBD" for Unscheduled Games

**File:** `frontend/js/app.js`

**Added:**
```javascript
} else {
  // Show TBD for games without scheduled dates
  gameDate = 'TBD';
}
```

**Result:**
- Games with scheduled dates: Show actual date/time
- Games without scheduled dates: Show "TBD"
- No more incorrect import timestamps

## Files Modified

- `import_real_data.py` - Updated `parse_game_date()` fallback behavior
- `frontend/js/app.js` - Added TBD handling for null game dates
- `docs/FIX-GAME-DATE-DISPLAY.md` - This documentation

## Testing

**Before Fix:**
```
Week 11 • Tue, Oct 28 at 12:07 PM  ❌ (import timestamp)
```

**After Fix:**
```
Week 11 • TBD  ✅ (shows game date is not scheduled yet)
```

**When game is scheduled:**
```
Week 11 • Sat, Nov 9 at 3:30 PM  ✅ (actual game date)
```

## Deployment

After deployment to production:
1. The next incremental update will preserve existing game dates
2. New games without scheduled dates will show "TBD"
3. When CFBD API adds game dates, the next update will populate them

## Prevention

This fix prevents future issues by:
- Never using `datetime.now()` as a fallback for game dates
- Explicitly handling missing date information
- Making it obvious to users when game times are TBD
