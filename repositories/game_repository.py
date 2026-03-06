"""Repository for game-related database operations."""

from typing import List, Optional

from loguru import logger
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (
    Artist,
    Category,
    CategoryStats,
    Designer,
    Game,
    GameArtist,
    GameCategory,
    GameDesigner,
    GameFamily,
    GameFamilyLink,
    GameMechanic,
    GameName,
    GamePublisher,
    GameRank,
    GameStat,
    Mechanic,
    MechanicStats,
    Publisher,
)
from schemas.game_schemas import GameCandidate, GameProfile, GameWithStats


class GameRepository:
    """Repository for game data access operations."""

    def __init__(self, session: AsyncSession):
        """Initialize with an active async session.

        Args:
            session: SQLAlchemy AsyncSession instance.
        """
        self.session = session

    async def find_games_by_names(
        self,
        names: List[str],
        fuzzy: bool = True,
        similarity_threshold: float = 0.3,
    ) -> List[dict]:
        """Lookup games by name (supports fuzzy matching via trigram).

        Args:
            names: List of game names to search for.
            fuzzy: If True, uses pg_trgm similarity for fuzzy matching.
            similarity_threshold: Minimum similarity score (0-1) for fuzzy matches.

        Returns:
            List of dicts with keys: game_id, primary_name, similarity.
        """
        if not names:
            return []

        if fuzzy:
            # Use trigram similarity for fuzzy matching
            # NOTE: Requires pg_trgm extension enabled in Postgres
            query = text("""
                SELECT DISTINCT ON (g.id)
                    g.id AS game_id,
                    g.primary_name,
                    GREATEST(
                        similarity(g.primary_name, :name),
                        MAX(similarity(gn.name, :name))
                    ) AS similarity
                FROM bgg.games g
                LEFT JOIN bgg.game_names gn ON g.id = gn.game_id
                WHERE g.primary_name % :name
                   OR gn.name % :name
                GROUP BY g.id, g.primary_name
                HAVING GREATEST(
                    similarity(g.primary_name, :name),
                    MAX(similarity(gn.name, :name))
                ) >= :threshold
                ORDER BY g.id, similarity DESC
            """)

            results = []
            for name in names:
                result = await self.session.execute(
                    query,
                    {"name": name, "threshold": similarity_threshold},
                )
                rows = result.fetchall()
                results.extend(
                    [
                        {
                            "game_id": row.game_id,
                            "primary_name": row.primary_name,
                            "similarity": float(row.similarity),
                        }
                        for row in rows
                    ]
                )

            logger.debug(f"Fuzzy search for {len(names)} names returned {len(results)} matches")
            return results
        else:
            # Exact match only
            query = text("""
                SELECT DISTINCT g.id AS game_id, g.primary_name
                FROM bgg.games g
                LEFT JOIN bgg.game_names gn ON g.id = gn.game_id
                WHERE LOWER(g.primary_name) = ANY(:names)
                   OR LOWER(gn.name) = ANY(:names)
            """)

            result = await self.session.execute(
                query,
                {"names": [n.lower() for n in names]},
            )
            rows = result.fetchall()
            results = [
                {
                    "game_id": row.game_id,
                    "primary_name": row.primary_name,
                    "similarity": 1.0,
                }
                for row in rows
            ]

            logger.debug(f"Exact search for {len(names)} names returned {len(results)} matches")
            return results

    async def get_game_profile(self, game_id: int) -> Optional[GameProfile]:
        """Get mechanics, categories, and stats for a game.

        Args:
            game_id: BGG game ID.

        Returns:
            GameProfile instance or None if game not found.
        """
        query = text("""
            SELECT
                g.id,
                g.primary_name,
                COALESCE(array_agg(DISTINCT m.name) FILTER (WHERE m.name IS NOT NULL), ARRAY[]::text[]) AS mechanics,
                COALESCE(array_agg(DISTINCT c.name) FILTER (WHERE c.name IS NOT NULL), ARRAY[]::text[]) AS categories,
                gs.average_weight,
                gs.bayes_average
            FROM bgg.games g
            LEFT JOIN bgg.game_mechanics gm ON g.id = gm.game_id
            LEFT JOIN bgg.mechanics m ON gm.mechanic_id = m.id
            LEFT JOIN bgg.game_categories gc ON g.id = gc.game_id
            LEFT JOIN bgg.categories c ON gc.category_id = c.id
            LEFT JOIN LATERAL (
                SELECT average_weight, bayes_average
                FROM bgg.game_stats
                WHERE game_id = g.id
                ORDER BY fetched_at DESC
                LIMIT 1
            ) gs ON true
            WHERE g.id = :game_id
            GROUP BY g.id, g.primary_name, gs.average_weight, gs.bayes_average
        """)

        result = await self.session.execute(query, {"game_id": game_id})
        row = result.fetchone()

        if not row:
            return None

        return GameProfile(
            game_id=row.id,
            primary_name=row.primary_name,
            mechanics=row.mechanics,
            categories=row.categories,
            avg_weight=float(row.average_weight) if row.average_weight else None,
            bayes_average=float(row.bayes_average) if row.bayes_average else None,
        )

    async def get_candidate_games(
        self,
        year_min: int = 2015,
        exclude_ids: Optional[List[int]] = None,
    ) -> List[GameCandidate]:
        """Fetch all games for ranking (minimal hard filters).

        Args:
            year_min: Minimum year published (default: 2015 for "recent" games).
            exclude_ids: List of game IDs to exclude (e.g., games user already owns).

        Returns:
            List of GameCandidate instances.
        """
        exclude_ids = exclude_ids or []

        query = text("""
            SELECT
                g.id,
                g.primary_name,
                g.year_published,
                g.min_players,
                g.max_players,
                g.playing_time,
                COALESCE(array_agg(DISTINCT m.name) FILTER (WHERE m.name IS NOT NULL), ARRAY[]::text[]) AS mechanics,
                COALESCE(array_agg(DISTINCT c.name) FILTER (WHERE c.name IS NOT NULL), ARRAY[]::text[]) AS categories,
                gs.average_weight,
                gs.bayes_average
            FROM bgg.games g
            LEFT JOIN bgg.game_mechanics gm ON g.id = gm.game_id
            LEFT JOIN bgg.mechanics m ON gm.mechanic_id = m.id
            LEFT JOIN bgg.game_categories gc ON g.id = gc.game_id
            LEFT JOIN bgg.categories c ON gc.category_id = c.id
            LEFT JOIN LATERAL (
                SELECT average_weight, bayes_average
                FROM bgg.game_stats
                WHERE game_id = g.id
                ORDER BY fetched_at DESC
                LIMIT 1
            ) gs ON true
            WHERE g.year_published >= :year_min
              AND (:exclude_empty OR g.id != ALL(:exclude_ids))
            GROUP BY g.id, g.primary_name, g.year_published, g.min_players, g.max_players, g.playing_time,
                     gs.average_weight, gs.bayes_average
        """)

        result = await self.session.execute(
            query,
            {
                "year_min": year_min,
                "exclude_ids": exclude_ids,
                "exclude_empty": len(exclude_ids) == 0,
            },
        )
        rows = result.fetchall()

        candidates = [
            GameCandidate(
                id=row.id,
                primary_name=row.primary_name,
                year_published=row.year_published,
                mechanics=row.mechanics,
                categories=row.categories,
                avg_weight=float(row.average_weight) if row.average_weight else None,
                bayes_average=float(row.bayes_average) if row.bayes_average else None,
                min_players=row.min_players,
                max_players=row.max_players,
                playing_time=row.playing_time,
            )
            for row in rows
        ]

        logger.info(
            f"Retrieved {len(candidates)} candidate games "
            f"(year >= {year_min}, excluded {len(exclude_ids)} IDs)"
        )
        return candidates

    async def get_games_with_stats(self, game_ids: List[int]) -> List[GameWithStats]:
        """Bulk fetch games with full details for final results.

        Args:
            game_ids: List of game IDs to fetch.

        Returns:
            List of GameWithStats instances.
        """
        if not game_ids:
            return []

        query = text("""
            SELECT
                g.id,
                g.primary_name,
                g.year_published,
                g.description,
                g.thumbnail_url,
                g.image_url,
                g.min_players,
                g.max_players,
                g.playing_time,
                g.min_age,
                COALESCE(array_agg(DISTINCT m.name) FILTER (WHERE m.name IS NOT NULL), ARRAY[]::text[]) AS mechanics,
                COALESCE(array_agg(DISTINCT c.name) FILTER (WHERE c.name IS NOT NULL), ARRAY[]::text[]) AS categories,
                gs.average_weight,
                gs.bayes_average,
                gs.users_rated,
                gs.average_rating
            FROM bgg.games g
            LEFT JOIN bgg.game_mechanics gm ON g.id = gm.game_id
            LEFT JOIN bgg.mechanics m ON gm.mechanic_id = m.id
            LEFT JOIN bgg.game_categories gc ON g.id = gc.game_id
            LEFT JOIN bgg.categories c ON gc.category_id = c.id
            LEFT JOIN LATERAL (
                SELECT average_weight, bayes_average, users_rated, average_rating
                FROM bgg.game_stats
                WHERE game_id = g.id
                ORDER BY fetched_at DESC
                LIMIT 1
            ) gs ON true
            WHERE g.id = ANY(:game_ids)
            GROUP BY g.id, g.primary_name, g.year_published, g.description, g.thumbnail_url, g.image_url,
                     g.min_players, g.max_players, g.playing_time, g.min_age,
                     gs.average_weight, gs.bayes_average, gs.users_rated, gs.average_rating
        """)

        result = await self.session.execute(query, {"game_ids": game_ids})
        rows = result.fetchall()

        games = [
            GameWithStats(
                id=row.id,
                primary_name=row.primary_name,
                year_published=row.year_published,
                description=row.description or "",
                thumbnail_url=row.thumbnail_url,
                image_url=row.image_url,
                mechanics=row.mechanics,
                categories=row.categories,
                avg_weight=float(row.average_weight) if row.average_weight else None,
                bayes_average=float(row.bayes_average) if row.bayes_average else None,
                min_players=row.min_players,
                max_players=row.max_players,
                playing_time=row.playing_time,
                min_age=row.min_age,
                users_rated=row.users_rated,
                average_rating=float(row.average_rating) if row.average_rating else None,
            )
            for row in rows
        ]

        logger.debug(f"Fetched {len(games)} games with full stats")
        return games

    async def get_idf_weights(self) -> tuple[dict[str, float], dict[str, float]]:
        """Fetch IDF weights for mechanics and categories.

        Returns:
            (mechanic_weights, category_weights) where keys are names, values are IDF weights.
            Empty dicts if no weights computed yet.
        """
        # Fetch mechanic weights
        mechanic_query = select(MechanicStats.mechanic_name, MechanicStats.idf_weight)
        result = await self.session.execute(mechanic_query)
        mechanic_rows = result.fetchall()
        mechanic_weights = {row.mechanic_name: row.idf_weight for row in mechanic_rows}

        # Fetch category weights
        category_query = select(CategoryStats.category_name, CategoryStats.idf_weight)
        result = await self.session.execute(category_query)
        category_rows = result.fetchall()
        category_weights = {row.category_name: row.idf_weight for row in category_rows}

        logger.debug(
            f"Loaded IDF weights: {len(mechanic_weights)} mechanics, "
            f"{len(category_weights)} categories"
        )

        return mechanic_weights, category_weights
