"""Database loading layer.

Two public functions correspond to the two pipeline modes:

  load_game_info(session, games)
      Upsert game metadata into bgg.games and all related lookup/junction tables.
      Safe to call multiple times — rows are updated on conflict.

  load_game_stats(session, stats_list)
      Append a new stats snapshot into bgg.game_stats and bgg.game_ranks.
      These tables are append-only; no conflict handling is applied.

Both functions accept a SQLAlchemy AsyncSession and commit nothing — the caller
owns the transaction boundary.
"""

from typing import List

from loguru import logger
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ingestion.transform import GameInfo, GameStats, LinkRecord


# ---------------------------------------------------------------------------
# Info pipeline loader
# ---------------------------------------------------------------------------

# Maps BGG link type → (lookup table, junction table, lookup fk column name)
_LINK_TABLE_MAP: dict = {
    "boardgamecategory": ("bgg.categories", "bgg.game_categories", "category_id"),
    "boardgamemechanic": ("bgg.mechanics", "bgg.game_mechanics", "mechanic_id"),
    "boardgamedesigner": ("bgg.designers", "bgg.game_designers", "designer_id"),
    "boardgamepublisher": ("bgg.publishers", "bgg.game_publishers", "publisher_id"),
    "boardgameartist": ("bgg.artists", "bgg.game_artists", "artist_id"),
    "boardgamefamily": ("bgg.game_families", "bgg.game_family_links", "family_id"),
}


async def get_all_existing_game_ids(session: AsyncSession) -> set[int]:
    """Load ALL game IDs currently in the database.

    Returns:
        Set of all game IDs in bgg.games table.
    """
    stmt = text("SELECT id FROM bgg.games")
    result = await session.execute(stmt)
    existing_ids = {row[0] for row in result.fetchall()}

    logger.info(f"Loaded {len(existing_ids)} existing game IDs from database")
    return existing_ids


async def get_existing_game_ids(session: AsyncSession, game_ids: List[int]) -> set[int]:
    """Check which game IDs already exist in the database.

    Args:
        session: Active SQLAlchemy async session.
        game_ids: List of game IDs to check.

    Returns:
        Set of game IDs that already exist in bgg.games.
    """
    if not game_ids:
        return set()

    stmt = text("""
        SELECT id FROM bgg.games
        WHERE id = ANY(:game_ids)
    """)
    result = await session.execute(stmt, {"game_ids": game_ids})
    existing_ids = {row[0] for row in result.fetchall()}

    logger.debug(f"Found {len(existing_ids)} existing games out of {len(game_ids)} checked")
    return existing_ids


async def load_game_info(session: AsyncSession, games: List[GameInfo]) -> None:
    """Upsert game info records and all associated lookup/junction tables.

    Args:
        session: Active SQLAlchemy async session (caller manages commit/rollback).
        games:   Validated GameInfo models to persist.
    """
    if not games:
        logger.debug("load_game_info called with empty list — nothing to do")
        return

    logger.info(f"Loading {len(games)} game info records")

    for game in games:
        await _upsert_game(session, game)
        await _upsert_game_names(session, game)
        await _upsert_links(session, game)

    logger.info(f"Finished loading {len(games)} game info records")


async def _upsert_game(session: AsyncSession, game: GameInfo) -> None:
    """Insert or update a single row in bgg.games."""
    stmt = text("""
        INSERT INTO bgg.games (
            id, primary_name, year_published, description,
            thumbnail_url, image_url,
            min_players, max_players,
            playing_time, min_playtime, max_playtime,
            min_age, updated_at
        ) VALUES (
            :id, :primary_name, :year_published, :description,
            :thumbnail_url, :image_url,
            :min_players, :max_players,
            :playing_time, :min_playtime, :max_playtime,
            :min_age, NOW()
        )
        ON CONFLICT (id) DO UPDATE SET
            primary_name   = EXCLUDED.primary_name,
            year_published = EXCLUDED.year_published,
            description    = EXCLUDED.description,
            thumbnail_url  = EXCLUDED.thumbnail_url,
            image_url      = EXCLUDED.image_url,
            min_players    = EXCLUDED.min_players,
            max_players    = EXCLUDED.max_players,
            playing_time   = EXCLUDED.playing_time,
            min_playtime   = EXCLUDED.min_playtime,
            max_playtime   = EXCLUDED.max_playtime,
            min_age        = EXCLUDED.min_age,
            updated_at     = NOW()
    """)
    await session.execute(
        stmt,
        {
            "id": game.id,
            "primary_name": game.primary_name,
            "year_published": game.year_published,
            "description": game.description,
            "thumbnail_url": game.thumbnail_url,
            "image_url": game.image_url,
            "min_players": game.min_players,
            "max_players": game.max_players,
            "playing_time": game.playing_time,
            "min_playtime": game.min_playtime,
            "max_playtime": game.max_playtime,
            "min_age": game.min_age,
        },
    )


async def _upsert_game_names(session: AsyncSession, game: GameInfo) -> None:
    """Replace all name records for a game (delete + re-insert)."""
    await session.execute(
        text("DELETE FROM bgg.game_names WHERE game_id = :game_id"),
        {"game_id": game.id},
    )
    for name in game.names:
        await session.execute(
            text("""
                INSERT INTO bgg.game_names (game_id, name, name_type, sort_index)
                VALUES (:game_id, :name, :name_type, :sort_index)
            """),
            {
                "game_id": game.id,
                "name": name.name,
                "name_type": name.name_type,
                "sort_index": name.sort_index,
            },
        )


