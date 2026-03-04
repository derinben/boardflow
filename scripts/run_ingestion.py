"""BGG ingestion pipeline entry point.

Usage
-----
    # Fetch metadata for the top 1000 BGG games:
    python scripts/run_ingestion.py --mode info --limit 1000

    # Append a stats snapshot for all games already in the DB:
    python scripts/run_ingestion.py --mode stats

    # Or via Makefile:
    make ingest-info
    make ingest-stats

Modes
-----
    info   — Downloads the BGG CSV dump, fetches game metadata from the API,
             upserts into bgg.games and all related lookup/junction tables.
             Safe to re-run; rows are updated on conflict.

    stats  — Fetches ratings/ranks for every game already in bgg.games,
             appends a new snapshot to bgg.game_stats and bgg.game_ranks.
             Rows are appended (full history preserved).
"""

import argparse
import asyncio
import os
import sys

from dotenv import load_dotenv
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Ensure project root is on sys.path when called as a script.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from ingestion.client import BGGClient
from ingestion.csv_seed import fetch_ranked_game_ids
from ingestion.load import (
    get_game_ids_needing_stats_refresh,
    load_game_info,
    load_game_stats,
)
from ingestion.transform import parse_game_info, parse_game_stats


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    level="INFO",
)


# ---------------------------------------------------------------------------
# Pipeline functions
# ---------------------------------------------------------------------------


async def worker(
    worker_id: int,
    client: BGGClient,
    session_factory: async_sessionmaker,
    game_ids: list[int],
    include_stats: bool,
    progress: dict,
    progress_lock: asyncio.Lock,
) -> None:
    """Single worker processing a chunk of game IDs.

    Args:
        worker_id:       Worker identifier for logging.
        client:          Shared BGGClient instance.
        session_factory: Async session factory for database operations.
        game_ids:        Chunk of game IDs for this worker to process.
        include_stats:   Whether to fetch stats (True) or info (False).
        progress:        Shared progress counter dict.
        progress_lock:   Lock for updating progress counter.
    """
    logger.info(f"[worker-{worker_id}] Starting with {len(game_ids)} games")

    async with session_factory() as session:
        total_loaded = 0
        async for xml_bytes in client.fetch_things_raw(game_ids, include_stats=include_stats):
            if include_stats:
                stats_list = parse_game_stats(xml_bytes)
                await load_game_stats(session, stats_list)
                await session.commit()
                batch_size = len(stats_list)
                total_loaded += batch_size
            else:
                games = parse_game_info(xml_bytes)
                await load_game_info(session, games)
                await session.commit()
                batch_size = len(games)
                total_loaded += batch_size

            # Update global progress
            async with progress_lock:
                progress['completed'] += batch_size
                logger.info(f"[worker-{worker_id}] Progress: {progress['completed']}/{progress['total']} games")

    logger.info(f"[worker-{worker_id}] Completed {total_loaded} games")


