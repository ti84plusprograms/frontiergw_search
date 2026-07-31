.PHONY: help install dev test lint build clean docker-up docker-down

help:
	@echo "Frontier GoWild Destination Explorer"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  install      Install all dependencies (backend venv + frontend node_modules)"
	@echo "  dev          Start both backend and frontend in development mode"
	@echo "  test         Run all tests"
	@echo "  lint         Run linters and formatters"
	@echo "  build        Build frontend for production"
	@echo "  clean        Remove build artifacts, caches, and venv"
	@echo "  docker-up    Start Docker Compose services"
	@echo "  docker-down  Stop Docker Compose services"

install:
	@echo "Installing Python backend..."
	cd apps/api && python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"
	@echo "Installing Node frontend..."
	pnpm install

dev:
	@echo "Starting development services..."
	docker compose -f infrastructure/docker-compose.yml up

test:
	@echo "Running backend tests..."
	cd apps/api && source .venv/bin/activate && pytest tests/ -v

lint:
	@echo "Linting and formatting backend..."
	cd apps/api && source .venv/bin/activate && ruff format . && ruff check --fix . && mypy app
	@echo "Type-checking frontend..."
	cd apps/web && pnpm type-check

build:
	@echo "Building frontend..."
	cd apps/web && pnpm build

clean:
	@echo "Cleaning up..."
	rm -rf apps/api/.venv apps/api/__pycache__ apps/api/.pytest_cache apps/api/.mypy_cache
	rm -rf apps/web/node_modules apps/web/.next apps/web/out apps/web/*.tsbuildinfo
	rm -rf apps/web/.turbo .turbo
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

docker-up:
	docker compose -f infrastructure/docker-compose.yml up

docker-down:
	docker compose -f infrastructure/docker-compose.yml down
