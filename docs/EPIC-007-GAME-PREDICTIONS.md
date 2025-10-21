# EPIC-007: Game Predictions for Next Week - Brownfield Enhancement

## Epic Goal

Enable users to view predicted winners and score estimates for upcoming games in the next week, leveraging the existing ELO rating system to generate data-driven game predictions.

## Epic Overview

**Priority:** Medium
**Estimated Total Effort:** 8-12 hours
**Status:** Ready for Development
**Type:** Feature Enhancement

---

## Problem Statement

Users currently can only see historical game results and current team rankings. There is no capability to predict outcomes for upcoming games, which would add significant value by:
- Helping users understand matchup dynamics before games are played
- Demonstrating the predictive power of the ELO rating system
- Increasing user engagement during the week between games
- Providing insight into which teams are favored and by how much

---

## Epic Description

### Existing System Context

**Current functionality:**
- ELO rating system tracks team strength based on game results
- Games are stored in the database with scores and metadata (models.py:57-100)
- API exposes game data via `/api/games` endpoint (main.py)
- Frontend displays game schedules for teams
- Weekly update script imports upcoming games from CFBD API

**Technology stack:**
- Backend: FastAPI with SQLAlchemy ORM
- Database: SQLite with `Game`, `Team`, and `Season` models
- Frontend: Vanilla JavaScript
- Data source: CFBD API (provides scheduled games with dates)

**Integration points:**
- Database: `Game` model (already has `is_processed` flag to distinguish future games)
- Backend API: Need new `/api/predictions` endpoint
- Frontend: Display predictions on rankings or games page
- ELO algorithm: Use existing rating system to calculate win probabilities
- CFBD API: Already imports future games during weekly updates

### Enhancement Details

**What's being added/changed:**
- Prediction algorithm using existing ELO ratings to calculate:
  - Win probability for each team
  - Predicted score based on ELO difference and historical averages
  - Predicted margin of victory
- New API endpoint `/api/predictions` to retrieve predictions for upcoming games
- Frontend display of predictions (winner, score estimates, win probability)
- Filter predictions by week, team, or "next week" (most common use case)

**How it integrates:**
- Leverages existing ELO ratings from `Team.elo_rating` field
- Uses unprocessed games (`is_processed = False`) from database
- Applies same ELO formula used for historical processing but in reverse (predict instead of update)
- Frontend can display predictions alongside or instead of actual results for future games
- No changes to existing game processing or rating update logic

**Success criteria:**
- Users can view predicted winners for all games in the next week
- Predictions show estimated scores for both teams
- Win probability percentage is displayed
- Predictions update automatically as ELO ratings change
- API responds in <500ms for typical week (10-50 games)
- Frontend clearly distinguishes predictions from actual results

---

## Stories

### Story 001: Implement Prediction Algorithm and API Endpoint

**Goal:** Create backend logic to generate game predictions based on ELO ratings

**Estimated Effort:** 4-5 hours

**Key Tasks:**
- Create prediction algorithm that:
  - Calculates win probability using ELO formula (same as existing algorithm)
  - Estimates scores based on ELO difference and historical scoring patterns
  - Applies home field advantage (+65 rating points)
  - Handles neutral site games
- Add new `/api/predictions` endpoint with filters:
  - `week` - Get predictions for specific week
  - `team_id` - Get predictions involving specific team
  - `next_week` - Boolean to get only next week's games (default: true)
- Return prediction data including:
  - Game details (teams, week, date)
  - Predicted winner
  - Predicted scores for both teams
  - Win probability percentage
  - Confidence level (based on ELO difference)
- Add service layer method `generate_predictions()` in ranking_service.py

**Deliverables:**
- Prediction algorithm implementation
- `/api/predictions` endpoint with filtering
- Service layer methods
- Unit tests for prediction logic

---

### Story 002: Add Frontend Display for Predictions

**Goal:** Display game predictions in the user interface

**Estimated Effort:** 3-4 hours

