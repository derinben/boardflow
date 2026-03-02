"""BGG XML API client.

Handles batching (max 20 IDs per request), rate limiting, and retry logic
for the BGG XMLAPI2.

BGG throttles requests that arrive too quickly. The recommended delay
between requests is at least 5 seconds. Servers return 429, 500, or 503
when throttled — all are retried with exponential back-off via tenacity.
"""

import time
from typing import Generator, List

import httpx
from loguru import logger
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

# BGG enforces a hard cap of 20 items per /thing request.
_BGG_BATCH_SIZE = 20


def _is_retriable(exc: BaseException) -> bool:
    """Return True for HTTP responses that BGG uses when throttling."""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in {429, 500, 503}
    return isinstance(exc, (httpx.TimeoutException, httpx.ConnectError))


class BGGClient:
    """Thin wrapper around the BGG XMLAPI2 /thing endpoint.

    Args:
        base_url:      API base URL (read from BGG_BASE_URL env var via caller).
        request_delay: Seconds to sleep between consecutive batches.
    """

    def __init__(self, base_url: str, request_delay: float = 5.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._request_delay = request_delay
        self._http = httpx.Client(timeout=30.0)
        logger.debug(
            f"BGGClient initialised (base_url={self._base_url}, delay={self._request_delay}s)"
        )

    def close(self) -> None:
        """Release the underlying HTTP connection pool."""
        self._http.close()

    def __enter__(self) -> "BGGClient":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_things_raw(
        self,
        game_ids: List[int],
        *,
        include_stats: bool = False,
    ) -> Generator[bytes, None, None]:
        """Yield raw XML bytes for each batch of up to 20 game IDs.

        Args:
            game_ids:      List of BGG game IDs to fetch.
            include_stats: If True, appends &stats=1 to request ratings/ranks.

        Yields:
            Raw XML bytes for each batch response.
        """
        batches = list(_chunks(game_ids, _BGG_BATCH_SIZE))
        logger.info(
            f"Fetching {len(game_ids)} games in {len(batches)} batches "
            f"(stats={'yes' if include_stats else 'no'})"
        )

        for i, batch in enumerate(batches):
            if i > 0:
                logger.debug(f"Rate-limit sleep {self._request_delay}s before batch {i + 1}")
                time.sleep(self._request_delay)

            xml_bytes = self._fetch_batch(batch, include_stats=include_stats)
            logger.debug(f"Batch {i + 1}/{len(batches)} returned {len(xml_bytes):,} bytes")
            yield xml_bytes

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @retry(
        retry=retry_if_exception(_is_retriable),
        wait=wait_exponential(multiplier=2, min=10, max=120),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def _fetch_batch(self, ids: List[int], *, include_stats: bool) -> bytes:
        """Fetch a single batch with automatic retry on retriable errors."""
        id_str = ",".join(str(i) for i in ids)
        params: dict = {"id": id_str, "type": "boardgame"}
        if include_stats:
            params["stats"] = "1"

        url = f"{self._base_url}/thing"
        logger.debug(f"GET {url} ids={id_str[:60]}{'...' if len(id_str) > 60 else ''}")

        response = self._http.get(url, params=params)
        response.raise_for_status()
        return response.content


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------


def _chunks(lst: List, size: int) -> Generator[List, None, None]:
    """Split list into successive chunks of at most `size` items."""
    for i in range(0, len(lst), size):
        yield lst[i : i + size]
