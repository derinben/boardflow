#!/usr/bin/env python3
"""Compute and store IDF weights for mechanics and categories.

Run this script after initial data ingestion and periodically (weekly/monthly)
as the games database grows.

Usage:
    python scripts/compute_idf_weights.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

from config import settings
from api.dependencies import get_session_factory
from services.idf_service import IDFService


async def main() -> None:
    """Compute IDF weights and store in database."""
    logger.info("Starting IDF weight computation")
    logger.info(f"IDF enabled: {settings.idf_enabled}")
    logger.info(f"IDF smoothing: {settings.idf_smoothing}")

    if not settings.idf_enabled:
        logger.warning("IDF is disabled in settings (IDF_ENABLED=false). Exiting.")
        return

    session_factory = get_session_factory()
    async with session_factory() as session:
        idf_service = IDFService(session, smoothing=settings.idf_smoothing)

        try:
            mechanic_weights, category_weights = await idf_service.compute_and_store_idf_weights()

            logger.success(
                f"IDF weights computed successfully: "
                f"{len(mechanic_weights)} mechanics, {len(category_weights)} categories"
            )

            # Display summary statistics
            if mechanic_weights:
                logger.info("\nTop 10 rarest mechanics:")
                top_rare = sorted(mechanic_weights.items(), key=lambda x: x[1], reverse=True)[:10]
                for name, weight in top_rare:
                    logger.info(f"  {name}: {weight:.4f}")

                logger.info("\nTop 10 most common mechanics:")
                top_common = sorted(mechanic_weights.items(), key=lambda x: x[1])[:10]
                for name, weight in top_common:
                    logger.info(f"  {name}: {weight:.4f}")

            if category_weights:
                logger.info("\nTop 10 rarest categories:")
                top_rare = sorted(category_weights.items(), key=lambda x: x[1], reverse=True)[:10]
                for name, weight in top_rare:
                    logger.info(f"  {name}: {weight:.4f}")

                logger.info("\nTop 10 most common categories:")
                top_common = sorted(category_weights.items(), key=lambda x: x[1])[:10]
                for name, weight in top_common:
                    logger.info(f"  {name}: {weight:.4f}")

        except Exception as e:
            logger.error(f"Failed to compute IDF weights: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
