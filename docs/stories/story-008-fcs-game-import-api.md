# Story 008: FCS Game Import & Team Schedule API Updates

**Epic**: EPIC-003 FCS Game Display for Schedule Completeness
**Story Type**: Brownfield Backend Enhancement
**Priority**: High
**Estimated Effort**: 3-4 hours

---

## User Story

As a **college football fan**,
I want **the system to import and expose FCS games via the API**,
So that **I can see my team's complete schedule including all opponents**.

---

## Story Context

### Existing System Integration

- **Integrates with**:
  - `import_real_data.py` (game import logic)
  - `cfbd_client.py` (CFBD API client)
  - `main.py` (team schedule API endpoint)
  - `models.py` (Game, Team models)
- **Technology**: FastAPI, CFBD API, SQLAlchemy
- **Follows pattern**: Extending existing import logic and API endpoints
- **Touch points**:
  - `import_games()` function in `import_real_data.py`
  - `/api/teams/{id}/schedule` endpoint in `main.py`
  - Team win/loss record calculation logic

### Current Behavior

Currently, `import_real_data.py` fetches games from CFBD API and skips FCS opponents entirely. When a team like "Ohio State" plays "Grambling" (FCS), the game is never imported. The team schedule API returns only FBS games.

### New Behavior

After this story, the import will:
1. Import FBS vs FBS games with `excluded_from_rankings=False` (existing behavior)
2. Import FBS vs FCS games with `excluded_from_rankings=True` (new behavior)
3. Team schedule API returns both types of games
4. Team records (W-L) still only count FBS games

---

## Acceptance Criteria

### Functional Requirements

1. **Import FCS games with exclusion flag**
   - `import_games()` imports FCS opponent games
   - FCS games are marked with `excluded_from_rankings=True`
   - FBS games remain marked with `excluded_from_rankings=False`
   - Import statistics report FCS games separately

2. **Team schedule API returns complete schedules**
   - `/api/teams/{id}/schedule` endpoint returns both FBS and FCS games
   - Response includes `excluded_from_rankings` field for each game
   - Games are ordered by week
   - Both game types are clearly distinguished in response

3. **Team records reflect FBS games only**
   - Team `wins` and `losses` fields only count FBS games
   - FCS game outcomes don't increment team records
   - API responses for team data show accurate FBS-only records

### Integration Requirements

4. **Existing import functionality continues to work**
   - FBS vs FBS game import unchanged
   - Import statistics reporting still accurate
   - Import validation and completeness checks work
   - CFBD API integration remains stable

5. **API follows existing patterns**
   - Team schedule response structure matches conventions
   - Error handling follows existing patterns
   - Response schema validation works
   - API documentation updated

6. **Integration with Game model**
   - Uses `excluded_from_rankings` flag from Story 007
   - Properly sets flag based on opponent type
   - Database queries are efficient (uses index)

### Quality Requirements

7. **Comprehensive test coverage**
   - Unit tests for FCS game import logic
   - Integration tests for team schedule API with FCS games
   - Tests verify team records exclude FCS games
   - Tests verify FCS games don't affect rankings
   - Edge case testing (e.g., all FCS opponents, no FCS opponents)

8. **Documentation updated**
   - API endpoint documentation shows new response fields
   - Import script help text mentions FCS game handling
   - Code comments explain FCS exclusion logic

9. **No regression in existing functionality**
   - All existing integration tests pass
   - Import script validation mode works
   - Team schedule API backward compatible
   - Performance remains acceptable

---

## Technical Implementation Notes

### Import Logic Updates (import_real_data.py)

