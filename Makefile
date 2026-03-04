.PHONY: setup db-start db-stop db-logs db-create migrate migrate-new ingest-info ingest-stats api-dev api-prod help

# Load .env so DATABASE_URL and POSTGRES_DB are available in this Makefile.
-include .env
export

# Default target
help:
	@echo "boardflow dev commands:"
	@echo "  setup         Install deps, start DB, create DB, run migrations"
	@echo "  db-start      Start PostgreSQL container"
	@echo "  db-stop       Stop and remove PostgreSQL container"
	@echo "  db-logs       Tail PostgreSQL container logs"
	@echo "  db-create     Create the $(POSTGRES_DB) database if it doesn't exist"
	@echo "  migrate       Run all pending Alembic migrations"
	@echo "  migrate-new   Create a new Alembic migration (set MSG= to name it)"
	@echo "  ingest-info   Run info pipeline (set LIMIT=N to override default)"
	@echo "  ingest-stats  Run stats pipeline (set LIMIT=N to cap number of games)"
	@echo "  api-dev       Run FastAPI server in development mode (hot reload)"
	@echo "  api-prod      Run FastAPI server in production mode"

setup: db-start
	uv sync
	@echo "Waiting 3s for postgres to be ready..."
	sleep 3
	$(MAKE) db-create
	$(MAKE) migrate

db-start:
	docker compose up -d
	@echo "PostgreSQL started at localhost:5442"

db-stop:
	docker compose down

db-logs:
	docker compose logs -f db

# Creates the application database using the postgres superuser.
# Safe to run repeatedly — CREATE DATABASE is skipped if it already exists.
db-create:
	@psql "postgresql://postgres:postgres@localhost:5442/postgres" \
	  -tc "SELECT 1 FROM pg_database WHERE datname = '$(POSTGRES_DB)'" \
	| grep -q 1 \
	|| psql "postgresql://postgres:postgres@localhost:5442/postgres" \
	     -c "CREATE DATABASE \"$(POSTGRES_DB)\";"
	@echo "Database '$(POSTGRES_DB)' is ready."

migrate:
	uv run alembic -c db/alembic.ini upgrade head

# Usage: make migrate-new MSG="add game tags table"
migrate-new:
	uv run alembic -c db/alembic.ini revision --autogenerate -m "$(MSG)"

# Usage: make ingest-info LIMIT=100
ingest-info:
ifdef LIMIT
	uv run python scripts/run_ingestion.py --mode info --limit $(LIMIT)
else
	uv run python scripts/run_ingestion.py --mode info
endif

# Usage: make ingest-stats LIMIT=100
ingest-stats:
ifdef LIMIT
	uv run python scripts/run_ingestion.py --mode stats --limit $(LIMIT)
else
	uv run python scripts/run_ingestion.py --mode stats
endif

# API development server with hot reload
api-dev:
	uv run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# API production server
api-prod:
	uv run uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
