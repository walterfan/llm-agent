.PHONY: help install start stop restart clean test lint format db-migrate db-upgrade db-downgrade db-reset db-seed db-convert-cities db-import-cities db-seed-cities db-cities-count logs

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m # No Color

# Default target
.DEFAULT_GOAL := help

##@ General

help: ## Display this help message
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(BLUE)🐰 Lazy Rabbit Agent - Makefile$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make $(GREEN)<target>$(NC)\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(BLUE)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Installation

install: ## Install all dependencies (backend + frontend)
	@echo "$(BLUE)📦 Installing dependencies...$(NC)"
	@cd backend && poetry install
	@cd frontend && npm install
	@echo "$(GREEN)✅ Dependencies installed$(NC)"

install-backend: ## Install backend dependencies only
	@echo "$(BLUE)📦 Installing backend dependencies...$(NC)"
	@cd backend && poetry install
	@echo "$(GREEN)✅ Backend dependencies installed$(NC)"

install-frontend: ## Install frontend dependencies only
	@echo "$(BLUE)📦 Installing frontend dependencies...$(NC)"
	@cd frontend && npm install
	@echo "$(GREEN)✅ Frontend dependencies installed$(NC)"

##@ Development

start: ## Start both backend and frontend
	@echo "$(BLUE)🚀 Starting all services...$(NC)"
	@./start-all.sh

start-backend: ## Start backend only
	@echo "$(BLUE)🔧 Starting backend...$(NC)"
	@./start.sh

start-frontend: ## Start frontend only
	@echo "$(BLUE)🌐 Starting frontend...$(NC)"
	@cd frontend && npm run dev

stop: ## Stop all services
	@echo "$(BLUE)🛑 Stopping all services...$(NC)"
	@./stop-all.sh

stop-backend: ## Stop backend only
	@echo "$(BLUE)🛑 Stopping backend...$(NC)"
	@./stop.sh

stop-frontend: ## Stop frontend only
	@echo "$(BLUE)🛑 Stopping frontend...$(NC)"
	@pkill -f "vite" || echo "$(YELLOW)No frontend process found$(NC)"

restart: stop start ## Restart all services

restart-backend: stop-backend start-backend ## Restart backend only

restart-frontend: stop-frontend start-frontend ## Restart frontend only

##@ Database

db-migrate: ## Create a new database migration
	@read -p "Enter migration message: " msg; \
	cd backend && poetry run alembic revision --autogenerate -m "$$msg"
	@echo "$(GREEN)✅ Migration created$(NC)"

db-upgrade: ## Apply all pending migrations
	@echo "$(BLUE)📊 Applying database migrations...$(NC)"
	@cd backend && poetry run alembic upgrade head
	@echo "$(GREEN)✅ Database upgraded$(NC)"

db-downgrade: ## Rollback last migration
	@echo "$(BLUE)📊 Rolling back database...$(NC)"
	@cd backend && poetry run alembic downgrade -1
	@echo "$(GREEN)✅ Database rolled back$(NC)"

db-reset: ## Reset database (WARNING: deletes all data)
	@echo "$(YELLOW)⚠️  WARNING: This will delete all data!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "$(BLUE)🗑️  Resetting database...$(NC)"; \
		rm -f backend/app.db; \
		cd backend && poetry run alembic upgrade head; \
		cd backend && poetry run python -m app.scripts.seed_rbac; \
		echo "$(GREEN)✅ Database reset complete$(NC)"; \
	else \
		echo "$(YELLOW)Cancelled$(NC)"; \
	fi

db-seed: ## Seed database with default roles and permissions
	@echo "$(BLUE)🌱 Seeding database...$(NC)"
	@cd backend && poetry run python -m app.scripts.seed_rbac
	@echo "$(GREEN)✅ Database seeded$(NC)"

db-status: ## Show current database migration status
	@echo "$(BLUE)📊 Database status:$(NC)"
	@cd backend && poetry run alembic current

db-history: ## Show migration history
	@echo "$(BLUE)📊 Migration history:$(NC)"
	@cd backend && poetry run alembic history

db-convert-cities: ## Convert Excel backup to CSV format
	@echo "$(BLUE)📊 Converting Excel to CSV...$(NC)"
	@cd backend && poetry run python scripts/excel_to_csv.py
	@echo "$(GREEN)✅ Conversion complete$(NC)"

db-import-cities: ## Import cities from CSV into database
	@echo "$(BLUE)📊 Importing cities...$(NC)"
	@cd backend && poetry run python scripts/import_cities.py
	@echo "$(GREEN)✅ Cities imported$(NC)"

db-seed-cities: db-convert-cities db-import-cities ## Convert Excel and import cities (full process)
	@echo "$(GREEN)✅ Cities seeded successfully$(NC)"

