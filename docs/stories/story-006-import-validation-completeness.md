# Story 006: Add Import Validation & Completeness Checks

**Story ID**: STORY-006
**Epic**: EPIC-002 - Dynamic Season Management & Complete Game Import
**Status**: Ready for Development
**Priority**: High
**Estimate**: 5-7 hours
**Complexity**: High

---

## User Story

**As a** system administrator importing college football data,
**I want** the import scripts to validate completeness and report any missing or skipped games,
**So that** I can identify and fix data quality issues (like the missing Ohio State Week 2 game) before they affect rankings.

---

## Story Context

### Existing System Integration

- **Integrates with:**
  - `import_real_data.py` (full season import)
  - `update_games.py` (incremental weekly updates)
  - `cfbd_client.py` (CFBD API wrapper)

- **Technology:**
  - Python 3.11+, requests library
  - CFBD API for game data
  - SQLite database for storage

- **Follows pattern:**
  - Existing import loop structure
  - Existing error logging pattern
  - Existing game filtering logic (FCS teams, incomplete games)

- **Touch points:**
  - `import_games()` function in both scripts
  - Team name matching logic
  - Game validation logic
  - Console output formatting

---

## Background: Current Import Problems

### Issue Identified

**Problem:** Ohio State showing 4-0 instead of 6-0 (missing Week 2 game and weeks 7-8)

**Root Causes:**
1. **Silent Failures:** Games skipped due to team name mismatches, no warning shown
2. **No Validation:** Import doesn't verify all expected games were imported
3. **No Completeness Check:** User doesn't know if 50 games or 45 games imported for a given week
4. **FCS Filtering:** Games against FCS opponents silently skipped (expected behavior, but not reported)

**Example Silent Failure:**
```python
# Current code silently skips games
if home_team_name not in team_objects or away_team_name not in team_objects:
    continue  # No warning, just skip
```

**User Impact:**
- Rankings are inaccurate
- Missing games not noticed until user manually checks
- No way to know what percentage of games successfully imported

---

## Acceptance Criteria

### Functional Requirements - Validation

1. **Pre-Import Validation:**
   - Check CFBD API connectivity before starting
   - Test API key is valid (try to fetch teams)
   - Verify database connection is writable
   - Print validation results: "✓ API connectivity OK" or "✗ API connection failed"

2. **Per-Week Completeness Validation:**
   - Query CFBD for total number of games in week
   - Count how many games successfully imported
   - Calculate and display: "Imported 48/50 games (96%)"
   - Flag weeks with <90% import rate as warnings

3. **Team Name Mismatch Detection:**
   - Track teams mentioned in CFBD response but not found in local database
   - Log each missed game with reason: "Skipped: Alabama vs Kent State (Kent State not in database)"
   - Suggest fixes: "Add Kent State to database or they'll continue to be skipped"

4. **Import Summary Report:**
   - After each week, print detailed summary:
     ```
     Week 7 Import Summary:
     ✓ Expected: 50 games (per CFBD API)
     ✓ Imported: 48 games (96%)
     ⚠ Skipped: 2 games
       - Alabama vs Kent State (FCS opponent)
       - Ohio State vs Akron (FCS opponent)
     ```

5. **Final Import Statistics:**
   - After full import, print totals:
     ```
     ================================================================================
     IMPORT SUMMARY
     ================================================================================
     Total Weeks Imported: 8
     Total Games Imported: 384/400 (96%)
     Total Games Skipped: 16
       - FCS Opponents: 14
       - Team Not Found: 2
     ================================================================================
     ```

### Functional Requirements - Validation Mode

6. **Dry-Run / Validate-Only Mode:**
   - Add `--validate-only` flag to both scripts
   - Performs all checks but doesn't write to database
   - Shows what WOULD be imported
   - Useful for testing before actual import

