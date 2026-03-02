.PHONY: setup db-start db-stop db-logs db-create migrate migrate-new ingest-info ingest-stats help

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
	@echo "  ingest-info   Run info pipeline (fetch game metadata)"
	@echo "  ingest-stats  Run stats pipeline (append ratings/ranks snapshot)"

setup: db-start
	uv sync
	@echo "Waiting 3s for postgres to be ready..."
	sleep 3
	$(MAKE) db-create
	$(MAKE) migrate

db-start:
	docker compose up -d
	@echo "PostgreSQL started at localhost:5432"

db-stop:
	docker compose down

db-logs:
	docker compose logs -f db

# Creates the application database using the postgres superuser.
# Safe to run repeatedly — CREATE DATABASE is skipped if it already exists.
db-create:
	psql "postgresql://postgres:postgres@localhost:5432/postgres" \
	  -tc "SELECT 1 FROM pg_database WHERE datname = '$(POSTGRES_DB)'" \
	  | grep -q 1 \
	  || psql "postgresql://postgres:postgres@localhost:5432/postgres" \
	       -c "CREATE DATABASE $(POSTGRES_DB);"
	@echo "Database '$(POSTGRES_DB)' is ready."

migrate:
	uv run alembic -c db/alembic.ini upgrade head

# Usage: make migrate-new MSG="add game tags table"
migrate-new:
	uv run alembic -c db/alembic.ini revision --autogenerate -m "$(MSG)"

ingest-info:
	uv run python scripts/run_ingestion.py --mode info

ingest-stats:
	uv run python scripts/run_ingestion.py --mode stats
