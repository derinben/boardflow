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
import os
import sys

from dotenv import load_dotenv
from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

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


def run_info_pipeline(
    client: BGGClient,
    session: Session,
    csv_url: str,
    limit: int,
) -> None:
    """Fetch and upsert game metadata for the top `limit` ranked BGG games.

    Args:
        client:  Initialised BGGClient.
        session: Active database session.
        csv_url: URL or local file path of the BGG bg_ranks CSV dump.
        limit:   Maximum number of games to ingest.
    """
    logger.info(f"[info] Seeding game IDs from CSV (limit={limit})")
    game_ids = fetch_ranked_game_ids(csv_url, limit)
    logger.info(f"[info] Retrieved {len(game_ids)} game IDs from CSV")

    total_loaded = 0
    for xml_bytes in client.fetch_things_raw(game_ids, include_stats=False):
        games = parse_game_info(xml_bytes)
        load_game_info(session, games)
        session.commit()
        total_loaded += len(games)
        logger.info(f"[info] Committed batch — {total_loaded}/{len(game_ids)} games loaded so far")

    logger.info(f"[info] Done. Total games upserted: {total_loaded}")


def run_stats_pipeline(
    client: BGGClient,
    session: Session,
    limit: int,
    max_age_days: int,
) -> None:
    """Append a stats snapshot for games with missing or stale stats.

    Uses smart refresh: only fetches stats for games where the last snapshot
    is older than max_age_days, or games that have never had stats fetched.

    Args:
        client:  Initialised BGGClient.
        session: Active database session.
        limit:   Cap on the number of games to update (0 = all).
        max_age_days: Only refresh games where last stats are older than this.
    """
    # Smart refresh: only fetch stale or missing stats
    game_ids = get_game_ids_needing_stats_refresh(session, max_age_days)

    if limit and limit < len(game_ids):
        game_ids = game_ids[:limit]
        logger.info(f"[stats] Capped to {limit} games (total needing refresh: {len(game_ids)})")

    if not game_ids:
        logger.info("[stats] No games need stats refresh — all stats are up to date")
        return

    logger.info(f"[stats] Fetching stats for {len(game_ids)} games")

    total_loaded = 0
    for xml_bytes in client.fetch_things_raw(game_ids, include_stats=True):
        stats_list = parse_game_stats(xml_bytes)
        load_game_stats(session, stats_list)
        session.commit()
        total_loaded += len(stats_list)
        logger.info(
            f"[stats] Committed batch — {total_loaded}/{len(game_ids)} stats snapshots appended"
        )

    logger.info(f"[stats] Done. Total stats snapshots appended: {total_loaded}")


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


def main() -> None:
    args = _parse_args()

    database_url = os.environ["DATABASE_URL"]
    base_url = os.environ.get("BGG_BASE_URL", "https://boardgamegeek.com/xmlapi2")
    request_delay = float(os.environ.get("BGG_REQUEST_DELAY_SECONDS", "5"))
    api_token = os.environ.get("BGG_API_TOKEN")
    default_limit = int(os.environ.get("BGG_INGEST_LIMIT", "1000"))
    limit = args.limit or default_limit
    stats_max_age_days = int(os.environ.get("BGG_STATS_MAX_AGE_DAYS", "7"))

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

    logger.info(f"Starting boardflow pipeline (mode={args.mode}, limit={limit})")

    engine = create_engine(database_url)

    with BGGClient(
        base_url=base_url, request_delay=request_delay, api_token=api_token
    ) as client:
        with Session(engine) as session:
            if args.mode == "info":
                run_info_pipeline(client, session, csv_url=csv_source, limit=limit)
            else:
                run_stats_pipeline(
                    client, session, limit=limit, max_age_days=stats_max_age_days
                )

    logger.info("Pipeline complete")


if __name__ == "__main__":
    main()
