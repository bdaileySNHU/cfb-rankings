# EPIC-017 Story 003: Integrate with Weekly Workflow Documentation

**Epic:** EPIC-017 - Retrospective Prediction Generation
**Story Points:** 2
**Priority:** Medium
**Status:** ✅ Complete
**Completion Date:** 2025-10-27
**Dependencies:** EPIC-017 Story 001 (Complete), EPIC-017 Story 002 (Complete)

---

## User Story

As a **system administrator**,
I want **clear documentation on when and how to use the backfill script**,
So that **I understand how it fits into the weekly workflow and can troubleshoot issues when they occur**.

---

## Story Context

### Existing System Integration

- **Integrates with:**
  - `docs/WEEKLY-WORKFLOW.md` (existing workflow documentation)
  - `README.md` (project overview)
  - `scripts/backfill_historical_predictions.py` (from Story 001 and 002)

- **Technology:** Markdown documentation

- **Follows pattern:**
  - Documentation style from existing `WEEKLY-WORKFLOW.md`
  - Troubleshooting format from `EPIC-*.md` files
  - Example output format from `scripts/weekly_update.py` docstrings

- **Touch points:**
  - Weekly workflow documentation
  - Project README
  - Script help text
  - Troubleshooting guides

---

## Acceptance Criteria

### Documentation Requirements

1. **`docs/WEEKLY-WORKFLOW.md` includes one-time backfill section**
   - Section title: "One-Time Setup: Historical Prediction Backfill"
   - Placed before regular "Weekly Timeline" section
   - Explains when to run backfill (once after setup, or when predictions are missing)
   - Includes step-by-step instructions with example commands
   - Notes: "Only needs to be run once, or when historical data changes"

2. **Workflow documentation includes backfill verification steps**
   - Section title: "Verifying Backfill Accuracy"
   - Steps to check predictions were created correctly
   - SQL queries to spot-check predictions
   - How to verify predictions use historical ratings
   - Example: `SELECT COUNT(*) FROM predictions` before/after

3. **Troubleshooting section covers common backfill issues**
   - Section title: "Troubleshooting Backfill Issues"
   - Issue: "No predictions created" → Solution: Check if games already have predictions
   - Issue: "Missing historical ratings" → Solution: Run data import first
   - Issue: "Unexpected predictions" → Solution: Use rollback procedure
   - Issue: "Script takes too long" → Solution: Use `--season` and `--week` filters

4. **Documentation includes usage examples with expected output**
   - Basic run: `python3 scripts/backfill_historical_predictions.py`
   - Dry run: `python3 scripts/backfill_historical_predictions.py --dry-run`
   - Specific season: `python3 scripts/backfill_historical_predictions.py --season 2025`
   - Rollback: `python3 scripts/backfill_historical_predictions.py --delete-backfilled --start-time "..." --end-time "..."`
   - Each example includes expected output snippet

5. **README.md updated with backfill script description**
   - Add entry in "Scripts" section
   - Brief description: "Backfill historical predictions using historical ELO ratings"
   - Link to WEEKLY-WORKFLOW.md for detailed instructions
   - Note: "One-time setup script"

6. **Script help text is comprehensive**
   - `--help` output includes all flags with descriptions
   - Includes usage examples in help text
   - Shows expected output format
   - References documentation: "See docs/WEEKLY-WORKFLOW.md for detailed instructions"

### Quality Requirements

7. **Documentation follows existing style and format**
   - Uses same heading levels as WEEKLY-WORKFLOW.md
   - Code blocks use bash syntax highlighting
   - Examples show actual expected output
   - Consistent with project tone (concise, technical, practical)

8. **All commands in documentation are tested**
   - Each example command has been run successfully
   - Expected output matches actual output
   - File paths are correct
   - No typos in commands

9. **Documentation is accessible to new team members**
   - No assumed knowledge beyond what's in existing docs
   - Explains "why" in addition to "how"
   - Links to related documentation
   - Clear next steps after completing backfill

---

## Technical Notes

