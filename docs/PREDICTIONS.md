# Game Predictions Documentation

## Overview

The Stat-urday Synthesis system provides game predictions for upcoming college football matchups using a modified ELO rating system. Predictions include estimated scores, winner determination, and confidence levels.

## How Predictions Are Calculated

### Win Probability Formula

Win probabilities are calculated using the standard ELO probability formula:

```
P(home wins) = 1 / (1 + 10^((away_rating - home_rating) / 400))
P(away wins) = 1 - P(home wins)
```

**Home Field Advantage**: Home teams receive a +65 rating point bonus before probability calculation.

**Neutral Site Games**: When `is_neutral_site = true`, no home field advantage is applied.

### Example Win Probability Calculation

**Scenario**: Georgia (ELO: 1850) hosts Alabama (ELO: 1820)

1. Apply home field advantage: 1850 + 65 = 1915
2. Calculate rating difference: 1820 - 1915 = -95
3. Apply formula: 1 / (1 + 10^(-95/400)) = 1 / (1 + 10^(-0.2375))
4. Result: 1 / (1 + 0.578) = 0.634 = **63.4% home win probability**
5. Away probability: 100% - 63.4% = **36.6%**

## Score Estimation Methodology

Predicted scores are estimated using the following formula:

```
base_score = 30
adjustment = (rating_difference / 100) * 3.5

predicted_home_score = base_score + adjustment
predicted_away_score = base_score - adjustment
```

**Validation**: Scores are clamped to the range [0, 150] to ensure realistic outputs.

### Example Score Calculation

**Scenario**: Georgia (ELO: 1850) hosts Alabama (ELO: 1820)

1. Apply home field advantage: 1915 (effective home rating)
2. Rating difference: 1915 - 1820 = 95
3. Calculate adjustment: (95 / 100) * 3.5 = 3.325
4. Home score: 30 + 3.325 = **33** (rounded)
5. Away score: 30 - 3.325 = **27** (rounded)

**Result**: Georgia 33, Alabama 27

### Score Estimation Constants

```python
BASE_SCORE = 30                  # Average expected score
SCORE_VARIANCE_FACTOR = 3.5      # Points per 100 rating difference
MIN_PREDICTED_SCORE = 0          # Minimum valid score
MAX_PREDICTED_SCORE = 150        # Maximum valid score
```

## Confidence Level Determination

Confidence levels are based on the probability margin between the two teams:

| Probability Margin | Confidence Level | Description |
|-------------------|------------------|-------------|
| > 30% | **High** | Clear favorite identified |
| 15% - 30% | **Medium** | Moderate favorite |
| < 15% | **Low** | Toss-up game |

### Example Confidence Calculations

1. **High Confidence**: Ohio State (75%) vs. Indiana (25%)
   - Margin: 75% - 25% = 50% → **High**

2. **Medium Confidence**: Michigan (60%) vs. Penn State (40%)
   - Margin: 60% - 40% = 20% → **Medium**

3. **Low Confidence**: Texas (52%) vs. Oklahoma (48%)
   - Margin: 52% - 48% = 4% → **Low**

## Validation Rules

The system enforces the following validation rules:

### Week Validation
```python
MIN_WEEK = 0    # Week 0 (preseason)
MAX_WEEK = 15   # Championship week
```

### Team Validation
- Team must exist in database
- Team must have a valid ELO rating (≥ 1)

### Game Validation
- Game must not be processed (no actual results yet)
- Week must be within valid range (0-15)

### Score Validation
- Scores must be between 0 and 150
- Non-integer scores are rounded to nearest integer

## Limitations and Caveats

### 1. Statistical Model Limitations
- **ELO is not predictive of injuries**: The model cannot account for player injuries or roster changes
- **Weather not considered**: Predictions don't factor in weather conditions
- **Motivational factors ignored**: Rivalry games, playoff implications, etc. are not weighted

