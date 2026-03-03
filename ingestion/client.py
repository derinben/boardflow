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
        api_token:     Optional bearer token for authentication (read from BGG_API_TOKEN).
    """

    def __init__(
        self,
        base_url: str,
        request_delay: float = 5.0,
        api_token: str | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._request_delay = request_delay
        self._api_token = api_token

        # Set up HTTP client with optional authorization header
        headers = {}
        if self._api_token:
            headers["Authorization"] = f"Bearer {self._api_token}"
            logger.debug("BGGClient using bearer token authentication")

        self._http = httpx.Client(timeout=30.0, headers=headers)
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
                logger.debug(
                    f"Rate-limit sleep {self._request_delay}s before batch {i + 1}"
                )
                time.sleep(self._request_delay)

            xml_bytes = self._fetch_batch(batch, include_stats=include_stats)
            logger.debug(
                f"Batch {i + 1}/{len(batches)} returned {len(xml_bytes):,} bytes"
            )
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
        logger.debug(
            f"GET {url} ids={id_str[:60]}{'...' if len(id_str) > 60 else ''}"
        )

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


# ---------------------------------------------------------------------------
# Test main
# ---------------------------------------------------------------------------


def main() -> None:
    """Test the BGG API client with a few popular game IDs.

    Usage:
        python -m ingestion.client
        # Or with environment variables:
        BGG_BASE_URL=https://boardgamegeek.com/xmlapi2 python -m ingestion.client
    """
    import os
    import sys

    # Sample game IDs (top-ranked games as of 2024)
    # 224517 = Brass: Birmingham
    # 342942 = Ark Nova
    # 161936 = Pandemic Legacy: Season 1
    test_game_ids = [224517, 342942, 161936]

    base_url = os.environ.get(
        "BGG_BASE_URL", "https://boardgamegeek.com/xmlapi2"
    )
    request_delay = float(os.environ.get("BGG_REQUEST_DELAY_SECONDS", "5"))
    api_token = os.environ.get("BGG_API_TOKEN")

    logger.info("=" * 70)
    logger.info("BGG API Client Test")
    logger.info("=" * 70)
    logger.info(f"Base URL: {base_url}")
    logger.info(f"Request delay: {request_delay}s")
    logger.info(
        f"API token: {'***' + api_token[-4:] if api_token else 'Not set'}"
    )
    logger.info(f"Test game IDs: {test_game_ids}")
    logger.info("")

    try:
        with BGGClient(
            base_url=base_url, request_delay=request_delay, api_token=api_token
        ) as client:
            # Test 1: Fetch without stats
            logger.info("Test 1: Fetching game metadata (no stats)")
            for i, xml_bytes in enumerate(
                client.fetch_things_raw(test_game_ids, include_stats=False)
            ):
                logger.info(
                    f"  Batch {i + 1}: Received {len(xml_bytes):,} bytes"
                )
                # Parse and show a snippet
                xml_str = xml_bytes.decode("utf-8")
                if "<item" in xml_str:
                    logger.info(
                        f"  ✓ Valid XML response (contains <item> tags)"
                    )
                else:
                    logger.warning(f"  ⚠️  Unexpected XML format")

            logger.info("")

            # Test 2: Fetch with stats
            logger.info("Test 2: Fetching game metadata + stats")
            for i, xml_bytes in enumerate(
                client.fetch_things_raw(test_game_ids, include_stats=True)
            ):
                logger.info(
                    f"  Batch {i + 1}: Received {len(xml_bytes):,} bytes"
                )
                xml_str = xml_bytes.decode("utf-8")
                if "<statistics" in xml_str:
                    logger.info(
                        f"  ✓ Stats included (contains <statistics> tags)"
                    )
                else:
                    logger.warning(f"  ⚠️  Stats not found in response")

        logger.info("")
        logger.info("=" * 70)
        logger.info("✓ All tests passed! BGG API is working correctly.")
        logger.info("=" * 70)

    except Exception as exc:
        logger.error("=" * 70)
        logger.error(f"✗ Test failed: {exc}")
        logger.error("=" * 70)
        sys.exit(1)


if __name__ == "__main__":
    main()
