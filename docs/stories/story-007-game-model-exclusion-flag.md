# Story 007: Game Model Exclusion Flag for FCS Games

**Epic**: EPIC-003 FCS Game Display for Schedule Completeness
**Story Type**: Brownfield Database Enhancement
**Priority**: High (Foundation for Epic)
**Estimated Effort**: 2-3 hours

---

## User Story

As a **college football fan**,
I want **the system to safely store FCS games without affecting rankings**,
So that **I can see complete team schedules while maintaining ranking integrity**.

---

## Story Context

### Existing System Integration

- **Integrates with**: `models.py` (Game model), `ranking_service.py` (ELO calculations), `database.py`
- **Technology**: SQLAlchemy ORM with SQLite database
- **Follows pattern**: Additive database schema changes with backward compatibility
- **Touch points**:
  - `Game` model definition
  - `RankingService.process_game()` method
  - All ranking calculation methods
  - Database migration (if using Alembic, otherwise manual schema update)

### Current Behavior

Currently, the `Game` model stores only FBS vs FBS games. When `import_real_data.py` encounters FCS opponents, those games are skipped entirely and never stored in the database. This keeps rankings clean but results in incomplete team schedules.

---

## Acceptance Criteria

### Functional Requirements

1. **Add `excluded_from_rankings` field to Game model**
   - Type: Boolean
   - Default: `False` (FBS games are included in rankings by default)
   - Nullable: `False` (required field)
   - Indexed: Yes (for query performance)

2. **Ensure all ranking queries explicitly filter excluded games**
   - `RankingService.process_game()` only processes games where `excluded_from_rankings=False`
   - `RankingService.calculate_sos()` only considers non-excluded games
   - `RankingService.get_current_rankings()` calculations use non-excluded games only
   - Team win/loss counts only increment for non-excluded games

3. **Database migration is backward compatible**
   - New field has sensible default (`False`)
   - Existing data migrates cleanly
   - No data loss during migration

### Integration Requirements

4. **Existing ranking functionality continues to work unchanged**
   - All existing games (pre-migration) treated as `excluded_from_rankings=False`
   - ELO calculations produce identical results for existing data
   - Team records (wins/losses) remain accurate

5. **New functionality follows existing patterns**
   - Follows SQLAlchemy model conventions in `models.py`
   - Database field naming matches existing conventions (snake_case)
   - Migration approach matches project standards

6. **Integration with RankingService maintains current behavior**
   - `process_game()` method explicitly checks exclusion flag
   - No implicit filtering (always explicit WHERE clauses)
   - Clear error handling for edge cases

### Quality Requirements

7. **Comprehensive test coverage**
   - Unit tests for model field
   - Integration tests for ranking calculations with excluded games
   - Test that excluded games don't affect ELO ratings
   - Test that excluded games don't affect team W-L records
   - Test that excluded games don't affect SOS calculations

8. **Documentation updated**
   - Model docstring explains exclusion flag purpose
   - Migration notes document the change
   - RankingService methods document exclusion filter

9. **No regression in existing functionality**
   - All 270+ existing tests pass
   - Ranking calculations produce same results
   - API endpoints return unchanged data (no FCS games yet)

---

## Technical Implementation Notes

### Model Change (models.py)

```python
class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True)
    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    away_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    home_score = Column(Integer, nullable=False)
    away_score = Column(Integer, nullable=False)
    week = Column(Integer, nullable=False)
    season = Column(Integer, nullable=False)
    is_neutral_site = Column(Boolean, default=False)
    is_processed = Column(Boolean, default=False)

    # NEW FIELD
    excluded_from_rankings = Column(Boolean, default=False, nullable=False, index=True)
    # Purpose: Mark FCS games or other non-ranked matchups
    # Default False: FBS games are included in rankings
    # Indexed: Performance for filtered queries

    # ... rest of model
```

### RankingService Updates

Update all ranking-related queries to explicitly filter:

```python
# Example in process_game()
def process_game(self, game: Game):
    """Process a game and update team ratings"""
    # CRITICAL: Only process games included in rankings
    if game.excluded_from_rankings:
        raise ValueError("Cannot process excluded game for rankings")

    # ... existing logic
```

```python
# Example in calculate_sos()
def calculate_sos(self, team: Team, season: int):
    """Calculate strength of schedule"""
    # Get only games included in rankings
    games = self.db.query(Game).filter(
        Game.excluded_from_rankings == False,  # EXPLICIT FILTER
        or_(Game.home_team_id == team.id, Game.away_team_id == team.id),
        Game.season == season
    ).all()

    # ... existing logic
```

### Database Migration

**Option A: Manual SQL (if not using Alembic)**
```sql
-- Add column with default
ALTER TABLE games ADD COLUMN excluded_from_rankings BOOLEAN DEFAULT 0 NOT NULL;

-- Create index for query performance
CREATE INDEX idx_games_excluded_from_rankings ON games(excluded_from_rankings);

-- Verify all existing games are False (0)
SELECT COUNT(*) FROM games WHERE excluded_from_rankings = 1;
-- Should return 0
```

**Option B: Alembic Migration (if using migrations)**
```python
def upgrade():
    op.add_column('games',
        sa.Column('excluded_from_rankings', sa.Boolean(),
                  nullable=False, server_default='0'))
    op.create_index('idx_games_excluded_from_rankings', 'games',
                    ['excluded_from_rankings'])

def downgrade():
    op.drop_index('idx_games_excluded_from_rankings', 'games')
    op.drop_column('games', 'excluded_from_rankings')
```

### Integration Approach

1. **Add field to model** (`models.py`)
2. **Run database migration** (manual SQL or Alembic)
3. **Update RankingService** with explicit filters
4. **Add comprehensive tests**
5. **Verify all existing tests pass**
6. **Document changes**

