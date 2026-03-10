# BoardFlow Architecture

## Overview

LLM-powered board game recommendation engine using content-based filtering and natural language query understanding.

---

## System Components

```
┌─────────────────────────────────────────────────────────────┐
│                         CLIENT                              │
│  (HTTP POST /api/recommendations + NL query)                │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Layer                          │
│  • Route handlers (api/routes.py)                           │
│  • Request/response schemas (api/schemas.py)                │
│  • Dependency injection (api/dependencies.py)               │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Service Layer                             │
│  ┌───────────────────┐      ┌─────────────────────┐        │
│  │  LLMService       │      │ RecommendationService│        │
│  │  • Extract intent │◄─────┤ • Build profile      │        │
│  │  • Generate       │      │ • Fetch candidates   │        │
│  │    explanations   │      │ • Rank games         │        │
│  └───────────────────┘      └──────────┬──────────┘        │
└──────────────────────────────────────────┼──────────────────┘
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  Repository Layer                           │
│  • GameRepository (repositories/game_repository.py)         │
│    - find_games_by_names() - Fuzzy match game names        │
│    - get_game_profile() - Extract mechanics/categories      │
│    - get_candidate_games() - Fetch all for ranking         │
│    - get_games_with_stats() - Bulk fetch top N             │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Database (PostgreSQL)                     │
│  Schema: bgg.*                                              │
│  • games, game_names                                        │
│  • mechanics, categories, designers, publishers, etc.       │
│  • game_stats, game_ranks (partitioned by time)            │
│  Extensions: pg_trgm (fuzzy matching)                      │
└─────────────────────────────────────────────────────────────┘

External APIs:
┌──────────────────┐
│  Claude API      │  (LLM extraction + explanation)
└──────────────────┘
```

---

## Request Flow

### 1. Query Extraction
```
User query → LLMService.extract_intent()
  ↓
Claude API parses NL query
  ↓
ExtractedIntent {
  games: [{name, sentiment}]
  mechanics: [...]
  categories: [...]
  preferences: {player_count, complexity, ...}
  ambiguities: [...]
}
```

### 2. Profile Building
```
ExtractedIntent.games (liked)
  ↓
repo.find_games_by_names() → fuzzy match (pg_trgm)
  ↓
repo.get_game_profile(game_id) for each match
  ↓
Aggregate:
  - top_mechanics (Counter → most common)
  - top_categories (Counter → most common)
  - avg_weight (mean complexity)
```

### 3. Candidate Retrieval
```
repo.get_candidate_games(year_min=2015, exclude_ids=[...])
  ↓
SQL query with minimal filters:
  - year_published >= 2015
  - exclude user's liked games
  - JOIN mechanics, categories, latest stats
  ↓
List[GameCandidate] (all games for ranking)
```

### 4. Ranking
```
For each candidate:
  score = profile_similarity + preference_alignment + quality + exploration

profile_similarity (0.3 max):
  - Jaccard(game.mechanics, user.top_mechanics) × 0.7
  - Jaccard(game.categories, user.top_categories) × 0.3

preference_alignment (0.35 max):
  - Player count proximity (0.2 max)
  - Complexity proximity (0.15 max)

quality (0.25 max):
  - Normalized bayes_average (0-10 → 0-0.25)

exploration (0.1 max):
  - (1 - profile_similarity) × exploration_weight

Sort by score descending
```

### 5. Explanation Generation
```
Top N game IDs
  ↓
repo.get_games_with_stats(game_ids) → full details
  ↓
For each game:
  LLMService.generate_explanation(
    game_name,
    user_profile,
    score_breakdown
  )
  ↓
Claude API generates human-readable explanation
  ↓
GameWithStats { ..., score, explanation }
```

---

## Data Models

### API Layer (api/schemas.py)
- `RecommendationRequest` - Input: query, top_n, year_min
- `GameRecommendation` - Output: game details + score + explanation
- `RecommendationResponse` - Output: query, recommendations[], count

### Service Layer (services/llm_service.py)
- `ExtractedIntent` - Parsed query structure
- `GameMention` - Game name + sentiment
- `Preferences` - Player count, complexity, playtime, recency

### Repository Layer (schemas/game_schemas.py)
- `GameProfile` - Mechanics, categories, stats for profile building
- `GameCandidate` - Minimal data for ranking phase
- `GameWithStats` - Full details for final results

### Database (db/models.py)
- `Game` - Core metadata
- `GameName` - Alternate names (for fuzzy matching)
- `Mechanic`, `Category`, `Designer`, etc. - Lookup tables
- `GameMechanic`, `GameCategory`, etc. - Junction tables
- `GameStat` - Ratings, complexity (partitioned by time)
- `GameRank` - Rankings (partitioned by time)