**Key Tasks:**
- Create predictions section on rankings page or new predictions page
- Display predictions in clear, user-friendly format:
  - Show predicted winner highlighted or with indicator
  - Display predicted scores for both teams
  - Show win probability as percentage or visual indicator
  - Include game date/time
- Add visual distinction between predictions and actual results:
  - "PREDICTED" badge or label
  - Different styling (lighter colors, italic text, etc.)
  - Clear indication that these are estimates
- Add filtering controls:
  - Next week (default)
  - Specific week selector
  - Specific team filter
- Ensure predictions refresh when ELO ratings change

**Deliverables:**
- Frontend UI components for predictions display
- Filtering controls
- Visual distinction from actual results
- Responsive design

---

### Story 003: Add Prediction Testing, Validation, and Documentation

**Goal:** Ensure prediction accuracy and provide visibility into prediction performance

**Estimated Effort:** 2-3 hours

**Key Tasks:**
- Add validation rules:
  - Only generate predictions for unprocessed games
  - Ensure both teams have valid ELO ratings
  - Validate predicted scores are reasonable (>0, <200)
- Add integration tests for `/api/predictions` endpoint
- Add E2E tests for predictions display
- Compare prediction accuracy to actual results (optional analytics):
  - Track correct winner predictions
  - Track score estimate accuracy (MAE - Mean Absolute Error)
  - Store prediction vs. actual comparison (optional future enhancement)
- Document prediction formula and methodology
- Add API documentation to OpenAPI/Swagger

**Deliverables:**
- Validation logic with bounds checking
- Integration and E2E tests
- API documentation
- Prediction methodology documentation

---

## Compatibility Requirements

- [x] Existing APIs remain unchanged (new `/api/predictions` endpoint, no modifications to existing endpoints)
- [x] Database schema changes are backward compatible (no schema changes, only reads existing data)
- [x] UI changes follow existing patterns (similar to games/rankings display)
- [x] Performance impact is minimal (read-only queries on existing data)

---

## Risk Assessment

### Primary Risks

1. **Prediction accuracy could be poor, reducing user trust**
   - **Mitigation:** Use proven ELO formula, include disclaimers, show win probability (not just binary prediction)
   - **Future Enhancement:** Track prediction accuracy over time, adjust algorithm if needed

2. **Frontend could confuse predictions with actual results**
   - **Mitigation:** Clear visual distinction, "PREDICTED" labels, different styling
   - **Rollback:** Remove predictions feature from frontend (backend remains harmless)

3. **Performance impact from calculating predictions for many games**
   - **Mitigation:** Efficient queries (filter unprocessed games), consider caching, limit to next week by default
   - **Rollback:** Disable endpoint or add rate limiting if performance degrades

4. **ELO ratings might not be granular enough for accurate score predictions**
   - **Mitigation:** Start with simple formula, iterate based on user feedback
   - **Note:** Win probability is primary value, scores are secondary estimates

### Rollback Plan

```bash
# Backend rollback: Remove predictions endpoint (if deployed)
# Edit main.py to comment out @app.get("/api/predictions") route
# Restart Gunicorn
sudo systemctl restart gunicorn

# Frontend rollback: Hide predictions section
# Edit app.js to remove loadPredictions() calls
# No server restart needed (static files)
```

---

## Definition of Done

- [ ] Story 001: Prediction algorithm implemented and tested
- [ ] Story 001: `/api/predictions` endpoint working with filters
- [ ] Story 002: Frontend displays predictions clearly
- [ ] Story 002: Visual distinction between predictions and actual results
- [ ] Story 003: Validation and testing complete
- [ ] Story 003: Documentation updated
- [ ] Predictions display correctly for next week's games
- [ ] Win probabilities are mathematically sound
- [ ] No regression in existing features (games, rankings, stats)
- [ ] API documentation updated in Swagger/OpenAPI
- [ ] Tests added for prediction logic and endpoints

---

## Technical Approach

### Prediction Algorithm (Story 001)