db-cities-count: ## Show current cities count in database
	@echo "$(BLUE)📊 Cities count:$(NC)"
	@cd backend && sqlite3 app.db "SELECT COUNT(*) as total FROM cities" | xargs -I {} echo "  Total cities: {}"
	@cd backend && sqlite3 app.db "SELECT location_id, location_name_zh, ad_code FROM cities WHERE location_name_zh LIKE '%北京%' LIMIT 3" | while IFS='|' read -r id name code; do echo "  Sample: $$name (id: $$id, code: $$code)"; done

##@ Build

build: type-check ## Build production artifacts (with type checking)
	@echo "$(BLUE)🏗️  Building project...$(NC)"
	@cd frontend && npm run build
	@echo "$(GREEN)✅ Build complete$(NC)"

build-frontend: ## Build frontend for production
	@echo "$(BLUE)🏗️  Building frontend...$(NC)"
	@cd frontend && npm run build
	@echo "$(GREEN)✅ Frontend built: frontend/dist/$(NC)"

##@ Type Safety

generate-types: ## Generate TypeScript types from OpenAPI schema
	@echo "$(BLUE)🔧 Generating TypeScript types from backend schema...$(NC)"
	@if ! curl -s -f http://localhost:8000/api/health > /dev/null 2>&1; then \
		echo "$(YELLOW)⚠️  Backend not running. Starting backend...$(NC)"; \
		$(MAKE) start-backend; \
		sleep 3; \
	fi
	@cd frontend && npm run generate-types
	@echo "$(GREEN)✅ Types generated: frontend/src/types/api.generated.ts$(NC)"

type-check: ## Run TypeScript type checking
	@echo "$(BLUE)🔍 Running TypeScript type checking...$(NC)"
	@cd frontend && npm run type-check
	@echo "$(GREEN)✅ Type checking passed$(NC)"

type-sync: generate-types type-check ## Generate types and validate them
	@echo "$(GREEN)✅ Types are in sync with backend$(NC)"

check: ## Run all critical checks (lint + type-check + arch + test) - USE BEFORE COMMIT
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(BLUE)🔍 Running all critical checks...$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@$(MAKE) lint
	@$(MAKE) type-check
	@$(MAKE) arch-check
	@$(MAKE) test
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(GREEN)✅ All checks passed! Ready to commit.$(NC)"
	@echo "$(BLUE)========================================$(NC)"

##@ Testing

test: ## Run all tests (backend + frontend)
	@echo "$(BLUE)🧪 Running tests...$(NC)"
	@$(MAKE) test-backend
	@$(MAKE) test-frontend

test-backend: ## Run backend tests
	@echo "$(BLUE)🧪 Running backend tests...$(NC)"
	@cd backend && poetry run pytest -v
	@echo "$(GREEN)✅ Backend tests complete$(NC)"

test-frontend: ## Run frontend tests
	@echo "$(BLUE)🧪 Running frontend tests...$(NC)"
	@cd frontend && npm run test
	@echo "$(GREEN)✅ Frontend tests complete$(NC)"

test-e2e: ## Run end-to-end tests
	@echo "$(BLUE)🧪 Running E2E tests...$(NC)"
	@cd frontend && npm run test:e2e
	@echo "$(GREEN)✅ E2E tests complete$(NC)"

test-coverage: ## Run tests with coverage report
	@echo "$(BLUE)🧪 Running tests with coverage...$(NC)"
	@cd frontend && npm run test:coverage
	@echo "$(GREEN)✅ Coverage report generated$(NC)"

##@ Code Quality

lint: ## Run linters on backend and frontend
	@echo "$(BLUE)🔍 Running linters...$(NC)"
	@$(MAKE) lint-backend
	@$(MAKE) lint-frontend

lint-backend: ## Run backend linter (flake8, black check)
	@echo "$(BLUE)🔍 Linting backend...$(NC)"
	@cd backend && poetry run black --check app || true
	@cd backend && poetry run flake8 app || true
	@echo "$(GREEN)✅ Backend lint complete$(NC)"

arch-check: arch-check-backend arch-check-frontend ## Check architecture boundaries (all)

arch-check-backend: ## Check backend architecture boundaries (import-linter)
	@echo "$(BLUE)🏛️  Checking backend architecture boundaries...$(NC)"
	@cd backend && poetry run lint-imports
	@echo "$(GREEN)✅ Backend architecture boundaries verified$(NC)"

arch-check-frontend: ## Check frontend architecture boundaries (dependency-cruiser)
	@echo "$(BLUE)🏛️  Checking frontend architecture boundaries...$(NC)"
	@cd frontend && npm run arch-check
	@echo "$(GREEN)✅ Frontend architecture boundaries verified$(NC)"

lint-frontend: ## Run frontend linter (eslint)
	@echo "$(BLUE)🔍 Linting frontend...$(NC)"
	@cd frontend && npm run lint
	@echo "$(GREEN)✅ Frontend lint complete$(NC)"

format: ## Format code (backend + frontend)
	@echo "$(BLUE)✨ Formatting code...$(NC)"
	@$(MAKE) format-backend
	@$(MAKE) format-frontend

