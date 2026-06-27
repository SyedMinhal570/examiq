# Makefile — type 'make dev' to start everything
.PHONY: dev test lint deploy

dev:          ## Start all local services
	docker compose up -d
	uvicorn src.api.main:app --reload --port 8000

test:         ## Run all tests
	uv run pytest tests/ -v --cov=src

lint:         ## Check code quality
	uv run ruff check src/ tests/
	uv run mypy src/ --ignore-missing-imports

migrate:      ## Run database migrations
	uv run alembic upgrade head

seed:         ## Seed demo exam items
	uv run python scripts/seed_items.py

deploy:       ## Deploy to Fly.io
	flyctl deploy

docker-build: ## Build Docker image
	docker build -t examiq:latest .

clean:        ## Stop and remove containers
	docker compose down -v