async def run_info_pipeline(
    base_url: str,
    request_delay: float,
    api_token: str,
    database_url: str,
    csv_url: str,
    limit: int,
    num_workers: int = 5,
) -> None:
    """Fetch and upsert game metadata for the top `limit` ranked BGG games using concurrent workers.

    Args:
        base_url:       BGG API base URL.
        request_delay:  Seconds between requests per worker.
        api_token:      BGG API token.
        database_url:   Database connection string.
        csv_url:        URL or local file path of the BGG bg_ranks CSV dump.
        limit:          Maximum number of games to ingest.
        num_workers:    Number of concurrent workers (default: 5).
    """
    logger.info(f"[info] Seeding game IDs from CSV (limit={limit})")
    game_ids = fetch_ranked_game_ids(csv_url, limit)
    logger.info(f"[info] Retrieved {len(game_ids)} game IDs from CSV")

    # Partition work among workers
    chunk_size = len(game_ids) // num_workers
    chunks = [
        game_ids[i*chunk_size:(i+1)*chunk_size if i < num_workers-1 else len(game_ids)]
        for i in range(num_workers)
    ]

    # Shared state
    cooldown_event = asyncio.Event()
    progress = {'completed': 0, 'total': len(game_ids)}
    progress_lock = asyncio.Lock()

    # Async DB engine with connection pool
    async_db_url = database_url.replace('postgresql://', 'postgresql+asyncpg://')
    engine = create_async_engine(
        async_db_url,
        pool_size=10,         # 2 per worker
        max_overflow=5,       # Burst capacity
        pool_pre_ping=True,   # Verify connections
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    # Launch workers
    async with BGGClient(base_url, request_delay, api_token, cooldown_event) as client:
        workers = [
            worker(i, client, session_factory, chunks[i], False, progress, progress_lock)
            for i in range(num_workers)
        ]
        await asyncio.gather(*workers, return_exceptions=True)

    await engine.dispose()
    logger.info(f"[info] Done. Total games upserted: {progress['completed']}")


async def run_stats_pipeline(
    base_url: str,
    request_delay: float,
    api_token: str,
    database_url: str,
    limit: int,
    max_age_days: int,
    num_workers: int = 5,
) -> None:
    """Append a stats snapshot for games with missing or stale stats using concurrent workers.

    Uses smart refresh: only fetches stats for games where the last snapshot
    is older than max_age_days, or games that have never had stats fetched.

    Args:
        base_url:       BGG API base URL.
        request_delay:  Seconds between requests per worker.
        api_token:      BGG API token.
        database_url:   Database connection string.
        limit:          Cap on the number of games to update (0 = all).
        max_age_days:   Only refresh games where last stats are older than this.
        num_workers:    Number of concurrent workers (default: 5).
    """
    # Async DB engine
    async_db_url = database_url.replace('postgresql://', 'postgresql+asyncpg://')
    engine = create_async_engine(
        async_db_url,
        pool_size=10,
        max_overflow=5,
        pool_pre_ping=True,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    # Smart refresh: only fetch stale or missing stats
    async with session_factory() as session:
        game_ids = await get_game_ids_needing_stats_refresh(session, max_age_days)

    if limit and limit < len(game_ids):
        game_ids = game_ids[:limit]
        logger.info(f"[stats] Capped to {limit} games (total needing refresh: {len(game_ids)})")

    if not game_ids:
        logger.info("[stats] No games need stats refresh — all stats are up to date")
        await engine.dispose()
        return

    logger.info(f"[stats] Fetching stats for {len(game_ids)} games")

    # Partition work among workers
    chunk_size = len(game_ids) // num_workers
    chunks = [
        game_ids[i*chunk_size:(i+1)*chunk_size if i < num_workers-1 else len(game_ids)]
        for i in range(num_workers)
    ]

    # Shared state
    cooldown_event = asyncio.Event()
    progress = {'completed': 0, 'total': len(game_ids)}
    progress_lock = asyncio.Lock()

    # Launch workers
    async with BGGClient(base_url, request_delay, api_token, cooldown_event) as client:
        workers = [
            worker(i, client, session_factory, chunks[i], True, progress, progress_lock)
            for i in range(num_workers)
        ]
        await asyncio.gather(*workers, return_exceptions=True)

    await engine.dispose()
    logger.info(f"[stats] Done. Total stats snapshots appended: {progress['completed']}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="BoardFlow BGG ingestion pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--mode",
        choices=["info", "stats"],
        default="info",
        help="Pipeline mode: 'info' fetches game metadata, 'stats' appends a ratings snapshot",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help=(
            "Maximum number of games to process. "
            "Defaults to BGG_INGEST_LIMIT env var (or 1000). "
            "For --mode=stats, 0 means all games in the DB."
        ),
    )
    return parser.parse_args()


async def main_async() -> None:
    args = _parse_args()

    database_url = os.environ["DATABASE_URL"]
    base_url = os.environ.get("BGG_BASE_URL", "https://boardgamegeek.com/xmlapi2")
    request_delay = float(os.environ.get("BGG_REQUEST_DELAY_SECONDS", "2"))  # Changed default to 2s
    api_token = os.environ.get("BGG_API_TOKEN")
    default_limit = int(os.environ.get("BGG_INGEST_LIMIT", "1000"))
    limit = args.limit or default_limit
    stats_max_age_days = int(os.environ.get("BGG_STATS_MAX_AGE_DAYS", "7"))
    num_workers = int(os.environ.get("BGG_NUM_WORKERS", "5"))

    # CSV source priority: BGG_CSV_LOCAL_PATH > BGG_CSV_DUMP_URL
    csv_local_path = os.environ.get("BGG_CSV_LOCAL_PATH")
    csv_dump_url = os.environ.get("BGG_CSV_DUMP_URL")

    if csv_local_path:
        csv_source = csv_local_path
        logger.info(f"CSV source: LOCAL (priority) - {csv_source}")
    elif csv_dump_url:
        csv_source = csv_dump_url
        logger.info(f"CSV source: REMOTE - {csv_source}")
    else:
        raise ValueError(
            "Either BGG_CSV_LOCAL_PATH or BGG_CSV_DUMP_URL must be set in environment"
        )

    logger.info(f"Starting boardflow pipeline (mode={args.mode}, limit={limit}, workers={num_workers})")

    if args.mode == "info":
        await run_info_pipeline(
            base_url=base_url,
            request_delay=request_delay,
            api_token=api_token,
            database_url=database_url,
            csv_url=csv_source,
            limit=limit,
            num_workers=num_workers,
        )
    else:
        await run_stats_pipeline(
            base_url=base_url,
            request_delay=request_delay,
            api_token=api_token,
            database_url=database_url,
            limit=limit,
            max_age_days=stats_max_age_days,
            num_workers=num_workers,
        )

    logger.info("Pipeline complete")


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
