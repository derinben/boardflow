"""Recommendation service orchestrating LLM, repository, and ranking logic."""

from collections import Counter
from typing import Dict, List, Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from repositories import GameRepository
from schemas import GameCandidate, GameProfile, GameWithStats
from services.llm_service import ExtractedIntent, LLMService


class RecommendationService:
    """Service for generating game recommendations."""

    def __init__(
        self,
        session: AsyncSession,
        llm_service: LLMService,
        exploration_weight: float = 0.1,
        idf_enabled: bool = True,
    ):
        """Initialize recommendation service.

        Args:
            session: Active database session.
            llm_service: LLM service for intent extraction and explanations.
            exploration_weight: Weight for exploration/diversity (0-1).
            idf_enabled: Whether to use IDF weighting for mechanics/categories.
        """
        self.repo = GameRepository(session)
        self.llm = llm_service
        self.exploration_weight = exploration_weight
        self.idf_enabled = idf_enabled

        # IDF weights cache (loaded on first recommendation call)
        self._mechanic_idf: Optional[Dict[str, float]] = None
        self._category_idf: Optional[Dict[str, float]] = None

    async def get_recommendations(
        self,
        query: str,
        top_n: int = 10,
        year_min: int = 2015,
    ) -> List[GameWithStats]:
        """Get game recommendations from natural language query.

        Args:
            query: User's natural language query.
            top_n: Number of recommendations to return.
            year_min: Minimum year published filter.

        Returns:
            List of GameWithStats with score and explanation fields populated.
        """
        logger.info(f"Processing recommendation query: {query[:100]}...")

        # 1. Extract intent via LLM
        intent = self.llm.extract_intent(query)
        logger.debug(f"Extracted intent: {intent.model_dump()}")

        # 2. Load IDF weights (once, cached)
        await self._load_idf_weights()

        # 3. Build user profile from mentioned games
        user_profile = await self._build_user_profile(intent)
        logger.debug(f"User profile: {user_profile}")

        # 4. Fetch candidate games
        exclude_ids = [g["game_id"] for g in user_profile.get("liked_games", [])]
        candidates = await self.repo.get_candidate_games(
            year_min=year_min,
            exclude_ids=exclude_ids,
        )
        logger.info(f"Fetched {len(candidates)} candidate games")

        # 5. Rank candidates
        ranked = self._rank_candidates(candidates, user_profile, intent)
        logger.info(f"Ranked candidates, top score: {ranked[0]['score']:.3f}")

        # 6. Get full details for top N
        top_game_ids = [r["game_id"] for r in ranked[:top_n]]
        games = await self.repo.get_games_with_stats(top_game_ids)

        # 7. Add scores and explanations
        score_map = {r["game_id"]: r for r in ranked[:top_n]}
        for game in games:
            rank_data = score_map[game.id]
            game.score = rank_data["score"]
            game.explanation = self.llm.generate_explanation(
                game.primary_name,
                user_profile,
                rank_data["breakdown"],
            )

        logger.info(f"Returning {len(games)} recommendations")
        return games

    async def _load_idf_weights(self) -> None:
        """Load IDF weights from database (cached after first call)."""
        if self._mechanic_idf is not None and self._category_idf is not None:
            return  # Already loaded

        if not self.idf_enabled:
            # Use equal weights (1.0) when IDF disabled
            self._mechanic_idf = {}
            self._category_idf = {}
            logger.info("IDF weighting disabled, using equal weights")
            return

        # Load from database
        self._mechanic_idf, self._category_idf = await self.repo.get_idf_weights()

        if not self._mechanic_idf and not self._category_idf:
            logger.warning(
                "No IDF weights found in database. Run scripts/compute_idf_weights.py to initialize. "
                "Falling back to equal weights."
            )

        logger.info(
            f"Loaded IDF weights: {len(self._mechanic_idf)} mechanics, "
            f"{len(self._category_idf)} categories"
        )

    async def _build_user_profile(self, intent: ExtractedIntent) -> Dict:
        """Build user profile from games they mentioned liking.

        Args:
            intent: Extracted intent with game mentions.

        Returns:
            Dict with top_mechanics, top_categories, avg_weight, liked_games.
        """
        liked_game_names = [
            g.name for g in intent.games if g.sentiment == "like"
        ]

        if not liked_game_names:
            logger.debug("No liked games mentioned, returning empty profile")
            return {
                "top_mechanics": [],
                "top_categories": [],
                "avg_weight": None,
                "liked_games": [],
            }

        # Fuzzy match game names
        matches = await self.repo.find_games_by_names(liked_game_names, fuzzy=True)
        logger.debug(f"Matched {len(matches)} games from {len(liked_game_names)} names")

        # Fetch profiles
        profiles: List[GameProfile] = []
        for match in matches:
            profile = await self.repo.get_game_profile(match["game_id"])
            if profile:
                profiles.append(profile)

        if not profiles:
            return {
                "top_mechanics": [],
                "top_categories": [],
                "avg_weight": None,
                "liked_games": [],
            }

        # Aggregate mechanics and categories
        all_mechanics = [m for p in profiles for m in p.mechanics]
        all_categories = [c for p in profiles for c in p.categories]

        mechanic_counts = Counter(all_mechanics)
        category_counts = Counter(all_categories)

        # Average complexity
        weights = [p.avg_weight for p in profiles if p.avg_weight]
        avg_weight = sum(weights) / len(weights) if weights else None

        return {
            "top_mechanics": [m for m, _ in mechanic_counts.most_common(10)],
            "top_categories": [c for c, _ in category_counts.most_common(5)],
            "avg_weight": avg_weight,
            "liked_games": [
                {"game_id": p.game_id, "name": p.primary_name} for p in profiles
            ],
        }

    def _rank_candidates(
        self,
        candidates: List[GameCandidate],
        user_profile: Dict,
        intent: ExtractedIntent,
    ) -> List[Dict]:
        """Rank candidates by relevance score.

        Args:
            candidates: List of candidate games.
            user_profile: User preference profile.
            intent: Extracted intent with preferences.

        Returns:
            List of dicts with game_id, score, breakdown (sorted desc by score).
        """
        ranked = []

        for game in candidates:
            score, breakdown = self._score_game(game, user_profile, intent)
            ranked.append(
                {
                    "game_id": game.id,
                    "score": score,
                    "breakdown": breakdown,
                }
            )

        # Sort by score descending
        ranked.sort(key=lambda x: x["score"], reverse=True)
        return ranked

    def _score_game(
        self,
        game: GameCandidate,
        user_profile: Dict,
        intent: ExtractedIntent,
    ) -> tuple[float, Dict]:
        """Score a single game.

        Returns:
            (total_score, breakdown_dict)
        """
        # 1. Profile similarity (mechanics + categories)
        profile_score = self._profile_similarity(game, user_profile)

        # 2. Preference alignment (soft constraints)
        preference_score = self._preference_alignment(game, user_profile, intent)

        # 3. Quality baseline
        quality_score = (game.bayes_average or 0) / 10.0 * 0.25

        # 4. Exploration boost
        exploration_score = (1 - profile_score) * self.exploration_weight

        total = profile_score + preference_score + quality_score + exploration_score

        return total, {
            "profile_score": profile_score,
            "preference_score": preference_score,
            "quality_score": quality_score,
            "exploration_score": exploration_score,
        }

    def _profile_similarity(self, game: GameCandidate, user_profile: Dict) -> float:
        """Weighted Jaccard similarity for mechanics + categories.

        Uses IDF weights to boost rare mechanics/categories and downweight common ones.

        Weight: 0.3 max
        """
        user_mechanics = set(user_profile.get("top_mechanics", []))
        user_categories = set(user_profile.get("top_categories", []))
        game_mechanics = set(game.mechanics)
        game_categories = set(game.categories)

        if not user_mechanics and not user_categories:
            return 0.0

        # Weighted Jaccard for mechanics (70%)
        mech_sim = self._weighted_jaccard(user_mechanics, game_mechanics, self._mechanic_idf or {})

        # Weighted Jaccard for categories (30%)
        cat_sim = self._weighted_jaccard(user_categories, game_categories, self._category_idf or {})

        # Weighted average (mechanics 70%, categories 30%)
        similarity = (mech_sim * 0.7 + cat_sim * 0.3)
        return similarity * 0.3  # Max contribution: 0.3

    def _weighted_jaccard(
        self,
        user_items: set[str],
        game_items: set[str],
        idf_weights: Dict[str, float],
    ) -> float:
        """Compute weighted Jaccard similarity using IDF weights.

        Formula: sum(weights of intersection) / sum(weights of union)

        Args:
            user_items: User's preferred mechanics/categories.
            game_items: Game's mechanics/categories.
            idf_weights: Dict mapping item names to IDF weights.

        Returns:
            Weighted Jaccard similarity (0-1).
        """
        intersection = user_items & game_items
        union = user_items | game_items

        if not union:
            return 0.0

        # Sum IDF weights (default 1.0 if item not in weights dict)
        intersection_weight = sum(idf_weights.get(item, 1.0) for item in intersection)
        union_weight = sum(idf_weights.get(item, 1.0) for item in union)

        return intersection_weight / union_weight if union_weight > 0 else 0.0

    def _preference_alignment(
        self,
        game: GameCandidate,
        user_profile: Dict,
        intent: ExtractedIntent,
    ) -> float:
        """Soft preference alignment score.

        Weight: 0.35 max
        """
        score = 0.0

        # Player count preference (0.2 max)
        prefs = intent.preferences
        if prefs.player_count and prefs.player_count.ideal:
            ideal = prefs.player_count.ideal
            if game.min_players and game.max_players:
                if game.min_players <= ideal <= game.max_players:
                    score += 0.2
                else:
                    # Penalize distance
                    distance = min(
                        abs(game.min_players - ideal),
                        abs(game.max_players - ideal),
                    )
                    score += 0.2 * (1 / (1 + distance / 5))

        # Complexity alignment (0.15 max)
        if user_profile.get("avg_weight") and game.avg_weight:
            delta = abs(game.avg_weight - user_profile["avg_weight"])
            score += 0.15 * (1 / (1 + delta))

        return score

    def _jaccard(self, set_a: set, set_b: set) -> float:
        """Jaccard similarity coefficient."""
        if not set_a and not set_b:
            return 0.0
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union if union > 0 else 0.0
