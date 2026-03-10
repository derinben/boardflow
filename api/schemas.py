"""API request/response schemas."""

from typing import List, Optional

from pydantic import BaseModel, Field


class RecommendationRequest(BaseModel):
    """Request body for recommendation endpoint."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Natural language query describing game preferences",
        examples=[
            "I like Catan and 7 Wonders, want something with trading",
            "I want a game for 8 players that's easy to learn",
            "Looking for a strategic war game for 2 players",
        ],
    )
    top_n: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of recommendations to return",
    )
    year_min: int = Field(
        default=2015,
        ge=1900,
        le=2030,
        description="Only recommend games published on or after this year",
    )


class GameRecommendation(BaseModel):
    """Single game recommendation response."""

    id: int
    name: str
    year_published: Optional[int] = None
    description: str
    thumbnail_url: Optional[str] = None
    image_url: Optional[str] = None
    mechanics: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    complexity: Optional[float] = Field(
        None,
        description="Complexity rating (1-5, higher = more complex)",
    )
    rating: Optional[float] = Field(
        None,
        description="Bayesian average rating (0-10)",
    )
    min_players: Optional[int] = None
    max_players: Optional[int] = None
    playing_time: Optional[int] = Field(None, description="Playing time in minutes")
    min_age: Optional[int] = None
    score: float = Field(..., description="Recommendation score (0-1)")
    explanation: str = Field(..., description="Why this game was recommended")


class RecommendationResponse(BaseModel):
    """Response from recommendation endpoint."""

    query: str = Field(..., description="Original query")
    recommendations: List[GameRecommendation] = Field(
        ...,
        description="Ranked list of game recommendations",
    )
    count: int = Field(..., description="Number of recommendations returned")


class HealthCheckResponse(BaseModel):
    """Health check response."""

    status: str = Field(default="healthy")
    database: str = Field(default="connected")
    llm: str = Field(default="configured")
