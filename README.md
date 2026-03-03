# BoardFlow

BGG (BoardGameGeek) data ingestion pipeline for board game metadata, ratings, and rankings.

## What It Does

- Fetches board game data from BoardGameGeek XML API
- Stores game metadata (names, categories, mechanics, designers, publishers)
- Tracks ratings and rankings over time (append-only history)
- Smart refresh: only updates stale stats

## Prerequisites

- **Docker** - [Install Docker](https://docs.docker.com/get-docker/)
- **Python 3.11+** with [uv](https://github.com/astral-sh/uv)
- **BGG API Token** - Required for API access

## Quick Start

```bash
# 1. Clone and setup environment
git clone <repo-url>
cd boardflow
cp .env.example .env

# 2. Edit .env - Add your BGG_API_TOKEN and set BGG_CSV_LOCAL_PATH
# BGG_API_TOKEN=your-token-here
# BGG_CSV_LOCAL_PATH=./data/boardgames_ranks.csv

# 3. Download BGG CSV rankings (manual step - see below)
mkdir -p data
# Download from https://boardgamegeek.com/data_dumps/bg_ranks
# Save as: ./data/boardgames_ranks.csv

# 4. Start everything
make setup
```

That's it! Database is running, migrations applied, ready to ingest.

## Common Tasks

### Test API Connection
```bash
python -m ingestion.client
```

### Ingest Game Metadata
```bash
# Start small (recommended for first run)
make ingest-info LIMIT=100

# Or use default limit from .env (1000 games)
make ingest-info
```

### Fetch Game Stats
```bash
# Fetches stats for games missing stats or older than 7 days
make ingest-stats

# Limit to top 100 stale games
make ingest-stats LIMIT=100
```

### Database Management
```bash
make db-start       # Start Postgres
make db-stop        # Stop Postgres
make db-logs        # View logs
make migrate        # Run migrations
```

## Usage Scenarios

### Scenario 1: Initial Setup
```bash
make ingest-info LIMIT=500    # Add 500 games
make ingest-stats             # Fetch stats for all 500
```

### Scenario 2: Add More Games
```bash
make ingest-info LIMIT=1000   # Now 1000 games total
make ingest-stats             # Fetches stats for 500 new games only
                              # (skips existing 500 - too recent)
```

### Scenario 3: Weekly Refresh
```bash
# After 7+ days
make ingest-stats             # Refreshes all games > 7 days old
```

### Scenario 4: Daily Active Monitoring
```bash
# Set BGG_STATS_MAX_AGE_DAYS=1 in .env
make ingest-stats LIMIT=100   # Refresh top 100 daily
```

## Configuration

All settings in `.env`:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BGG_API_TOKEN` | Yes | - | Bearer token for BGG API |
| `BGG_CSV_LOCAL_PATH` | Yes* | - | Path to local CSV file |
| `BGG_CSV_DUMP_URL` | Yes* | - | URL to download CSV (fallback) |
| `BGG_STATS_MAX_AGE_DAYS` | No | 7 | Only refresh stats older than this |
| `BGG_INGEST_LIMIT` | No | 1000 | Default number of games to ingest |
| `DATABASE_URL` | No | (auto) | PostgreSQL connection string |

\* At least one CSV source required

## Architecture

```
BGG CSV → ingestion/csv_seed.py → Game IDs
    ↓
BGG API → ingestion/client.py → XML
    ↓
ingestion/transform.py → Validated Models
    ↓
ingestion/load.py → Postgres (bgg schema)
```

### Database Schema

- `bgg.games` - Core game records
- `bgg.game_names` - All name variants
- `bgg.categories`, `bgg.mechanics`, `bgg.designers`, etc. - Lookup tables
- `bgg.game_stats` - Ratings/ownership snapshots (partitioned by month)
- `bgg.game_ranks` - Ranking snapshots (partitioned by month)

## Troubleshooting

**Error: BGG_API_TOKEN not set**
- Add your token to `.env`: `BGG_API_TOKEN=your-token-here`

**Error: CSV file not found**
- Download manually: https://boardgamegeek.com/data_dumps/bg_ranks
- Save to path in `BGG_CSV_LOCAL_PATH` (default: `./data/boardgames_ranks.csv`)

**Warning: CSV file is X hours old**
- Re-download the CSV if you need fresh rankings
- Or increase `BGG_CSV_MAX_AGE_HOURS` in `.env`

**No games need stats refresh**
- All stats are up to date (< 7 days old)
- Lower `BGG_STATS_MAX_AGE_DAYS` to force refresh