7. **Strict Mode:**
   - Add `--strict` flag to fail on validation warnings
   - Exit with error code if <95% import rate
   - Prevents partial imports from being accepted
   - Useful for automated/CI workflows

### Integration Requirements

8. **Backward Compatibility:**
   - All existing import workflows continue to work
   - New validation is opt-in via flags
   - Default behavior: warnings only, doesn't block
   - No breaking changes to existing function signatures

9. **Logging:**
   - Use Python `logging` module for structured logs
   - Log level configurable: `--log-level DEBUG|INFO|WARNING|ERROR`
   - Logs include timestamps and context
   - Errors logged to stderr, info to stdout

10. **Performance:**
    - Validation adds minimal overhead (<5 seconds per week)
    - API queries batched where possible
    - Database queries optimized (use existing connections)

### Quality Requirements

11. **Test Coverage:**
    - Unit tests for validation functions
    - Integration tests for `--validate-only` mode
    - Test with mock CFBD responses (various scenarios)
    - Test team name mismatch detection

12. **Documentation:**
    - Update `docs/UPDATE-GAME-DATA.md` with validation examples
    - Add troubleshooting section for common import issues
    - Document `--validate-only` and `--strict` flags in help text
    - Provide example validation output

13. **Existing Functionality:**
    - All 236 existing tests pass
    - No changes to database schema
    - Import speed not significantly affected
    - Existing error handling preserved

---

## Files to Modify

### `import_real_data.py` - Add Validation

**New Functions:**

```python
def validate_api_connection(cfbd: CFBDClient) -> bool:
    """
    Test CFBD API connectivity and authentication.

    Returns:
        bool: True if API accessible, False otherwise
    """
    try:
        teams = cfbd.get_teams(2025)
        return teams is not None and len(teams) > 0
    except Exception as e:
        print(f"✗ API Connection Failed: {e}")
        return False

def get_expected_game_count(cfbd: CFBDClient, year: int, week: int) -> int:
    """
    Query CFBD for total number of games in a week.

    Args:
        cfbd: CFBD client
        year: Season year
        week: Week number

    Returns:
        int: Total games in week (including FCS)
    """
    games = cfbd.get_games(year, week=week)
    return len(games) if games else 0

def validate_week_completeness(expected: int, imported: int, skipped: List[Dict]) -> Dict:
    """
    Validate week import completeness.

    Args:
        expected: Total games from CFBD
        imported: Games successfully imported
        skipped: List of skipped games with reasons

    Returns:
        dict: Validation results with status and warnings
    """
    import_rate = (imported / expected * 100) if expected > 0 else 0

    return {
        'expected': expected,
        'imported': imported,
        'skipped': len(skipped),
        'import_rate': import_rate,
        'status': 'OK' if import_rate >= 90 else 'WARNING',
        'skipped_games': skipped
    }
```

**Modify `import_games()` Function:**

```python
def import_games(cfbd: CFBDClient, db, team_objects: dict, year: int = 2025,
                max_week: int = None, validate_only: bool = False, strict: bool = False):
    """
    Import games for the season with validation.

    Args:
        validate_only: If True, don't write to database (dry-run)
        strict: If True, fail on validation warnings
    """

    # Track statistics
    total_expected = 0
    total_imported = 0
    total_skipped = []

    for week in weeks:
        print(f"\nWeek {week}...")

        # Get expected game count
        expected_games = get_expected_game_count(cfbd, year, week)
        total_expected += expected_games

        games_data = cfbd.get_games(year, week=week)
        week_imported = 0
        week_skipped = []

        for game_data in games_data:
            home_team_name = game_data.get('homeTeam')
            away_team_name = game_data.get('awayTeam')

            # Track team name mismatches
            if home_team_name not in team_objects:
                week_skipped.append({
                    'game': f"{away_team_name} @ {home_team_name}",
                    'reason': f"{home_team_name} not in database"
                })
                continue

            if away_team_name not in team_objects:
                week_skipped.append({
                    'game': f"{away_team_name} @ {home_team_name}",
                    'reason': f"{away_team_name} not in database"
                })
                continue

            # ... existing import logic ...

            if not validate_only:
                db.add(game)
                db.commit()

            week_imported += 1

        # Week summary
        validation = validate_week_completeness(expected_games, week_imported, week_skipped)
        print_week_summary(week, validation)

        if strict and validation['status'] == 'WARNING':
            raise Exception(f"Week {week} import rate below threshold: {validation['import_rate']:.1f}%")

        total_imported += week_imported
        total_skipped.extend(week_skipped)

    # Final summary
    print_final_summary(total_expected, total_imported, total_skipped)
```

