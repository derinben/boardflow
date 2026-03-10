# BoardFlow Project Overview

**LLM-powered board game recommendation engine** using natural language queries, content-based filtering, and BGG data.

---

**Core Features:**
- ✅ Boardgamegeek application data ingestion (metadata, stats, rankings)
- ✅ Natural language query parsing (Claude API)
- ✅ Content-based recommendation algorithm with IDF weighting
- ✅ FastAPI REST API
- ✅ Async PostgreSQL with partitioned time-series tables

---

## Quick Start

```bash
# Setup
cp .env.example .env  # Add ANTHROPIC_API_KEY, BGG_API_TOKEN
make setup            # Start DB, run migrations

# Ingest data (incremental - skips existing games)
make ingest-info LIMIT=1000              # Random games (default)
make ingest-info-ranked LIMIT=1000       # Top-ranked games by BGG rank
make ingest-stats                        # Stats for all games

# Compute IDF weights (run after ingestion)
uv run python scripts/compute_idf_weights.py

# Test API
uv run python scripts/test_api.py
```

---

## Architecture

```mermaid
graph TD
    A[User Query] -->|"I like Catan..."| B[FastAPI]
    B --> C[LLMService]
    C -->|Extract Intent| D[Claude API]
    D -->|games, mechanics, prefs| E[RecommendationService]
    E --> F[GameRepository]
    F -->|Load IDF Weights| G[(PostgreSQL)]
    F -->|Fetch Candidates| G
    E -->|Weighted Jaccard| H[Rank Games]
    H --> I[Top N Games]
    I --> C
    C -->|Generate Explanations| D
    D -->|"Because you like..."| J[JSON Response]
```

### Data Flow

1. **Query Extraction** → Claude parses NL query into structured intent
2. **Profile Building** → Aggregate mechanics/categories from user's liked games
3. **Load IDF Weights** → Fetch precomputed weights (rare mechanics boosted)
4. **Candidate Retrieval** → Fetch all games (minimal filters)
5. **Ranking** → Score using weighted Jaccard + preferences + quality + exploration
6. **Explanation** → Claude generates human-readable reasoning

---

## Key Components

| Component | Purpose | Location |
|-----------|---------|----------|
| **Data Ingestion** | BGG XML API → Postgres | `ingestion/` |
| **IDF Service** | Compute TF-IDF weights | `services/idf_service.py` |
| **Recommendation Service** | Orchestrate ranking logic | `services/recommendation_service.py` |
| **LLM Service** | Claude API (extraction + explanations) | `services/llm_service.py` |
| **Game Repository** | Database access layer | `repositories/game_repository.py` |
| **FastAPI** | REST API endpoints | `api/` |
| **Database** | PostgreSQL + partitioned tables | `db/` |

---

## Database Schema

```
bgg.games                  -- Core game metadata
bgg.game_names             -- Alternate names (fuzzy matching)
bgg.mechanics              -- Lookup: mechanics
bgg.categories             -- Lookup: categories
bgg.game_mechanics         -- Junction: game ↔ mechanics
bgg.game_categories        -- Junction: game ↔ categories
bgg.game_stats             -- Time-series: ratings, complexity (partitioned)
bgg.game_ranks             -- Time-series: rankings (partitioned)

-- NEW: IDF Weighting Tables
bgg.mechanic_stats         -- Precomputed IDF weights for mechanics
bgg.category_stats         -- Precomputed IDF weights for categories
```

**Extensions Required:**
- `pg_trgm` (fuzzy text matching)

---

## Recommendation Algorithm

### Scoring Formula

```
Total Score (0-1) = Profile (0.3) + Preference (0.35) + Quality (0.25) + Exploration (0.1)
```

**Profile Similarity (0.3 max):**
- Weighted Jaccard: `sum(IDF_weights × intersection) / sum(IDF_weights × union)`
- Mechanics: 70%, Categories: 30%
- **New:** IDF weights boost rare mechanics (deck building, worker placement) over common ones (dice rolling)

**Preference Alignment (0.35 max):**
- Player count proximity (0.2)
- Complexity proximity (0.15)

**Quality Baseline (0.25 max):**
- Normalized BGG Bayesian average

**Exploration Boost (0.1 max):**
- `(1 - profile_similarity) × weight` to prevent echo chamber

### IDF Weighting Impact

**Example:** Matching rare mechanic "Passed Action Token" (IDF=7.99) vs common "Dice Rolling" (IDF=1.43)
- Rare match contribution: **3.6× higher** than common match
- Result: Games with distinctive mechanics rank higher

---

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/boardflow

