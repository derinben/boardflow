# Repository Pattern Usage Guide

## Overview

The repository layer provides clean separation between business logic and database access. All database queries are encapsulated in repository classes.

## Structure

```
repositories/
├── __init__.py          # Exports GameRepository
├── base.py              # Base repository utilities (if needed)
└── game_repository.py   # Game-specific queries

schemas/
├── __init__.py          # Exports all schemas
└── game_schemas.py      # Pydantic models (GameProfile, GameCandidate, GameWithStats)
```

## Usage Example

### 1. Setup Database Session

```python
import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Create async engine
database_url = os.environ["DATABASE_URL"]
async_db_url = database_url.replace('postgresql://', 'postgresql+asyncpg://')
engine = create_async_engine(async_db_url, pool_pre_ping=True)
session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
```

### 2. Use Repository

```python
from repositories import GameRepository

async def example():
    async with session_factory() as session:
        repo = GameRepository(session)

        # Find games by name (fuzzy matching)
        results = await repo.find_games_by_names(["Catan", "7 Wonders"], fuzzy=True)
        for result in results:
            print(f"{result['primary_name']} (similarity: {result['similarity']:.2f})")

        # Get game profile for building user preferences
        profile = await repo.get_game_profile(game_id=13)
        print(f"Mechanics: {profile.mechanics}")
        print(f"Categories: {profile.categories}")
        print(f"Complexity: {profile.avg_weight}")

        # Get candidate games for ranking (minimal filters)
        candidates = await repo.get_candidate_games(year_min=2015, exclude_ids=[13, 42])
        print(f"Found {len(candidates)} candidate games")

        # Get full details for final results
        top_game_ids = [1, 2, 3]  # From ranking step
        games = await repo.get_games_with_stats(top_game_ids)
        for game in games:
            print(f"{game.primary_name} - Rating: {game.bayes_average}")

        # Get IDF weights for weighted similarity scoring
        mechanic_weights, category_weights = await repo.get_idf_weights()
        print(f"Loaded {len(mechanic_weights)} mechanic weights")
```

## Schema Models

### GameProfile
Used for extracting mechanics/categories/stats from games user mentions.

**Fields:**
- `game_id`: BGG game ID
- `primary_name`: Game name
- `mechanics`: List of mechanic names
- `categories`: List of category names
- `avg_weight`: Complexity (1-5, higher = more complex)
- `bayes_average`: Quality rating (0-10)

### GameCandidate
Minimal data for ranking phase (before fetching full details).

**Fields:**
- `id`, `primary_name`, `year_published`
- `mechanics`, `categories`
- `avg_weight`, `bayes_average`
- `min_players`, `max_players`, `playing_time`

### GameWithStats
Full game details for final recommendation results.

**Fields:** All of GameCandidate plus:
- `description`, `thumbnail_url`, `image_url`
- `min_age`, `users_rated`, `average_rating`
- `score` (added by service layer during ranking)
- `explanation` (why this game was recommended)

## Integration with Service Layer

The repository is used by the service layer for data access:

```python
# services/recommendation_service.py
from repositories import GameRepository
from schemas import GameWithStats

class RecommendationService:
    def __init__(self, session: AsyncSession):
        self.repo = GameRepository(session)

    async def get_recommendations(self, query: str, top_n: int = 10) -> List[GameWithStats]:
        # 1. Parse query (LLM)
        # 2. Build user profile using repo.get_game_profile()
        # 3. Fetch candidates using repo.get_candidate_games()
        # 4. Rank candidates
        # 5. Fetch full details using repo.get_games_with_stats()
        # 6. Add score/explanation to results
        # 7. Return top N
        pass
```

## Available Methods

### `find_games_by_names(names, fuzzy=True, similarity_threshold=0.3)`
Lookup games by name with optional fuzzy matching (pg_trgm).

### `get_game_profile(game_id)`
Extract mechanics, categories, and stats for a specific game.

### `get_candidate_games(year_min=2015, exclude_ids=None)`
Fetch all games for ranking (minimal hard filters).

### `get_games_with_stats(game_ids)`
Bulk fetch games with full details for final results.

### `get_idf_weights()`
Fetch precomputed IDF weights for mechanics and categories. Used for weighted Jaccard similarity in recommendations. Returns `(mechanic_weights, category_weights)` as dicts.

## Notes

- **Fuzzy Matching**: Requires `pg_trgm` extension enabled in Postgres:
  ```sql
  CREATE EXTENSION IF NOT EXISTS pg_trgm;
  ```

- **IDF Weights**: Compute weights using `scripts/compute_idf_weights.py` after initial data ingestion. Refresh periodically as database grows.

- **Session Management**: Repository accepts an active `AsyncSession`. The caller (service/endpoint) owns transaction boundaries (commit/rollback).

- **Type Safety**: All methods return Pydantic models, not raw ORM objects. This decouples the API layer from database schema changes.
