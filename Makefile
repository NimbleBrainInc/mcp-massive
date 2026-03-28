# MCPB bundle configuration
BUNDLE_NAME = mcp-massive
VERSION ?= 0.0.1

.PHONY: help install dev-install format format-check lint lint-fix test test-cov test-e2e clean check all bundle bundle-run run run-stdio run-http test-http bump

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install the package
	uv pip install -e .

dev-install: ## Install with dev dependencies
	uv pip install -e . --group dev

format: ## Format code with ruff
	uv run ruff format src/ tests/

format-check: ## Check code formatting with ruff
	uv run ruff format --check src/ tests/

lint: ## Lint code with ruff
	uv run ruff check src/ tests/

lint-fix: ## Lint and fix code with ruff
	uv run ruff check --fix src/ tests/

test: ## Run tests with pytest
	uv run pytest tests/ -v

test-cov: ## Run tests with coverage
	uv run pytest tests/ -v --cov=src/mcp_massive --cov-report=term-missing

test-integration: ## Run integration tests (needs ANTHROPIC_API_KEY)
	uv run pytest tests-integration/ -v -s

test-e2e: ## Run end-to-end MCPB tests
	uv run pytest e2e/ -v -s

clean: ## Clean up artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".coverage" -exec rm -rf {} + 2>/dev/null || true
	rm -rf bundle/ *.mcpb

run: ## Run the MCP server
	uv run python -m mcp_massive.server

run-stdio: ## Run in stdio mode (for Claude desktop)
	uv run fastmcp run src/mcp_massive/server.py

run-http: ## Run HTTP server with uvicorn
	uv run uvicorn mcp_massive.server:app --host 0.0.0.0 --port 8000

test-http: ## Test HTTP server is running
	@echo "Testing health endpoint..."
	@curl -s http://localhost:8000/health | grep -q "healthy" && echo "✓ Server is healthy" || echo "✗ Server not responding"

check: format-check lint test ## Run all checks

all: clean install format lint test ## Full workflow

# MCPB bundle commands
bundle: ## Build MCPB bundle locally
	@./scripts/build-bundle.sh . $(VERSION)

bundle-run: bundle ## Build and run MCPB bundle locally
	@echo "Starting bundle with mcpb-python base image..."
	@python -m http.server 9999 --directory . &
	@sleep 1
	docker run --rm \
		--add-host host.docker.internal:host-gateway \
		-p 8000:8000 \
		-e BUNDLE_URL=http://host.docker.internal:9999/$(BUNDLE_NAME)-v$(VERSION).mcpb \
		ghcr.io/nimblebrain/mcpb-python:3.14

bump: ## Bump version across all files (usage: make bump VERSION=0.2.0)
	@if [ -z "$(VERSION)" ]; then echo "Usage: make bump VERSION=x.y.z"; exit 1; fi
	@echo "Bumping version to $(VERSION)..."
	@jq --arg v "$(VERSION)" '.version = $$v' manifest.json > manifest.tmp.json && mv manifest.tmp.json manifest.json
	@sed -i '' 's/^version = ".*"/version = "$(VERSION)"/' pyproject.toml
	@sed -i '' 's/^__version__ = ".*"/__version__ = "$(VERSION)"/' src/mcp_massive/__init__.py
	@echo "Updated:"
	@echo "  manifest.json:               $$(jq -r .version manifest.json)"
	@echo "  pyproject.toml:              $$(grep '^version' pyproject.toml)"
	@echo "  src/mcp_massive/__init__.py: $$(grep '__version__' src/mcp_massive/__init__.py)"

# Aliases
fmt: format
t: test
l: lint