```python
def import_games(cfbd: CFBDClient, db, team_objects: dict, year: int, max_week: int = None, validate_only: bool = False, strict: bool = False):
    """Import games including FCS opponents for schedule completeness"""

    # ... existing setup ...

    # Track FCS games separately
    fcs_games_imported = 0

    for week in weeks:
        games_data = cfbd.get_games(year, week=week)

        for game_data in games_data:
            home_team_name = game_data.get('homeTeam')
            away_team_name = game_data.get('awayTeam')
            home_score = game_data.get('homePoints')
            away_score = game_data.get('awayPoints')

            # Skip incomplete games
            if home_score is None or away_score is None:
                skipped_incomplete += 1
                continue

            # Check if this is an FBS vs FCS game
            home_is_fbs = home_team_name in team_objects
            away_is_fbs = away_team_name in team_objects

            # Case 1: Both FBS (existing behavior)
            if home_is_fbs and away_is_fbs:
                # Import as ranked game (excluded_from_rankings=False)
                import_fbs_game(db, team_objects, game_data, week, year)
                total_imported += 1

            # Case 2: One FBS, one FCS (NEW behavior)
            elif home_is_fbs or away_is_fbs:
                # Import as non-ranked game (excluded_from_rankings=True)
                import_fcs_game(db, team_objects, game_data, week, year)
                fcs_games_imported += 1

            # Case 3: Both FCS or both not found
            else:
                skipped_fcs += 1
                continue

    # Update import statistics
    return {
        "imported": total_imported,
        "fcs_imported": fcs_games_imported,  # NEW
        "skipped": total_skipped,
        "skipped_fcs": skipped_fcs,
        "skipped_incomplete": skipped_incomplete
    }


def import_fbs_game(db, team_objects, game_data, week, year):
    """Import FBS vs FBS game (included in rankings)"""
    home_team = team_objects[game_data['homeTeam']]
    away_team = team_objects[game_data['awayTeam']]

    game = Game(
        home_team_id=home_team.id,
        away_team_id=away_team.id,
        home_score=game_data['homePoints'],
        away_score=game_data['awayPoints'],
        week=week,
        season=year,
        is_neutral_site=game_data.get('neutralSite', False),
        excluded_from_rankings=False  # Included in rankings
    )

    db.add(game)
    db.commit()
    db.refresh(game)

    # Process game for rankings
    ranking_service = RankingService(db)
    ranking_service.process_game(game)

    # Update team records
    if game.home_score > game.away_score:
        home_team.wins += 1
        away_team.losses += 1
    else:
        away_team.wins += 1
        home_team.losses += 1


def import_fcs_game(db, team_objects, game_data, week, year):
    """Import FBS vs FCS game (excluded from rankings)"""
    # Determine which team is FBS
    home_name = game_data['homeTeam']
    away_name = game_data['awayTeam']

    if home_name in team_objects:
        fbs_team = team_objects[home_name]
        fbs_is_home = True
    else:
        fbs_team = team_objects[away_name]
        fbs_is_home = False

    # For FCS games, we need to create a placeholder opponent
    # OR store partial game data (only FBS team side)
    # Decision: Store with NULL for FCS team ID

    game = Game(
        home_team_id=fbs_team.id if fbs_is_home else None,
        away_team_id=fbs_team.id if not fbs_is_home else None,
        home_score=game_data['homePoints'],
        away_score=game_data['awayPoints'],
        week=week,
        season=year,
        is_neutral_site=game_data.get('neutralSite', False),
        excluded_from_rankings=True,  # Excluded from rankings
        fcs_opponent_name=away_name if fbs_is_home else home_name  # NEW FIELD NEEDED
    )

    db.add(game)
    db.commit()

    # DO NOT process for rankings
    # DO NOT update team W-L records
```

**Note**: This reveals we need to add `fcs_opponent_name` field to Game model in Story 007. Let's note that as an addition.

### Alternative Simpler Approach

Instead of NULL team IDs, we could create FCS teams in database with a special flag:

```python
def get_or_create_fcs_team(db, team_name):
    """Get or create FCS team placeholder"""
    team = db.query(Team).filter(Team.name == team_name).first()

    if not team:
        team = Team(
            name=team_name,
            conference=ConferenceType.FCS,  # NEW enum value needed
            is_fcs=True,  # NEW field needed
            elo_rating=0,  # Not used
            initial_rating=0,
            recruiting_rank=999,
            transfer_rank=999,
            returning_production=0.5
        )
        db.add(team)
        db.commit()

    return team
```

