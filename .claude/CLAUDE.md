# Project Rules

## Logging
- ALWAYS use `loguru` for all logging. Never use Python's built-in `logging` module or `print` statements for debugging.
- Import pattern: `from loguru import logger`

## Changelog
- ALWAYS update docs/CHANGELOG.md when making user-facing changes
- ASK for confirmation before writing to docs/CHANGELOG.md — never auto-update it

## Documentation
- Extra docs go ONLY under /docs
- ALWAYS ask user for confirmation before creating or modifying any file under /docs

## Todo List
- Maintain a .todo file in the repo root
- Update it when tasks are completed or new ones identified
- Format: `[ ] task description` / `[x] completed task`

## BGG API
- Rate limit: 5 second delay between requests (`BGG_REQUEST_DELAY_SECONDS` env var)
- No auth required for basic queries
- Max 20 game IDs per `/xmlapi2/thing` request
- Never use `www.boardgamegeek.com` — use `boardgamegeek.com` directly
- 500/503 responses mean throttling — handled automatically via tenacity in `ingestion/client.py`

## Database Schemas
- `bgg` schema: raw ingested data from the API (source of truth — never manually edit rows)
- `features` schema: engineered ML features (deferred — see .todo)
- `bgg.game_stats` and `bgg.game_ranks` are partitioned RANGE tables (by `fetched_at`, monthly)
- Add new monthly partitions when approaching coverage limit — use `make migrate-new`

## Ingestion Pipeline
- `--mode=info`: Upserts game metadata (idempotent, safe to re-run)
- `--mode=stats`: Appends a ratings/ranks snapshot (append-only, preserves history)
- Run info pipeline before stats — stats pipeline reads game IDs from `bgg.games`

## Alembic Workflow
- Create migration: `make migrate-new MSG="description"`
- Apply migrations: `make migrate` (also auto-creates the `boardflow` database if missing)
- All migrations live in `db/versions/`
- Partitioned tables require raw SQL in migrations (SQLAlchemy cannot emit PARTITION BY)

## Dev Environment
- Start everything: `make setup` (install deps + start DB + run migrations)
- Start DB only: `make db-start`
- Run ingestion: `make ingest-info` / `make ingest-stats`

## General Behavior
- Always prepare a plan before starting a task
- Ask the user for any clarifications about the provided requirements and make sure to over-engineer them.
- Keep the code base clean, readable, modular, and well-documented
- Suggest claude skills to be created if we are repeating the same task over and over again
- When making code edits, check for what other docs are to be edited in the /docs to reflect the changes instead of creating new ones.