### Documentation Structure

**WEEKLY-WORKFLOW.md Update:**

Add new section after "Overview" and before "Weekly Timeline":

```markdown
## One-Time Setup: Historical Prediction Backfill

### When to Run This

Run the backfill script **once** when:
- Setting up the system for the first time and you have historical game data
- Predictions are missing for past weeks (visible on Prediction Comparison page)
- Historical ELO ratings have been recalculated and you want updated predictions

**Important:** This is a one-time operation. Once predictions exist, the script will skip them (no duplicates).

### Prerequisites

Before running backfill:
1. ✓ Game data imported (run `import_real_data.py` first)
2. ✓ Ranking calculations completed (ELO ratings exist)
3. ✓ Historical ratings saved in `ranking_history` table

### Running the Backfill

#### Step 1: Preview Changes (Dry Run)

Always start with a dry run to see what will be created:

```bash
cd "/path/to/Stat-urday Synthesis"
python3 scripts/backfill_historical_predictions.py --dry-run
```

**Expected output:**
```
================================================================================
Retrospective Prediction Backfill - DRY RUN MODE
================================================================================
Season: 2025
Found 350 processed games without predictions

Week 1: Processing 48 games...
  [DRY RUN] Would create 48 predictions

...

Summary:
  Total games processed: 350
  Predictions that would be created: 350
  Warnings: 1
  Errors: 0

DRY RUN - No changes written to database
Run without --dry-run to commit changes
================================================================================
```

#### Step 2: Run Actual Backfill

If the dry run looks correct, run without `--dry-run`:

```bash
python3 scripts/backfill_historical_predictions.py
```

**Expected duration:** 8-15 seconds for a full season (~350 games)

#### Step 3: Verify Results

Check that predictions were created:

```bash
# Count total predictions
sqlite3 cfb_rankings.db "SELECT COUNT(*) FROM predictions;"

# Sample a few predictions
sqlite3 cfb_rankings.db "SELECT game_id, predicted_winner_id, win_probability, created_at FROM predictions LIMIT 5;"
```

---

## Verifying Backfill Accuracy

### Check 1: Prediction Count

Verify prediction count matches processed game count:

```bash
# Count processed games
sqlite3 cfb_rankings.db "SELECT COUNT(*) FROM games WHERE is_processed = 1;"

# Count predictions
sqlite3 cfb_rankings.db "SELECT COUNT(*) FROM predictions;"
```

These numbers should match (or predictions may be slightly higher if some games have multiple predictions).

### Check 2: Historical Ratings Used

Verify predictions used historical ratings (not current ratings):

```bash
# Sample prediction with historical ratings
sqlite3 cfb_rankings.db "
SELECT
  g.week,
  t1.school as home_team,
  t2.school as away_team,
  p.home_elo_at_prediction,
  p.away_elo_at_prediction,
  p.win_probability
FROM predictions p
JOIN games g ON p.game_id = g.id
JOIN teams t1 ON g.home_team_id = t1.id
JOIN teams t2 ON g.away_team_id = t2.id
LIMIT 5;
"
```

Compare these ratings to current ratings - they should differ (historical ratings were from before the game).

### Check 3: Prediction Timestamps

Verify predictions have realistic timestamps (2 days before game):

```bash
sqlite3 cfb_rankings.db "
SELECT
  g.game_date,
  p.created_at,
  julianday(g.game_date) - julianday(p.created_at) as days_before
