"""LLM service for query extraction and explanation generation using Claude API."""

import json
import os
from typing import Dict, List, Optional

import anthropic
from loguru import logger
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------


class GameMention(BaseModel):
    """A game mentioned by the user."""

    name: str
    sentiment: str = Field(..., description="'like', 'dislike', or 'neutral'")


class PlayerCountPreference(BaseModel):
    """Player count preference."""

    min: Optional[int] = None
    max: Optional[int] = None
    ideal: Optional[int] = None
    ambiguous: Optional[str] = Field(
        None,
        description="Original ambiguous text if player count couldn't be parsed",
    )


class Preferences(BaseModel):
    """User preferences extracted from query."""

    player_count: Optional[PlayerCountPreference] = None
    complexity: Optional[str] = Field(
        None,
        description="'prefer_simple', 'prefer_complex', or 'neutral'",
    )
    playtime_max_minutes: Optional[int] = None
    recency: Optional[str] = Field(
        None,
        description="'prefer_new' or 'any'",
    )


class ExtractedIntent(BaseModel):
    """Structured intent extracted from user's natural language query."""

    games: List[GameMention] = Field(default_factory=list)
    desired_mechanics: List[str] = Field(default_factory=list)
    desired_categories: List[str] = Field(default_factory=list)
    exclude_mechanics: List[str] = Field(default_factory=list)
    exclude_categories: List[str] = Field(default_factory=list)
    preferences: Preferences = Field(default_factory=Preferences)
    ambiguities: List[str] = Field(
        default_factory=list,
        description="List of fields that need clarification (e.g., 'player_count')",
    )


# ---------------------------------------------------------------------------
# LLM Service
# ---------------------------------------------------------------------------


class LLMService:
    """Service for Claude API interactions."""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022"):
        """Initialize LLM service.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var).
            model: Claude model to use.
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY must be set or passed to LLMService")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = model
        logger.debug(f"LLMService initialized with model: {model}")

    def extract_intent(self, query: str) -> ExtractedIntent:
        """Extract structured intent from natural language query.

        Args:
            query: User's natural language query.

        Returns:
            ExtractedIntent with parsed games, mechanics, preferences, etc.
        """
        prompt = self._build_extraction_prompt(query)

        logger.info(f"Extracting intent from query: {query[:100]}...")

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        # Extract JSON from response
        content = response.content[0].text
        logger.debug(f"LLM response: {content}")

        try:
            # Parse JSON response
            data = json.loads(content)
            intent = ExtractedIntent(**data)
            logger.info(
                f"Extracted intent: {len(intent.games)} games, "
                f"{len(intent.desired_mechanics)} mechanics, "
                f"{len(intent.ambiguities)} ambiguities"
            )
            return intent
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.error(f"Response content: {content}")
            # Return empty intent on parse failure
            return ExtractedIntent()

    def generate_explanation(
        self,
        game_name: str,
        user_profile: Dict,
        score_breakdown: Dict,
    ) -> str:
        """Generate human-readable explanation for a recommendation.

        Args:
            game_name: Name of recommended game.
            user_profile: User preference profile (mechanics, categories, avg_weight).
            score_breakdown: Dict with score components (profile_match, preference_alignment, etc.).

        Returns:
            Explanation string.
        """
        prompt = f"""Generate a concise (2-3 sentences) explanation for why we recommended "{game_name}" to this user.

User Profile:
- Liked mechanics: {', '.join(user_profile.get('top_mechanics', [])[:5])}
- Liked categories: {', '.join(user_profile.get('top_categories', [])[:3])}
- Average complexity preference: {user_profile.get('avg_weight', 'unknown')}

Score Breakdown:
- Mechanic/category match: {score_breakdown.get('profile_score', 0):.2f}
- Preference alignment: {score_breakdown.get('preference_score', 0):.2f}
- Quality rating: {score_breakdown.get('quality_score', 0):.2f}

Focus on the strongest match factors. Be specific about mechanics/categories that overlap.
"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )

        explanation = response.content[0].text.strip()
        logger.debug(f"Generated explanation for {game_name}: {explanation[:100]}...")
        return explanation

    def _build_extraction_prompt(self, query: str) -> str:
        """Build the prompt for intent extraction."""
        return f"""Extract structured information from this board game recommendation query.

Query: "{query}"

Return ONLY valid JSON (no markdown, no explanations) with this exact structure:
{{
  "games": [
    {{"name": "game name", "sentiment": "like|dislike|neutral"}}
  ],
  "desired_mechanics": ["mechanic1", "mechanic2"],
  "desired_categories": ["category1", "category2"],
  "exclude_mechanics": ["mechanic to avoid"],
  "exclude_categories": ["category to avoid"],
  "preferences": {{
    "player_count": {{
      "min": null,
      "max": null,
      "ideal": null,
      "ambiguous": "original text if unclear (e.g., 'dinner party')"
    }},
    "complexity": "prefer_simple|prefer_complex|neutral",
    "playtime_max_minutes": null,
    "recency": "prefer_new|any"
  }},
  "ambiguities": ["player_count", "complexity"]
}}

Instructions:
- Extract game names mentioned (Catan, 7 Wonders, etc.) with sentiment
- Identify mechanics (trading, drafting, worker placement, deck building, etc.)
- Identify categories/themes (war, fantasy, sci-fi, party game, etc.)
- Parse preferences loosely:
  - "learn quickly", "simple", "easy" → complexity: "prefer_simple"
  - "deep", "complex", "strategic" → complexity: "prefer_complex"
  - "20 people", "large group" → player_count with ambiguous text if unclear
  - "dinner party" → player_count.ambiguous = "dinner party"
  - "fresh", "new", "recent" → recency: "prefer_new"
- List ambiguities that need clarification
- Omit fields that aren't mentioned (use null/empty)
"""
