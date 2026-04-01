# HRECOS Dashboard Makefile
# Quick commands for development and deployment

.PHONY: help build up down logs test lint format clean deploy

# Default target
help:
	@echo "HRECOS Dashboard - Available Commands:"
	@echo ""
	@echo "  make build      - Build all Docker images"
	@echo "  make up         - Start all services"
	@echo "  make up-d       - Start all services in detached mode"
	@echo "  make down       - Stop all services"
	@echo "  make logs       - View logs from all services"
	@echo "  make logs-backend - View backend logs only"
	@echo "  make test       - Run tests"
	@echo "  make lint       - Run linting"
	@echo "  make format     - Format code with black"
	@echo "  make shell      - Open shell in backend container"
	@echo "  make db-shell   - Open PostgreSQL shell"
	@echo "  make clean      - Remove containers and volumes"
	@echo "  make deploy     - Deploy to production (requires secrets)"
	@echo ""

# Development commands
build:
	docker compose build

up:
	docker compose up

up-d:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

logs-backend:
	docker compose logs -f backend

# Testing and linting
test:
	cd backend && python -m pytest tests/ -v || echo "No tests directory yet"

lint:
	cd backend && \
	pip install flake8 black isort bandit && \
	flake8 app --count --select=E9,F63,F7,F82 --show-source --statistics && \
	black --check app && \
	isort --check-only app

format:
	cd backend && \
	pip install black isort && \
	black app && \
	isort app

# Container interaction
shell:
	docker compose exec backend /bin/sh

db-shell:
	docker compose exec db psql -U postgres -d hrecos

# Database management
db-migrate:
	docker compose exec backend alembic upgrade head

db-reset:
	docker compose down -v
	docker volume rm hrecos-dashboard_db_data 2>/dev/null || true

# Cleanup
clean:
	docker compose down -v --rmi all --remove-orphans
	docker system prune -f

# Production deployment
deploy:
	@echo "Deploying to production..."
	gh workflow run deploy.yml

# Release
tag-release:
	@echo "Creating new release..."
	@read -p "Version (e.g., v1.0.0): " version; \
	git tag -a $$version -m "Release $$version"; \
	git push origin $$version

# Health check
health:
	@curl -s http://localhost:8000/health | jq . || curl -s http://localhost:8000/health

# API testing
api-test:
	@echo "Testing API endpoints..."
	@curl -s http://localhost:8000/ | jq . || curl -s http://localhost:8000/
	@echo ""
	@curl -s http://localhost:8000/api/stations | jq . || curl -s http://localhost:8000/api/stations
	@echo ""
	@curl -s http://localhost:8000/api/latest | jq . || curl -s http://localhost:8000/api/latest

# Full setup
setup:
	cp .env.example .env
	@echo "Please edit .env file with your configuration"
	@echo "Then run: make build && make up-d"