**Console Output Functions:**

```python
def print_week_summary(week: int, validation: Dict):
    """Print week import summary"""
    status_icon = '✓' if validation['status'] == 'OK' else '⚠'

    print(f"{status_icon} Week {week} Summary:")
    print(f"  Expected: {validation['expected']} games")
    print(f"  Imported: {validation['imported']} games ({validation['import_rate']:.1f}%)")

    if validation['skipped'] > 0:
        print(f"  Skipped: {validation['skipped']} games")
        for game in validation['skipped_games'][:5]:  # Show first 5
            print(f"    - {game['game']} ({game['reason']})")
        if len(validation['skipped_games']) > 5:
            print(f"    ... and {len(validation['skipped_games']) - 5} more")

def print_final_summary(expected: int, imported: int, skipped: List):
    """Print final import statistics"""
    import_rate = (imported / expected * 100) if expected > 0 else 0

    print("\n" + "="*80)
    print("IMPORT SUMMARY")
    print("="*80)
    print(f"Total Games Expected: {expected}")
    print(f"Total Games Imported: {imported} ({import_rate:.1f}%)")
    print(f"Total Games Skipped: {len(skipped)}")

    # Categorize skipped games
    skip_reasons = {}
    for game in skipped:
        reason = game['reason']
        if reason not in skip_reasons:
            skip_reasons[reason] = []
        skip_reasons[reason].append(game['game'])

    print("\nSkipped Games by Reason:")
    for reason, games in skip_reasons.items():
        print(f"  {reason}: {len(games)} games")
        for game in games[:3]:  # Show first 3
            print(f"    - {game}")
        if len(games) > 3:
            print(f"    ... and {len(games) - 3} more")

    print("="*80)
```

### `update_games.py` - Similar Validation

Apply same validation pattern to `update_games.py`:

- Add `--validate-only` and `--strict` flags
- Track expected vs imported per week
- Print weekly summaries
- Final import report

### CLI Arguments

**Add to both scripts:**

```python
parser.add_argument('--validate-only', action='store_true',
                   help='Validate import without writing to database (dry-run)')
parser.add_argument('--strict', action='store_true',
                   help='Fail on validation warnings (<95%% import rate)')
parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                   default='INFO', help='Logging level (default: INFO)')
```

---

## Example Output

### Normal Import (With Warnings)

```
Week 7 Import...
✓ Week 7 Summary:
  Expected: 50 games
  Imported: 48 games (96.0%)
  Skipped: 2 games
    - Alabama @ Kent State (Kent State not in database - FCS)
    - Ohio State @ Akron (Akron not in database - FCS)

Week 8 Import...
⚠ Week 8 Summary:
  Expected: 52 games
  Imported: 46 games (88.5%)
  Skipped: 6 games
    - Georgia Tech @ Notre Dame (Georgia Tech not in database)
    - BYU @ UCF (BYU not in database)
    - Cincinnati @ West Virginia (Cincinnati not in database)
    ... and 3 more

================================================================================
IMPORT SUMMARY
================================================================================
Total Games Expected: 400
Total Games Imported: 384 (96.0%)
Total Games Skipped: 16

Skipped Games by Reason:
  Team not in database - FCS: 14 games
    - Alabama @ Kent State
    - Ohio State @ Akron
    - Michigan @ Eastern Michigan
    ... and 11 more
  Team not in database: 2 games
    - Georgia Tech @ Notre Dame
    - BYU @ UCF
================================================================================

⚠ WARNING: Some teams were not found in the database.
Consider adding them or they will continue to be skipped in future imports.
```

