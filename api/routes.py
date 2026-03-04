"""API route handlers."""

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services import LLMService, RecommendationService

from .dependencies import get_db_session, get_llm_service
from .schemas import (
    GameRecommendation,
    HealthCheckResponse,
    RecommendationRequest,
    RecommendationResponse,
)

router = APIRouter()


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(
    session: AsyncSession = Depends(get_db_session),
    llm: LLMService = Depends(get_llm_service),
) -> HealthCheckResponse:
    """Health check endpoint.

    Verifies database connection and LLM service configuration.
    """
    # Check database
    try:
        result = await session.execute(text("SELECT 1"))
        result.scalar()
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = f"error: {str(e)}"

    # Check LLM
    llm_status = "configured" if llm.api_key else "missing_api_key"

    return HealthCheckResponse(
        status="healthy" if db_status == "connected" and llm_status == "configured" else "degraded",
        database=db_status,
        llm=llm_status,
    )


@router.post("/recommendations", response_model=RecommendationResponse)
async def get_recommendations(
    request: RecommendationRequest,
    session: AsyncSession = Depends(get_db_session),
    llm: LLMService = Depends(get_llm_service),
) -> RecommendationResponse:
    """Get game recommendations from natural language query.

    **Example queries:**
    - "I like Catan and 7 Wonders, want something with trading"
    - "I want a game for 8 players that's easy to learn"
    - "Looking for a strategic war game published in the last 5 years"

    **Process:**
    1. Extract intent via LLM (games, mechanics, preferences)
    2. Build user profile from liked games
    3. Fetch candidate games from database
    4. Rank by relevance (profile match + preferences + quality + exploration)
    5. Generate explanations for top recommendations

    **Returns:**
    List of ranked game recommendations with scores and explanations.
    """
    try:
        logger.info(f"Recommendation request: query='{request.query[:100]}...', top_n={request.top_n}")

        # Initialize service
        rec_service = RecommendationService(
            session=session,
            llm_service=llm,
            exploration_weight=0.1,
        )

        # Get recommendations
        games = await rec_service.get_recommendations(
            query=request.query,
            top_n=request.top_n,
            year_min=request.year_min,
        )

        # Convert to API response schema
        recommendations = [
            GameRecommendation(
                id=game.id,
                name=game.primary_name,
                year_published=game.year_published,
                description=game.description,
                thumbnail_url=game.thumbnail_url,
                image_url=game.image_url,
                mechanics=game.mechanics,
                categories=game.categories,
                complexity=game.avg_weight,
                rating=game.bayes_average,
                min_players=game.min_players,
                max_players=game.max_players,
                playing_time=game.playing_time,
                min_age=game.min_age,
                score=game.score or 0.0,
                explanation=game.explanation or "",
            )
            for game in games
        ]

        logger.info(f"Returning {len(recommendations)} recommendations")

        return RecommendationResponse(
            query=request.query,
            recommendations=recommendations,
            count=len(recommendations),
        )

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Recommendation request failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
