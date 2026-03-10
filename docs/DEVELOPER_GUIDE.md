# Developer Guide

**Complete guide to working with BoardFlow's backend.**

This guide consolidates API usage, service layer patterns, repository access, and configuration into a single reference.

---

## Contents

- [Quick Start](#quick-start) - Get running in 5 minutes
- [Architecture Overview](#architecture-overview) - How components fit together
- [API Layer](#api-layer) - FastAPI endpoints and usage
- [Service Layer](#service-layer) - Business logic and algorithms
- [Repository Layer](#repository-layer) - Database access patterns
- [Configuration](#configuration) - Environment variables and tuning

**Related Guides:**
- [ARCHITECTURE.md](./ARCHITECTURE.md) - Deep dive into system design and algorithms
- [INGESTION.md](./INGESTION.md) - BGG data pipeline and ETL

---

## Quick Start

Get the API running and make your first recommendation request.

### Prerequisites

- Python 3.12+
- PostgreSQL 16+ with `pg_trgm` extension
- Claude API key (Anthropic or AWS Bedrock)
- BGG game data ingested (see [INGESTION.md](./INGESTION.md))

### 1. Install Dependencies

```bash
uv sync
```

This installs FastAPI, uvicorn, SQLAlchemy, and all dependencies.

### 2. Configure Environment

Create `.env` file (or export variables):

```bash
# Required
DATABASE_URL=postgresql://boardflow:boardflow@localhost:5442/boardflow
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Optional
LLM_PROVIDER=anthropic  # or 'bedrock'
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
BGG_BASE_URL=https://boardgamegeek.com/xmlapi2
```

### 3. Enable pg_trgm Extension

Required for fuzzy game name matching:

```bash
psql $DATABASE_URL -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
```

### 4. Start the API Server

**Development (with hot reload):**
```bash
make api-dev
# or
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

**Production:**
```bash
make api-prod
# or
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Server starts at: **http://localhost:8000**

### 5. Test the API

**Health check:**
```bash
curl http://localhost:8000/api/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "llm": "configured"
}
```

**Get recommendations:**
```bash
curl -X POST http://localhost:8000/api/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "query": "I like Catan and 7 Wonders, want something with trading",
    "top_n": 5,
    "year_min": 2015
  }'
```

**Expected response:**
```json
{
  "query": "I like Catan and 7 Wonders, want something with trading",
  "recommendations": [
    {
      "id": 13,
      "name": "Catan",
      "year_published": 1995,
      "description": "Players collect resources...",
      "mechanics": ["Trading", "Dice Rolling"],
      "categories": ["Economic", "Negotiation"],
      "complexity": 2.3,
      "rating": 7.2,
      "score": 0.85,
      "explanation": "Recommended because it shares Trading mechanics..."
    }
  ],
  "count": 5
}
```

### 6. Interactive Documentation

FastAPI provides automatic interactive docs:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

Use these to explore endpoints and test queries in your browser.

---

## Architecture Overview

High-level system design showing how components work together.

### Component Layers

```
┌─────────────────────────────────────────────────────────────┐
│                      CLIENT REQUEST                         │
│  POST /api/recommendations + natural language query         │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      API LAYER                              │
│  • FastAPI routes (api/routes.py)                           │
│  • Request/response validation (api/schemas.py)             │
│  • Dependency injection (api/dependencies.py)               │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    SERVICE LAYER                            │
│  ┌──────────────────┐      ┌──────────────────────┐        │
│  │ LLMService       │      │ RecommendationService│        │
│  │ • Extract intent │◄─────┤ • Build user profile │        │
│  │ • Generate       │      │ • Fetch candidates   │        │
│  │   explanations   │      │ • Rank by relevance  │        │
│  └──────────────────┘      └──────────┬───────────┘        │
└──────────────────────────────────────────┼──────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   REPOSITORY LAYER                          │
│  GameRepository (repositories/game_repository.py)           │
│  • find_games_by_names() - Fuzzy match user input          │
│  • get_game_profile() - Extract mechanics/categories       │
│  • get_candidate_games() - Fetch all games for ranking     │
│  • get_games_with_stats() - Bulk fetch top N results       │
│  • get_idf_weights() - TF-IDF weights for ranking          │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                 DATABASE (PostgreSQL)                       │
│  • bgg.games, bgg.game_names                                │
│  • bgg.mechanics, bgg.categories (lookup tables)            │
│  • bgg.game_stats (ratings, partitioned by time)            │
│  • pg_trgm extension for fuzzy matching                     │
└─────────────────────────────────────────────────────────────┘

External:  Claude API (intent extraction + explanations)
```

### Request Flow

**Full recommendation flow:**

1. **Client Request** → POST `/api/recommendations` with natural language query
2. **API Layer** → Validates request, injects dependencies (DB session, LLM service)
3. **LLM Extraction** → Parse query into structured intent (liked games, desired mechanics, preferences)
4. **Profile Building** → Fuzzy match user's liked games, aggregate their mechanics/categories
5. **Candidate Retrieval** → Fetch all games from DB (filtered by year, excluding liked games)
6. **Ranking** → Score each candidate (profile similarity + preferences + quality + exploration)
7. **Top-N Selection** → Sort by score, take top N game IDs
8. **Fetch Details** → Bulk query for full game data (descriptions, images, stats)
9. **Explanation Generation** → LLM generates human-readable "why recommended"
10. **Response** → Return JSON with games, scores, explanations

**Typical timing:** 3-8 seconds (LLM calls are slowest: 1-2s extraction, 1-4s explanations)

### Data Flow Example

```python
# User query
"I like Catan and 7 Wonders, want something with trading"

# Step 1: LLM extracts intent
{
  "games": [
    {"name": "Catan", "sentiment": "like"},
    {"name": "7 Wonders", "sentiment": "like"}
  ],
  "desired_mechanics": ["Trading"],
  "preferences": {}
}

# Step 2: Build profile from liked games
{
  "top_mechanics": ["Trading", "Dice Rolling", "Hand Management"],
  "top_categories": ["Economic", "Card Game"],
  "avg_complexity": 2.3
}

# Step 3: Rank candidates
# Each game scored 0-1 based on:
# - Profile match (mechanics/categories overlap)
# - Preference alignment (player count, complexity)
# - Quality (BGG rating)
# - Exploration (novelty bonus)

# Step 4: Return top N with explanations
[
  {
    "name": "Bohnanza",
    "score": 0.82,
    "explanation": "Perfect match for your Trading preference..."
  },
  ...
]
```

**See [ARCHITECTURE.md](./ARCHITECTURE.md) for deep dive into algorithms and data models.**

---

## API Layer

FastAPI endpoints for recommendation and health checks.

### Endpoints

#### GET /api/health

Health check endpoint to verify database and LLM connectivity.

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "llm": "configured"
}
```

**Status values:**
- `"healthy"` - All systems operational
- `"degraded"` - Partial failure (check `database` and `llm` fields)

---

#### POST /api/recommendations

Get game recommendations from natural language query.

**Request Body:**
```json
{
  "query": "I like Catan and 7 Wonders, want something with trading",
  "top_n": 10,
  "year_min": 2015
}
```

**Parameters:**

| Field | Type | Required | Default | Range | Description |
|-------|------|----------|---------|-------|-------------|
| `query` | string | ✅ Yes | - | 1-1000 chars | Natural language preference description |
| `top_n` | integer | No | 10 | 1-50 | Number of recommendations to return |
| `year_min` | integer | No | 2015 | 1900-2030 | Only games published >= this year |

**Response:**
```json
{
  "query": "I like Catan and 7 Wonders, want something with trading",
  "recommendations": [
    {
      "id": 13,
      "name": "Catan",
      "year_published": 1995,
      "description": "Players collect resources and build settlements...",
      "thumbnail_url": "https://cf.geekdo-images.com/...",
      "image_url": "https://cf.geekdo-images.com/...",
      "mechanics": ["Trading", "Dice Rolling", "Hand Management"],
      "categories": ["Economic", "Negotiation"],
      "complexity": 2.33,
      "rating": 7.18,
      "min_players": 3,
      "max_players": 4,
      "playing_time": 120,
      "min_age": 10,
      "score": 0.85,
      "explanation": "Recommended because it shares Trading and Negotiation mechanics with your liked games (90% match), complexity 2.3 is similar to your average preference of 2.5, and highly rated (7.2/10)."
    }
  ],
  "count": 10
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | BoardGameGeek game ID |
| `name` | string | Primary game name |
| `year_published` | integer? | Publication year (null if unknown) |
| `description` | string | Game description |
| `thumbnail_url` | string? | Small image URL (null if no image) |
| `image_url` | string? | Full-size image URL |
| `mechanics` | string[] | Game mechanics (e.g., "Worker Placement") |
| `categories` | string[] | Game categories (e.g., "Fantasy") |
| `complexity` | float? | Complexity rating 1-5 (BGG average weight) |
| `rating` | float? | Quality rating 0-10 (BGG Bayesian average) |
| `min_players` | integer? | Minimum player count |
| `max_players` | integer? | Maximum player count |
| `playing_time` | integer? | Playing time in minutes |
| `min_age` | integer? | Minimum recommended age |
| `score` | float | Recommendation score 0-1 (higher = better match) |
| `explanation` | string | Human-readable explanation for recommendation |

---

### Example Queries

#### Simple Preference
```bash
curl -X POST http://localhost:8000/api/recommendations \
  -H "Content-Type: application/json" \
  -d '{"query": "I like Catan", "top_n": 5}'
```

#### Specific Mechanics
```bash
curl -X POST http://localhost:8000/api/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "query": "I want a game with worker placement and deck building",
    "top_n": 10,
    "year_min": 2020
  }'
```

#### Player Count Constraint
```bash
curl -X POST http://localhost:8000/api/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "query": "I need a game for 8 players that is easy to learn",
    "top_n": 5
  }'
```

#### Theme-Based Search
```bash
curl -X POST http://localhost:8000/api/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Looking for a strategic war game set in medieval times",
    "top_n": 10
  }'
```

#### With Exclusions
```bash
curl -X POST http://localhost:8000/api/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "query": "I like Catan but not 7 Wonders. Want trading but no drafting",
    "top_n": 5
  }'
```

---

### Python Client Example

```python
import httpx
import asyncio

async def get_recommendations(query: str, top_n: int = 10):
    """Get game recommendations from API."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/recommendations",
            json={
                "query": query,
                "top_n": top_n,
                "year_min": 2015,
            },
            timeout=30.0,  # LLM calls can be slow
        )
        response.raise_for_status()
        return response.json()

# Usage
result = asyncio.run(get_recommendations("I like Catan, want something fresh"))
for rec in result["recommendations"]:
    print(f"{rec['name']} (Score: {rec['score']:.2f})")
    print(f"  {rec['explanation']}\n")
```

---

### Error Handling

#### 400 Bad Request
**Cause:** Invalid request parameters

**Examples:**
- Query too long (>1000 chars)
- `top_n` out of range (not 1-50)
- `year_min` invalid (not 1900-2030)

**Response:**
```json
{
  "detail": [
    {
      "loc": ["body", "query"],
      "msg": "ensure this value has at most 1000 characters",
      "type": "value_error.any_str.max_length"
    }
  ]
}
```

#### 500 Internal Server Error
**Causes:**
- Database connection failure
- LLM API failure (invalid key, rate limit)
- Missing `pg_trgm` extension

**Response:**
```json
{
  "detail": "ANTHROPIC_API_KEY environment variable not set"
}
```

**Debugging steps:**
1. Check logs: `tail -f logs/api.log`
2. Verify database: `psql $DATABASE_URL -c "SELECT 1"`
3. Test LLM key: `curl https://api.anthropic.com/v1/messages -H "x-api-key: $ANTHROPIC_API_KEY"`

---

### Performance

**Typical response times:**
- Simple query (no liked games): 3-5s
- Complex query (multiple games): 5-8s

**Breakdown:**
- LLM intent extraction: 1-2s
- Database queries: 0.5-1s
- Ranking: 0.1-0.5s
- LLM explanation generation: 1-4s (proportional to `top_n`)

**Optimization tips:**
- Use smaller `top_n` for faster responses (fewer explanations needed)
- Cache common queries (future enhancement)
- Batch explanation generation (future enhancement)

---

## Service Layer

Business logic orchestration: LLM extraction, profile building, and ranking algorithms.

### Components

#### LLMService (`services/llm_service.py`)

Handles Claude API interactions for:
- **Intent extraction** - Parse natural language → structured data
- **Explanation generation** - Create human-readable "why recommended"

**Key methods:**
```python
class LLMService:
    async def extract_intent(self, query: str) -> ExtractedIntent:
        """Parse natural language query into structured intent."""
        
    async def generate_explanation(
        self, 
        game_name: str,
        user_profile: dict,
        score_components: dict
    ) -> str:
        """Generate explanation for why game was recommended."""
```

#### RecommendationService (`services/recommendation_service.py`)

Orchestrates the full recommendation flow:

**Flow:**
1. Extract intent via LLM
2. Build user profile from liked games
3. Fetch candidate games from database
4. Rank by relevance score
5. Generate explanations for top N

**Key methods:**
```python
class RecommendationService:
    def __init__(
        self,
        session: AsyncSession,
        llm_service: LLMService,
        exploration_weight: float = 0.1
    ):
        """Initialize with DB session and LLM service."""
        
    async def get_recommendations(
        self,
        query: str,
        top_n: int = 10,
        year_min: int = 2015
    ) -> List[GameWithStats]:
        """Get ranked game recommendations."""
```

---

### Intent Extraction Examples

#### Example 1: Simple Query
**Input:** `"I like Catan, want something fresh"`

**Extracted Intent:**
```python
{
  "games": [{"name": "Catan", "sentiment": "like"}],
  "desired_mechanics": [],
  "desired_categories": [],
  "exclude_mechanics": [],
  "exclude_categories": [],
  "preferences": {
    "recency": "prefer_new",
    "player_count": None,
    "complexity": None,
    "playtime_max_minutes": None
  },
  "ambiguities": []
}
```

#### Example 2: Complex Query
**Input:** `"I like Catan and 7 Wonders, didn't like the drafting. Want something with trading for my dinner party with 8 friends"`

**Extracted Intent:**
```python
{
  "games": [
    {"name": "Catan", "sentiment": "like"},
    {"name": "7 Wonders", "sentiment": "like"}
  ],
  "desired_mechanics": ["Trading"],
  "exclude_mechanics": ["Drafting"],
  "preferences": {
    "player_count": {"ideal": 8}
  },
  "ambiguities": []
}
```

#### Example 3: Ambiguous Query
**Input:** `"I want a game for my dinner party that I can learn quickly"`

**Extracted Intent:**
```python
{
  "games": [],
  "preferences": {
    "player_count": {"ambiguous": "dinner party"},
    "complexity": "prefer_simple"
  },
  "ambiguities": ["player_count"]
}
```

---

### Ranking Algorithm

Games are scored 0-1 based on four components:

**Total Score = Profile + Preference + Quality + Exploration**

#### 1. Profile Similarity (max 0.3)

Measures overlap with user's liked games using weighted Jaccard similarity:

```python
profile_score = (
    jaccard(game.mechanics, user.top_mechanics) * 0.7 +
    jaccard(game.categories, user.top_categories) * 0.3
) * 0.3
```

**With TF-IDF weighting:**
- Rare mechanics (e.g., "Roll/Spin and Move") get higher weight
- Common mechanics (e.g., "Hand Management") get lower weight
- 3.6× improvement in ranking niche games

**Example:**
- Game has ["Trading", "Worker Placement"]
- User likes ["Trading", "Dice Rolling", "Hand Management"]
- Jaccard = 1/4 = 0.25
- Profile score = 0.25 × 0.3 = 0.075

#### 2. Preference Alignment (max 0.35)

Soft constraints for player count and complexity:

```python
# Player count (max 0.2)
if game.min_players <= ideal <= game.max_players:
    score += 0.2
else:
    distance = min(abs(game.min_players - ideal), abs(game.max_players - ideal))
    score += 0.2 * (1 / (1 + distance / 5))  # Exponential decay

# Complexity (max 0.15)
if user.avg_complexity is not None:
    distance = abs(game.complexity - user.avg_complexity)
    score += 0.15 * (1 / (1 + distance))
```

**Example:**
- User wants 6 players, game supports 4-8: Full 0.2 score
- User wants 6 players, game supports 2-4: Distance=2, score=0.13
- User avg complexity 2.5, game is 2.3: Distance=0.2, score=0.125

#### 3. Quality Baseline (max 0.25)

Normalized BGG Bayesian average rating:

```python
quality_score = (game.bayes_average / 10.0) * 0.25
```

**Example:**
- Game rating 8.0/10 → 0.20 quality score
- Game rating 5.0/10 → 0.125 quality score

#### 4. Exploration Boost (max 0.1 default)

Rewards novelty to prevent echo chamber:

```python
exploration_score = (1 - profile_score / 0.3) * exploration_weight
```

**Example:**
- Perfect profile match (0.3) → 0 exploration (no novelty)
- No profile match (0) → 0.1 exploration (maximum novelty)

---

### Score Breakdown Example

```python
{
  "game": "Bohnanza",
  "profile_score": 0.24,       # 80% mechanic match (Trading)
  "preference_score": 0.28,    # Good player count + complexity
  "quality_score": 0.20,       # Rating 8.0/10
  "exploration_score": 0.02,   # Low novelty (good profile match)
  "total": 0.74                # Combined score
}
```

---

### Complete Usage Example

```python
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from services import LLMService, RecommendationService

async def main():
    # Setup database connection
    database_url = os.environ["DATABASE_URL"]
    async_db_url = database_url.replace('postgresql://', 'postgresql+asyncpg://')
    engine = create_async_engine(
        async_db_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=5
    )
    session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
        class_=AsyncSession
    )

    # Initialize services
    llm_service = LLMService()  # Uses ANTHROPIC_API_KEY env var

    async with session_factory() as session:
        rec_service = RecommendationService(
            session=session,
            llm_service=llm_service,
            exploration_weight=0.1,  # 10% novelty bonus
        )

        # Get recommendations
        query = "I like Catan and 7 Wonders, want something with trading"
        recommendations = await rec_service.get_recommendations(
            query=query,
            top_n=10,
            year_min=2015,
        )

        # Display results
        for i, game in enumerate(recommendations, 1):
            print(f"{i}. {game.primary_name} (Score: {game.score:.3f})")
            print(f"   Rating: {game.bayes_average:.2f}, Complexity: {game.avg_weight:.2f}")
            print(f"   Mechanics: {', '.join(game.mechanics[:5])}")
            print(f"   {game.explanation}\n")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
```

---

### Tuning Parameters

**Exploration Weight:**
```python
RecommendationService(
    session=session,
    llm_service=llm_service,
    exploration_weight=0.1,  # 0-1, higher = more diverse results
)
```

- `0.0` - Pure content-based filtering (only similar games)
- `0.1` - Default (slight diversity)
- `0.3` - High diversity (more unexpected recommendations)

**Score Component Weights** (in `recommendation_service.py`):
```python
# Current defaults
PROFILE_WEIGHT = 0.3        # Mechanic/category match
PREFERENCE_WEIGHT = 0.35    # Player count, complexity
QUALITY_WEIGHT = 0.25       # BGG rating
EXPLORATION_WEIGHT = 0.1    # Novelty bonus
```

---

## Repository Layer

Database access patterns and query encapsulation.

### Overview

The repository layer provides clean separation between business logic and database access. All SQL queries are encapsulated in repository classes.

**Structure:**
```
repositories/
├── __init__.py          # Exports GameRepository
└── game_repository.py   # Game-specific queries

schemas/
├── __init__.py          # Exports all schemas
└── game_schemas.py      # Pydantic models (GameProfile, GameCandidate, GameWithStats)
```

**Benefits:**
- Service layer doesn't write SQL
- Easy to mock for testing
- Type-safe with Pydantic models
- Decouples API from database schema

---

### GameRepository Methods

#### find_games_by_names()

Lookup games by name with optional fuzzy matching (pg_trgm).

**Signature:**
```python
async def find_games_by_names(
    self,
    names: List[str],
    fuzzy: bool = True,
    similarity_threshold: float = 0.3
) -> List[Dict[str, Any]]:
    """
    Find games by name, with fuzzy matching.
    
    Returns:
        List of dicts with 'id', 'primary_name', 'similarity'
    """
```

**Example:**
```python
repo = GameRepository(session)
results = await repo.find_games_by_names(["Cattan", "7 Wondeers"], fuzzy=True)

# Results:
# [
#   {'id': 13, 'primary_name': 'Catan', 'similarity': 0.83},
#   {'id': 68448, 'primary_name': '7 Wonders', 'similarity': 0.90}
# ]
```

**SQL (fuzzy mode):**
```sql
SELECT g.id, g.primary_name, similarity(gn.name, 'Cattan') AS similarity
FROM bgg.game_names gn
JOIN bgg.games g ON g.id = gn.game_id
WHERE gn.name % 'Cattan'  -- pg_trgm trigram operator
ORDER BY similarity DESC
LIMIT 5;
```

---

#### get_game_profile()

Extract mechanics, categories, and stats for a specific game.

**Signature:**
```python
async def get_game_profile(self, game_id: int) -> GameProfile:
    """
    Get game profile for building user preferences.
    
    Returns:
        GameProfile with mechanics, categories, complexity, rating
    """
```

**Returns:** `GameProfile` model with fields:
- `game_id: int`
- `primary_name: str`
- `mechanics: List[str]`
- `categories: List[str]`
- `avg_weight: float` (complexity 1-5)
- `bayes_average: float` (rating 0-10)

**Example:**
```python
profile = await repo.get_game_profile(game_id=13)

# Result:
# GameProfile(
#   game_id=13,
#   primary_name="Catan",
#   mechanics=["Trading", "Dice Rolling", "Hand Management"],
#   categories=["Economic", "Negotiation"],
#   avg_weight=2.33,
#   bayes_average=7.18
# )
```

---

#### get_candidate_games()

Fetch all games for ranking (minimal hard filters).

**Signature:**
```python
async def get_candidate_games(
    self,
    year_min: int = 2015,
    exclude_ids: Optional[List[int]] = None
) -> List[GameCandidate]:
    """
    Fetch all games for ranking phase.
    
    Returns:
        List of GameCandidate (minimal data for efficient ranking)
    """
```

**Returns:** `GameCandidate` models with fields:
- `id, primary_name, year_published`
- `mechanics, categories`
- `avg_weight, bayes_average`
- `min_players, max_players, playing_time`

**Example:**
```python
candidates = await repo.get_candidate_games(
    year_min=2015,
    exclude_ids=[13, 68448]  # Exclude user's liked games
)

# Returns ~2000-3000 games for ranking
print(f"Found {len(candidates)} candidates")
```

---

#### get_games_with_stats()

Bulk fetch games with full details for final results.

**Signature:**
```python
async def get_games_with_stats(
    self, 
    game_ids: List[int]
) -> List[GameWithStats]:
    """
    Fetch full game details for top N recommendations.
    
    Returns:
        List of GameWithStats (all fields including descriptions, images)
    """
```

**Returns:** `GameWithStats` models with all `GameCandidate` fields plus:
- `description: str`
- `thumbnail_url: Optional[str]`
- `image_url: Optional[str]`
- `min_age: Optional[int]`
- `users_rated: Optional[int]`
- `average_rating: Optional[float]`

**Example:**
```python
top_ids = [13, 68448, 822]  # From ranking step
games = await repo.get_games_with_stats(top_ids)

for game in games:
    print(f"{game.primary_name}: {game.description[:100]}...")
```

---

#### get_idf_weights()

Fetch precomputed IDF weights for mechanics and categories.

**Signature:**
```python
async def get_idf_weights(self) -> Tuple[Dict[str, float], Dict[str, float]]:
    """
    Get IDF weights for weighted Jaccard similarity.
    
    Returns:
        (mechanic_weights, category_weights) as dicts
    """
```

**Example:**
```python
mechanic_weights, category_weights = await repo.get_idf_weights()

# Result:
# mechanic_weights = {
#   "Hand Management": 0.42,  # Common mechanic (low weight)
#   "Roll/Spin and Move": 2.15,  # Rare mechanic (high weight)
#   ...
# }
```

**IDF Formula:**
```python
idf_weight = log(total_games / (1 + games_with_mechanic))
```

**Weights computed by:** `scripts/compute_idf_weights.py`

---

### Schema Models

#### GameProfile

Used for extracting mechanics/categories/stats from games user mentions.

```python
class GameProfile(BaseModel):
    game_id: int
    primary_name: str
    mechanics: List[str]
    categories: List[str]
    avg_weight: Optional[float]  # Complexity 1-5
    bayes_average: Optional[float]  # Rating 0-10
```

#### GameCandidate

Minimal data for ranking phase (before fetching full details).

```python
class GameCandidate(BaseModel):
    id: int
    primary_name: str
    year_published: Optional[int]
    mechanics: List[str]
    categories: List[str]
    avg_weight: Optional[float]
    bayes_average: Optional[float]
    min_players: Optional[int]
    max_players: Optional[int]
    playing_time: Optional[int]
```

#### GameWithStats

Full game details for final recommendation results.

```python
class GameWithStats(GameCandidate):  # Inherits all GameCandidate fields
    description: str
    thumbnail_url: Optional[str]
    image_url: Optional[str]
    min_age: Optional[int]
    users_rated: Optional[int]
    average_rating: Optional[float]
    
    # Added by service layer:
    score: float  # Recommendation score (0-1)
    explanation: str  # Why recommended
```

---

### Integration with Service Layer

```python
# services/recommendation_service.py
from repositories import GameRepository
from schemas import GameWithStats

class RecommendationService:
    def __init__(self, session: AsyncSession, llm_service: LLMService):
        self.repo = GameRepository(session)
        self.llm = llm_service

    async def get_recommendations(self, query: str, top_n: int = 10) -> List[GameWithStats]:
        # 1. Parse query (LLM)
        intent = await self.llm.extract_intent(query)
        
        # 2. Build user profile
        liked_games = await self.repo.find_games_by_names(
            [g.name for g in intent.games if g.sentiment == "like"]
        )
        profiles = [await self.repo.get_game_profile(g['id']) for g in liked_games]
        user_profile = self._aggregate_profiles(profiles)
        
        # 3. Fetch candidates
        candidates = await self.repo.get_candidate_games(
            year_min=2015,
            exclude_ids=[g['id'] for g in liked_games]
        )
        
        # 4. Rank candidates
        scored = [(c, self._score_game(c, user_profile, intent)) for c in candidates]
        top_ids = [c.id for c, score in sorted(scored, key=lambda x: x[1], reverse=True)[:top_n]]
        
        # 5. Fetch full details
        games = await self.repo.get_games_with_stats(top_ids)
        
        # 6. Add scores and explanations
        for game in games:
            game.score = next(s for c, s in scored if c.id == game.id)
            game.explanation = await self.llm.generate_explanation(game, user_profile)
        
        return games
```

---

### Database Session Management

Repository accepts an active `AsyncSession`. The caller (service/endpoint) owns transaction boundaries.

**Example:**
```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Setup (once at startup)
database_url = os.environ["DATABASE_URL"].replace('postgresql://', 'postgresql+asyncpg://')
engine = create_async_engine(database_url, pool_pre_ping=True)
session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# Usage (per request)
async with session_factory() as session:
    repo = GameRepository(session)
    games = await repo.get_candidate_games(year_min=2015)
    # Session automatically commits/rolls back on context exit
```

---

### Requirements

**pg_trgm extension** (for fuzzy matching):
```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

**IDF weights** (for ranking):
```bash
python scripts/compute_idf_weights.py
```

Refresh periodically as database grows (e.g., after major data ingestion).

---

## Configuration

Environment variables, LLM providers, and tuning parameters.

### Environment Variables

All configuration via `.env` file or exported environment variables.

#### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@localhost:5432/boardflow` |
| `ANTHROPIC_API_KEY` | Claude API key (if using Anthropic) | `sk-ant-xxxxx` |

#### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `anthropic` | LLM provider: `anthropic` or `bedrock` |
| `ANTHROPIC_MODEL` | `claude-3-5-sonnet-20241022` | Claude model ID |
| `BGG_BASE_URL` | `https://boardgamegeek.com/xmlapi2` | BGG API base URL |
| `IDF_ENABLED` | `true` | Enable IDF weighting for ranking |

#### AWS Bedrock (if LLM_PROVIDER=bedrock)

| Variable | Description |
|----------|-------------|
| `AWS_REGION` | AWS region (e.g., `us-east-1`) |
| `AWS_ACCESS_KEY_ID` | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key |
| `BEDROCK_MODEL_ID` | Bedrock model ID (e.g., `anthropic.claude-3-5-sonnet-20241022-v2:0`) |

---

### LLM Provider Configuration

BoardFlow supports two LLM providers for Claude models.

#### Option 1: Anthropic Native API (Recommended for Development)

**Setup:**
```bash
# .env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-xxxxx
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
```

**Pros:**
- Simple setup (API key only)
- Faster iteration during development
- Direct access to latest models

**Cons:**
- Anthropic billing (no AWS cost tracking)
- Less enterprise features

---

#### Option 2: AWS Bedrock (Recommended for Production)

**Setup:**
```bash
# .env
LLM_PROVIDER=bedrock
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0

# AWS credentials via env or ~/.aws/credentials
AWS_ACCESS_KEY_ID=xxxxx
AWS_SECRET_ACCESS_KEY=xxxxx
```

**Pros:**
- AWS billing with detailed cost tracking
- IAM permissions and governance
- Enterprise-grade security
- Multi-region redundancy

**Cons:**
- More complex setup (IAM, policies)
- Slightly higher latency (AWS API gateway)

**IAM Policy Required:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": "arn:aws:bedrock:*::foundation-model/anthropic.claude-*"
    }
  ]
}
```

---

### Service Parameters

#### RecommendationService

**Exploration weight** (controls diversity):
```python
RecommendationService(
    session=session,
    llm_service=llm_service,
    exploration_weight=0.1,  # 0-1, higher = more diverse results
)
```

**Recommendations:**
- `0.0` - Pure similarity (only similar games recommended)
- `0.1` - Default (slight diversity, avoids echo chamber)
- `0.3` - High diversity (more unexpected recommendations)

#### Ranking Weights

Located in `services/recommendation_service.py`:

```python
# Score component weights (must sum to ~1.0)
PROFILE_WEIGHT = 0.3        # Mechanic/category similarity
PREFERENCE_WEIGHT = 0.35    # Player count, complexity alignment
QUALITY_WEIGHT = 0.25       # BGG rating
# exploration_weight from constructor (default 0.1)
```

**Tuning guidelines:**
- Increase `PROFILE_WEIGHT` for stricter similarity
- Increase `PREFERENCE_WEIGHT` for player count/complexity priority
- Increase `QUALITY_WEIGHT` to favor highly-rated games
- Increase `exploration_weight` for more serendipity

---

### Database Configuration

**Connection pool settings** (in `api/dependencies.py`):

```python
engine = create_async_engine(
    async_db_url,
    pool_pre_ping=True,     # Verify connections before use
    pool_size=10,           # Concurrent connections
    max_overflow=5,         # Extra connections if pool full
    pool_recycle=3600,      # Recycle connections after 1 hour
)
```

**For high load:**
- Increase `pool_size` (10 → 20)
- Increase `max_overflow` (5 → 10)
- Add read replicas for candidate queries

---

### IDF Weights

**Enable/disable:**
```bash
# .env
IDF_ENABLED=true  # Use TF-IDF weighting (recommended)
```

**Compute weights:**
```bash
python scripts/compute_idf_weights.py
```

This populates `bgg.mechanic_stats` and `bgg.category_stats` tables with precomputed IDF weights.

**When to recompute:**
- After initial data ingestion (required)
- After adding 1000+ new games (optional)
- When ranking quality degrades (rare mechanic games rank too low)

**Impact:**
- 3.6× better ranking for rare mechanics
- Negligible performance overhead (weights cached in memory)

---

### FastAPI Settings

**CORS origins** (in `api/app.py`):

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative frontend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**For production:**
```python
allow_origins=[
    "https://yourdomain.com",
    "https://www.yourdomain.com",
]
```

---

### Example .env File

```bash
# Database
DATABASE_URL=postgresql://boardflow:boardflow@localhost:5442/boardflow

# LLM Provider (Anthropic)
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-xxxxx
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# LLM Provider (Bedrock) - Alternative
# LLM_PROVIDER=bedrock
# AWS_REGION=us-east-1
# BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0

# Optional
BGG_BASE_URL=https://boardgamegeek.com/xmlapi2
IDF_ENABLED=true
```

---

### Troubleshooting

#### "pg_trgm extension not found"
```sql
psql $DATABASE_URL -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
```

#### "ANTHROPIC_API_KEY must be set"
```bash
export ANTHROPIC_API_KEY=sk-ant-xxxxx
# or add to .env
```

#### "Database connection failed"
```bash
# Check PostgreSQL is running
make db-start

# Test connection
psql $DATABASE_URL -c "SELECT 1"
```

#### "IDF weights not found"
```bash
# Compute weights
python scripts/compute_idf_weights.py

# Verify
psql $DATABASE_URL -c "SELECT COUNT(*) FROM bgg.mechanic_stats"
```

#### Slow responses
- Check Claude API rate limits (tier-based)
- Reduce `top_n` (fewer explanation calls)
- Enable caching (future enhancement)
- Use Bedrock multi-region for redundancy

---

## Summary

You now have a complete reference for:
- ✅ **Quick Start** - API setup and first query
- ✅ **Architecture** - How components fit together
- ✅ **API Layer** - Endpoints and usage patterns
- ✅ **Service Layer** - Business logic and algorithms
- ✅ **Repository Layer** - Database access patterns
- ✅ **Configuration** - Environment variables and tuning

**Next steps:**
- Read [ARCHITECTURE.md](./ARCHITECTURE.md) for deep dive into algorithms
- Read [INGESTION.md](./INGESTION.md) for data pipeline setup
- Check `/docs` endpoint for interactive API documentation

**Questions?** Check logs, enable debug mode, or review error handling sections above.
