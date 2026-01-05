# Coding Standards

## Overview

This document defines coding conventions and best practices for the College Football Rankings System. Following these standards ensures code consistency, maintainability, and quality.

---

## General Principles

### Code Quality
1. **Readability over cleverness** - Write code that is easy to understand
2. **Explicit is better than implicit** - Be clear about intent
3. **Consistency** - Follow established patterns in the codebase
4. **Documentation** - Comment complex logic, use docstrings for functions
5. **Testing** - Write tests for all new features and bug fixes

### Design Principles
- **Separation of concerns** - API, business logic, and data layers are separate
- **Single responsibility** - Each module/function has one clear purpose
- **DRY (Don't Repeat Yourself)** - Extract common patterns into reusable functions
- **KISS (Keep It Simple, Stupid)** - Prefer simple solutions over complex ones

---

## Python Coding Standards

### Style Guide
- Follow **PEP 8** - Python's official style guide
- Use **Black** for automatic code formatting
- Use **Flake8** for linting
- Use **isort** for import sorting

### Formatting

#### Line Length
- Maximum **120 characters** per line
- Break long lines logically (e.g., after commas, operators)

#### Indentation
- **4 spaces** (no tabs)
- Consistent indentation for continuation lines

#### Imports
```python
# Standard library
import os
import sys
from datetime import datetime

# Third-party
from fastapi import FastAPI, HTTPException
from sqlalchemy.orm import Session

# Local application
from src.models.models import Team, Game
from src.core.ranking_service import RankingService
```

**Order:**
1. Standard library imports
2. Third-party library imports
3. Local application imports
4. Blank line between each group

**Use `isort`** to automatically organize imports.

### Naming Conventions

#### Functions and Variables
```python
# snake_case for functions and variables
def calculate_elo_rating(team_a, team_b):
    win_probability = 0.5
    return win_probability

current_season = 2025
game_count = 10
```

#### Classes
```python
# PascalCase for class names
class RankingService:
    pass

class TeamResponse:
    pass
```

#### Constants
```python
# UPPER_CASE for constants
K_FACTOR = 32
MAX_MOV_MULTIPLIER = 2.5
HOME_FIELD_ADVANTAGE = 65
```

#### Private Methods
```python
# Leading underscore for private methods
class RankingService:
    def _calculate_mov_multiplier(self, score_diff):
        pass
```

### Type Hints

**Always use type hints** for function signatures:

```python
def calculate_win_probability(
    rating_a: float,
    rating_b: float,
    home_advantage: int = 0
) -> float:
    """Calculate win probability using ELO ratings."""
    pass

def get_team(db: Session, team_id: int) -> Optional[Team]:
    """Retrieve team from database."""
    return db.query(Team).filter(Team.id == team_id).first()
```

**Type hint imports:**
```python
from typing import Optional, List, Dict, Any, Tuple
```

### Docstrings

Use **Google-style docstrings** for all public functions, classes, and modules:

```python
def process_game(game: Game, db: Session) -> Dict[str, Any]:
    """Process a completed game and update team ratings.

    Calculates ELO rating changes based on game outcome, margin of victory,
    and home field advantage. Updates team ratings and stores historical
    snapshots.

    Args:
        game: Game object with final scores and team information
        db: Database session for persistence

    Returns:
        Dictionary containing:
            - winner_rating_change: Float, ELO points gained by winner
            - loser_rating_change: Float, ELO points lost by loser
            - mov_multiplier: Float, margin of victory multiplier applied

    Raises:
        ValueError: If game is not processed or missing required data

    Example:
        >>> result = process_game(game, db)
        >>> print(f"Winner gained {result['winner_rating_change']} points")
    """
    pass
```

**Docstring sections:**
- Summary line (one sentence)
- Detailed description (optional)
- `Args:` - Parameter descriptions
- `Returns:` - Return value description
- `Raises:` - Exceptions that may be raised
- `Example:` - Usage example (optional)

### Error Handling

#### Use specific exceptions
```python
# Good
if not game.is_processed:
    raise ValueError("Game must be processed before calculating ratings")

# Bad
if not game.is_processed:
    raise Exception("Error")  # Too generic
```

#### Catch specific exceptions
```python
# Good
try:
    team = db.query(Team).filter(Team.id == team_id).one()
except NoResultFound:
    raise HTTPException(status_code=404, detail="Team not found")

# Bad
try:
    team = db.query(Team).filter(Team.id == team_id).one()
except:  # Catching all exceptions
    pass
```

#### Log errors appropriately
```python
import logging

logger = logging.getLogger(__name__)

try:
    result = process_game(game, db)
except ValueError as e:
    logger.error(f"Error processing game {game.id}: {e}")
    raise
```

### Database Queries

#### Use SQLAlchemy ORM
```python
# Good - ORM style
teams = db.query(Team).filter(Team.division == "FBS").all()

# Avoid raw SQL unless necessary
# (Complex queries or performance-critical operations)
```

#### Filter queries carefully
```python
# Specific filters
active_games = db.query(Game).filter(
    Game.season == season,
    Game.is_processed == True,
    Game.excluded_from_rankings == False
).all()
```

#### Use relationships
```python
# Define relationships in models
class Game(Base):
    home_team = relationship("Team", foreign_keys=[home_team_id])
    away_team = relationship("Team", foreign_keys=[away_team_id])

# Access via relationship
game.home_team.name  # Instead of separate query
```

### FastAPI Conventions

#### Route definitions
```python
@app.get("/api/teams/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: int,
    db: Session = Depends(get_db)
):
    """Get team by ID."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team
```

#### Dependency injection
```python
from fastapi import Depends
from src.models.database import get_db

# Use Depends() for database sessions
def get_rankings(db: Session = Depends(get_db)):
    pass
```

#### Pydantic schemas
```python
from pydantic import BaseModel, Field

class TeamResponse(BaseModel):
    id: int
    name: str
    elo_rating: float = Field(..., description="Current ELO rating")

    class Config:
        from_attributes = True  # Allow ORM mode
```

### Testing Standards

#### Test file naming
- Match source file: `src/core/ranking_service.py` → `tests/unit/test_ranking_service.py`
- Prefix with `test_`

#### Test function naming
```python
def test_calculate_elo_rating_higher_rated_team_wins():
    """Test ELO calculation when higher-rated team wins."""
    pass

def test_get_team_not_found_returns_404():
    """Test 404 response when team doesn't exist."""
    pass
```

**Naming pattern:** `test_<function>_<scenario>_<expected_result>`

#### Test structure
```python
def test_process_game_updates_ratings():
    """Test that processing a game updates team ratings."""
    # Arrange - Set up test data
    team_a = Team(id=1, elo_rating=1600)
    team_b = Team(id=2, elo_rating=1500)
    game = Game(home_team_id=1, away_team_id=2, home_score=35, away_score=14)

    # Act - Execute the function
    result = process_game(game, db)

    # Assert - Verify expectations
    assert result['winner_rating_change'] > 0
    assert result['loser_rating_change'] < 0
```

**Use AAA pattern:** Arrange, Act, Assert

#### Use fixtures
```python
import pytest

@pytest.fixture
def sample_team():
    """Create a sample team for testing."""
    return Team(id=1, name="Test Team", elo_rating=1500)

def test_team_creation(sample_team):
    assert sample_team.elo_rating == 1500
```

---

## JavaScript Coding Standards

### Style Guide
- **ES6+** syntax (const, let, arrow functions, async/await)
- **2-space indentation**
- **Semicolons** at end of statements
- **Single quotes** for strings

### Naming Conventions

#### Variables and Functions
```javascript
// camelCase for variables and functions
const activeSeason = 2025;
let currentWeek = 14;

function loadRankings() {
  // ...
}

const calculateWinProbability = (ratingA, ratingB) => {
  // ...
};
```

#### Constants
```javascript
// UPPER_CASE for constants
const API_BASE_URL = '/api';
const MAX_RETRIES = 3;
```

#### Classes (if used)
```javascript
// PascalCase for classes
class RankingsManager {
  constructor() {
    this.rankings = [];
  }
}
```

### Code Structure

#### Module pattern
```javascript
// Encapsulate related functionality
const api = {
  async getRankings(season) {
    // ...
  },

  async getTeams() {
    // ...
  }
};
```

#### Async/await for API calls
```javascript
// Good - Async/await
async function loadRankings() {
  try {
    const rankings = await api.getRankings(2025);
    displayRankings(rankings);
  } catch (error) {
    console.error('Error loading rankings:', error);
    showError('Failed to load rankings');
  }
}

// Avoid - Promise chains (unless necessary)
api.getRankings(2025)
  .then(rankings => displayRankings(rankings))
  .catch(error => showError(error));
```

#### Arrow functions
```javascript
// Use arrow functions for callbacks
teams.forEach(team => {
  console.log(team.name);
});

// Traditional function for methods
const rankingsManager = {
  loadData: function() {
    // 'this' context is preserved
  }
};
```

### DOM Manipulation

#### Query selectors
```javascript
// Use specific selectors
const rankingsTable = document.getElementById('rankings-table');
const buttons = document.querySelectorAll('.filter-button');

// Cache DOM queries
const loading = document.getElementById('loading');
const content = document.getElementById('content');
// Reuse these references
```

#### Event listeners
```javascript
// Add event listeners in setup function
function setupEventListeners() {
  const seasonSelect = document.getElementById('season-select');
  if (seasonSelect) {
    seasonSelect.addEventListener('change', handleSeasonChange);
  }
}

// Named handler functions
async function handleSeasonChange(event) {
  const season = parseInt(event.target.value);
  await loadRankings(season);
}
```

### Error Handling

```javascript
async function loadData() {
  try {
    const data = await api.getData();
    processData(data);
  } catch (error) {
    console.error('Error loading data:', error);

    // Show user-friendly message
    showError('Failed to load data. Please try again later.');
  }
}
```

### Comments

```javascript
// Single-line comments for brief explanations
const activeSeason = 2025;  // Current season year

/**
 * Multi-line comments for function documentation
 *
 * @param {number} season - Season year
 * @returns {Promise<Array>} Array of ranking objects
 */
async function getRankings(season) {
  // ...
}
```

### API Client Pattern

```javascript
// Centralized API client
const api = {
  baseUrl: '/api',

  async fetch(endpoint) {
    const response = await fetch(`${this.baseUrl}${endpoint}`);
    if (!response.ok) {
      throw new Error(`HTTP error ${response.status}`);
    }
    return response.json();
  },

  async getRankings(season) {
    const params = season ? `?season=${season}` : '';
    return this.fetch(`/rankings${params}`);
  }
};
```

---

## HTML/CSS Standards

### HTML

#### Semantic HTML
```html
<!-- Good - Semantic tags -->
<header>
  <h1>College Football Rankings</h1>
</header>

<nav>
  <a href="index.html">Rankings</a>
</nav>

<main>
  <section class="rankings">
    <!-- Content -->
  </section>
</main>

<!-- Avoid - Non-semantic divs everywhere -->
<div class="header">
  <div class="title">College Football Rankings</div>
</div>
```

#### Attributes
- **IDs for unique elements:** `id="season-select"`
- **Classes for styling:** `class="stat-card"`
- **Data attributes for JS:** `data-team-id="123"`

### CSS

#### Class naming
```css
/* kebab-case for classes */
.stat-card {
  padding: 1rem;
}

.team-logo-container {
  display: flex;
}
```

#### CSS Variables
```css
:root {
  --primary-color: #1e40af;
  --text-primary: #1f2937;
  --spacing-md: 1rem;
}

.card {
  color: var(--text-primary);
  padding: var(--spacing-md);
}
```

---

## Git Commit Standards

### Commit Message Format

```
<type>: <Short summary in present tense>

<Optional detailed description>

<Optional footer>
```

### Types
- **Feature:** - New functionality
- **Fix:** - Bug fixes
- **Refactor:** - Code restructuring (no behavior change)
- **Docs:** - Documentation changes
- **Test:** - Test additions or updates
- **Chore:** - Build, dependencies, tooling

### Examples
```
Feature: Add multi-year season selector to comparison page

Enable users to compare AP Poll vs ELO prediction accuracy across
different seasons. Season dropdown allows switching between years.

🤖 Generated with Claude Code
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

```
Fix: Correct import path for ap_poll_service module

Fix ModuleNotFoundError by using correct import path:
src.core.ap_poll_service instead of ap_poll_service
```

---

## Code Review Checklist

### Before Committing
- [ ] Code follows style guide (Black, Flake8, isort)
- [ ] All tests pass (`pytest`)
- [ ] New code has tests
- [ ] Docstrings added for public functions
- [ ] No hardcoded secrets or API keys
- [ ] No debug print statements or commented code
- [ ] Meaningful commit message

### Code Review
- [ ] Code is readable and maintainable
- [ ] Follows existing patterns in codebase
- [ ] Error handling is appropriate
- [ ] Database queries are efficient
- [ ] No security vulnerabilities
- [ ] Documentation is updated

---

## Tools and Automation

### Pre-commit Checks
```bash
# Format Python code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint Python code
flake8 src/ tests/

# Run tests
pytest
```

### Makefile Targets
```bash
# Run all quality checks
make lint

# Run tests
make test

# Full check (lint + test)
make check
```

---

## Anti-Patterns to Avoid

### Python
❌ **Using `from module import *`**
```python
# Bad
from sqlalchemy import *

# Good
from sqlalchemy import Column, Integer, String
```

❌ **Bare except clauses**
```python
# Bad
try:
    risky_operation()
except:
    pass

# Good
try:
    risky_operation()
except SpecificException as e:
    logger.error(f"Operation failed: {e}")
    raise
```

❌ **Mutable default arguments**
```python
# Bad
def add_item(item, items=[]):
    items.append(item)
    return items

# Good
def add_item(item, items=None):
    if items is None:
        items = []
    items.append(item)
    return items
```

### JavaScript
❌ **Using `var`**
```javascript
// Bad
var season = 2025;

// Good
const season = 2025;
let currentWeek = 14;
```

❌ **Callback hell**
```javascript
// Bad
getData(function(data) {
  processData(data, function(result) {
    saveData(result, function() {
      // ...
    });
  });
});

// Good
const data = await getData();
const result = await processData(data);
await saveData(result);
```

---

## Summary

**Python:** PEP 8 + Type Hints + Docstrings + Black
**JavaScript:** ES6+ + Async/Await + Module Pattern
**HTML/CSS:** Semantic HTML + CSS Variables
**Git:** Conventional commits with clear messages
**Testing:** AAA pattern + Descriptive names
**Documentation:** Clear docstrings and comments for complex logic