### Validate-Only Mode

```
$ python3 import_real_data.py --validate-only

✓ API Connection: OK
✓ Database Connection: OK

Week 7 Validation...
✓ Week 7: Would import 48/50 games (96.0%)

Week 8 Validation...
⚠ Week 8: Would import 46/52 games (88.5%)

================================================================================
VALIDATION SUMMARY (DRY-RUN - NO DATABASE CHANGES)
================================================================================
Total Games: 384/400 (96.0%)
Validation Status: OK

Run without --validate-only to perform actual import.
================================================================================
```

### Strict Mode (Fails on Warning)

```
$ python3 import_real_data.py --strict

Week 8 Import...
⚠ Week 8 Summary:
  Expected: 52 games
  Imported: 46 games (88.5%)

ERROR: Week 8 import rate below threshold: 88.5%
Import aborted due to validation failure.

Use --validate-only to see what would be imported without writing to database.
Remove --strict flag to import anyway with warnings.
```

---

## Testing Strategy

### Unit Tests

```python
class TestValidation:
    def test_validate_api_connection_success(self, mock_cfbd):
        """Test API validation with working connection"""
        mock_cfbd.get_teams.return_value = [{'school': 'Alabama'}]

        assert validate_api_connection(mock_cfbd) is True

    def test_validate_api_connection_failure(self, mock_cfbd):
        """Test API validation with failed connection"""
        mock_cfbd.get_teams.side_effect = RequestException("Network error")

        assert validate_api_connection(mock_cfbd) is False

    def test_validate_week_completeness_ok(self):
        """Test week validation with good import rate"""
        result = validate_week_completeness(50, 48, [])

        assert result['status'] == 'OK'
        assert result['import_rate'] == 96.0

    def test_validate_week_completeness_warning(self):
        """Test week validation with low import rate"""
        skipped = [{'game': 'A vs B', 'reason': 'Team not found'}] * 6
        result = validate_week_completeness(52, 46, skipped)

        assert result['status'] == 'WARNING'
        assert result['import_rate'] < 90

    def test_import_with_validate_only(self, mock_db, mock_cfbd):
        """Test validate-only mode doesn't write to database"""
        import_games(mock_cfbd, mock_db, {}, validate_only=True)

        # Verify no database writes
        assert mock_db.add.call_count == 0
        assert mock_db.commit.call_count == 0

    def test_import_with_strict_mode_fails(self, mock_db, mock_cfbd):
        """Test strict mode fails on low import rate"""
        # Mock CFBD to return games that will be skipped
        mock_cfbd.get_games.return_value = [/* games with unknown teams */]

        with pytest.raises(Exception, match="import rate below threshold"):
            import_games(mock_cfbd, mock_db, {}, strict=True)
```

### Integration Tests

```bash
# Test 1: Normal import with validation
python3 import_real_data.py
# Verify: Shows week summaries and final summary

# Test 2: Validate-only mode
python3 import_real_data.py --validate-only
# Verify: No database changes, shows dry-run message

# Test 3: Strict mode with good data
python3 import_real_data.py --strict --max-week 1
# Verify: Succeeds if import rate >95%

# Test 4: Check help text
python3 import_real_data.py --help
# Verify: Shows new flags and descriptions
```

---

## Risk Assessment

### Primary Risks

**Risk 1: Validation Overhead Slows Import**
- **Scenario:** Extra API queries add 30+ seconds per import
- **Mitigation:**
  - Batch API queries where possible
  - Cache results within same import session
  - Make validation optional (can disable)