```python
# In ranking_service.py
def generate_predictions(db: Session, week: int = None, team_id: int = None, next_week: bool = True) -> List[GamePrediction]:
    """
    Generate predictions for upcoming (unprocessed) games

    Args:
        db: Database session
        week: Optional week filter
        team_id: Optional team filter
        next_week: If True, only predict games in next week (default: True)

    Returns:
        List of GamePrediction objects with winner, scores, and probabilities
    """
    # Get unprocessed games
    query = db.query(Game).filter(Game.is_processed == False)

    if next_week:
        # Get current week from Season model
        current_week = db.query(Season.current_week).filter(Season.year == current_year).scalar()
        query = query.filter(Game.week == current_week + 1)
    elif week:
        query = query.filter(Game.week == week)

    if team_id:
        query = query.filter(
            (Game.home_team_id == team_id) | (Game.away_team_id == team_id)
        )

    games = query.all()
    predictions = []

    for game in games:
        # Get team ratings
        home_team = db.query(Team).filter(Team.id == game.home_team_id).first()
        away_team = db.query(Team).filter(Team.id == game.away_team_id).first()

        # Apply home field advantage (same as existing algorithm)
        home_rating = home_team.elo_rating + (0 if game.is_neutral_site else 65)
        away_rating = away_team.elo_rating

        # Calculate win probability (standard ELO formula)
        home_win_prob = 1 / (1 + 10 ** ((away_rating - home_rating) / 400))

        # Estimate scores based on ELO difference
        # Simple model: Higher rated team scores more
        rating_diff = home_rating - away_rating

        # Base scores (historical average ~30 points per team)
        base_score = 30

        # Adjust based on rating difference (every 100 rating points ~= 7 point margin)
        score_adjustment = (rating_diff / 100) * 3.5

        predicted_home_score = round(base_score + score_adjustment)
        predicted_away_score = round(base_score - score_adjustment)

        # Ensure scores are reasonable
        predicted_home_score = max(0, min(predicted_home_score, 100))
        predicted_away_score = max(0, min(predicted_away_score, 100))

        predictions.append({
            "game_id": game.id,
            "home_team": home_team.name,
            "away_team": away_team.name,
            "week": game.week,
            "season": game.season,
            "game_date": game.game_date,
            "is_neutral_site": game.is_neutral_site,
            "predicted_winner": home_team.name if home_win_prob > 0.5 else away_team.name,
            "predicted_home_score": predicted_home_score,
            "predicted_away_score": predicted_away_score,
            "home_win_probability": round(home_win_prob * 100, 1),
            "away_win_probability": round((1 - home_win_prob) * 100, 1),
            "confidence": "High" if abs(home_win_prob - 0.5) > 0.3 else "Medium" if abs(home_win_prob - 0.5) > 0.15 else "Low"
        })

    return predictions
```

### API Endpoint (Story 001)

```python
# In main.py
@app.get("/api/predictions", response_model=List[GamePredictionSchema])
def get_predictions(
    week: Optional[int] = None,
    team_id: Optional[int] = None,
    next_week: bool = True,
    db: Session = Depends(get_db)
):
    """
    Get game predictions for upcoming games

    Query Parameters:
    - week: Get predictions for specific week
    - team_id: Filter predictions for specific team
    - next_week: Only show next week's games (default: true)
    """
    return generate_predictions(db, week, team_id, next_week)
```

### Frontend Display (Story 002)

```javascript
// In app.js
async function loadPredictions() {
    try {
        const response = await fetch('/api/predictions?next_week=true');
        const predictions = await response.json();

        const container = document.getElementById('predictions-container');
        container.innerHTML = '<h2>Next Week Predictions</h2>';

        predictions.forEach(pred => {
            const gameDiv = document.createElement('div');
            gameDiv.className = 'prediction-card';
            gameDiv.innerHTML = `
                <div class="prediction-header">
                    <span class="prediction-badge">PREDICTED</span>
                    <span class="game-date">Week ${pred.week} - ${formatDate(pred.game_date)}</span>
                </div>
                <div class="matchup">
                    <div class="team ${pred.predicted_winner === pred.away_team ? 'winner' : ''}">
                        <span class="team-name">${pred.away_team}</span>
                        <span class="score">${pred.predicted_away_score}</span>
                    </div>
                    <div class="vs">@</div>
                    <div class="team ${pred.predicted_winner === pred.home_team ? 'winner' : ''}">
                        <span class="team-name">${pred.home_team}</span>
                        <span class="score">${pred.predicted_home_score}</span>
                    </div>
                </div>
                <div class="prediction-details">
                    <div class="win-probability">
                        Win Probability: ${pred.home_win_probability}% - ${pred.away_win_probability}%
                    </div>
                    <div class="confidence">Confidence: ${pred.confidence}</div>
                </div>
            `;
            container.appendChild(gameDiv);
        });
    } catch (error) {
        console.error('Error loading predictions:', error);
    }
}
```

