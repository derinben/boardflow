"""BGG CSV data dump seeder.

Loads the BGG board game rankings CSV dump (from URL or local file) and returns
the top-N game IDs sorted by rank (ascending). This is the cheapest way to get
a quality-ordered list of game IDs for the initial ingestion.

BGG CSV columns: id, rank, bggrating, avgrating, name
"""

import io
import os
from datetime import datetime
from pathlib import Path
from typing import List

import httpx
import pandas as pd
from loguru import logger


def _validate_csv_freshness(file_path: Path) -> None:
    """Check CSV file age and warn if stale.

    Reads BGG_CSV_MAX_AGE_HOURS env var (default: 24) and compares
    against file modification time. Logs a warning if file is older
    than threshold, but does not raise an error.

    Args:
        file_path: Path to the CSV file to validate.
    """
    max_age_hours = float(os.environ.get("BGG_CSV_MAX_AGE_HOURS", "24"))

    modified_time = datetime.fromtimestamp(file_path.stat().st_mtime)
    age = datetime.now() - modified_time
    age_hours = age.total_seconds() / 3600

    logger.info(
        f"CSV file age: {age_hours:.1f} hours "
        f"(last modified: {modified_time.strftime('%Y-%m-%d %H:%M:%S')})"
    )

    if age_hours > max_age_hours:
        logger.warning(
            f"⚠️  CSV file is {age_hours:.1f} hours old "
            f"(threshold: {max_age_hours} hours) - consider refreshing"
        )


def fetch_all_ranked_game_ids(csv_source: str) -> List[int]:
    """Load ALL ranked game IDs from CSV (no limit, no sampling).

    Args:
        csv_source: URL of the BGG bg_ranks CSV dump, or local file path.

    Returns:
        List of all game IDs where rank >= 1 (typically ~30k games).

    Raises:
        httpx.HTTPStatusError: If the CSV download fails (URL source).
        FileNotFoundError: If the local file doesn't exist (file source).
    """
    # Determine if source is a URL or local file path
    is_url = csv_source.startswith(("http://", "https://"))

    if is_url:
        logger.info(f"Downloading BGG CSV dump from {csv_source}")
        response = httpx.get(csv_source, follow_redirects=True, timeout=60.0)
        response.raise_for_status()
        logger.debug(f"CSV download complete, {len(response.content):,} bytes")
        csv_data = io.StringIO(response.text)
    else:
        # Treat as local file path
        file_path = Path(csv_source)
        if not file_path.exists():
            raise FileNotFoundError(
                f"BGG_CSV_LOCAL_PATH is set but file does not exist: {csv_source}"
            )

        logger.info(f"Reading BGG CSV dump from local file: {csv_source}")
        _validate_csv_freshness(file_path)
        file_size = file_path.stat().st_size
        logger.debug(f"File size: {file_size:,} bytes")
        csv_data = str(file_path)

    df = pd.read_csv(
        csv_data,
        usecols=["id", "rank"],
        dtype={"id": "Int64", "rank": "Int64"},
    )

    # Drop rows with missing id or rank
    df = df.dropna(subset=["id", "rank"])

    # Filter out unranked games (rank=0 or rank<1)
    df = df[df["rank"] >= 1]

    game_ids: List[int] = df["id"].astype(int).tolist()
    logger.info(f"Loaded {len(game_ids)} ranked game IDs from CSV")
    return game_ids


def load_rank_mapping(csv_source: str) -> dict[int, int]:
    """Load game_id -> rank mapping from CSV.

    Args:
        csv_source: URL of the BGG bg_ranks CSV dump, or local file path.

    Returns:
        Dict mapping game_id to its rank (for sorting in ranked mode).

    Raises:
        httpx.HTTPStatusError: If the CSV download fails (URL source).
        FileNotFoundError: If the local file doesn't exist (file source).
    """
    # Determine if source is a URL or local file path
    is_url = csv_source.startswith(("http://", "https://"))

    if is_url:
        logger.debug(f"Downloading BGG CSV for rank mapping from {csv_source}")
        response = httpx.get(csv_source, follow_redirects=True, timeout=60.0)
        response.raise_for_status()
        csv_data = io.StringIO(response.text)
    else:
        file_path = Path(csv_source)
        if not file_path.exists():
            raise FileNotFoundError(
                f"BGG_CSV_LOCAL_PATH is set but file does not exist: {csv_source}"
            )
        csv_data = str(file_path)

    df = pd.read_csv(
        csv_data,
        usecols=["id", "rank"],
        dtype={"id": "Int64", "rank": "Int64"},
    )

    df = df.dropna(subset=["id", "rank"])
    df = df[df["rank"] >= 1]

    rank_map = dict(zip(df["id"].astype(int), df["rank"].astype(int)))
    logger.debug(f"Loaded rank mapping for {len(rank_map)} games")
    return rank_map