- **Impact:** Low - validation is opt-in

**Risk 2: False Positive Warnings**
- **Scenario:** FCS games flagged as "missing" but intentionally excluded
- **Mitigation:**
  - Clearly label FCS games in skip reasons
  - Document expected behavior
  - Provide `--ignore-fcs` flag if needed
- **Impact:** Low - warnings are informational only

**Risk 3: Strict Mode Too Strict**
- **Scenario:** Strict mode blocks valid imports due to FCS games
- **Mitigation:**
  - Default to warnings-only (strict is opt-in)
  - Allow threshold configuration: `--min-import-rate 90`
  - Clear error messages explaining why it failed
- **Impact:** Low - strict mode is optional

### Rollback Plan

If validation causes issues:

1. **Disable Validation:**
   - Don't use `--validate-only` or `--strict` flags
   - Import proceeds as before

2. **Remove Validation Code:**
   - Git revert to remove validation functions
   - Import functionality preserved (validation is additive)

3. **Configuration Override:**
   - Add `DISABLE_VALIDATION=true` env variable
   - Skip validation if set

---

## Definition of Done

- [ ] Pre-import validation (API connectivity check) implemented

- [ ] Per-week completeness validation implemented

- [ ] Team name mismatch detection implemented

- [ ] Import summary report implemented

- [ ] `--validate-only` flag working in both scripts

- [ ] `--strict` flag working and fails appropriately

- [ ] Console output formatted and readable

- [ ] All unit tests passing

- [ ] Integration tests for validation modes

- [ ] Documentation updated:
  - [ ] `docs/UPDATE-GAME-DATA.md` - Validation examples
  - [ ] Script help text (`--help`)
  - [ ] Troubleshooting section for import issues

- [ ] All 236 existing tests pass

- [ ] Manual testing:
  - [ ] Import with validation (shows summaries)
  - [ ] Import with `--validate-only` (no DB changes)
  - [ ] Import with `--strict` (fails on warnings)
  - [ ] Import with real 2025 data (verify accuracy)

- [ ] Performance verified (<5 seconds overhead per week)

- [ ] No breaking changes to existing workflows

---

## Dependencies

**Blocked By:**
- Story 1 (STORY-004) - Can use `get_current_week()` for validation
- Story 2 (STORY-005) - Uses same scripts

**Blocks:**
- None (this is the final story)

---

## Success Metrics

After this story is complete, the system should:

1. **Detect Issues:** User immediately sees when games are missing
2. **Explain Issues:** Clear reasons why games were skipped
3. **Prevent Bad Imports:** Strict mode catches incomplete imports in CI
4. **Build Confidence:** Users trust import completeness via validation reports

**Example Success:**
- User runs import, sees "⚠ Week 8: 88.5% import rate"
- User investigates, finds "Georgia Tech not in database"
- User adds Georgia Tech, re-runs import
- User sees "✓ Week 8: 100% import rate"
- Rankings are now accurate

---

## Developer Handoff Notes

**Implementation Priority:**

1. Start with `validate_api_connection()` - Simplest, immediate value
2. Add per-week completeness tracking
3. Implement team mismatch detection
4. Add console output formatting
5. Implement `--validate-only` mode
6. Implement `--strict` mode last

**Key Design Decisions:**

- **Validation is additive** - Doesn't change existing import logic
- **Opt-in strictness** - Warnings by default, errors only with `--strict`
- **Clear output** - Use colors/symbols for readability (✓ ⚠ ✗)
- **Performance conscious** - Batch queries, cache results

**Testing Focus:**

- Test with incomplete data (missing teams)
- Test with 100% complete data
- Test validate-only mode (no DB writes)
- Test strict mode failure path

---

**Story Created:** 2025-10-18
**Created By:** John (PM Agent)
**Ready for Development:** After Stories 1 and 2 complete
**Assigned To:** Dev Agent (James)