### Existing Pattern Reference

- Follow model field patterns in `models.py` (see `is_neutral_site`, `is_processed` for boolean examples)
- Follow SQLAlchemy conventions already established
- Use explicit boolean comparisons in queries (`== False` not `is False`)

### Key Constraints

- **CRITICAL**: All ranking calculations must explicitly filter `excluded_from_rankings=False`
- **CRITICAL**: Never rely on implicit filtering or defaults in queries
- **CRITICAL**: Existing 270+ test suite must pass without modification
- Database migration must be reversible
- Performance impact should be negligible (indexed field)

---

## Definition of Done

- ✅ `excluded_from_rankings` field added to Game model
- ✅ Database migration completed successfully
- ✅ Field is indexed for query performance
- ✅ All RankingService methods explicitly filter excluded games
- ✅ Unit tests added for new field
- ✅ Integration tests verify exclusion behavior
- ✅ All 270+ existing tests pass unchanged
- ✅ ELO calculations produce identical results for existing data
- ✅ Team W-L records remain accurate
- ✅ Code follows existing patterns and standards
- ✅ Documentation updated (model docstrings, migration notes)
- ✅ No performance regression

---

## Test Cases

### Unit Tests (test_models.py)

```python
def test_game_excluded_from_rankings_default():
    """Test that excluded_from_rankings defaults to False"""
    game = Game(
        home_team_id=1,
        away_team_id=2,
        home_score=27,
        away_score=24,
        week=1,
        season=2025
    )
    assert game.excluded_from_rankings is False

def test_game_excluded_from_rankings_explicit():
    """Test that excluded_from_rankings can be set to True"""
    game = Game(
        home_team_id=1,
        away_team_id=2,
        home_score=70,
        away_score=0,
        week=2,
        season=2025,
        excluded_from_rankings=True
    )
    assert game.excluded_from_rankings is True
```

### Integration Tests (test_ranking_service.py)

```python
def test_excluded_game_does_not_affect_elo(test_db):
    """Test that excluded games don't affect ELO ratings"""
    # Create teams
    team_a = TeamFactory(elo_rating=1500.0)
    team_b = TeamFactory(elo_rating=1400.0)

    # Record initial ratings
    initial_a = team_a.elo_rating
    initial_b = team_b.elo_rating

    # Create excluded game
    game = GameFactory(
        home_team=team_a,
        away_team=team_b,
        home_score=70,
        away_score=0,
        excluded_from_rankings=True
    )

    # Attempt to process (should raise error or skip)
    ranking_service = RankingService(test_db)
    with pytest.raises(ValueError):
        ranking_service.process_game(game)

    # Ratings should be unchanged
    assert team_a.elo_rating == initial_a
    assert team_b.elo_rating == initial_b

def test_excluded_game_does_not_affect_record(test_db):
    """Test that excluded games don't affect team W-L records"""
    # Create teams
    team_a = TeamFactory(wins=0, losses=0)
    team_b = TeamFactory(wins=0, losses=0)

    # Create excluded game
    game = GameFactory(
        home_team=team_a,
        away_team=team_b,
        home_score=70,
        away_score=0,
        excluded_from_rankings=True
    )

    # Process should not affect records
    # (W-L updates should only happen for included games)

    assert team_a.wins == 0
    assert team_a.losses == 0
    assert team_b.wins == 0
    assert team_b.losses == 0

def test_sos_calculation_excludes_fcs_games(test_db):
    """Test that SOS only considers non-excluded games"""
    # Setup: Team A plays 2 FBS opponents and 1 FCS opponent
    team_a = TeamFactory(elo_rating=1600.0)
    fbs_opp_1 = TeamFactory(elo_rating=1700.0)
    fbs_opp_2 = TeamFactory(elo_rating=1550.0)
    fcs_opp = TeamFactory(elo_rating=1200.0)

    # FBS games (included)
    GameFactory(home_team=team_a, away_team=fbs_opp_1, excluded_from_rankings=False)
    GameFactory(home_team=team_a, away_team=fbs_opp_2, excluded_from_rankings=False)

    # FCS game (excluded)
    GameFactory(home_team=team_a, away_team=fcs_opp, excluded_from_rankings=True)

    # Calculate SOS
    ranking_service = RankingService(test_db)
    sos = ranking_service.calculate_sos(team_a, 2025)

    # SOS should average only FBS opponents (1700 + 1550) / 2 = 1625
    # NOT include FCS opponent (1200)
    assert sos == pytest.approx(1625.0, abs=0.1)
```

### Regression Tests

```python
def test_existing_games_still_included_in_rankings(test_db):
    """Test that existing games (pre-migration) are included in rankings"""
    # Simulate existing game (default excluded_from_rankings=False)
    game = GameFactory(excluded_from_rankings=False)

    ranking_service = RankingService(test_db)

    # Should process without error
    result = ranking_service.process_game(game)
    assert result is not None
    assert game.is_processed is True
```

---

## Risk Assessment

### Primary Risk
Accidentally including FCS games in ranking calculations due to missing filters

### Mitigation
- Explicit `excluded_from_rankings == False` filters in all ranking queries
- Comprehensive test coverage verifying exclusion behavior
- Code review focused on RankingService changes
- Run full test suite before and after changes

### Rollback Plan
- Database migration can be reversed (drop column)
- Git revert of code changes
- Verify test suite passes after rollback

---

## Dependencies

- None (foundation story for EPIC-003)

## Blocked By

- None

## Blocks

- Story 008 (Backend Import & API Updates) - needs this model change first

---

**Created by**: John (PM Agent)
**Date**: 2025-10-18
**Story Points**: 3
**Priority**: P0 (Must complete before Story 008)