FROM predictions p
JOIN games g ON p.game_id = g.id
LIMIT 5;
"
```

`days_before` should be approximately 2.0 for most games.

### Check 4: Website Display

Visit the Prediction Comparison page to see predictions:
- Navigate to `/team/{team_id}/predictions`
- Verify all weeks show prediction data
- Check that accuracy percentages are calculated

---

## Troubleshooting Backfill Issues

### Issue: "Found 0 games to process"

**Symptoms:**
```
Found 0 processed games without predictions
✅ Backfill completed successfully (no work needed)
```

**Causes:**
1. All games already have predictions (script was already run)
2. No games in database (need to run import_real_data.py first)
3. No games marked as `is_processed = True`

**Solutions:**
1. Check prediction count: `sqlite3 cfb_rankings.db "SELECT COUNT(*) FROM predictions;"`
2. Check game count: `sqlite3 cfb_rankings.db "SELECT COUNT(*) FROM games;"`
3. If games exist but predictions don't, check for errors in script output

---

### Issue: "No historical rating found, using default 1500"

**Symptoms:**
```
Week 1: Processing 48 games...
  ⚠ Team ID 42 missing historical rating for week 0, using default 1500
  ✓ Generated 48 predictions (1 warning)
```

**Causes:**
1. Historical ratings not saved in `ranking_history` table (expected for Week 1)
2. Team is new and has no rating history yet
3. Data import didn't populate `ranking_history`

**Solutions:**
1. **For Week 1 games:** This is normal - Week 1 uses week 0 or default ratings
2. **For other weeks:** Run data import again to populate `ranking_history`:
   ```bash
   python3 import_real_data.py
   ```
3. **If persistent:** Check that ranking calculations are being saved:
   ```bash
   sqlite3 cfb_rankings.db "SELECT COUNT(*) FROM ranking_history;"
   ```

---

### Issue: "Predictions look wrong"

**Symptoms:**
- Win probabilities don't match expectations
- Predicted scores seem off
- Accuracy percentage is lower than expected

**Causes:**
1. Used current ratings instead of historical ratings (script bug)
2. Historical ratings were incorrect when originally calculated
3. Prediction algorithm has changed since historical data was created

**Solutions:**
1. **Rollback incorrect predictions:**
   ```bash
   # Note the start/end times from backfill run log
   python3 scripts/backfill_historical_predictions.py --delete-backfilled \
     --start-time "2025-10-27 10:00:00" --end-time "2025-10-27 10:05:00"
   ```

2. **Verify historical ratings are correct:**
   ```bash
   sqlite3 cfb_rankings.db "
   SELECT team_id, season, week, rating
   FROM ranking_history
   WHERE season = 2025 AND week = 5
   ORDER BY rating DESC
   LIMIT 10;
   "
   ```

3. **Re-run backfill with dry-run to spot-check:**
   ```bash
   python3 scripts/backfill_historical_predictions.py --dry-run --season 2025 --week 5
   ```

---

### Issue: "Script takes too long"

**Symptoms:**
- Script runs for several minutes
- Want to process only specific week or season

**Solutions:**
1. **Process specific season:**
   ```bash
   python3 scripts/backfill_historical_predictions.py --season 2025
   ```

2. **Process specific week:**
   ```bash
   python3 scripts/backfill_historical_predictions.py --season 2025 --week 8
   ```

3. **Check for database issues:**
   - Ensure `game_id` is indexed in predictions table
   - Check database file isn't corrupted
   - Verify disk space available

---

### Issue: "Need to undo backfill"

**Symptoms:**
- Realized historical ratings were wrong
- Want to re-run with corrected data
- Accidentally ran backfill twice

**Solutions:**
1. **Find timestamp range from backfill log:**
   Look for log output like:
   ```
   [2025-10-27 10:00:15] INFO: CFB Rankings Retrospective Prediction Backfill
   ...
   [2025-10-27 10:00:23] INFO: ✅ Backfill completed successfully
   ```

2. **Run rollback command:**
   ```bash
   python3 scripts/backfill_historical_predictions.py --delete-backfilled \
     --start-time "2025-10-27 10:00:00" --end-time "2025-10-27 10:01:00"
   ```

3. **Confirm deletion:**
   Script will prompt: `Delete 350 predictions? (yes/no):`
   Type `yes` and press Enter

4. **Verify deletion:**
   ```bash
   sqlite3 cfb_rankings.db "SELECT COUNT(*) FROM predictions;"
   ```

---

## Integration with Regular Workflow

The backfill script is **separate** from the regular weekly workflow:

**One-Time Backfill** (EPIC-017):
- Run once to populate predictions for past games
- Uses historical ratings from before each game
- Creates predictions with past timestamps

**Weekly Prediction Generation** (Existing):
- Run every Tuesday/Wednesday for upcoming games
- Uses current ratings
- Creates predictions with current timestamp

**Timeline:**
```
Setup (once):
  1. Import historical data → import_real_data.py
  2. Backfill predictions → backfill_historical_predictions.py