### Validation (Story 003)

```python
# In ranking_service.py
def validate_prediction(game: Game, home_team: Team, away_team: Team) -> bool:
    """Validate game can be predicted"""
    if game.is_processed:
        return False
    if not home_team or not away_team:
        return False
    if home_team.elo_rating <= 0 or away_team.elo_rating <= 0:
        return False
    return True

def validate_predicted_score(score: int) -> int:
    """Ensure predicted score is reasonable"""
    return max(0, min(score, 150))  # Cap at 150 points
```

---

## Files Modified

**Story 001 (Backend Implementation):**
- `ranking_service.py` (~60 lines for prediction algorithm)
- `main.py` (~20 lines for `/api/predictions` endpoint)
- `schemas.py` (~15 lines for GamePredictionSchema)

**Story 002 (Frontend Display):**
- `static/app.js` (~40 lines for loadPredictions function)
- `static/styles.css` (~30 lines for prediction styling)
- `templates/index.html` (~10 lines for predictions container)

**Story 003 (Testing & Documentation):**
- `tests/unit/test_predictions.py` (~50 lines new test file)
- `tests/integration/test_predictions_api.py` (~40 lines new test file)
- `docs/PREDICTIONS.md` (~30 lines new documentation file)

---

## Success Metrics

### Quantitative
- `/api/predictions` endpoint responds in <500ms for 50 games
- Prediction accuracy (winner) > 65% when compared to actual results (historical validation)
- Zero errors in prediction calculation logic
- All tests pass (unit, integration, E2E)

### Qualitative
- Users understand that predictions are estimates, not guarantees
- Predictions add value to user experience (engagement metrics)
- Clear visual distinction from actual game results
- Predictions seem "reasonable" to users familiar with teams

---

## Deployment Plan

### Story 001 Deployment

```bash
# 1. SSH to VPS
ssh user@vps

# 2. Navigate to app directory
cd /var/www/cfb-rankings

# 3. Pull latest code
git pull origin main

# 4. Restart Gunicorn
sudo systemctl restart gunicorn

# 5. Test predictions endpoint
curl http://your-domain.com/api/predictions?next_week=true | jq
```

### Story 002 Deployment

```bash
# Static files (CSS, JS, HTML) are served automatically
# Just need to ensure they're deployed with git pull
# No additional restart needed
```

---

## Future Enhancements (Out of Scope)

- **Prediction accuracy tracking**: Store predictions when made, compare to actual results
- **Historical prediction performance**: Show "we correctly predicted 72% of winners this season"
- **Advanced scoring model**: Incorporate offensive/defensive statistics beyond ELO
- **Spread predictions**: Show not just winner but predicted point spread
- **Playoff probability**: Use predictions to calculate playoff chances
- **User predictions**: Allow users to make their own predictions and compare to system
- **Confidence intervals**: Show range of possible scores, not just point estimates
- **Live updating predictions**: Recalculate predictions as games complete each week

---

**Epic Created:** 2025-10-21
**Epic Owner:** Product Manager (John)
**Ready for Development:** ✅

---

## Story Documents

- **Epic:** `docs/EPIC-007-GAME-PREDICTIONS.md` (this document)
- **Story 001:** `docs/EPIC-007-STORY-001.md` (to be created)
- **Story 002:** `docs/EPIC-007-STORY-002.md` (to be created)
- **Story 003:** `docs/EPIC-007-STORY-003.md` (to be created)
