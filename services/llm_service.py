"""LLM service for query extraction and explanation generation using Claude API."""

import json
from typing import Dict, List, Optional

import anthropic
import boto3
from loguru import logger
from pydantic import BaseModel, Field

from config import LLMProvider, settings


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

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        aws_region: Optional[str] = None,
    ):
        """Initialize LLM service.

        Args:
            provider: LLM provider (anthropic or bedrock). Defaults to settings.llm_provider.
            api_key: Anthropic API key (for native API). Defaults to settings.anthropic_api_key.
            model: Model name/ID. Defaults to provider-specific setting.
            aws_region: AWS region for Bedrock. Defaults to settings.aws_region.
        """
        self.provider = provider or settings.llm_provider
        self.aws_region = aws_region or settings.aws_region

        if self.provider == LLMProvider.ANTHROPIC:
            self.api_key = api_key or settings.anthropic_api_key
            if not self.api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY must be set in .env or passed to LLMService for Anthropic provider"
                )
            self.client = anthropic.Anthropic(api_key=self.api_key)
            self.model = model or settings.anthropic_model
            logger.info(f"LLMService initialized with Anthropic native API, model: {self.model}")

        elif self.provider == LLMProvider.BEDROCK:
            self.bedrock_client = boto3.client(
                service_name="bedrock-runtime",
                region_name=self.aws_region,
            )
            self.model = model or settings.bedrock_model_id
            logger.info(
                f"LLMService initialized with AWS Bedrock, model: {self.model}, region: {self.aws_region}"
            )

        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def extract_intent(self, query: str) -> ExtractedIntent:
        """Extract structured intent from natural language query.

        Args:
            query: User's natural language query.

        Returns:
            ExtractedIntent with parsed games, mechanics, preferences, etc.
        """
        prompt = self._build_extraction_prompt(query)

        logger.info(f"Extracting intent from query: {query[:100]}...")

        # Get response based on provider
        if self.provider == LLMProvider.ANTHROPIC:
            content = self._call_anthropic(prompt, max_tokens=2000)
        else:  # BEDROCK
            content = self._call_bedrock(prompt, max_tokens=2000)

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

        # Get response based on provider
        if self.provider == LLMProvider.ANTHROPIC:
            explanation = self._call_anthropic(prompt, max_tokens=200)
        else:  # BEDROCK
            explanation = self._call_bedrock(prompt, max_tokens=200)

        explanation = explanation.strip()
        logger.debug(f"Generated explanation for {game_name}: {explanation[:100]}...")
        return explanation

    def _call_anthropic(self, prompt: str, max_tokens: int = 2000) -> str:
        """Call Anthropic native API.

        Args:
            prompt: User prompt.
            max_tokens: Maximum tokens to generate.

        Returns:
            Response text content.
        """
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    def _call_bedrock(self, prompt: str, max_tokens: int = 2000) -> str:
        """Call AWS Bedrock API.

        Args:
            prompt: User prompt.
            max_tokens: Maximum tokens to generate.

        Returns:
            Response text content.
        """
        # Bedrock request body for Claude models
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }

        try:
            response = self.bedrock_client.invoke_model(
                modelId=self.model,
                body=json.dumps(request_body),
            )

            # Parse response
            response_body = json.loads(response["body"].read())
            raw_text = response_body["content"][0]["text"]

            # Extract JSON from markdown code blocks or raw text
            return self._extract_json_from_text(raw_text)

        except Exception as e:
            logger.error(f"Bedrock API call failed: {e}")
            raise

    def _extract_json_from_text(self, text: str) -> str:
        """Extract JSON from text response, handling markdown code blocks.

        Args:
            text: Raw text response that may contain JSON in markdown blocks.

        Returns:
            Extracted JSON string.
        """
        # Handle markdown code blocks
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end != -1:
                return text[start:end].strip()

        # Also handle plain ``` blocks
        if "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end != -1:
                return text[start:end].strip()

        # Look for JSON object boundaries
        start_brace = text.find("{")
        if start_brace != -1:
            brace_count = 0
            for i, char in enumerate(text[start_brace:], start_brace):
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        return text[start_brace : i + 1]

        return text.strip()

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
