# API Usage Guide

## Overview

FastAPI-based REST API for board game recommendations using LLM-powered query understanding and content-based filtering.

---

## Quick Start

### 1. Install Dependencies

```bash
uv sync
```

This installs FastAPI, uvicorn, and all other dependencies.

### 2. Set Environment Variables

```bash
# Required
export DATABASE_URL="postgresql://boardflow:boardflow@localhost:5442/boardflow"
export ANTHROPIC_API_KEY="sk-ant-..."

# Optional
export BGG_BASE_URL="https://boardgamegeek.com/xmlapi2"
```

Or add to `.env` file (already loaded by the app).

### 3. Enable pg_trgm Extension

Required for fuzzy game name matching:

```sql
psql $DATABASE_URL -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
```

### 4. Start API Server

**Development (hot reload):**
```bash
make api-dev
# or
uv run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

**Production:**
```bash
make api-prod
# or
uv run uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 5. Test the API

**Health check:**
```bash
curl http://localhost:8000/api/health
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

---

## API Endpoints

### GET /api/health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "llm": "configured"
}
```

---

### POST /api/recommendations

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
- `query` (required): Natural language description of preferences
- `top_n` (optional, default=10): Number of recommendations (1-50)
- `year_min` (optional, default=2015): Only games published >= this year

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
      "thumbnail_url": "https://...",
      "image_url": "https://...",
      "mechanics": ["Trading", "Dice Rolling", "Hand Management"],
      "categories": ["Economic", "Negotiation"],
      "complexity": 2.3,
      "rating": 7.2,
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

---

## Example Queries

### Simple Preference
```json
{
  "query": "I like Catan",
  "top_n": 5
}
```

### Specific Mechanics
```json
{
  "query": "I want a game with worker placement and deck building",
  "top_n": 10,
  "year_min": 2020
}
```

### Player Count
```json
{
  "query": "I need a game for 8 players that's easy to learn",
  "top_n": 5
}
```

### Theme-Based
```json
{
  "query": "Looking for a strategic war game set in medieval times",
  "top_n": 10
}
```

### Exclusions
```json
{
  "query": "I like Catan but not 7 Wonders. Want something with trading but without drafting",
  "top_n": 5
}
```

---

## Interactive API Docs

FastAPI provides automatic interactive documentation:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

Use these to:
- Explore endpoints
- Test queries directly in browser
- View request/response schemas
- Download OpenAPI spec

---

## Python Client Example

```python
import httpx
import asyncio

async def get_recommendations(query: str, top_n: int = 10):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/recommendations",
            json={
                "query": query,
                "top_n": top_n,
                "year_min": 2015,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()

# Usage
result = asyncio.run(get_recommendations("I like Catan, want something fresh"))
for rec in result["recommendations"]:
    print(f"{rec['name']} (Score: {rec['score']:.2f})")
    print(f"  {rec['explanation']}")
```

---

## Architecture

```
POST /api/recommendations
    ↓
[FastAPI Route Handler]
    ↓
[RecommendationService]
    ├─ LLMService.extract_intent() → Parse query
    ├─ GameRepository.find_games_by_names() → Match liked games
    ├─ GameRepository.get_game_profile() → Build user profile
    ├─ GameRepository.get_candidate_games() → Fetch candidates
    ├─ Rank candidates (profile + preferences + quality + exploration)
    ├─ GameRepository.get_games_with_stats() → Fetch top N details
    └─ LLMService.generate_explanation() → Explain each recommendation
    ↓
JSON Response
```

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | PostgreSQL connection string |
| `ANTHROPIC_API_KEY` | Yes | - | Claude API key for LLM |
| `BGG_BASE_URL` | No | `https://boardgamegeek.com/xmlapi2` | BGG API base URL |

### Service Parameters

Can be adjusted in `api/routes.py`:

```python
rec_service = RecommendationService(
    session=session,
    llm_service=llm,
    exploration_weight=0.1,  # 0-1, higher = more diverse results
)
```

---

## Error Handling

### 400 Bad Request
Invalid request parameters (e.g., query too long, top_n out of range).

### 500 Internal Server Error
Server-side error (database connection, LLM API failure, etc.). Check logs.

### Example Error Response
```json
{
  "detail": "ANTHROPIC_API_KEY environment variable not set"
}
```

---

## Performance

**Typical request time:** 3-8 seconds
- LLM intent extraction: 1-2s
- Database queries: 0.5-1s
- Ranking: 0.1-0.5s
- Explanation generation: 1-4s (depends on top_n)

**Optimization tips:**
- Use lower `top_n` for faster responses
- Cache common queries (TODO)
- Batch explanation generation (TODO)

---

## Deployment

### Docker (TODO)

```bash
docker build -t boardflow-api .
docker run -p 8000:8000 \
  -e DATABASE_URL=... \
  -e ANTHROPIC_API_KEY=... \
  boardflow-api
```

### Systemd Service (TODO)

See `deploy/boardflow-api.service` for systemd unit file.

---

## Troubleshooting

### "pg_trgm extension not found"
Enable the extension:
```sql
psql $DATABASE_URL -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
```

### "ANTHROPIC_API_KEY must be set"
Add to `.env`:
```bash
ANTHROPIC_API_KEY=sk-ant-...
```

### "Database connection failed"
Check `DATABASE_URL` and ensure PostgreSQL is running:
```bash
make db-start
```

### Slow responses
- Check Claude API rate limits
- Consider reducing `top_n`
- Add caching layer (future work)
