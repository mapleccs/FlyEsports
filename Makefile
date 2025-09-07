.PHONY: help install dev test lint format clean build up down logs migrate migrate-auto migrate-upgrade migrate-downgrade db-shell

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies for both frontend and backend
	@echo "Installing backend dependencies..."
	cd backend && pip install -r requirements.txt
	@echo "Installing frontend dependencies..."
	cd frontend && npm install
	@echo "Setting up pre-commit hooks..."
	pre-commit install

dev: ## Start development environment
	@echo "Starting development environment with .env.dev..."
	cp .env.dev .env
	docker-compose up -d

test: ## Run tests
	@echo "Running backend tests..."
	cd backend && python -m pytest
	@echo "Running frontend tests..."
	cd frontend && npm run test:unit

lint: ## Run linters
	@echo "Running backend linters..."
	cd backend && python -m black --check .
	cd backend && python -m flake8 .
	cd backend && python -m mypy .
	@echo "Running frontend linters..."
	cd frontend && npm run lint

format: ## Format code
	@echo "Formatting backend code..."
	cd backend && python -m black .
	cd backend && python -m isort .
	@echo "Formatting frontend code..."
	cd frontend && npm run format

clean: ## Clean up containers and volumes
	docker-compose down -v
	docker system prune -f

build: ## Build all services
	docker-compose build

up: ## Start all services in background
	docker-compose up -d

down: ## Stop all services
	docker-compose down

logs: ## View logs from all services
	docker-compose logs -f

backend-shell: ## Access backend container shell
	docker-compose exec backend bash

frontend-shell: ## Access frontend container shell
	docker-compose exec frontend sh

db-shell: ## Access database shell
	docker-compose exec postgres psql -U flyesports -d flyesports

# Database Migration Commands
migrate: ## Create a new migration
	@echo "Creating new migration..."
	cd backend && alembic revision --autogenerate -m "$(name)"

migrate-auto: ## Create auto-generated migration
	@echo "Creating auto-generated migration..."
	cd backend && alembic revision --autogenerate -m "auto_migration"

migrate-upgrade: ## Apply migrations to database
	@echo "Applying migrations..."
	cd backend && alembic upgrade head

migrate-downgrade: ## Rollback one migration
	@echo "Rolling back one migration..."
	cd backend && alembic downgrade -1

migrate-history: ## Show migration history
	@echo "Migration history:"
	cd backend && alembic history --verbose

migrate-current: ## Show current migration
	@echo "Current migration:"
	cd backend && alembic current

migrate-reset: ## Reset database (WARNING: destructive)
	@echo "⚠️  WARNING: This will destroy all data!"
	@read -p "Are you sure? [y/N] " -n 1 -r && echo
	@if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		cd backend && alembic downgrade base && alembic upgrade head; \
	fi

# Environment Management
env-dev: ## Copy development environment
	@echo "Setting up development environment..."
	cp .env.dev .env
	@echo "Development environment configured!"

env-check: ## Check environment configuration
	@echo "Current environment configuration:"
	@if [ -f .env ]; then echo ".env file exists"; else echo "⚠️  .env file missing"; fi
	@if [ -f .env.dev ]; then echo ".env.dev file exists"; else echo "⚠️  .env.dev file missing"; fi
	@if [ -f .env.example ]; then echo ".env.example file exists"; else echo "⚠️  .env.example file missing"; fi

# Code Quality
pre-commit: ## Run pre-commit hooks on all files
	pre-commit run --all-files

setup: ## Complete project setup
	@echo "🚀 Setting up FlyEsports project..."
	make install
	make env-dev
	@echo "✅ Project setup complete!"
	@echo "Run 'make dev' to start the development environment."