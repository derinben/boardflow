# BGG Ingestion Pipeline Guide

Comprehensive guide for the BoardFlow BGG data ingestion system.

## Overview

BoardFlow ingests board game data from BoardGameGeek (BGG) in two stages:

1. **Info Pipeline** (`--mode=info`) - Fetches game metadata (names, descriptions, mechanics, etc.)
2. **Stats Pipeline** (`--mode=stats`) - Fetches ratings, ranks, and statistics snapshots

## Table of Contents

- [CSV Seeding Strategy](#csv-seeding-strategy)
- [Source Priority Logic](#source-priority-logic)
- [Freshness Validation](#freshness-validation)
- [Pipeline Modes](#pipeline-modes)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Migration Guide](#migration-guide)

---

## CSV Seeding Strategy

### Why CSV First?

The info pipeline needs a list of game IDs to fetch from the BGG API. The most efficient approach is to seed from BGG's ranked games CSV dump, which provides:

- **Quality-ordered list**: Top-ranked games first
- **Single source**: No need to paginate or search
- **Efficient batching**: Process top N games in one pass

### CSV Format

Expected CSV structure (from `boardgamegeek.com/data_dumps/bg_ranks`):

```csv
id,name,yearpublished,rank,bayesaverage,average,usersrated,is_expansion,...
224517,"Brass: Birmingham",2018,1,8.39523,8.56737,57074,0,...
342942,"Ark Nova",2021,2,8.35487,8.54133,59432,0,...
```

**Key columns used**:
- `id` - BGG game ID (primary key)
- `rank` - Overall board game rank (used for sorting/limiting)

---

## Source Priority Logic

### Configuration Priority

The system supports two CSV sources with strict priority:

```
BGG_CSV_LOCAL_PATH (if set) > BGG_CSV_DUMP_URL (fallback)
```

**Priority rules**:
1. If `BGG_CSV_LOCAL_PATH` is set → Use local file (ignore remote URL)
2. If `BGG_CSV_LOCAL_PATH` is unset → Use `BGG_CSV_DUMP_URL`
3. If both are unset → **ERROR**: Pipeline cannot proceed

### Why This Design?

- **Explicit control**: When you set local path, you want to use that specific file
- **Fail-fast**: No silent fallbacks that might use stale remote data
- **Audit trail**: Logs clearly show which source was used

### Example Configuration

**Scenario 1: Using local file (recommended)**
```bash
# .env
BGG_CSV_LOCAL_PATH=./data/boardgames_ranks.csv
BGG_CSV_DUMP_URL=https://boardgamegeek.com/data_dumps/bg_ranks  # Ignored
```

**Scenario 2: Using remote URL**
```bash
# .env
# BGG_CSV_LOCAL_PATH=  # Commented out or unset
BGG_CSV_DUMP_URL=https://boardgamegeek.com/data_dumps/bg_ranks
```

---

## Freshness Validation

### What It Does

When using a local CSV file, the system validates file age and warns if stale.

### Configuration

```bash
BGG_CSV_MAX_AGE_HOURS=24  # Default: 24 hours
```

### Validation Behavior

```python
# Example log output

# File is fresh (< 24 hours old)
INFO: CSV file age: 2.5 hours (last modified: 2026-03-03 11:00:00)

# File is stale (> 24 hours old)
INFO: CSV file age: 36.2 hours (last modified: 2026-03-01 15:00:00)
WARNING: ⚠️  CSV file is 36.2 hours old (threshold: 24.0 hours) - consider refreshing
```

**Important**: Warnings do not stop the pipeline. The file is still used for ingestion.

### Why Validate Freshness?

BGG rankings change daily. Using stale data means:
- Missing newly-ranked games
- Outdated rank ordering
- Potential gaps in historical stats

**Recommendation**: Re-download CSV dumps weekly for production, daily for active development.

---

## Pipeline Modes

### Info Mode (`--mode=info`)

**Purpose**: Fetch and upsert game metadata

**Workflow**:
1. Load game IDs from CSV (sorted by rank)
2. Fetch game metadata from BGG API in batches of 20
3. Parse XML responses into structured models
4. Upsert into `bgg.games` and related tables

**Usage**:
```bash
# Via Makefile
make ingest-info

# Direct invocation with custom limit
uv run python scripts/run_ingestion.py --mode info --limit 5000
```

**Characteristics**:
- **Idempotent**: Safe to re-run; existing games are updated
- **Rate-limited**: 5-second delay between batches (configurable via `BGG_REQUEST_DELAY_SECONDS`)
- **Batch size**: 20 games per API request (BGG hard limit)

**Database writes**:
- `bgg.games` - Core game records (upserted)
- `bgg.game_names` - All name variants (deleted + re-inserted per game)
- `bgg.categories`, `bgg.mechanics`, `bgg.designers`, etc. - Lookup tables (upserted)
- Junction tables - Game relationships (upserted)

### Stats Mode (`--mode=stats`)

**Purpose**: Append a ratings/ranks snapshot for games with stale or missing stats

**Workflow**:
1. Query game IDs from `bgg.games` where:
   - Last stats snapshot is older than `BGG_STATS_MAX_AGE_DAYS` (default: 7 days), OR
   - Game has never had stats fetched
2. Fetch stats from BGG API in batches of 20
3. Parse ratings and ranks from XML
4. Insert into partitioned `bgg.game_stats` and `bgg.game_ranks` tables

**Usage**:
```bash
# Via Makefile (refreshes games with stats older than 7 days)
make ingest-stats

# With custom limit (refresh only first 100 stale games)
make ingest-stats LIMIT=100

# Direct invocation
uv run python scripts/run_ingestion.py --mode stats
```

**Characteristics**:
- **Smart refresh**: Only fetches stats for games with missing or outdated stats
- **Append-only**: Never updates; preserves full history
- **Requires info first**: Reads game IDs from `bgg.games`
- **Partitioned**: Data stored in monthly partitions by `fetched_at`
- **Configurable staleness**: Set `BGG_STATS_MAX_AGE_DAYS` to control refresh threshold

**Database writes**:
- `bgg.game_stats` - Aggregate statistics per game (appended)
- `bgg.game_ranks` - Per-category ranks per game (appended)

**Example scenarios**:
- Initial run: Fetches stats for all games (none have stats yet)
- 3 days later: Skips all games (all stats are < 7 days old)
- 8 days later: Refreshes all games (all stats are > 7 days old)
- After adding new games via `--mode=info`: Fetches stats for new games only

---

## Configuration

### Environment Variables

All configuration is managed via `.env`:

```bash
# PostgreSQL
DATABASE_URL=postgresql://postgres:postgres@localhost:5440/boardflow
POSTGRES_DB=boardflow

# BGG API
BGG_BASE_URL=https://boardgamegeek.com/xmlapi2
BGG_REQUEST_DELAY_SECONDS=5
BGG_INGEST_LIMIT=1000
BGG_STATS_MAX_AGE_DAYS=7

# BGG API authentication
BGG_API_TOKEN=your-token-here

# CSV Seeding (Priority: LOCAL > REMOTE)
BGG_CSV_DUMP_URL=https://boardgamegeek.com/data_dumps/bg_ranks
BGG_CSV_LOCAL_PATH=./data/boardgames_ranks.csv
BGG_CSV_MAX_AGE_HOURS=24
```

### Key Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | PostgreSQL connection string |
| `BGG_BASE_URL` | No | `https://boardgamegeek.com/xmlapi2` | BGG API base URL |
| `BGG_REQUEST_DELAY_SECONDS` | No | `5` | Delay between API requests (rate limiting) |
| `BGG_INGEST_LIMIT` | No | `1000` | Default number of games to ingest |
| `BGG_STATS_MAX_AGE_DAYS` | No | `7` | Only refresh stats older than this (in days) |
| `BGG_API_TOKEN` | Yes | - | Bearer token for BGG API authentication |
| `BGG_CSV_DUMP_URL` | Conditional* | - | Remote CSV URL (required if local path unset) |
| `BGG_CSV_LOCAL_PATH` | Conditional* | - | Local CSV file path (takes priority if set) |
| `BGG_CSV_MAX_AGE_HOURS` | No | `24` | Warn threshold for stale local files |

\* At least one CSV source (local or remote) must be configured.

---

## Troubleshooting

### Error: "Either BGG_CSV_LOCAL_PATH or BGG_CSV_DUMP_URL must be set"

**Cause**: Neither CSV source is configured in `.env`

**Solution**:
```bash
# Option 1: Use local file (recommended)
BGG_CSV_LOCAL_PATH=./data/boardgames_ranks.csv

# Option 2: Use remote URL
BGG_CSV_DUMP_URL=https://boardgamegeek.com/data_dumps/bg_ranks
```

### Error: "BGG_CSV_LOCAL_PATH is set but file does not exist"

**Cause**: `BGG_CSV_LOCAL_PATH` points to a missing file

**Solution**:
1. Download the CSV manually from BGG
2. Place it at the configured path
3. Or comment out `BGG_CSV_LOCAL_PATH` to use remote URL

```bash
# Download CSV dump
wget https://boardgamegeek.com/data_dumps/bg_ranks -O data/boardgames_ranks.csv

# Or fallback to remote
# BGG_CSV_LOCAL_PATH=  # Comment out
BGG_CSV_DUMP_URL=https://boardgamegeek.com/data_dumps/bg_ranks
```

### Warning: "CSV file is X hours old"

**Cause**: Local CSV file hasn't been updated recently

**Impact**: Non-blocking; pipeline continues with stale data

**Solution** (if data freshness is critical):
```bash
# Re-download the CSV
wget https://boardgamegeek.com/data_dumps/bg_ranks \
  -O data/boardgames_ranks.csv

# Or increase threshold
BGG_CSV_MAX_AGE_HOURS=168  # 1 week tolerance
```

### Error: "No games found in bgg.games"

**Cause**: Running `--mode=stats` before `--mode=info`

**Solution**: Run info pipeline first
```bash
make ingest-info  # Run first
make ingest-stats # Then run stats
```

### Error: "429 Too Many Requests" or "503 Service Unavailable"

**Cause**: BGG rate limiting triggered

**Behavior**: Automatic retry with exponential backoff (up to 5 attempts)

**Solution** (if persistent):
```bash
# Increase delay between requests
BGG_REQUEST_DELAY_SECONDS=10  # Default is 5
```

### Error: "No partition for fetched_at"

**Cause**: Stats data falls outside existing monthly partitions

**Solution**: Create new partition via migration
```bash
make migrate-new MSG="add game_stats partition for 2026-04"
```

Then manually edit the migration to add partition:
```sql
CREATE TABLE IF NOT EXISTS bgg.game_stats_2026_04
PARTITION OF bgg.game_stats
FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
```

---

## Migration Guide

### From Remote URL to Local File

**Before** (using remote URL):
```bash
# .env
BGG_CSV_DUMP_URL=https://boardgamegeek.com/data_dumps/bg_ranks
```

**Migration steps**:

1. Download the CSV dump manually:
   ```bash
   mkdir -p data
   wget https://boardgamegeek.com/data_dumps/bg_ranks \
     -O data/boardgames_ranks.csv
   ```

2. Update `.env`:
   ```bash
   # Add local path (takes priority)
   BGG_CSV_LOCAL_PATH=./data/boardgames_ranks.csv

   # Remote URL is now ignored but can stay for reference
   BGG_CSV_DUMP_URL=https://boardgamegeek.com/data_dumps/bg_ranks
   ```

3. Test ingestion:
   ```bash
   make ingest-info
   # Check logs for: "CSV source: LOCAL (priority) - ./data/boardgames_ranks.csv"
   ```

### Updating Stale Local CSV

**Recommended workflow**:

```bash
# 1. Backup old CSV (optional)
cp data/boardgames_ranks.csv data/boardgames_ranks.csv.bak

# 2. Download fresh CSV
wget https://boardgamegeek.com/data_dumps/bg_ranks \
  -O data/boardgames_ranks.csv

# 3. Verify freshness
ls -lh data/boardgames_ranks.csv

# 4. Re-run info pipeline (idempotent, safe)
make ingest-info
```

**Automation option** (cron job for weekly refresh):
```bash
# Add to crontab
0 2 * * 0 cd /path/to/boardflow && wget -q https://boardgamegeek.com/data_dumps/bg_ranks -O data/boardgames_ranks.csv
```

---

## Best Practices

### Development Workflow

1. **Initial setup**: Use local CSV with top 1000 games
   ```bash
   BGG_CSV_LOCAL_PATH=./data/boardgames_ranks.csv
   BGG_INGEST_LIMIT=1000
   ```

2. **Test quickly**: Limit to top 100 games
   ```bash
   uv run python scripts/run_ingestion.py --mode info --limit 100
   ```

3. **Full refresh**: Run info + stats in sequence
   ```bash
   make ingest-info
   make ingest-stats
   ```

### Production Workflow

1. **Schedule weekly CSV refresh**:
   - Download fresh dump every Sunday at 2 AM
   - Keep 2-week history of old dumps for rollback

2. **Run info pipeline monthly**:
   - Capture new games and metadata updates
   - Safe to run more frequently (idempotent)

3. **Run stats pipeline daily**:
   - Preserve historical ranking trends
   - Append-only; no risk of data loss

4. **Monitor partition coverage**:
   - Create new partitions 1 month in advance
   - Set up alerts for approaching partition boundaries

### Performance Tips

1. **Batch size**: BGG enforces 20 games/request (cannot increase)

2. **Request delay**: Default 5 seconds is conservative
   - Can reduce to 3 seconds if rate limits aren't hit
   - Increase to 10 seconds if seeing frequent 429/503 errors

3. **Database indexes**: Ensure indexes on:
   - `bgg.games.id` (primary key)
   - `bgg.game_stats.game_id, fetched_at` (composite)
   - `bgg.game_ranks.game_id, rank_type, fetched_at` (composite)

4. **Partitioning**: Monthly partitions balance:
   - Query performance (smaller partitions)
   - Maintenance overhead (not too granular)

---

## Typical Workflow

# Weekly routine:
make ingest-info LIMIT=5000  # Update game metadata weekly
make ingest-stats            # Refresh stats for games > 7 days old

# Daily for active games (optional):
# Set BGG_STATS_MAX_AGE_DAYS=1 in .env
make ingest-stats LIMIT=100  # Only refresh top 100 most stale


## How It Works
#### Scenario 1: Initial Run
Add 100 games - `make ingest-info LIMIT=100`   
Fetches stats for all 100 (none have stats) - `make ingest-stats`            

#### Scenario 2: Incremental Additions
Add 100 more games (total 200 in DB)
Fetches stats for:
- 100 new games (never had stats)
- 0 old games (< 7 days old)
Total: 100 games fetched

```
make ingest-info LIMIT=200
make ingest-stats 
```

#### Scenario 3: After 8 Days
Fetches stats for all 200 games (all > 7 days old) - `make ingest-stats`

####  Scenario 4: Custom Threshold
In .env: `BGG_STATS_MAX_AGE_DAYS=1` - Refreshes daily - `make ingest-stats`