# LLM (choose one)
LLM_PROVIDER=anthropic                              # or bedrock
ANTHROPIC_API_KEY=sk-ant-...                        # Native API
BEDROCK_MODEL_ID=anthropic.claude-sonnet-4-5-...   # AWS Bedrock

# BGG Ingestion
BGG_API_TOKEN=your-token-here
BGG_CSV_LOCAL_PATH=./data/boardgames_ranks.csv
BGG_REQUEST_DELAY_SECONDS=2
BGG_NUM_WORKERS=5

# IDF Weighting (NEW)
IDF_ENABLED=true
IDF_SMOOTHING=1.0
```

---

## Scripts

| Script | Purpose | When to Run |
|--------|---------|-------------|
| `scripts/run_ingestion.py` | Ingest BGG data (incremental) | Initial setup + periodic refresh |
| `scripts/compute_idf_weights.py` | **Compute IDF weights** | **After ingestion, monthly refresh** |
| `scripts/verify_idf_implementation.py` | Test IDF implementation | After compute_idf_weights.py |
| `scripts/test_api.py` | Test API recommendations | After starting API server |

**Ingestion Modes:**
- `--mode info` (default) - Ingest game metadata (random or ranked)
- `--mode info --ranked` - Ingest top-ranked games by BGG rank
- `--mode stats` - Fetch stats for existing games

---

## Migrations

```bash
# Run pending migrations
uv run alembic -c db/alembic.ini upgrade head

# Create new migration
uv run alembic -c db/alembic.ini revision -m "description"
```

**Latest:** `20260306_add_idf_stats` - Added mechanic_stats and category_stats tables

---

## Testing

```bash
# Start API server
uv run fastapi dev api/app.py

# Test recommendations
uv run python scripts/test_api.py

# Verify IDF implementation
uv run python scripts/verify_idf_implementation.py
```

**Expected Test Results:**
```
✓ IDF weights loaded: 173 mechanics, 84 categories
✓ Weighted Jaccard correctly boosts rare mechanics (0.4588 vs 0.1257)
✓ IDF disabled mode working (using equal weights)
```

---

## Performance

**Typical Request:** 3-8 seconds
- Intent extraction: 1-2s (Claude API)
- Candidate retrieval + ranking: 0.5-1.5s
- Explanation generation: 1-4s (Claude API, sequential)

**Database:** 5,893 games (as of March 6, 2026)
- 173 unique mechanics
- 84 unique categories

**Bottlenecks:**
1. LLM API calls (2× per request)
2. Candidate retrieval SQL query

**Optimizations:**
- IDF weights cached in memory (one-time load)
- Partitioned time-series tables (game_stats, game_ranks)

---

## Recent Changes

### March 6, 2026: Guaranteed LIMIT via Set-Difference Ingestion

**Ingestion Improvements:**
- **Guaranteed LIMIT**: Set-difference approach ensures exactly LIMIT new games ingested
- **Incremental ingestion**: Loads ALL CSV IDs + ALL DB IDs → computes difference
- **Random sampling (default)**: Better diversity than always top-ranked
- **Ranked mode (--ranked)**: Top-ranked NEW games (not overall)
- **Fixed CSV bug**: Filter out 144K unranked games (rank=0)

**Algorithm:**
1. Load ALL 30K ranked game IDs from CSV
2. Load ALL existing game IDs from DB
3. Compute: new_games = CSV - DB
4. Sample LIMIT from new_games (random or ranked)
5. Ingest via concurrent workers

**Usage:**
```bash
make ingest-info LIMIT=1000              # Random games - guarantees 1000 NEW
make ingest-info-ranked LIMIT=1000       # Top-ranked NEW games - guarantees 1000 NEW
# Both modes guarantee LIMIT (or all remaining if fewer available)
```

**Example:** If DB has 25K games and CSV has 30,210 total:
- Available NEW: 5,210 games
- Request LIMIT=10,000 → logs warning, ingests all 5,210 ✓

### March 6, 2026: TF-IDF Normalization

**Problem:** Common mechanics (dice rolling, hand management) overwhelmed scores

**Solution:** Implemented IDF (Inverse Document Frequency) weighting
- Formula: `IDF = log((N + 1) / (df + 1))`
- Rare mechanics get ~8.0 weight, common ~1.4 weight
- Replaced binary Jaccard with weighted Jaccard

**Impact:**
- Rare mechanic matches score
- More distinctive recommendations
- Backward compatible (falls back to equal weights if disabled)
---

## Contact

**Project:** BoardFlow - Board Game Recommendation Engine
**Developer:** Derin Ben Roberts
**Last Updated:** March 10, 2026