---

## Key Algorithms

### Fuzzy Name Matching (pg_trgm)
```sql
SELECT id, primary_name, similarity(primary_name, 'cattan') AS sim
FROM bgg.games
WHERE primary_name % 'cattan'  -- trigram operator
ORDER BY sim DESC
LIMIT 5;
```

### Jaccard Similarity
```python
def jaccard(set_a, set_b):
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0
```

### Soft Preference Alignment
```python
# Player count (soft, not exclusionary)
if game.min_players <= ideal <= game.max_players:
    score += 0.2
else:
    distance = min(abs(game.min_players - ideal), abs(game.max_players - ideal))
    score += 0.2 * (1 / (1 + distance / 5))  # Exponential decay
```

---

## Configuration

### Environment Variables
- `DATABASE_URL` - PostgreSQL connection string
- `ANTHROPIC_API_KEY` - Claude API key
- `BGG_BASE_URL` - BGG API base (optional)

### Tunable Parameters
```python
RecommendationService(
    exploration_weight=0.1  # 0-1, higher = more diversity
)

# Scoring weights (in _score_game and _profile_similarity)
profile_weight = 0.3
preference_weight = 0.35
quality_weight = 0.25
exploration_weight = 0.1
```

---

## Database Schema

```sql
-- Core tables
bgg.games (id, primary_name, year_published, min/max_players, ...)
bgg.game_names (game_id, name, name_type)

-- Lookup tables
bgg.mechanics (id, name)
bgg.categories (id, name)
bgg.designers, publishers, artists, game_families

-- Junction tables
bgg.game_mechanics (game_id, mechanic_id)
bgg.game_categories (game_id, category_id)
bgg.game_designers, game_publishers, game_artists, game_family_links

-- Stats (partitioned by fetched_at)
bgg.game_stats (game_id, average_weight, bayes_average, users_rated, ...)
bgg.game_ranks (game_id, rank_type, rank_name, rank_value, ...)
```

---

## Performance Characteristics

### Typical Request Time: 3-8 seconds
- LLM intent extraction: 1-2s
- Fuzzy name matching: 0.1-0.5s
- Profile building: 0.1-0.3s
- Candidate retrieval: 0.5-1s (depends on year_min filter)
- Ranking: 0.1-0.5s (O(n) where n = candidate count)
- Explanation generation: 1-4s (O(top_n), sequential Claude API calls)

### Bottlenecks
1. **LLM API calls** (2x per request: extraction + explanations)
2. **Candidate retrieval** (SQL query joins mechanics/categories/stats)

### Optimization Opportunities
- Cache intent extraction for common queries
- Batch explanation generation (parallel Claude API calls)
- Pre-compute mechanic/category vectors (future: embeddings)
- Add Redis for session-level caching

---

## Deployment Architecture

```
┌───────────────┐
│  Load Balancer│
└───────┬───────┘
        │
        ├─────────┐
        │         │
   ┌────▼────┐ ┌──▼──────┐
   │ API #1  │ │ API #2  │  (uvicorn workers)
   └────┬────┘ └──┬──────┘
        │         │
        └────┬────┘
             │
        ┌────▼────────┐
        │ PostgreSQL  │
        │ (primary)   │
        └─────────────┘
```

**Future:**
- Read replicas for candidate queries
- Redis cache layer
- API gateway (rate limiting, auth)
- Background job queue (bulk recommendations)

---

## Testing Strategy

### Unit Tests
- `services/llm_service.py` - Mock Claude API responses
- `services/recommendation_service.py` - Mock repository
- `repositories/game_repository.py` - In-memory SQLite

### Integration Tests
- End-to-end API requests with test database
- Verify query → recommendations flow

### Load Tests
- Concurrent requests (locust/k6)
- Database connection pool sizing
- LLM API rate limits

---

## Future Enhancements

### Phase 1 (Immediate)
- [ ] Cache common queries (Redis)
- [ ] Batch explanation generation (parallel)
- [ ] Add logging/monitoring (structured logs, metrics)

### Phase 2 (Short-term)
- [ ] User accounts + recommendation history
- [ ] Collaborative filtering (user similarity)
- [ ] A/B testing framework (ranking algorithms)

### Phase 3 (Long-term)
- [ ] Vector embeddings (sentence transformers for descriptions)
- [ ] Hybrid ranking (content + collaborative + embeddings)
- [ ] Real-time BGG data sync
- [ ] Multi-language support

---

## References

- [Developer Guide](./DEVELOPER_GUIDE.md) - Complete API, service, and repository usage
- [Data Ingestion Guide](./INGESTION.md) - BGG pipeline and ETL
