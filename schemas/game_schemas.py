"""Pydantic models for game data transfer and API responses.

These models decouple the API/service layer from SQLAlchemy ORM models.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class GameProfile(BaseModel):
    """Game profile for building user preference profiles.

    Used to extract mechanics/categories/stats from games the user mentions.
    """

    game_id: int
    primary_name: str
    mechanics: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    avg_weight: Optional[float] = Field(
        None,
        description="Average complexity (1-5, where 5 is most complex)",
    )
    bayes_average: Optional[float] = Field(
        None,
        description="Bayesian average rating (0-10)",
    )


class GameCandidate(BaseModel):
    """Minimal game data for ranking candidates.

    Used during the ranking phase before fetching full details.
    """

    id: int
    primary_name: str
    year_published: Optional[int] = None
    mechanics: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    avg_weight: Optional[float] = None
    bayes_average: Optional[float] = None
    min_players: Optional[int] = None
    max_players: Optional[int] = None
    playing_time: Optional[int] = Field(None, description="Playing time in minutes")


class GameWithStats(BaseModel):
    """Full game details including stats and metadata.

    Used for final recommendation results shown to the user.
    """

    id: int
    primary_name: str
    year_published: Optional[int] = None
    description: str = ""
    thumbnail_url: Optional[str] = None
    image_url: Optional[str] = None
    mechanics: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    avg_weight: Optional[float] = None
    bayes_average: Optional[float] = None
    min_players: Optional[int] = None
    max_players: Optional[int] = None
    playing_time: Optional[int] = None
    min_age: Optional[int] = None
    users_rated: Optional[int] = Field(None, description="Number of users who rated this game")
    average_rating: Optional[float] = Field(None, description="Average user rating (0-10)")

    # These fields are added by the service layer during ranking
    score: Optional[float] = Field(
        None,
        description="Recommendation score (0-1, higher is better)",
    )
    explanation: Optional[str] = Field(
        None,
        description="Human-readable explanation of why this game was recommended",
    )
