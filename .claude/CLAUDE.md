# Project Rules

## Logging
- ALWAYS use `loguru` for all logging. Never use Python's built-in `logging` module or `print` statements for debugging.
- Import pattern: `from loguru import logger`

## Documentation
- Extra docs go ONLY under /docs
- ALWAYS ask user for confirmation before creating or modifying any file under /docs

## Todo List
- Maintain a .todo file in the repo root
- Update it when tasks are completed or new ones identified
- Format: `[ ] task description` / `[x] completed task`

## BGG API
- Rate limit: 5 second delay between requests (`BGG_REQUEST_DELAY_SECONDS` env var)
- Authentication: Requires bearer token via `BGG_API_TOKEN` env var
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
  - CSV source priority: `BGG_CSV_LOCAL_PATH` (if set) takes precedence over `BGG_CSV_DUMP_URL`
  - Fails fast if local path is configured but file doesn't exist (no fallback to remote URL)
  - Local files are validated for freshness (warns if older than `BGG_CSV_MAX_AGE_HOURS`, default: 24 hours)
  - Logs which source is used (LOCAL vs REMOTE) for audit trail
- `--mode=stats`: Appends a ratings/ranks snapshot (append-only, preserves history)
  - Smart refresh: only fetches stats for games where last snapshot is older than `BGG_STATS_MAX_AGE_DAYS` (default: 7 days)
  - Skips games with recent stats to minimize API calls
  - Always fetches stats for games that have never had stats before
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
- At the end of a session, figure out whether an existing doc needs to be updated and if there is too much of divergent changes, create a new file.