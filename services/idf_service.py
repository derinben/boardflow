"""Service for computing and storing IDF (Inverse Document Frequency) weights."""

import math
from typing import Dict, Tuple

from loguru import logger
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import CategoryStats, MechanicStats


class IDFService:
    """Compute and persist IDF weights for mechanics and categories."""

    def __init__(self, session: AsyncSession, smoothing: float = 1.0):
        """Initialize IDF service.

        Args:
            session: SQLAlchemy AsyncSession instance.
            smoothing: Smoothing factor for IDF computation (default: 1.0).
        """
        self.session = session
        self.smoothing = smoothing

    async def compute_and_store_idf_weights(self) -> Tuple[Dict[str, float], Dict[str, float]]:
        """Compute IDF weights for all mechanics and categories, then store in DB.

        Formula: idf = log((N + smoothing) / (df + smoothing))
        Where:
            N = total games in database
            df = document frequency (games using mechanic/category)
            smoothing = prevents division by zero and log(0)

        Returns:
            (mechanic_weights, category_weights) dicts mapping names to IDF weights.
        """
        logger.info("Computing IDF weights for mechanics and categories")

        # 1. Count total games
        total_games_query = text("SELECT COUNT(*) FROM bgg.games")
        result = await self.session.execute(total_games_query)
        total_games = result.scalar()

        if not total_games or total_games == 0:
            logger.warning("No games in database, skipping IDF computation")
            return {}, {}

        logger.info(f"Total games in database: {total_games}")

        # 2. Compute mechanic IDF weights
        mechanic_weights = await self._compute_mechanic_idf(total_games)

        # 3. Compute category IDF weights
        category_weights = await self._compute_category_idf(total_games)

        logger.info(
            f"Computed IDF weights: {len(mechanic_weights)} mechanics, "
            f"{len(category_weights)} categories"
        )

        return mechanic_weights, category_weights

    async def _compute_mechanic_idf(self, total_games: int) -> Dict[str, float]:
        """Compute and store IDF weights for mechanics.

        Args:
            total_games: Total number of games in database.

        Returns:
            Dict mapping mechanic names to IDF weights.
        """
        # Aggregate mechanic frequencies
        query = text("""
            SELECT
                m.id AS mechanic_id,
                m.name AS mechanic_name,
                COUNT(gm.game_id) AS doc_freq
            FROM bgg.mechanics m
            LEFT JOIN bgg.game_mechanics gm ON m.id = gm.mechanic_id
            GROUP BY m.id, m.name
        """)

        result = await self.session.execute(query)
        rows = result.fetchall()

        mechanic_weights = {}

        for row in rows:
            # Compute IDF: log((N + s) / (df + s))
            idf = math.log((total_games + self.smoothing) / (row.doc_freq + self.smoothing))
            mechanic_weights[row.mechanic_name] = idf

            # Upsert into mechanic_stats
            await self.session.merge(
                MechanicStats(
                    mechanic_id=row.mechanic_id,
                    mechanic_name=row.mechanic_name,
                    document_frequency=row.doc_freq,
                    idf_weight=idf,
                )
            )

        await self.session.commit()

        # Log summary
        if mechanic_weights:
            top_rare = sorted(mechanic_weights.items(), key=lambda x: x[1], reverse=True)[:5]
            top_common = sorted(mechanic_weights.items(), key=lambda x: x[1])[:5]
            logger.info(f"Top 5 rarest mechanics: {top_rare}")
            logger.info(f"Top 5 most common mechanics: {top_common}")

        return mechanic_weights

    async def _compute_category_idf(self, total_games: int) -> Dict[str, float]:
        """Compute and store IDF weights for categories.

        Args:
            total_games: Total number of games in database.

        Returns:
            Dict mapping category names to IDF weights.
        """
        # Aggregate category frequencies
        query = text("""
            SELECT
                c.id AS category_id,
                c.name AS category_name,
                COUNT(gc.game_id) AS doc_freq
            FROM bgg.categories c
            LEFT JOIN bgg.game_categories gc ON c.id = gc.category_id
            GROUP BY c.id, c.name
        """)

        result = await self.session.execute(query)
        rows = result.fetchall()

        category_weights = {}

        for row in rows:
            # Compute IDF: log((N + s) / (df + s))
            idf = math.log((total_games + self.smoothing) / (row.doc_freq + self.smoothing))
            category_weights[row.category_name] = idf

            # Upsert into category_stats
            await self.session.merge(
                CategoryStats(
                    category_id=row.category_id,
                    category_name=row.category_name,
                    document_frequency=row.doc_freq,
                    idf_weight=idf,
                )
            )

        await self.session.commit()

        # Log summary
        if category_weights:
            top_rare = sorted(category_weights.items(), key=lambda x: x[1], reverse=True)[:5]
            top_common = sorted(category_weights.items(), key=lambda x: x[1])[:5]
            logger.info(f"Top 5 rarest categories: {top_rare}")
            logger.info(f"Top 5 most common categories: {top_common}")

        return category_weights
