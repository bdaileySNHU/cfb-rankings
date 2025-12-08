# Coding Standards

This document defines the coding standards for the Stat-urday Synthesis project to ensure consistency, maintainability, and code quality.

---

## Table of Contents

- [Python Naming Conventions](#python-naming-conventions)
- [PEP 8 Compliance](#pep-8-compliance)
- [Import Organization](#import-organization)
- [Docstring Style Guide](#docstring-style-guide)
- [Type Hints Policy](#type-hints-policy)
- [Error Handling Patterns](#error-handling-patterns)
- [Code Quality Tools](#code-quality-tools)

---

## Python Naming Conventions

Follow these naming conventions throughout the codebase:

### Files
- **Convention:** `snake_case.py`
- **Examples:** `ranking_service.py`, `cfbd_client.py`, `import_real_data.py`

### Classes
- **Convention:** `PascalCase`
- **Examples:** `RankingService`, `Team`, `Game`, `CFBDClient`

### Functions and Methods
- **Convention:** `snake_case`
- **Examples:** `calculate_elo`, `get_rankings`, `process_game`

### Variables
- **Convention:** `snake_case`
- **Examples:** `elo_rating`, `home_score`, `team_name`

### Constants
- **Convention:** `UPPER_SNAKE_CASE`
- **Examples:** `BASE_ELO`, `HOME_ADVANTAGE`, `MAX_K_FACTOR`

### Private Methods/Variables
- **Convention:** `_leading_underscore`
- **Examples:** `_calculate_expected_score`, `_internal_cache`

### Example Class
```python
class RankingService:
    """Service for calculating ELO ratings."""

    BASE_ELO = 1500  # Constant

    def __init__(self, db_session):
        self.db = db_session
        self._cache = {}  # Private variable

    def calculate_elo(self, team_rating, opponent_rating):
        """Public method - snake_case."""
        return self._apply_k_factor(team_rating, opponent_rating)

    def _apply_k_factor(self, rating, opponent):
        """Private method - leading underscore."""
        pass
```

---

## PEP 8 Compliance

### Line Length
- **Maximum:** 100 characters
- **Rationale:** Matches existing codebase style, allows readable side-by-side diffs

### Indentation
- **Convention:** 4 spaces (no tabs)
- **Example:**
  ```python
  def calculate_elo(rating):
      if rating > 1500:
          return rating * 1.1
      else:
          return rating
  ```

### Blank Lines
- **2 blank lines** between top-level definitions (classes, functions)
- **1 blank line** between methods within a class
- **Example:**
  ```python
  class Team:
      pass


  class Game:
      pass


  def calculate_ratings():
      pass
  ```

### Whitespace
- No trailing whitespace
- One space around operators: `x = y + 1` (not `x=y+1`)
- No space inside brackets: `list[0]` (not `list[ 0 ]`)
- Space after commas: `func(a, b)` (not `func(a,b)`)

### Imports
- One import per line (except `from x import a, b`)
- **Example:**
  ```python
  # Good
  import os
  import sys
  from typing import List, Optional

  # Bad
  import os, sys
  ```

---

## Import Organization

Imports should be organized in three groups, separated by blank lines:

### Group 1: Standard Library
Python built-in modules

### Group 2: Third-Party
External packages (FastAPI, SQLAlchemy, pytest, etc.)

### Group 3: Local Application
Project modules

Each group should be **alphabetically sorted**.

### Example
```python
# Group 1: Standard library imports
import os
import sys
from datetime import datetime
from typing import List, Optional

# Group 2: Third-party imports
from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# Group 3: Local application imports
import schemas
from database import get_db
from models import Game, Team
from ranking_service import RankingService
```

### Tool Support
Use **isort** to automatically organize imports:
```bash
# Check import organization
isort --check-only .

# Apply import sorting
isort .
```

---

## Docstring Style Guide

Use **Google style** docstrings for all public functions, methods, and classes.

### Module-Level Docstring
```python
"""College Football Ranking API - Main Application

This module provides the FastAPI application with all REST API endpoints
for the Modified ELO ranking system.

Key Endpoints:
    - GET /api/rankings: Retrieve current team rankings
    - GET /api/teams: List all teams
    - POST /api/games: Add new game and update rankings

Example:
    Run the application with uvicorn:
        $ uvicorn main:app --reload
"""
```

### Function Docstring
```python
def calculate_elo_change(rating_diff: int, actual_score: float, k_factor: int = 32) -> float:
    """Calculate ELO rating change based on game outcome.

    Uses the standard ELO formula with configurable K-factor to determine
    how much a team's rating should change after a game.

    Args:
        rating_diff: Difference between opponent and team rating
        actual_score: 1.0 for win, 0.0 for loss, 0.5 for tie
        k_factor: Volatility factor (default: 32, higher = more volatile)

    Returns:
        Rating change value (positive for gain, negative for loss)

    Raises:
        ValueError: If actual_score is not between 0.0 and 1.0

    Example:
        >>> calculate_elo_change(100, 1.0)
        18.2
        >>> calculate_elo_change(-50, 0.0)
        -13.6
    """
    if not 0.0 <= actual_score <= 1.0:
        raise ValueError("actual_score must be between 0.0 and 1.0")

    expected = 1 / (1 + 10 ** (rating_diff / 400))
    return k_factor * (actual_score - expected)
```

### Class Docstring
```python
class Team(Base):
    """SQLAlchemy ORM model representing a college football team.

    Stores team information including name, conference, preseason metrics,
    and current ELO rating. Related to Game model through home_games and
    away_games relationships.

    Attributes:
        id: Unique team identifier (primary key)
        name: Official team name (e.g., "Georgia", "Ohio State")
        conference: Conference type (P5, G5, or FCS)
        elo_rating: Current Modified ELO rating (base 1500 for FBS)
        recruiting_rank: 247Sports recruiting class rank (1-133)
        transfer_rank: Transfer portal team rank (1-133)

    Relationships:
        home_games: Games where this team is the home team
        away_games: Games where this team is the away team
        rankings: Historical ranking snapshots by week

    Example:
        >>> team = Team(name="Georgia", conference=ConferenceType.P5)
        >>> team.elo_rating = 1850.0
        >>> db.session.add(team)
        >>> db.session.commit()
    """
```

### Docstring Sections

Required sections (when applicable):
- **Args:** Parameter descriptions with types
- **Returns:** Return value description with type
- **Raises:** Exceptions that may be raised
- **Example:** Usage examples (especially for complex functions)

---

## Type Hints Policy

### New Code
- **Required** for all public functions and methods
- **Encouraged** for complex internal functions
- **Optional** for simple private methods

### Existing Code
- **Not required** to retrofit type hints to legacy code
- **Encouraged** when modifying existing functions
- **Required** when adding new parameters to existing functions

### Standard Types
Prefer standard library types:
```python
def get_teams(limit: int = 25) -> list[Team]:
    """Use list[Team] not List[Team] in Python 3.11+"""
    pass
```

### Complex Types
Use typing module for complex types:
```python
from typing import Optional, Union

def find_team(name: str, season: Optional[int] = None) -> Optional[Team]:
    """Optional indicates value may be None"""
    pass

def calculate_rating(score: Union[int, float]) -> float:
    """Union indicates multiple possible types"""
    pass
```

### Example
```python
from typing import Optional
from sqlalchemy.orm import Session

def get_team_stats(
    db: Session,
    team_id: int,
    season: Optional[int] = None,
    include_predictions: bool = False
) -> dict[str, int | float]:
    """All parameters and return type are annotated."""
    pass
```

---

## Error Handling Patterns

### API Endpoints (FastAPI)
Use `HTTPException` for API errors:
```python
from fastapi import HTTPException

@app.get("/api/teams/{team_id}")
def get_team(team_id: int, db: Session = Depends(get_db)):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team
```

### Service Layer
Raise domain-specific exceptions:
```python
class InvalidRatingError(Exception):
    """Raised when rating calculation produces invalid result."""
    pass

class RankingService:
    def calculate_elo(self, rating):
        if rating < 0:
            raise InvalidRatingError(f"Rating cannot be negative: {rating}")
        # ... calculation
```

### External API Calls
Handle and log errors appropriately:
```python
import logging
import requests

logger = logging.getLogger(__name__)

def fetch_games(season: int) -> list[dict]:
    try:
        response = requests.get(f"{API_URL}/games?season={season}")
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as e:
        logger.error(f"CFBD API error: {e}")
        raise
    except requests.RequestException as e:
        logger.error(f"Network error fetching games: {e}")
        return []
```

### Database Operations
Let SQLAlchemy exceptions bubble up, but log them:
```python
import logging
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

def create_team(db: Session, team_data: dict):
    try:
        team = Team(**team_data)
        db.add(team)
        db.commit()
        return team
    except IntegrityError as e:
        logger.error(f"Database integrity error: {e}")
        db.rollback()
        raise
```

---

## Code Quality Tools

### Black (Code Formatter)
Automatically formats code to PEP 8 standards.

**Configuration:** `pyproject.toml`
```toml
[tool.black]
line-length = 100
target-version = ['py311']
```

**Usage:**
```bash
# Check formatting (doesn't modify files)
black --check .

# Apply formatting
black .
```

### Flake8 (Linter)
Checks code quality and style issues.

**Configuration:** `.flake8`
```ini
[flake8]
max-line-length = 100
extend-ignore = E203, W503
```

**Usage:**
```bash
# Check code quality
flake8 .

# Check specific file
flake8 main.py
```

### isort (Import Sorter)
Organizes imports according to PEP 8.

**Configuration:** `pyproject.toml`
```toml
[tool.isort]
profile = "black"
line_length = 100
```

**Usage:**
```bash
# Check import organization
isort --check-only .

# Apply import sorting
isort .
```

### Pre-Commit Workflow
Run all tools before committing:
```bash
# Check everything
black --check . && flake8 . && isort --check-only . && pytest -m "not e2e" -v

# Apply fixes
black . && isort .
```

---

## Current State Baseline

As of 2025-12-08, the codebase has the following baseline:

### Black Formatting
- **Status:** Baseline established, not yet applied
- **Files Needing Formatting:** 50+ files would be reformatted
- **Next Step:** Apply `black .` in Story 28.7 after all file reorganization
- **Configuration:** pyproject.toml with line-length=100, target-version=py311

### Flake8 Linting
- **Status:** Baseline established
- **Total Violations:** 758 issues detected
- **Critical Issues:** None (no syntax errors or undefined names)
- **Common Issues:** Line length, whitespace, unused imports (to be addressed incrementally)
- **Configuration:** .flake8 with max-line-length=100, ignore E203/W503

### isort Import Organization
- **Status:** Baseline established, to be applied in Story 28.4
- **Files Needing Sorting:** 50+ files have incorrectly sorted imports
- **Current:** Inconsistent import organization across files
- **Target:** All imports following standard library → third-party → local pattern
- **Configuration:** pyproject.toml with profile=black, line_length=100

---

## Enforcement

### Required
- **Before Pull Request:** All tests must pass
- **Code Review:** Reviewers check adherence to these standards
- **CI Pipeline:** Automated checks run on all pull requests

### Optional
- **Pre-Commit Hooks:** Developers may use git hooks to run checks locally
- **IDE Integration:** Configure IDE to use Black/Flake8/isort

---

## Questions or Suggestions?

These standards are living documents. If you have suggestions for improvements, open an issue or pull request!

---

**Last Updated:** 2025-12-08
**Part of:** EPIC-028 Comprehensive Codebase Cleanup (Story 28.2)
