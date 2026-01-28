.PHONY: help install test test-verbose test-unit test-integration test-cov clean lint format test-docker cleanup-firecracker cleanup-firecracker-dirs

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON := python
UV := uv
PYTEST := uv run pytest
PYTEST_ARGS := tests/

help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies using uv
	@echo "Installing dependencies..."
	$(UV) sync

install-dev: ## Install development dependencies
	@echo "Installing development dependencies..."
	$(UV) sync --dev

test: cleanup-firecracker ## Run all tests (continue on failures)
	@echo "Running tests..."
	-$(PYTEST) $(PYTEST_ARGS) || true

test-stop: ## Run tests but stop on first failure
	@echo "Running tests (stop on first failure)..."
	-$(PYTEST) -x $(PYTEST_ARGS) || true

test-maxfail: ## Run tests but stop after N failures (usage: make test-maxfail MAXFAIL=5)
	@echo "Running tests (stop after $(MAXFAIL) failures)..."
	$(PYTEST) --maxfail=$(MAXFAIL) $(PYTEST_ARGS)

test-verbose: ## Run tests with verbose output
	@echo "Running tests with verbose output..."
	$(PYTEST) -v $(PYTEST_ARGS)

test-quiet: ## Run tests with minimal output
	@echo "Running tests (quiet mode)..."
	$(PYTEST) -q $(PYTEST_ARGS)

test-unit: ## Run only unit tests (excluding integration tests)
	@echo "Running unit tests..."
	-$(PYTEST) -v -m "not integration" $(PYTEST_ARGS) || true

test-integration: ## Run only integration tests
	@echo "Running integration tests..."
	$(PYTEST) -v -m "integration" $(PYTEST_ARGS)

test-cov: ## Run tests with coverage report
	@echo "Running tests with coverage..."
	-$(UV) run pytest --cov=firecracker --cov-report=term-missing --cov-report=html $(PYTEST_ARGS) || true

test-cov-html: ## Run tests and generate HTML coverage report
	@echo "Running tests with HTML coverage report..."
	$(UV) run pytest --cov=firecracker --cov-report=html $(PYTEST_ARGS)
	@echo "Coverage report generated in htmlcov/index.html"

test-watch: ## Run tests in watch mode (requires pytest-watch)
	@echo "Running tests in watch mode..."
	$(UV) run pytest-watch $(PYTEST_ARGS)

test-failed: ## Re-run only failed tests
	@echo "Re-running failed tests..."
	$(PYTEST) --lf $(PYTEST_ARGS)

test-last-failed: ## Show which tests failed in the last run
	@echo "Showing last failed tests..."
	$(PYTEST) --lf --collect-only $(PYTEST_ARGS)

test-specific: ## Run a specific test (usage: make test-specific TEST=test_name)
	@echo "Running specific test: $(TEST)"
	$(PYTEST) -v $(PYTEST_ARGS)::$(TEST)

test-file: ## Run tests in a specific file (usage: make test-file FILE=tests/test_microvm.py)
	@echo "Running tests in file: $(FILE)"
	$(PYTEST) -v $(FILE)

lint: ## Run linter (requires ruff)
	@echo "Running linter..."
	$(UV) run ruff check firecracker tests

lint-fix: ## Run linter and auto-fix issues
	@echo "Running linter with auto-fix..."
	$(UV) run ruff check --fix firecracker tests

format: ## Format code (requires ruff)
	@echo "Formatting code..."
	$(UV) run ruff format firecracker tests

format-check: ## Check if code is formatted correctly
	@echo "Checking code formatting..."
	$(UV) run ruff format --check firecracker tests

type-check: ## Run type checker (requires mypy)
	@echo "Running type checker..."
	$(UV) run mypy firecracker

clean: ## Clean up temporary files
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	find . -type f -name ".DS_Store" -delete 2>/dev/null || true
	@echo "Cleanup complete."

clean-all: clean ## Clean everything including virtual environment
	@echo "Removing virtual environment..."
	rm -rf .venv
	@echo "Complete cleanup done."

cleanup-firecracker: ## Clean up Firecracker resources (processes, TAP devices, nftables rules)
	@echo "Cleaning up Firecracker resources..."
	@python scripts/cleanup_resources.py

cleanup-firecracker-dirs: cleanup-firecracker ## Clean up Firecracker resources including directories
	@echo "Cleaning up Firecracker directories..."
	@python scripts/cleanup_resources.py

ci: lint type-check test ## Run all CI checks (lint, type-check, test)
	@echo "All CI checks passed!"

dev: install-dev ## Install development dependencies
	@echo "Development environment setup complete."

all: clean install test ## Clean, install, and run tests
	@echo "Build and test complete."

test-docker: ## Run tests in Docker with KVM access
	@echo "Running tests in Docker..."
	@./scripts/run-tests-docker.sh

test-docker-build: ## Build Docker image for testing
	@echo "Building Docker test image..."
	@docker compose -f docker-compose.test.yml build

test-docker-shell: ## Start a shell in the Docker test container
	@echo "Starting shell in Docker test container..."
	@./scripts/run-tests-docker.sh -s

test-docker-verbose: ## Run tests in Docker with verbose output
	@echo "Running tests in Docker with verbose output..."
	@./scripts/run-tests-docker.sh -v

test-docker-coverage: ## Run tests in Docker with coverage report
	@echo "Running tests in Docker with coverage..."
	@./scripts/run-tests-docker.sh -c

test-docker-clean: ## Clean Docker test resources
	@echo "Cleaning Docker test resources..."
	@docker compose -f docker-compose.test.yml down -v
	@echo "Docker test resources cleaned."
