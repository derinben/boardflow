# Service Layer Usage Guide

## Overview

The service layer orchestrates business logic, combining LLM extraction, repository queries, and ranking algorithms.

## Components

### 1. LLMService
Handles Claude API interactions for:
- Intent extraction (NL query → structured data)
- Explanation generation (why we recommended a game)

### 2. RecommendationService
Orchestrates the recommendation flow:
1. Extract intent via LLM
2. Build user profile from liked games
3. Fetch candidate games
4. Rank by relevance
5. Generate explanations

---

## Complete Example

```python
import asyncio
import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from services import LLMService, RecommendationService

async def main():
    # Setup database
    database_url = os.environ["DATABASE_URL"]
    async_db_url = database_url.replace('postgresql://', 'postgresql+asyncpg://')
    engine = create_async_engine(async_db_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    # Initialize services
    llm_service = LLMService()  # Uses ANTHROPIC_API_KEY env var

    async with session_factory() as session:
        rec_service = RecommendationService(
            session=session,
            llm_service=llm_service,
            exploration_weight=0.1,
        )

        # Get recommendations
        query = "I like Catan and 7 Wonders, want something with trading but not drafting"
        recommendations = await rec_service.get_recommendations(
            query=query,
            top_n=10,
            year_min=2015,
        )

        # Display results
        for i, game in enumerate(recommendations, 1):
            print(f"{i}. {game.primary_name} (Score: {game.score:.3f})")
            print(f"   {game.explanation}")
            print(f"   Mechanics: {', '.join(game.mechanics[:5])}")
            print(f"   Complexity: {game.avg_weight}, Rating: {game.bayes_average}")
            print()

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Intent Extraction Examples

### Example 1: Simple Query
**Query:** "I like Catan, want something fresh"

**Extracted Intent:**
```json
{
  "games": [{"name": "Catan", "sentiment": "like"}],
  "desired_mechanics": [],
  "desired_categories": [],
  "preferences": {
    "recency": "prefer_new"
  },
  "ambiguities": []
}
```

### Example 2: Complex Query
**Query:** "I like playing Catan and 7 Wonders, didn't like the drafting. Want something with trading for my dinner party with 8 friends"

**Extracted Intent:**
```json
{
  "games": [
    {"name": "Catan", "sentiment": "like"},
    {"name": "7 Wonders", "sentiment": "like"}
  ],
  "desired_mechanics": ["trading"],
  "exclude_mechanics": ["drafting"],
  "preferences": {
    "player_count": {
      "ideal": 8,
      "ambiguous": null
    }
  },
  "ambiguities": []
}
```

### Example 3: Ambiguous Query
**Query:** "I want a game for my dinner party that I can learn quickly"

**Extracted Intent:**
```json
{
  "games": [],
  "desired_mechanics": [],
  "preferences": {
    "player_count": {
      "ambiguous": "dinner party"
    },
    "complexity": "prefer_simple"
  },
  "ambiguities": ["player_count"]
}
```

---

## Ranking Algorithm

### Score Components

**Total Score = Profile + Preference + Quality + Exploration**

1. **Profile Similarity (0.3 max)**
   - Jaccard similarity on mechanics (70%) + categories (30%)
   - Measures overlap with user's liked games

2. **Preference Alignment (0.35 max)**
   - Player count match (0.2 max)
   - Complexity proximity (0.15 max)
   - Soft constraints (no hard exclusions)

3. **Quality Baseline (0.25 max)**
   - Normalized Bayesian average rating (0-10 → 0-0.25)

4. **Exploration Boost (0.1 max by default)**
   - Rewards novelty: (1 - profile_similarity) × weight
   - Prevents echo chamber recommendations

### Example Score Breakdown

```python
{
  "profile_score": 0.24,      # 80% mechanic match
  "preference_score": 0.28,   # Good player count + complexity
  "quality_score": 0.20,      # Rating 8.0/10
  "exploration_score": 0.08,  # Some novelty
  "total": 0.80
}
```

---

## Configuration

### Environment Variables

```bash
# Required
DATABASE_URL=postgresql://user:pass@localhost:5432/boardflow
ANTHROPIC_API_KEY=sk-ant-...

# Optional
BGG_BASE_URL=https://boardgamegeek.com/xmlapi2
```

### Service Parameters

```python
RecommendationService(
    session=session,
    llm_service=llm_service,
    exploration_weight=0.1,  # 0-1, higher = more diverse results
)

rec_service.get_recommendations(
    query="...",
    top_n=10,        # Number of results
    year_min=2015,   # Only games from 2015+
)
```

---

## Next Steps

1. **Enable pg_trgm extension** (required for fuzzy matching):
   ```sql
   CREATE EXTENSION IF NOT EXISTS pg_trgm;
   ```

2. **Test intent extraction:**
   ```python
   llm = LLMService()
   intent = llm.extract_intent("I like Catan")
   print(intent.model_dump())
   ```

3. **Build API endpoint** (FastAPI):
   - `POST /api/recommendations` → query → service → JSON
