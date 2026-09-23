.PHONY: help install dev frontend test test-unit test-integration lint format docker-up docker-down docker-build docker-logs clean migrate

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install all Python dependencies
	pip install -r requirements.txt

dev: ## Run the backend API in development mode with hot reload
	uvicorn backend.api.app:app --reload --host 0.0.0.0 --port 8000

frontend: ## Run the Streamlit frontend
	streamlit run frontend/app.py --server.port 8501

test: ## Run the full test suite with coverage
	pytest backend/tests/ -v --cov=backend --cov-report=term-missing

test-unit: ## Run unit tests only
	pytest backend/tests/unit/ -v

test-integration: ## Run integration tests only
	pytest backend/tests/integration/ -v

lint: ## Run code linting with ruff
	ruff check backend/ frontend/

format: ## Auto-format code with ruff
	ruff format backend/ frontend/

docker-up: ## Start all services via Docker Compose
	docker-compose up -d

docker-down: ## Stop all Docker Compose services
	docker-compose down

docker-build: ## Build all Docker images
	docker-compose build

docker-logs: ## Tail logs from all containers
	docker-compose logs -f

clean: ## Remove caches, compiled files, and volumes
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	find . -type f -name "*.pyc" -delete 2>/dev/null; true
	rm -rf .pytest_cache htmlcov .coverage 2>/dev/null; true

migrate: ## Run Alembic database migrations
	alembic upgrade head