### 2. Small Sample Size Issues
- Early season predictions (weeks 0-3) may be less accurate due to limited game data
- Teams with few FBS games played have less reliable ratings

### 3. Score Estimation Accuracy
- Score predictions are **estimates only** and should not be considered definitive
- Actual game variance is much higher than the model suggests
- The linear score formula is a simplification of complex offensive/defensive matchups

### 4. ELO Rating Assumptions
- ELO assumes team strength is relatively stable throughout the season
- Does not account for team improvement/decline over time
- Treats all wins equally (no context for blowouts vs. close games in current rating)

### 5. Home Field Advantage
- Fixed +65 point bonus may not accurately represent all venues
- Some stadiums (e.g., Death Valley, The Swamp) may have larger advantages
- Neutral site assumption may not capture pseudo-home games

### 6. Conference Strength
- Model does not explicitly account for conference strength
- Cross-conference predictions may be less reliable
- Power 5 vs. Group of 5 matchups require careful interpretation

## API Usage

### Get Predictions Endpoint

```
GET /api/predictions
```

**Query Parameters**:
- `week` (optional): Specific week number (0-15)
- `team_id` (optional): Filter by team ID
- `next_week` (optional, default: true): Only show next week's games
- `season` (optional): Season year (≥ 2020)

**Example Requests**:

```bash
# Get all next week predictions
GET /api/predictions?next_week=true

# Get predictions for week 5
GET /api/predictions?week=5&next_week=false

# Get predictions for team ID 333 (Alabama)
GET /api/predictions?team_id=333&next_week=true

# Get predictions for specific season
GET /api/predictions?season=2023&week=10&next_week=false
```

**Response Schema**:

```json
{
  "game_id": 401525551,
  "home_team_id": 333,
  "home_team": "Alabama",
  "away_team_id": 61,
  "away_team": "Georgia",
  "week": 8,
  "season": 2023,
  "game_date": "2023-10-28T19:30:00Z",
  "is_neutral_site": false,
  "predicted_winner": "Alabama",
  "predicted_winner_id": 333,
  "predicted_home_score": 33,
  "predicted_away_score": 27,
  "home_win_probability": 63.4,
  "away_win_probability": 36.6,
  "confidence": "Medium",
  "home_team_rating": 1850.5,
  "away_team_rating": 1820.3
}
```

## Frontend Display

Predictions are displayed in the main rankings page with:

- **Yellow PREDICTED badge**: Distinguishes predictions from actual results
- **Dashed border**: Visual indicator that results are estimates
- **Winner highlighting**: Predicted winner shown in blue
- **Confidence indicator**: Color-coded (green/yellow/red) confidence level
- **Win probabilities**: Percentage breakdown for both teams

## Testing and Validation

The prediction system includes comprehensive testing:

- **15 unit tests**: Core prediction logic validation
- **9 validation tests**: Input validation and edge cases
- **14 integration tests**: API endpoint testing
- **Regression tests**: Ensures no breaking changes to existing functionality

Total test coverage: **318 tests passing**

## Future Enhancements

Potential improvements to the prediction system:

1. **Machine Learning Integration**: Train models on historical data for better score prediction
2. **Injury Reports**: Incorporate player availability data
3. **Weather API**: Factor in weather conditions for game day
4. **Historical Accuracy Tracking**: Monitor prediction accuracy over time
5. **Confidence Intervals**: Provide score ranges instead of point estimates
6. **Advanced Metrics**: Incorporate EPA, SP+, or FPI for hybrid predictions

## References

- ELO Rating System: [Wikipedia](https://en.wikipedia.org/wiki/Elo_rating_system)
- College Football Data API: [College Football Data](https://collegefootballdata.com/)
- FastAPI Documentation: [FastAPI](https://fastapi.tiangolo.com/)

---

**Last Updated**: 2024-10-21
**Version**: 1.0.0
**Maintained By**: Stat-urday Synthesis Development Team
