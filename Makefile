.DEFAULT_GOAL := help

.PHONY: install test test-verbose test-single lint format typecheck check clean help

install: ## Install dependencies
	poetry install

test: ## Run tests
	poetry run pytest --no-header -q || test $$? -eq 5

test-verbose: ## Run tests with verbose output
	poetry run pytest -v

test-single: ## Run a single test (usage: make test-single K=test_name)
	poetry run pytest -k "$(K)"

lint: ## Check linting (ruff + black)
	poetry run ruff check .
	poetry run black --check .

format: ## Auto-format code (ruff fix + black)
	poetry run ruff check --fix .
	poetry run black .

typecheck: ## Run type checking
	poetry run mypy faststack_core/ cli/

check: lint typecheck test ## Run all checks (CI gate)

clean: ## Remove build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/ .coverage

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
