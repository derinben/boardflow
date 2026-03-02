"""BGG CSV data dump seeder.

Downloads the BGG board game rankings CSV dump and returns the top-N
game IDs sorted by rank (ascending). This is the cheapest way to get
a quality-ordered list of game IDs for the initial ingestion.

BGG CSV columns: id, rank, bggrating, avgrating, name
"""

import io
from typing import List

import httpx
import pandas as pd
from loguru import logger


def fetch_ranked_game_ids(csv_url: str, limit: int) -> List[int]:
    """Download the BGG ranks CSV and return the top `limit` game IDs by rank.

    Args:
        csv_url: URL of the BGG bg_ranks CSV dump.
        limit:   Maximum number of game IDs to return.

    Returns:
        List of BGG game IDs ordered by ascending rank (best first).

    Raises:
        httpx.HTTPStatusError: If the CSV download fails.
        ValueError: If `limit` is not a positive integer.
    """
    if limit < 1:
        raise ValueError(f"limit must be >= 1, got {limit}")

    logger.info(f"Downloading BGG CSV dump from {csv_url}")
    response = httpx.get(csv_url, follow_redirects=True, timeout=60.0)
    response.raise_for_status()

    logger.debug(f"CSV download complete, {len(response.content):,} bytes")

    df = pd.read_csv(
        io.StringIO(response.text),
        usecols=["id", "rank"],
        dtype={"id": "Int64", "rank": "Int64"},
    )

    # Drop rows with missing id or rank (e.g. unranked games in the dump).
    df = df.dropna(subset=["id", "rank"])
    df = df.sort_values("rank").head(limit)

    game_ids: List[int] = df["id"].astype(int).tolist()
    logger.info(f"Selected {len(game_ids)} game IDs (rank 1 to {df['rank'].max()})")
    return game_ids