Weekly (ongoing):
  Tuesday: Generate predictions for upcoming games → generate_predictions.py
  Sunday: Import weekend results → weekly_update.py
```

After initial backfill, you only use the regular weekly workflow.

---
```

**README.md Update:**

Add to "Scripts" section:

```markdown
### `scripts/backfill_historical_predictions.py`

**One-time setup script** that generates predictions for past games using historical ELO ratings that existed before each game was played.

**Purpose:** Populate the Prediction Comparison feature with historically accurate predictions for analysis of prediction algorithm performance.

**When to run:** Once during initial setup, or when historical predictions are missing.

**Usage:**
```bash
# Preview changes (recommended first step)
python3 scripts/backfill_historical_predictions.py --dry-run

# Run actual backfill
python3 scripts/backfill_historical_predictions.py
```

**See:** `docs/WEEKLY-WORKFLOW.md` for detailed instructions and troubleshooting.
```

---

## Definition of Done

- [x] `docs/WEEKLY-WORKFLOW.md` updated with "One-Time Setup: Historical Prediction Backfill" section
- [x] Workflow documentation includes "Verifying Backfill Accuracy" section with SQL verification queries
- [x] Troubleshooting section added with 4+ common issues and solutions
- [x] All command examples tested and verified working (Stories 001 and 002)
- [x] Expected output snippets match actual script output
- [x] README.md updated with backfill script entry in Scripts section
- [x] Script `--help` output includes usage examples and documentation reference (Story 002)
- [x] Documentation reviewed for clarity and completeness
- [x] Links between documents are correct and working
- [x] New team member can follow documentation without assistance

---

## Risk and Compatibility Check

### Minimal Risk Assessment

**Primary Risk:** Documentation becomes outdated as script evolves

**Mitigation:**
- Include version/date in documentation headers
- Reference specific script flags that are unlikely to change
- Use generic examples that work across versions
- Add note: "Last updated: 2025-10-27"

**Rollback:**
- Previous documentation versions in git history
- Can revert commits if documentation is incorrect

### Compatibility Verification

- ✅ **No breaking changes to existing APIs:** Documentation only, no code changes
- ✅ **Database changes are additive only:** No database changes in this story
- ✅ **UI changes follow existing design patterns:** No UI changes
- ✅ **Performance impact is negligible:** Documentation has no performance impact

---

## Validation Checklist

### Scope Validation

- ✅ **Story can be completed in one development session:** Documentation updates, 1-2 hours work
- ✅ **Integration approach is straightforward:** Update existing markdown files
- ✅ **Follows existing patterns exactly:** Matches WEEKLY-WORKFLOW.md style
- ✅ **No design or architecture work required:** Following established doc format

### Clarity Check

- ✅ **Story requirements are unambiguous:** Each documentation section clearly specified
- ✅ **Integration points are clearly specified:** Specific files and sections to update
- ✅ **Success criteria are testable:** Can verify each documentation section exists
- ✅ **Rollback approach is simple:** Git revert of documentation commits

---

## Testing Plan

### Documentation Quality Checks

**Manual Review Checklist:**

```
Completeness:
[ ] All required sections present in WEEKLY-WORKFLOW.md
[ ] All troubleshooting scenarios covered
[ ] All command examples included
[ ] README.md updated

Accuracy:
[ ] All commands tested and working
[ ] Expected output matches actual output
[ ] File paths are correct
[ ] SQL queries return expected results

Clarity:
[ ] No jargon without explanation
[ ] Step-by-step instructions are clear
[ ] Examples show both input and output
[ ] Troubleshooting solutions are actionable

Consistency:
[ ] Heading levels match existing docs
[ ] Code block formatting consistent
[ ] Tone matches project style
[ ] Terminology consistent across docs
```

