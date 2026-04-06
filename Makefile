.DEFAULT_GOAL := help

VENV_DIR := .venv

.PHONY: venv install install-dev update \
        test test-verbose test-single test-unit test-integration test-e2e test-fast \
        lint format typecheck check coverage \
        pre-commit-install pre-commit \
        clean clean-all help

# ---------------------------------------------------------------------------
# Environment setup
# ---------------------------------------------------------------------------

venv: ## Create virtual environment
	python3 -m venv $(VENV_DIR)
	$(VENV_DIR)/bin/pip install --upgrade pip

install: ## Install all dependencies + pre-commit hooks
	poetry install
	poetry run pre-commit install

install-dev: venv install ## One-shot dev environment setup (new contributors start here)
	@echo "\n✅ Dev environment ready. Run 'make check' to verify."

update: ## Update dependencies to latest compatible versions
	poetry update
	poetry run pre-commit autoupdate

# ---------------------------------------------------------------------------
# Testing
# ---------------------------------------------------------------------------

test: ## Run tests with coverage (CI gate: fails if <85%)
	poetry run pytest --cov --cov-fail-under=85 --no-header -q || test $$? -eq 5

test-verbose: ## Run tests with verbose output + coverage
	poetry run pytest --cov

test-single: ## Run a single test (usage: make test-single K=test_name)
	poetry run pytest -k "$(K)"

test-unit: ## Run only unit tests (core + templates)
	poetry run pytest -m unit --no-header -q

test-integration: ## Run only integration tests (CLI commands)
	poetry run pytest -m integration --no-header -q

test-e2e: ## Run only e2e tests (full workflow)
	poetry run pytest -m e2e --no-header -q

test-fast: ## Run all tests except slow ones
	poetry run pytest -m "not slow" --no-header -q

coverage: ## Generate HTML coverage report
	poetry run pytest --cov --cov-report=html --no-header -q
	@echo "Coverage report: htmlcov/index.html"

# ---------------------------------------------------------------------------
# Code quality
# ---------------------------------------------------------------------------

lint: ## Check linting (ruff + black)
	poetry run ruff check .
	poetry run black --check .

format: ## Auto-format code (ruff fix + black)
	poetry run ruff check --fix .
	poetry run black .

typecheck: ## Run type checking
	poetry run mypy faststack_core/ cli/

check: lint typecheck test ## Run all checks (CI gate)

pre-commit-install: ## Install pre-commit hooks into .git/hooks
	poetry run pre-commit install

pre-commit: ## Run pre-commit hooks on all files
	poetry run pre-commit run --all-files

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

clean: ## Remove build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/ .coverage

clean-all: clean ## Remove everything including virtual environment
	rm -rf $(VENV_DIR)

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
