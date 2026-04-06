# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#   FastStack — Hybrid FastAPI Framework
#   Runtime core + CLI generator for async FastAPI projects
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
# Author:  Manav Gupta <manavg@gmail.com>
# Usage:   run `make` or `make help` to view available targets
#
# help: FastStack  (Hybrid FastAPI framework — runtime core + CLI generator)
#

SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c

# ─────────────────────────────────────────────────────────────────────────
# Project variables
# ─────────────────────────────────────────────────────────────────────────
PROJECT_NAME := faststack
VENV_DIR     := .venv
COVERAGE_MIN := 85

# Directories and files to clean
DIRS_TO_CLEAN := __pycache__ .pytest_cache .mypy_cache .ruff_cache \
	htmlcov dist build .eggs *.egg-info

FILES_TO_CLEAN := .coverage coverage.xml

# =============================================================================
# DYNAMIC HELP
# =============================================================================
.PHONY: help
help:
	@grep "^# help\:" Makefile | grep -v grep | sed 's/\# help\: //' | sed 's/\# help\://'

.DEFAULT_GOAL := help

# =============================================================================
# help:
# help: 🌱 VIRTUAL ENVIRONMENT & INSTALLATION
# =============================================================================

# help: venv                 - Create a fresh virtual environment
.PHONY: venv
venv:
	python3 -m venv $(VENV_DIR)
	$(VENV_DIR)/bin/pip install --upgrade pip

# help: install              - Install all dependencies
.PHONY: install
install:
	poetry install

# help: install-dev          - Full dev setup (venv + deps + pre-commit hooks)
.PHONY: install-dev
install-dev: venv install
	poetry run pre-commit install
	@echo ""
	@echo "✅ Dev environment ready. Run 'make check' to verify."

# help: update               - Update dependencies to latest compatible versions
.PHONY: update
update:
	poetry update
	poetry run pre-commit autoupdate

# =============================================================================
# help:
# help: 🧪 TESTING
# =============================================================================

# help: test                 - Run tests with coverage (CI gate: fails if <$(COVERAGE_MIN)%)
.PHONY: test
test:
	poetry run pytest --cov --cov-fail-under=$(COVERAGE_MIN) --no-header -q || test $$? -eq 5

# help: test-verbose         - Run tests with verbose output + coverage
.PHONY: test-verbose
test-verbose:
	poetry run pytest --cov

# help: test-single          - Run a single test (usage: make test-single K=test_name)
.PHONY: test-single
test-single:
	poetry run pytest -k "$(K)"

# help: test-unit            - Run only unit tests (core + templates)
.PHONY: test-unit
test-unit:
	poetry run pytest -m unit --no-header -q

# help: test-integration     - Run only integration tests (CLI commands)
.PHONY: test-integration
test-integration:
	poetry run pytest -m integration --no-header -q

# help: test-e2e             - Run only e2e tests (full workflow validation)
.PHONY: test-e2e
test-e2e:
	poetry run pytest -m e2e --no-header -q

# help: test-fast            - Run all tests except slow ones
.PHONY: test-fast
test-fast:
	poetry run pytest -m "not slow" --no-header -q

# help: coverage             - Generate HTML + XML coverage report
.PHONY: coverage
coverage:
	poetry run pytest --cov --cov-report=html --cov-report=xml --no-header -q
	@echo "Coverage report: htmlcov/index.html"

# =============================================================================
# help:
# help: 🔍 CODE QUALITY
# =============================================================================

# help: lint                 - Check linting (ruff + black)
.PHONY: lint
lint:
	poetry run ruff check .
	poetry run black --check .

# help: format               - Auto-format code (ruff fix + black)
.PHONY: format
format:
	poetry run ruff check --fix .
	poetry run black .

# help: typecheck            - Run static type checking (mypy)
.PHONY: typecheck
typecheck:
	poetry run mypy faststack_core/ cli/

# help: check                - Run all checks: lint + typecheck + test (CI gate)
.PHONY: check
check: lint typecheck test

# help: pre-commit           - Run pre-commit hooks on all files
.PHONY: pre-commit
pre-commit:
	poetry run pre-commit run --all-files

# help: pre-commit-install   - Install pre-commit hooks into .git/hooks
.PHONY: pre-commit-install
pre-commit-install:
	poetry run pre-commit install

# =============================================================================
# help:
# help: 🧹 CLEANUP
# =============================================================================

# help: clean                - Remove build artifacts and caches
.PHONY: clean
clean:
	find . -type d \( -name __pycache__ -o -name .pytest_cache -o -name .mypy_cache -o -name .ruff_cache -o -name htmlcov -o -name "*.egg-info" \) -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/ .coverage coverage.xml

# help: clean-all            - Remove everything including virtual environment
.PHONY: clean-all
clean-all: clean
	rm -rf $(VENV_DIR)
