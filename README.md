# BoardFlow

## Why Am I Doing This?
Just for fun. I am a board game enthusiast and wanted to see if I can create a personalized experience while selecting my next boardgame.

## What It Does

- A lil bit of Data Engineering - Fetches board game data from BoardGameGeek XML API -> ingests into a local pgdb
- A lil bit of AI Engineering - Understand user's query and fetches a suitable list of boardgames with an explanation as to why you may like it. <br>
This project currently employs a barebones version of a recommendation model that I can consider to be the baseline. 

## What can you do with this repo?
If you are a fellow geek, feel free to run through the steps below to run this application, do some analytics on the boardgame data to see if we can get any funny insights and/or let me know how we can improve the recommendations logic. 

For more project related changes and details, refer to - [PROJECT.md](PROJECT.md)

#### Roll up your sleeves if you wish you proceed further.

## Prerequisites

- **Docker** - [Install Docker](https://docs.docker.com/get-docker/)
- **Direnv** - [Install direnv](https://direnv.net/docs/installation.html)
- **Python 3.12+** with [uv](https://github.com/astral-sh/uv)
- **CSV Dump** of BGG stored under `/data` - [BGG Data Dump](https://boardgamegeek.com/data_dumps/bg_ranks)
- **Beekeeper Studio** (Optional) - To view the tables and query around with a nice UI - [Beekeeper Studio
](https://www.beekeeperstudio.io/)
- **BGG API Token** - Required for API access 

## Quick Start

```bash
# 1. Clone and setup environment
git clone <repo-url>
cd boardflow
cp .env.example .env

# 2. Edit .env - Configure required variables (see Configuration section below)
# ANTHROPIC_API_KEY=sk-ant-...          # For Claude API
# BGG_API_TOKEN=your-token-here         # For BGG API
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
# Ingest random games (default, incremental - guarantees LIMIT)
make ingest-info LIMIT=100

# Ingest top-ranked NEW games (sorted by BGG rank - guarantees LIMIT)
make ingest-info-ranked LIMIT=100

# Or use default limit from .env (1000 games)
make ingest-info
```

**Note:** Both modes **guarantee** exactly LIMIT new games (or all remaining if fewer available). Uses set-difference to ensure no wasted API calls.

**Alternative:** Run ingestion script directly:
```bash
uv run python scripts/run_ingestion.py --mode info --limit 1000
uv run python scripts/run_ingestion.py --mode info --limit 1000 --ranked
uv run python scripts/run_ingestion.py --mode stats
```

### Fetch Game Stats
```bash
# Fetches stats for games missing stats or older than 7 days
make ingest-stats

# Limit to top 100 stale games
make ingest-stats LIMIT=100
```

### Compute IDF Weights
```bash
# Run after ingestion to enable weighted recommendations
uv run python scripts/compute_idf_weights.py

# Verify implementation
uv run python scripts/verify_idf_implementation.py
```

### Database Management
```bash
make db-start       # Start Postgres
make db-stop        # Stop Postgres
make db-logs        # View logs
make migrate        # Run migrations
```

**Manual migrations:**
```bash
# Run pending migrations
uv run alembic -c db/alembic.ini upgrade head

# Create new migration
uv run alembic -c db/alembic.ini revision -m "description"
```

### Testing
```bash
# Start API server
uv run fastapi dev api/app.py

# Test recommendations
uv run python scripts/test_api.py

# Verify IDF implementation
uv run python scripts/verify_idf_implementation.py
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
| `DATABASE_URL` | No | `postgresql://postgres:postgres@localhost:5432/boardflow` | PostgreSQL connection string |
| `LLM_PROVIDER` | No | anthropic | LLM provider: `anthropic` or `bedrock` |
| `ANTHROPIC_API_KEY` | Yes* | - | Claude API key (native API) |
| `BEDROCK_MODEL_ID` | Yes* | - | AWS Bedrock model ID (e.g., `anthropic.claude-sonnet-4-5-...`) |
| `BGG_API_TOKEN` | Yes | - | Bearer token for BGG API |
| `BGG_CSV_LOCAL_PATH` | Yes** | - | Path to local CSV file |
| `BGG_CSV_DUMP_URL` | Yes** | - | URL to download CSV (fallback) |
| `BGG_REQUEST_DELAY_SECONDS` | No | 2 | Delay between requests per worker |
| `BGG_NUM_WORKERS` | No | 5 | Number of concurrent workers |
| `BGG_STATS_MAX_AGE_DAYS` | No | 7 | Only refresh stats older than this |
| `BGG_INGEST_LIMIT` | No | 1000 | Default number of games to ingest |
| `IDF_ENABLED` | No | true | Enable IDF weighting for recommendations |
| `IDF_SMOOTHING` | No | 1.0 | Smoothing factor for IDF calculation |

\* Required based on `LLM_PROVIDER` choice
\** At least one CSV source required

### Concurrency & Performance

The pipeline uses **async/await with 5 concurrent workers** by default:
- **Request delay**: 2 seconds per worker (configurable via `BGG_REQUEST_DELAY_SECONDS`)
- **Workers**: 5 concurrent workers (configurable via `BGG_NUM_WORKERS`)
- **Global cooldown**: If any worker hits rate limits (HTTP 429/503), all workers pause for 5 seconds
- **Performance**: ~10× faster than sequential processing (1000 games in ~30s vs 4 minutes)

Adjust `BGG_NUM_WORKERS` and `BGG_REQUEST_DELAY_SECONDS` based on your needs:
- More aggressive: `BGG_NUM_WORKERS=5 BGG_REQUEST_DELAY_SECONDS=2`
- Conservative: `BGG_NUM_WORKERS=3 BGG_REQUEST_DELAY_SECONDS=3`

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

## Frontend - BoardFlow Web App

React + TypeScript web interface for discovering board games through natural language queries.

### Features
- Natural language search ("I like Catan, want something with trading")
- Card-based game display with thumbnails, scores, explanations
- Client-side filtering (complexity, player count, mechanics, categories)
- Game comparison (side-by-side table)
- Responsive design (mobile, tablet, desktop)

### Setup

```bash
cd frontend
npm install
```

### Development

**Two terminals required:**

```bash
# Terminal 1 - Backend API
cd /path/to/boardflow
uvicorn api.main:app --reload
# Runs on http://localhost:8000

# Terminal 2 - Frontend Dev Server
cd frontend
npm run dev
# Runs on http://localhost:5173
```

Open http://localhost:5173 in your browser.

**How it works:**
- Vite dev server proxies `/api/*` requests to backend (port 8000)
- Hot module reload - changes appear instantly
- Backend must be running for searches to work

### Production Build 

```bash
cd frontend
npm run build
```

Creates `frontend/dist/` with static files. Backend serves these in production via FastAPI's `StaticFiles`.

### Learn More
I am by no means a frontend developer but Claude Code here is helping out a brother. But to have some context on what's happening,
check out `frontend/FRONTEND_GUIDE.md` for:
- Component architecture explanation
- State flow diagrams
- How React/Chakra UI work together
- Debugging tips for beginners

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

**Frontend: API requests failing**
- Ensure backend is running on port 8000
- Check Vite proxy config in `frontend/vite.config.ts`
- Open browser console for error details