async def _upsert_links(session: AsyncSession, game: GameInfo) -> None:
    """Upsert all link records (categories, mechanics, designers, etc.)."""
    # Group links by type for bulk upsert.
    by_type: dict[str, List[LinkRecord]] = {}
    for link in game.links:
        by_type.setdefault(link.link_type, []).append(link)

    for link_type, links in by_type.items():
        if link_type not in _LINK_TABLE_MAP:
            continue
        lookup_table, junction_table, fk_col = _LINK_TABLE_MAP[link_type]

        for link in links:
            # Upsert into lookup table (id is the BGG entity id).
            await session.execute(
                text(f"""
                    INSERT INTO {lookup_table} (id, name)
                    VALUES (:id, :name)
                    ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name
                """),
                {"id": link.id, "name": link.name},
            )
            # Upsert into junction table.
            await session.execute(
                text(f"""
                    INSERT INTO {junction_table} (game_id, {fk_col})
                    VALUES (:game_id, :fk_id)
                    ON CONFLICT DO NOTHING
                """),
                {"game_id": game.id, "fk_id": link.id},
            )


# ---------------------------------------------------------------------------
# Stats pipeline loader
# ---------------------------------------------------------------------------


async def load_game_stats(session: AsyncSession, stats_list: List[GameStats]) -> None:
    """Append stats snapshots to bgg.game_stats and bgg.game_ranks.

    These tables are append-only — each call inserts new rows regardless
    of whether a row for the same game_id already exists.

    Args:
        session:    Active SQLAlchemy async session.
        stats_list: Validated GameStats models from the current pipeline run.
    """
    if not stats_list:
        logger.debug("load_game_stats called with empty list — nothing to do")
        return

    logger.info(f"Appending stats snapshots for {len(stats_list)} games")

    for stats in stats_list:
        await _insert_game_stat(session, stats)
        await _insert_game_ranks(session, stats)

    logger.info(f"Finished appending stats for {len(stats_list)} games")


async def get_ingested_game_ids(session: AsyncSession) -> List[int]:
    """Return all game IDs currently stored in bgg.games.

    Used by the stats pipeline to determine which games to refresh.

    Args:
        session: Active SQLAlchemy async session.

    Returns:
        Sorted list of game IDs.
    """
    result = await session.execute(text("SELECT id FROM bgg.games ORDER BY id"))
    rows = result.fetchall()
    ids = [row[0] for row in rows]
    logger.debug(f"Found {len(ids)} existing game IDs in bgg.games")
    return ids


async def get_game_ids_needing_stats_refresh(session: AsyncSession, max_age_days: int) -> List[int]:
    """Return game IDs where stats are missing or older than threshold.

    Args:
        session: Active SQLAlchemy async session.
        max_age_days: Only return games where last stats snapshot is older than this.

    Returns:
        Sorted list of game IDs needing stats refresh.
    """
    result = await session.execute(
        text("""
            SELECT g.id
            FROM bgg.games g
            LEFT JOIN LATERAL (
                SELECT fetched_at
                FROM bgg.game_stats
                WHERE game_id = g.id
                ORDER BY fetched_at DESC
                LIMIT 1
            ) latest_stats ON true
            WHERE latest_stats.fetched_at IS NULL
               OR latest_stats.fetched_at < NOW() - :days * INTERVAL '1 day'
            ORDER BY g.id
        """),
        {"days": max_age_days},
    )
    rows = result.fetchall()
    ids = [row[0] for row in rows]
    logger.info(
        f"Found {len(ids)} games needing stats refresh "
        f"(missing or older than {max_age_days} days)"
    )
    return ids


async def _insert_game_stat(session: AsyncSession, stats: GameStats) -> None:
    await session.execute(
        text("""
            INSERT INTO bgg.game_stats (
                game_id, users_rated, average_rating, bayes_average,
                stddev, owned, trading, wanting, wishing,
                num_comments, num_weights, average_weight, fetched_at
            ) VALUES (
                :game_id, :users_rated, :average_rating, :bayes_average,
                :stddev, :owned, :trading, :wanting, :wishing,
                :num_comments, :num_weights, :average_weight, :fetched_at
            )
        """),
        {
            "game_id": stats.game_id,
            "users_rated": stats.users_rated,
            "average_rating": stats.average_rating,
            "bayes_average": stats.bayes_average,
            "stddev": stats.stddev,
            "owned": stats.owned,
            "trading": stats.trading,
            "wanting": stats.wanting,
            "wishing": stats.wishing,
            "num_comments": stats.num_comments,
            "num_weights": stats.num_weights,
            "average_weight": stats.average_weight,
            "fetched_at": stats.fetched_at,
        },
    )


async def _insert_game_ranks(session: AsyncSession, stats: GameStats) -> None:
    for rank in stats.ranks:
        await session.execute(
            text("""
                INSERT INTO bgg.game_ranks (
                    game_id, rank_type, rank_name, friendly_name,
                    rank_value, bayes_average, fetched_at
                ) VALUES (
                    :game_id, :rank_type, :rank_name, :friendly_name,
                    :rank_value, :bayes_average, :fetched_at
                )
            """),
            {
                "game_id": stats.game_id,
                "rank_type": rank.rank_type,
                "rank_name": rank.rank_name,
                "friendly_name": rank.friendly_name,
                "rank_value": rank.rank_value,
                "bayes_average": rank.bayes_average,
                "fetched_at": stats.fetched_at,
            },
        )