def fetch_ranked_game_ids(csv_source: str, limit: int, ranked: bool = False) -> List[int]:
    """Load the BGG ranks CSV and return game IDs.

    Args:
        csv_source: URL of the BGG bg_ranks CSV dump, or local file path.
        limit:      Maximum number of game IDs to return.
        ranked:     If True, return top-ranked games sorted by rank.
                    If False (default), return random sample of all ranked games.

    Returns:
        List of BGG game IDs. If ranked=True, ordered by ascending rank (best first).
        If ranked=False, random sample of games.

    Raises:
        httpx.HTTPStatusError: If the CSV download fails (URL source).
        FileNotFoundError: If the local file doesn't exist (file source).
        ValueError: If `limit` is not a positive integer.
    """
    if limit < 1:
        raise ValueError(f"limit must be >= 1, got {limit}")

    # Determine if source is a URL or local file path
    is_url = csv_source.startswith(("http://", "https://"))

    if is_url:
        logger.info(f"Downloading BGG CSV dump from {csv_source}")

        # Get token from environment variable (if needed for authentication)
        token = os.getenv("BGG_API_TOKEN")

        response = httpx.get(csv_source, follow_redirects=True, timeout=60.0)
        response.raise_for_status()

        logger.debug(f"CSV download complete, {len(response.content):,} bytes")
        csv_data = io.StringIO(response.text)
    else:
        # Treat as local file path
        file_path = Path(csv_source)
        if not file_path.exists():
            raise FileNotFoundError(
                f"BGG_CSV_LOCAL_PATH is set but file does not exist: {csv_source}"
            )

        logger.info(f"Reading BGG CSV dump from local file: {csv_source}")

        # Validate file freshness
        _validate_csv_freshness(file_path)

        file_size = file_path.stat().st_size
        logger.debug(f"File size: {file_size:,} bytes")
        csv_data = str(file_path)

    df = pd.read_csv(
        csv_data,
        usecols=["id", "rank"],
        dtype={"id": "Int64", "rank": "Int64"},
    )

    # Drop rows with missing id or rank (e.g. unranked games in the dump).
    df = df.dropna(subset=["id", "rank"])

    # Filter out unranked games (rank=0 or rank<1)
    df = df[df["rank"] >= 1]

    if ranked:
        # Top-ranked games sorted by rank
        df = df.sort_values("rank").head(limit)
        game_ids: List[int] = df["id"].astype(int).tolist()
        logger.info(
            f"Selected {len(game_ids)} top-ranked game IDs (rank {df['rank'].min()} to {df['rank'].max()})"
        )
    else:
        # Random sample of games
        df = df.sample(n=min(limit, len(df)), random_state=None)  # random_state=None for true randomness
        game_ids: List[int] = df["id"].astype(int).tolist()
        logger.info(
            f"Selected {len(game_ids)} random game IDs from {len(df)} available ranked games"
        )

    return game_ids


if __name__ == "__main__":
    # Example usage - supports both URLs and local file paths
    # Use local CSV file (preferred if manually downloaded):
    csv_source = os.getenv("BGG_CSV_LOCAL_PATH", "data/bg_ranks.csv")

    # Or use URL (if authentication works):
    # csv_source = os.getenv("BGG_CSV_DUMP_URL", "https://boardgamegeek.com/data_dumps/bg_ranks")

    TOP_N = 100
    ids = fetch_ranked_game_ids(csv_source, TOP_N)
    print(ids)