This approach is cleaner and maintains referential integrity. **Recommend this approach.**

### API Endpoint Updates (main.py)

```python
@app.get("/api/teams/{team_id}/schedule")
def get_team_schedule(team_id: int, season: int = None):
    """Get team schedule including FCS games"""
    db = SessionLocal()

    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Get active season if not specified
    if season is None:
        active_season = db.query(Season).filter(Season.is_active == True).first()
        season = active_season.year if active_season else 2025

    # Get all games (FBS and FCS) for this team
    home_games = db.query(Game).filter(
        Game.home_team_id == team.id,
        Game.season == season
    ).all()

    away_games = db.query(Game).filter(
        Game.away_team_id == team.id,
        Game.season == season
    ).all()

    # Combine and format
    games = []
    for game in sorted(home_games + away_games, key=lambda g: g.week):
        if game.home_team_id == team.id:
            # Team is home
            opponent = game.away_team
            opponent_name = opponent.name
            is_home = True
            team_score = game.home_score
            opponent_score = game.away_score
        else:
            # Team is away
            opponent = game.home_team
            opponent_name = opponent.name
            is_home = False
            team_score = game.away_score
            opponent_score = game.home_score

        # Determine if game was played
        is_played = game.home_score is not None and game.away_score is not None

        # Format result
        if is_played:
            if team_score > opponent_score:
                score = f"W {team_score}-{opponent_score}"
            else:
                score = f"L {team_score}-{opponent_score}"
        else:
            score = None

        games.append({
            "week": game.week,
            "opponent_id": opponent.id,
            "opponent_name": opponent_name,
            "is_home": is_home,
            "is_neutral_site": game.is_neutral_site,
            "is_played": is_played,
            "score": score,
            "excluded_from_rankings": game.excluded_from_rankings,  # NEW FIELD
            "is_fcs": opponent.is_fcs if hasattr(opponent, 'is_fcs') else False  # NEW FIELD
        })

    db.close()

    return {
        "team_id": team.id,
        "team_name": team.name,
        "season": season,
        "games": games
    }
```

### Model Updates Required (Addition to Story 007)

**Team Model:**
```python
class Team(Base):
    # ... existing fields ...
    is_fcs = Column(Boolean, default=False, nullable=False)
    # True for FCS teams, False for FBS teams
```

**ConferenceType Enum:**
```python
class ConferenceType(str, Enum):
    POWER_5 = "P5"
    GROUP_5 = "G5"
    FCS = "FCS"  # NEW
```

---

## Acceptance Criteria Details

### Test Case: Ohio State Schedule

**Before Story 008:**
```json
{
  "team_name": "Ohio State",
  "games": [
    {"week": 1, "opponent_name": "Texas", ...},
    {"week": 3, "opponent_name": "Ohio", ...},
    {"week": 5, "opponent_name": "Washington", ...},
    {"week": 6, "opponent_name": "Minnesota", ...}
  ]
}
```

**After Story 008:**
```json
{
  "team_name": "Ohio State",
  "games": [
    {"week": 1, "opponent_name": "Texas", "excluded_from_rankings": false, "is_fcs": false},
    {"week": 2, "opponent_name": "Grambling", "excluded_from_rankings": true, "is_fcs": true},
    {"week": 3, "opponent_name": "Ohio", "excluded_from_rankings": false, "is_fcs": false},
    {"week": 5, "opponent_name": "Washington", "excluded_from_rankings": false, "is_fcs": false},
    {"week": 6, "opponent_name": "Minnesota", "excluded_from_rankings": false, "is_fcs": false}
  ]
}
```

### Test Case: Team Records

**Ohio State Record:**
- Plays 5 games: 4 FBS (all wins) + 1 FCS (win)
- **Record should be 4-0** (FBS only)
- **NOT 5-0** (FCS game excluded)

---

## Definition of Done

- ✅ FCS games imported with `excluded_from_rankings=True`
- ✅ FCS teams created in database with `is_fcs=True` flag
- ✅ Import statistics report FCS games separately
- ✅ Team schedule API returns complete schedules
- ✅ API response includes `excluded_from_rankings` and `is_fcs` fields
- ✅ Team W-L records only count FBS games
- ✅ All integration tests pass
- ✅ No regression in existing import or API functionality
- ✅ API documentation updated
- ✅ Code follows existing patterns

