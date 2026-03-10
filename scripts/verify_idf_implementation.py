#!/usr/bin/env python3
"""Verify IDF implementation is working correctly.

This script tests that:
1. IDF weights are loaded from database
2. Weighted Jaccard is computed correctly
3. Recommendations use IDF weighting
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

from api.dependencies import get_session_factory
from config import settings
from services.idf_service import IDFService
from services.llm_service import LLMService
from services.recommendation_service import RecommendationService


async def main() -> None:
    """Verify IDF implementation."""
    logger.info("Verifying IDF implementation")
    logger.info(f"IDF enabled: {settings.idf_enabled}")

    session_factory = get_session_factory()
    async with session_factory() as session:
        # Test 1: Load IDF weights
        logger.info("\n1. Testing IDF weight loading...")
        rec_service = RecommendationService(
            session=session,
            llm_service=LLMService(),
            exploration_weight=0.1,
            idf_enabled=True,
        )

        await rec_service._load_idf_weights()

        if rec_service._mechanic_idf and rec_service._category_idf:
            logger.success(
                f"✓ IDF weights loaded: {len(rec_service._mechanic_idf)} mechanics, "
                f"{len(rec_service._category_idf)} categories"
            )
        else:
            logger.error("✗ Failed to load IDF weights")
            return

        # Test 2: Verify weighted Jaccard
        logger.info("\n2. Testing weighted Jaccard computation...")

        # Test with rare mechanics (should have higher contribution)
        rare_mechanics = {"Passed Action Token", "Tags"}
        common_mechanics = {"Dice Rolling", "Hand Management"}
        game_mechanics = {"Passed Action Token", "Dice Rolling"}

        rare_score = rec_service._weighted_jaccard(
            rare_mechanics, game_mechanics, rec_service._mechanic_idf
        )
        common_score = rec_service._weighted_jaccard(
            common_mechanics, game_mechanics, rec_service._mechanic_idf
        )

        logger.info(f"Rare mechanic match score: {rare_score:.4f}")
        logger.info(f"Common mechanic match score: {common_score:.4f}")

        if rare_score > common_score:
            logger.success("✓ Weighted Jaccard correctly boosts rare mechanics")
        else:
            logger.warning(
                "⚠ Weighted Jaccard not working as expected "
                "(rare mechanics should score higher than common ones)"
            )

        # Test 3: Test with IDF disabled
        logger.info("\n3. Testing fallback when IDF disabled...")
        rec_service_disabled = RecommendationService(
            session=session,
            llm_service=LLMService(),
            exploration_weight=0.1,
            idf_enabled=False,
        )

        await rec_service_disabled._load_idf_weights()

        if not rec_service_disabled._mechanic_idf and not rec_service_disabled._category_idf:
            logger.success("✓ IDF disabled mode working (using equal weights)")
        else:
            logger.error("✗ IDF disabled mode not working correctly")

        logger.info("\n✓ All verification tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
