# Contributing to Stat-urday Synthesis

Thank you for your interest in contributing to the College Football Ranking System! This guide will help you get started with development, testing, and submitting contributions.

---

## Table of Contents

- [Development Environment Setup](#development-environment-setup)
- [Running the Application](#running-the-application)
- [Running Tests](#running-tests)
- [Code Contribution Workflow](#code-contribution-workflow)
- [Code Review Checklist](#code-review-checklist)
- [Getting Help](#getting-help)

---

## Development Environment Setup

### Prerequisites

- **Python 3.11+** (required for FastAPI and modern type hints)
- **pip** (Python package manager)
- **Git** (version control)
- **CollegeFootballData API Key** (free - get from [collegefootballdata.com/key](https://collegefootballdata.com/key))

### Initial Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/cfb-rankings.git
   cd cfb-rankings
   ```

2. **Create and activate virtual environment:**
   ```bash
   # Create virtual environment
   python3 -m venv venv

   # Activate virtual environment
   # On Mac/Linux:
   source venv/bin/activate

   # On Windows:
   venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   # Install production dependencies
   pip install -r requirements.txt

   # Install development dependencies (testing, linting, formatting)
   pip install -r requirements-dev.txt
   ```

4. **Configure environment variables:**
   ```bash
   # Copy example environment file
   cp .env.example .env

   # Edit .env and add your CFBD API key
   # .env file should contain:
   CFBD_API_KEY=your_api_key_here
   DATABASE_URL=sqlite:///./cfb_rankings.db
   CFBD_MONTHLY_LIMIT=1000
   ```

5. **Initialize database with sample data:**
   ```bash
   # Option 1: Use sample data for development
   python3 seed_data.py

   # Option 2: Import real data (requires CFBD API key)
   python3 import_real_data.py --reset
   ```

---

## Running the Application

### Backend (FastAPI)

**Option 1: Direct Python execution**
```bash
python3 main.py
```

**Option 2: Using uvicorn with auto-reload (recommended for development)**
```bash
uvicorn main:app --reload
```

The backend will start at: `http://localhost:8000`

### Frontend

The frontend is served as static files by the FastAPI backend.

**Access the application:**
- **Main Rankings Page:** [http://localhost:8000/frontend/](http://localhost:8000/frontend/)
- **API Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs) (interactive Swagger UI)
- **ReDoc API Docs:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Verifying Setup

Test that everything works:
```bash
# Check backend is running
curl http://localhost:8000/api/rankings

# Should return JSON with team rankings
```

---

## Running Tests

The project has a comprehensive test suite with 124 tests covering unit, integration, and end-to-end scenarios.

### Run All Tests

```bash
# Run all tests (skips E2E by default)
pytest -v

# Run with coverage report
pytest --cov=. --cov-report=html --cov-report=term-missing

# View coverage in browser
open htmlcov/index.html
```

### Run Specific Test Categories

```bash
# Unit tests only (fastest - tests individual functions/classes)
pytest -m unit -v

# Integration tests only (tests API endpoints, database interactions)
pytest -m integration -v

# End-to-end tests (tests complete user workflows with browser automation)
pytest -m e2e -v

# Skip E2E tests for quick iteration
pytest -m "not e2e" -v
```

### Run Specific Test Files

```bash
# Test a specific file
pytest tests/test_ranking_service.py -v

# Test a specific function
pytest tests/test_ranking_service.py::test_calculate_elo -v

# Test with output (see print statements)
pytest tests/test_ranking_service.py -v -s
```

### Before Committing

Always run tests before committing to ensure your changes don't break existing functionality:

```bash
# Quick test (unit + integration, skip E2E)
pytest -m "not e2e" -v

# Full test suite (includes E2E - takes longer)
pytest -v
```

**All tests must pass before submitting a pull request.**

---

## Code Contribution Workflow

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/cfb-rankings.git
cd cfb-rankings

# Add upstream remote
git remote add upstream https://github.com/original/cfb-rankings.git
```

### 2. Create Feature Branch

```bash
# Update your main branch
git checkout main
git pull upstream main

# Create feature branch with descriptive name
git checkout -b feature/add-team-stats
# or
git checkout -b fix/ranking-calculation-bug
# or
git checkout -b docs/update-api-documentation
```

**Branch naming conventions:**
- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation updates
- `refactor/description` - Code refactoring
- `test/description` - Test improvements

### 3. Make Changes

- Write clear, concise code following the project's coding standards
- Add tests for new functionality
- Update documentation if needed
- Keep commits focused and atomic

### 4. Test Your Changes

```bash
# Run tests to ensure nothing broke
pytest -v

# Run linting (if configured)
flake8 .

# Format code (if configured)
black .
isort .
```

### 5. Commit Changes

```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "Add team statistics calculation endpoint

- Implement new /api/teams/{id}/stats endpoint
- Add tests for statistics calculations
- Update API documentation"
```

**Commit message guidelines:**
- First line: Short summary (50 chars or less)
- Blank line
- Detailed description if needed (what and why, not how)
- Reference issue numbers if applicable (#123)

### 6. Push and Create Pull Request

```bash
# Push to your fork
git push origin feature/add-team-stats

# Go to GitHub and create pull request from your branch to upstream main
```

**Pull Request Guidelines:**
- Clear title describing the change
- Detailed description of what changed and why
- Reference any related issues
- Include screenshots for UI changes
- Ensure all tests pass in CI

### 7. Code Review Process

- Respond to review comments promptly
- Make requested changes in new commits
- Once approved, your PR will be merged

---

## Code Review Checklist

Before submitting your pull request, verify:

### Functionality
- [ ] All tests pass locally (`pytest -v`)
- [ ] New features have corresponding tests
- [ ] Bug fixes include regression tests
- [ ] Manual testing completed for UI/API changes

### Code Quality
- [ ] Code follows PEP 8 style guide
- [ ] No debug code (print statements, commented code, etc.)
- [ ] Functions/methods have docstrings (Google style)
- [ ] Variable names are descriptive
- [ ] No overly complex functions (consider breaking up)

### Documentation
- [ ] README.md updated if user-facing changes
- [ ] API documentation updated if endpoints changed
- [ ] Docstrings added for new functions/classes
- [ ] Comments added for complex logic

### Security
- [ ] No sensitive data committed (API keys, passwords, etc.)
- [ ] No SQL injection vulnerabilities
- [ ] No XSS vulnerabilities in frontend
- [ ] Input validation for all API endpoints

### Database
- [ ] Database migrations created if schema changed
- [ ] Migrations tested (up and down)
- [ ] No breaking changes to existing data

### Git
- [ ] Commit messages are clear and descriptive
- [ ] No merge commits (rebase if needed)
- [ ] Branch is up-to-date with main

---

## Code Quality Tools (Optional)

The project supports code quality tools to maintain consistency:

### Black (Code Formatter)
```bash
# Check formatting (doesn't modify files)
black --check .

# Apply formatting
black .
```

### Flake8 (Linter)
```bash
# Check code quality
flake8 .
```

### isort (Import Sorter)
```bash
# Check import organization
isort --check-only .

# Apply import sorting
isort .
```

### Run All Quality Checks
```bash
# Check everything before committing
black --check . && flake8 . && isort --check-only . && pytest -m "not e2e" -v
```

---

## Getting Help

### Documentation
- **Architecture:** See `docs/architecture.md` for system architecture
- **Development Guide:** See `DEVELOPMENT.md` for detailed development info
- **Testing Guide:** See `docs/TESTING.md` for testing best practices
- **API Docs:** Visit [http://localhost:8000/docs](http://localhost:8000/docs) when running locally

### Questions and Issues
- **Bug Reports:** Open an issue on GitHub with steps to reproduce
- **Feature Requests:** Open an issue describing the feature and use case
- **Questions:** Open a discussion on GitHub or comment on relevant issues

### Common Development Issues

**Import errors:**
- Ensure virtual environment is activated: `source venv/bin/activate`
- Reinstall dependencies: `pip install -r requirements.txt`

**Database errors:**
- Delete database and reseed: `rm cfb_rankings.db && python3 seed_data.py`
- Check DATABASE_URL in .env file

**API call failures:**
- Verify CFBD_API_KEY is set in .env
- Check API usage hasn't exceeded limit: `curl http://localhost:8000/api/admin/api-usage`

**Test failures:**
- Check pytest markers are correct
- Ensure test database is clean
- Run tests individually to isolate failures: `pytest tests/test_file.py::test_function -v`

---

## Thank You!

Your contributions make this project better for everyone. We appreciate your time and effort! 🎉