### Command Verification

Test each documented command:

1. **Dry run command:**
   ```bash
   python3 scripts/backfill_historical_predictions.py --dry-run
   # Verify: Runs successfully, shows preview
   ```

2. **Actual backfill:**
   ```bash
   python3 scripts/backfill_historical_predictions.py
   # Verify: Creates predictions
   ```

3. **Season-specific:**
   ```bash
   python3 scripts/backfill_historical_predictions.py --season 2025
   # Verify: Processes only 2025 season
   ```

4. **Rollback:**
   ```bash
   python3 scripts/backfill_historical_predictions.py --delete-backfilled \
     --start-time "2025-10-27 10:00:00" --end-time "2025-10-27 10:05:00"
   # Verify: Deletes correct predictions
   ```

5. **Verification queries:**
   ```bash
   sqlite3 cfb_rankings.db "SELECT COUNT(*) FROM predictions;"
   # Verify: Returns count
   ```

### User Acceptance Testing

**Scenario: New team member follows documentation**

1. Provide documentation to someone unfamiliar with the project
2. Ask them to run backfill following the docs (without additional help)
3. Verify they can:
   - Understand when to run backfill
   - Successfully run dry-run
   - Run actual backfill
   - Verify results
   - Troubleshoot common issues

**Success Criteria:**
- User completes backfill without asking questions
- User understands why they're running each command
- User can verify results independently

---

## Related Documentation

- **Weekly Workflow:** `docs/WEEKLY-WORKFLOW.md` (will be updated)
- **Epic Overview:** `docs/EPIC-017-RETROSPECTIVE-PREDICTIONS.md`
- **Story 001:** `docs/EPIC-017-STORY-001.md` (Script implementation)
- **Story 002:** `docs/EPIC-017-STORY-002.md` (Safety checks)
- **Project README:** `README.md` (will be updated)

---

## Example Documentation Sections

### WEEKLY-WORKFLOW.md - One-Time Setup Section

```markdown
## One-Time Setup: Historical Prediction Backfill

### Overview

The backfill script generates predictions for past games using the ELO ratings that existed **before each game was played**. This populates the Prediction Comparison feature with historically accurate prediction data.

**Key Concept:** The script doesn't use current ratings - it looks up what the ratings were before each game, ensuring predictions reflect what the system would have actually predicted at that time.

### When to Run

Run this script **once** when:
- Setting up the system for the first time
- You notice missing predictions on the Prediction Comparison page
- Historical ratings have been recalculated

**Note:** The script automatically skips games that already have predictions (no duplicates).

### Prerequisites

✓ Game data imported (`python3 import_real_data.py`)
✓ Rankings calculated (ELO ratings exist in database)
✓ Historical ratings saved in `ranking_history` table

### Quick Start

```bash
cd "/path/to/Stat-urday Synthesis"

# Step 1: Preview (always do this first)
python3 scripts/backfill_historical_predictions.py --dry-run

# Step 2: Run if preview looks correct
python3 scripts/backfill_historical_predictions.py

# Step 3: Verify
sqlite3 cfb_rankings.db "SELECT COUNT(*) FROM predictions;"
```

**Expected duration:** ~10 seconds for a full season

### What It Does

For each completed game:
1. Looks up team ELO ratings from the week **before** the game
2. Calculates win probability using historical ratings
3. Saves prediction with timestamp 2 days before game
4. Logs progress and any issues

### After Backfill

Once backfill completes:
- Visit `/team/{team_id}/predictions` to see historical predictions
- Continue with regular weekly workflow (generate predictions for upcoming games)
- Backfill doesn't need to be run again (unless you add new historical data)
```

---

**Created:** 2025-10-27
**Last Updated:** 2025-10-27
**Assigned To:** Development Team