format-backend: ## Format backend code with black
	@echo "$(BLUE)✨ Formatting backend...$(NC)"
	@cd backend && poetry run black app
	@echo "$(GREEN)✅ Backend formatted$(NC)"

format-frontend: ## Format frontend code with prettier
	@echo "$(BLUE)✨ Formatting frontend...$(NC)"
	@cd frontend && npm run format
	@echo "$(GREEN)✅ Frontend formatted$(NC)"

##@ Logs

logs: ## Tail all logs
	@echo "$(BLUE)📋 Tailing logs (Ctrl+C to stop)...$(NC)"
	@tail -f backend/logs/backend.log backend/logs/frontend.log 2>/dev/null || echo "$(YELLOW)No log files found$(NC)"

logs-backend: ## Tail backend logs
	@echo "$(BLUE)📋 Tailing backend logs (Ctrl+C to stop)...$(NC)"
	@tail -f backend/logs/backend.log

logs-frontend: ## Tail frontend logs
	@echo "$(BLUE)📋 Tailing frontend logs (Ctrl+C to stop)...$(NC)"
	@tail -f backend/logs/frontend.log

logs-clear: ## Clear all log files
	@echo "$(BLUE)🗑️  Clearing logs...$(NC)"
	@rm -f backend/logs/*.log backend/logs/*.pid
	@echo "$(GREEN)✅ Logs cleared$(NC)"

##@ Cleanup

clean: ## Clean temporary files and build artifacts
	@echo "$(BLUE)🧹 Cleaning...$(NC)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@rm -rf frontend/dist 2>/dev/null || true
	@rm -rf backend/.coverage 2>/dev/null || true
	@echo "$(GREEN)✅ Cleaned$(NC)"

clean-db: ## Remove database file (WARNING: deletes all data)
	@echo "$(YELLOW)⚠️  WARNING: This will delete the database!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		rm -f backend/app.db; \
		echo "$(GREEN)✅ Database deleted$(NC)"; \
	else \
		echo "$(YELLOW)Cancelled$(NC)"; \
	fi

clean-logs: logs-clear ## Alias for logs-clear

##@ Environment

env-check: ## Check if all required tools are installed
	@echo "$(BLUE)🔍 Checking environment...$(NC)"
	@command -v python3 >/dev/null 2>&1 && echo "$(GREEN)✅ Python 3$(NC)" || echo "$(RED)✗ Python 3$(NC)"
	@command -v poetry >/dev/null 2>&1 && echo "$(GREEN)✅ Poetry$(NC)" || echo "$(RED)✗ Poetry$(NC)"
	@command -v node >/dev/null 2>&1 && echo "$(GREEN)✅ Node.js$(NC)" || echo "$(RED)✗ Node.js$(NC)"
	@command -v npm >/dev/null 2>&1 && echo "$(GREEN)✅ npm$(NC)" || echo "$(RED)✗ npm$(NC)"
	@test -f .env && echo "$(GREEN)✅ .env file$(NC)" || echo "$(YELLOW)⚠  .env file not found$(NC)"

env-create: ## Create .env file from .env.sample
	@if [ ! -f .env ]; then \
		cp .env.sample .env; \
		echo "$(GREEN)✅ .env file created from .env.sample$(NC)"; \
		echo "$(YELLOW)⚠  Please edit .env and add your API keys$(NC)"; \
	else \
		echo "$(YELLOW).env file already exists$(NC)"; \
	fi

##@ Docker (if needed in future)

docker-build: ## Build Docker images
	@echo "$(BLUE)🐳 Building Docker images...$(NC)"
	@docker-compose build
	@echo "$(GREEN)✅ Docker images built$(NC)"

docker-up: ## Start services with Docker Compose
	@echo "$(BLUE)🐳 Starting Docker containers...$(NC)"
	@docker-compose up -d
	@echo "$(GREEN)✅ Docker containers started$(NC)"

docker-down: ## Stop Docker containers
	@echo "$(BLUE)🐳 Stopping Docker containers...$(NC)"
	@docker-compose down
	@echo "$(GREEN)✅ Docker containers stopped$(NC)"

docker-logs: ## Show Docker logs
	@docker-compose logs -f

##@ Quick Start

init: env-check install db-upgrade db-seed ## Initialize project (first time setup)
	@echo ""
	@echo "$(GREEN)========================================$(NC)"
	@echo "$(GREEN)✅ Initialization Complete!$(NC)"
	@echo "$(GREEN)========================================$(NC)"
	@echo ""
	@echo "$(BLUE)Next steps:$(NC)"
	@echo "  1. Edit .env and add your API keys"
	@echo "  2. Run: $(GREEN)make start$(NC)"
	@echo "  3. Open: $(BLUE)http://localhost:5173$(NC)"
	@echo ""

dev: start ## Alias for 'make start'

prod: build ## Build for production
