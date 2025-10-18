# College Football Ranking System - Test Automation Makefile
# Provides convenient commands for running tests locally and in CI/CD

.PHONY: help test test-unit test-integration test-e2e test-fast coverage coverage-html clean install

# Default target - show help
help:
	@echo "College Football Ranking System - Test Commands"
	@echo ""
	@echo "Available targets:"
	@echo "  make test              Run all tests (unit + integration, skip E2E)"
	@echo "  make test-unit         Run only unit tests (fast)"
	@echo "  make test-integration  Run only integration tests"
	@echo "  make test-e2e          Run only E2E tests (requires server)"
	@echo "  make test-fast         Run all tests in parallel (faster)"
	@echo "  make test-all          Run ALL tests including E2E"
	@echo "  make coverage          Run tests with coverage report (terminal)"
	@echo "  make coverage-html     Run tests with HTML coverage report"
	@echo "  make clean             Remove test artifacts and cache"
	@echo "  make install           Install test dependencies"
	@echo ""

# Run all tests except E2E (default for CI/CD)
test:
	pytest -m "not e2e" -v

# Run only unit tests (fast, isolated)
test-unit:
	pytest -m unit -v

# Run only integration tests (API + database)
test-integration:
	pytest -m integration -v

# Run only E2E tests (browser-based)
test-e2e:
	@echo "Note: E2E tests require a running server on port 8765"
	@echo "Start server with: python3 main.py"
	pytest -m e2e -v

# Run all tests in parallel for speed
test-fast:
	pytest -m "not e2e" -n auto -v

# Run ALL tests including E2E
test-all:
	pytest -v

# Run tests with coverage (terminal output)
coverage:
	pytest -m "not e2e" --cov=. --cov-report=term-missing

# Run tests with HTML coverage report
coverage-html:
	pytest -m "not e2e" --cov=. --cov-report=html
	@echo ""
	@echo "Coverage report generated in htmlcov/index.html"
	@echo "Open with: open htmlcov/index.html"

# Clean test artifacts
clean:
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "Test artifacts cleaned"

# Install test dependencies
install:
	pip install -r requirements-dev.txt
	python3 -m playwright install chromium
	@echo "Test dependencies installed"