---

## Test Cases

### Integration Tests (test_cfbd_import.py)

```python
def test_import_fcs_game_with_exclusion_flag(test_db, mock_cfbd_client):
    """Test importing FCS game with exclusion flag"""
    from import_real_data import import_teams, import_games

    # Setup: Import FBS teams
    team_objects = import_teams(mock_cfbd_client, test_db, year=2025)

    # Mock data: Ohio State vs Grambling (FCS)
    mock_cfbd_client.get_games.return_value = [
        {
            'homeTeam': 'Ohio State',
            'awayTeam': 'Grambling',
            'homePoints': 70,
            'awayPoints': 0,
            'week': 2,
            'neutralSite': False
        }
    ]

    # Act
    stats = import_games(mock_cfbd_client, test_db, team_objects, year=2025, max_week=2)

    # Assert
    assert stats['fcs_imported'] == 1

    # Verify game in database
    game = test_db.query(Game).filter(Game.week == 2).first()
    assert game is not None
    assert game.excluded_from_rankings is True
    assert game.away_team.name == 'Grambling'
    assert game.away_team.is_fcs is True


def test_fcs_game_does_not_affect_team_record(test_db, mock_cfbd_client):
    """Test that FCS games don't affect team W-L records"""
    from import_real_data import import_teams, import_games

    team_objects = import_teams(mock_cfbd_client, test_db, year=2025)

    # Mock: Ohio State plays 1 FBS game (win) and 1 FCS game (win)
    mock_cfbd_client.get_games.return_value = [
        {
            'homeTeam': 'Ohio State',
            'awayTeam': 'Texas',  # FBS
            'homePoints': 14,
            'awayPoints': 7,
            'week': 1,
            'neutralSite': False
        },
        {
            'homeTeam': 'Ohio State',
            'awayTeam': 'Grambling',  # FCS
            'homePoints': 70,
            'awayPoints': 0,
            'week': 2,
            'neutralSite': False
        }
    ]

    # Act
    import_games(mock_cfbd_client, test_db, team_objects, year=2025, max_week=2)

    # Assert: Record should be 1-0 (FBS only)
    ohio_state = test_db.query(Team).filter(Team.name == 'Ohio State').first()
    assert ohio_state.wins == 1
    assert ohio_state.losses == 0


def test_team_schedule_api_includes_fcs_games(test_client, test_db):
    """Test team schedule API returns FCS games"""
    # Setup: Create team with FBS and FCS games
    ohio_state = TeamFactory(name='Ohio State')
    texas = TeamFactory(name='Texas')
    grambling = TeamFactory(name='Grambling', is_fcs=True)

    GameFactory(
        home_team=ohio_state,
        away_team=texas,
        week=1,
        excluded_from_rankings=False
    )
    GameFactory(
        home_team=ohio_state,
        away_team=grambling,
        week=2,
        excluded_from_rankings=True
    )

    # Act
    response = test_client.get(f"/api/teams/{ohio_state.id}/schedule")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data['games']) == 2

    week1 = data['games'][0]
    assert week1['opponent_name'] == 'Texas'
    assert week1['excluded_from_rankings'] is False
    assert week1['is_fcs'] is False

    week2 = data['games'][1]
    assert week2['opponent_name'] == 'Grambling'
    assert week2['excluded_from_rankings'] is True
    assert week2['is_fcs'] is True
```

---

## Dependencies

- **Depends on**: Story 007 (Game model exclusion flag)
- **Blocks**: Story 009 (Frontend display)

## Notes for Story 007

This story revealed we need additional fields in Story 007:
1. `Team.is_fcs` boolean field
2. `ConferenceType.FCS` enum value

Please update Story 007 to include these changes.

---

**Created by**: John (PM Agent)
**Date**: 2025-10-18
**Story Points**: 5
**Priority**: P1 (After Story 007)
