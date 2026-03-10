# BoardFlow

**LLM-powered board game recommendation engine** using content-based filtering with IDF weighting, and BoardGameGeek data. Natural language queries → personalized game suggestions with explanations.

**Tech Stack:** Python, FastAPI, PostgreSQL, React/TypeScript, Anthropic Claude API (or AWS Bedrock), async ingestion pipeline.

---

## Why did I build this?
Just for fun. I am a board game enthusiast and wanted to see if I can create a personalized experience while selecting my next boardgame.

## What It Does

- A lil bit of Data Engineering - Fetches board game data from BoardGameGeek XML API -> ingests into a local pgdb
- A lil bit of AI Engineering - Understand user's query and fetches a suitable list of boardgames with an explanation as to why you may like it. <br>
This project currently employs a barebones version of a recommendation model that I can consider to be the baseline. 


### Core Stuff

**Data Ingestion Pipeline:**
- Fetches board game metadata from BoardGameGeek XML API
- Two modes: **Random sampling** (diversity) or **Ranked mode** (top-rated games first)
- Async/concurrent workers with rate limiting (10× faster than sequential)
- Incremental ingestion (skips existing games, guarantees exact LIMIT)
- Stores in PostgreSQL with partitioned time-series tables

**AI-Powered Recommendations:**
- **LLM Providers**: Anthropic Claude API (native) or AWS Bedrock
- Natural language query parsing via Claude (extracts preferences, liked games)
- Content-based filtering with **IDF weighting** (rare mechanics score higher)
- 4-component scoring: Profile similarity (30%), Preferences (35%), Quality (25%), Exploration (10%)
- Claude generates human-readable explanations for each recommendation

**Web Interface:**
- React + TypeScript frontend with natural language search
- Client-side filtering (complexity, player count, mechanics, categories)
- Game comparison and side-by-side views
- Responsive design (mobile/tablet/desktop) 

## How It Works

**Data Pipeline:**
```
BGG CSV Rankings (30K games) → Filter by rank → PostgreSQL (game IDs)
    ↓
BGG XML API → Batch fetch (20 games/request) → Parse & validate
    ↓
PostgreSQL (bgg schema) → Game metadata, mechanics, categories, stats
    ↓
IDF Computation → Mechanic/category importance weights
```

**Recommendation Flow:**
```
User Query ("I like Catan, want trading mechanics")
    ↓
Claude API → Extract: liked games, preferred mechanics, player count, complexity
    ↓
Build Profile → Aggregate mechanics/categories from liked games (weighted by IDF)
    ↓
Candidate Retrieval → Fetch all games from PostgreSQL
    ↓
Scoring Algorithm → Profile similarity + Preferences + Quality + Exploration
    ↓
Top 10 Games → Claude API generates explanations for each
    ↓
JSON Response → Frontend displays cards with scores and reasoning
```

## What Can You Do?

- **Run the app**: Follow setup below to get personalized game recommendations
- **Analyze data**: Explore multitude of board games, mechanics, categories
- **Improve recommendations**: Experiment with scoring weights, new features etc
- **Contribute**: See [PROJECT.md](PROJECT.md) for technical details and recent changes

#### Roll up your sleeves if you wish to proceed further.

## Prerequisites

**Required:**
- **Docker** - For PostgreSQL database - [Install Docker](https://docs.docker.com/get-docker/)
- **Python 3.12+** with [uv](https://github.com/astral-sh/uv) - Python package manager
- **BGG CSV Dump** - Game rankings from BoardGameGeek - [Download CSV](https://boardgamegeek.com/data_dumps/bg_ranks)
- **BGG API Token** - For fetching game metadata - Contact BGG or check their API docs
- **Anthropic API Key** - For Claude AI recommendations - [Get key](https://console.anthropic.com/) (or use AWS Bedrock)

**Optional:**
- **Direnv** - Auto-load environment variables - [Install direnv](https://direnv.net/docs/installation.html)
- **Beekeeper Studio** - Visual DB client for exploring data - [Download](https://www.beekeeperstudio.io/) 

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
uv run python -m ingestion.client
```

### Ingest Game Metadata

**Two Ingestion Modes:**

**1. Random Mode (Default)** - Better for catalog diversity
```bash
make ingest-info LIMIT=100
```
Samples randomly from 30K ranked games. Best for exploring the full catalog, not just top-rated games.

**2. Ranked Mode** - Best for quality-first approach
```bash
make ingest-info-ranked LIMIT=100
```
Ingests top-ranked NEW games first (sorted by BGG rank). Best for starting with highest-rated games.

**Or use default limit from .env (1000 games):**
```bash
make ingest-info
```

**How it works:**
- Set-difference algorithm: Loads ALL CSV game IDs and ALL DB game IDs → computes difference → samples exactly LIMIT new games
- **Guarantees** exactly LIMIT new games (or all remaining if fewer available)
- No wasted API calls on duplicate games

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

**What it does:** Calculates importance weights for mechanics and categories. Rare mechanics (e.g., "Worker Placement") get higher weights than common ones (e.g., "Dice Rolling"), leading to more distinctive recommendations.

```bash
# Run after ingestion to enable weighted recommendations
uv run python scripts/compute_idf_weights.py

# Verify implementation (checks that rare mechanics score higher)
uv run python scripts/verify_idf_implementation.py
```

**When to run:** After initial ingestion, then monthly when you add significant numbers of new games.

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
# Start API server (development mode with hot reload)
make api-dev
# Or manually: uv run uvicorn api.main:app --reload

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

### LLM Provider Setup

**Choose one:**

**Option 1: Anthropic Claude API**
```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```
Get your API key at: https://console.anthropic.com/

**Option 2: AWS Bedrock**
```bash
LLM_PROVIDER=bedrock
BEDROCK_MODEL_ID=anthropic.claude-sonnet-4-5-20241022-v2:0
AWS_REGION=us-east-1
AWS_PROFILE=your-profile  # Or use IAM role
```
Requires AWS credentials configured (via `aws configure` or IAM role).

### All Environment Variables

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
We need this detailed because the BGG XML api has rate limits. 

The pipeline uses **async/await with 5 concurrent workers** by default:
- **Request delay**: 2 seconds per worker (configurable via `BGG_REQUEST_DELAY_SECONDS`)
- **Workers**: 5 concurrent workers (configurable via `BGG_NUM_WORKERS`)
- **Global cooldown**: If any worker hits rate limits (HTTP 429/503), all workers pause for 5 seconds
- **Performance**: ~10× faster than sequential processing (1000 games in ~30s vs 4 minutes)

Adjust `BGG_NUM_WORKERS` and `BGG_REQUEST_DELAY_SECONDS` based on your needs:
- More aggressive: `BGG_NUM_WORKERS=5 BGG_REQUEST_DELAY_SECONDS=2`
- Conservative: `BGG_NUM_WORKERS=3 BGG_REQUEST_DELAY_SECONDS=3`

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
make api-dev
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
