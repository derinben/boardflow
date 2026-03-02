"""BGG XML → validated Python models.

Parses the raw XML bytes from the BGG /thing endpoint into typed Pydantic
models for downstream loading.

Two top-level models:
  - GameInfo  — core metadata (used by info pipeline mode)
  - GameStats — ratings, weight, and ranks (used by stats pipeline mode)

Both can be extracted from the same XML response (when stats=1 is requested).
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone

from lxml import etree
from loguru import logger
from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class GameNameRecord(BaseModel):
    """An alternate or primary name entry."""

    name: str
    name_type: str  # 'primary' | 'alternate'
    sort_index: int


class LinkRecord(BaseModel):
    """A named link (category, mechanic, designer, publisher, artist, family)."""

    id: int
    name: str
    link_type: str  # e.g. 'boardgamecategory', 'boardgamemechanic', …


class RankRecord(BaseModel):
    """A single rank entry (boardgame, strategygames, etc.)."""

    rank_type: str       # 'subtype' | 'family'
    rank_name: str       # e.g. 'boardgame', 'strategygames'
    friendly_name: str
    rank_value: Optional[int]   # None means "Not Ranked"
    bayes_average: Optional[float]


# ---------------------------------------------------------------------------
# Top-level models
# ---------------------------------------------------------------------------


class GameInfo(BaseModel):
    """Core game metadata extracted from a BGG /thing XML item."""

    id: int
    primary_name: str
    year_published: Optional[int]
    description: Optional[str]
    thumbnail_url: Optional[str]
    image_url: Optional[str]
    min_players: Optional[int]
    max_players: Optional[int]
    playing_time: Optional[int]
    min_playtime: Optional[int]
    max_playtime: Optional[int]
    min_age: Optional[int]
    names: List[GameNameRecord]
    links: List[LinkRecord]

    @field_validator("primary_name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("primary_name must not be empty")
        return v


class GameStats(BaseModel):
    """Ratings and ranking data for a single game snapshot."""

    game_id: int
    users_rated: Optional[int]
    average_rating: Optional[float]
    bayes_average: Optional[float]
    stddev: Optional[float]
    owned: Optional[int]
    trading: Optional[int]
    wanting: Optional[int]
    wishing: Optional[int]
    num_comments: Optional[int]
    num_weights: Optional[int]
    average_weight: Optional[float]
    ranks: List[RankRecord]
    fetched_at: datetime


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

# Link types we care about — mapped to their relationship category.
_LINK_TYPES = {
    "boardgamecategory",
    "boardgamemechanic",
    "boardgamedesigner",
    "boardgamepublisher",
    "boardgameartist",
    "boardgamefamily",
}


def parse_game_info(xml_bytes: bytes) -> List[GameInfo]:
    """Parse raw XML into a list of GameInfo models.

    Args:
        xml_bytes: Raw bytes from the BGG /thing endpoint.

    Returns:
        List of GameInfo (one per <item> element in the response).
    """
    root = etree.fromstring(xml_bytes)
    results: List[GameInfo] = []

    for item in root.findall("item"):
        try:
            info = _parse_single_game_info(item)
            results.append(info)
        except Exception as exc:
            game_id = item.get("id", "unknown")
            logger.warning(f"Skipping game id={game_id} due to parse error: {exc}")

    logger.debug(f"Parsed {len(results)} GameInfo records from XML")
    return results


def parse_game_stats(xml_bytes: bytes, fetched_at: Optional[datetime] = None) -> List[GameStats]:
    """Parse raw XML into a list of GameStats models.

    Expects the XML to have been fetched with stats=1.

    Args:
        xml_bytes:  Raw bytes from the BGG /thing?stats=1 endpoint.
        fetched_at: Timestamp for this snapshot (defaults to now).

    Returns:
        List of GameStats (one per <item> element in the response).
    """
    if fetched_at is None:
        fetched_at = datetime.now(tz=timezone.utc)

    root = etree.fromstring(xml_bytes)
    results: List[GameStats] = []

    for item in root.findall("item"):
        try:
            stats = _parse_single_game_stats(item, fetched_at)
            results.append(stats)
        except Exception as exc:
            game_id = item.get("id", "unknown")
            logger.warning(f"Skipping stats for game id={game_id}: {exc}")

    logger.debug(f"Parsed {len(results)} GameStats records from XML")
    return results


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _int_or_none(value: Optional[str]) -> Optional[int]:
    if value is None or value in ("", "0"):
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _float_or_none(value: Optional[str]) -> Optional[float]:
    if value is None or value in ("", "0"):
        return None
    try:
        v = float(value)
        return None if v == 0.0 else v
    except ValueError:
        return None


def _attr(el: etree._Element, tag: str, attr: str = "value") -> Optional[str]:
    """Return the `attr` attribute of the first child with `tag`, or None."""
    child = el.find(tag)
    if child is None:
        return None
    return child.get(attr)


def _parse_single_game_info(item: etree._Element) -> GameInfo:
    game_id = int(item.get("id"))

    # Names
    names: List[GameNameRecord] = []
    primary_name = ""
    for name_el in item.findall("name"):
        n = GameNameRecord(
            name=name_el.get("value", ""),
            name_type=name_el.get("type", "alternate"),
            sort_index=int(name_el.get("sortindex", "1")),
        )
        names.append(n)
        if n.name_type == "primary":
            primary_name = n.name

    if not primary_name and names:
        primary_name = names[0].name

    # Links (categories, mechanics, designers, etc.)
    links: List[LinkRecord] = []
    for link_el in item.findall("link"):
        ltype = link_el.get("type", "")
        if ltype in _LINK_TYPES:
            links.append(
                LinkRecord(
                    id=int(link_el.get("id")),
                    name=link_el.get("value", ""),
                    link_type=ltype,
                )
            )

    # Description — strip HTML entities; lxml handles XML escaping already.
    desc_el = item.find("description")
    description = (desc_el.text or "").strip() if desc_el is not None else None

    return GameInfo(
        id=game_id,
        primary_name=primary_name,
        year_published=_int_or_none(_attr(item, "yearpublished")),
        description=description or None,
        thumbnail_url=(item.findtext("thumbnail") or "").strip() or None,
        image_url=(item.findtext("image") or "").strip() or None,
        min_players=_int_or_none(_attr(item, "minplayers")),
        max_players=_int_or_none(_attr(item, "maxplayers")),
        playing_time=_int_or_none(_attr(item, "playingtime")),
        min_playtime=_int_or_none(_attr(item, "minplaytime")),
        max_playtime=_int_or_none(_attr(item, "maxplaytime")),
        min_age=_int_or_none(_attr(item, "minage")),
        names=names,
        links=links,
    )


def _parse_single_game_stats(item: etree._Element, fetched_at: datetime) -> GameStats:
    game_id = int(item.get("id"))

    stats_el = item.find(".//statistics/ratings")
    if stats_el is None:
        raise ValueError(f"No <statistics><ratings> element for game_id={game_id}")

    # Ranks
    ranks: List[RankRecord] = []
    for rank_el in stats_el.findall(".//ranks/rank"):
        raw_value = rank_el.get("value", "")
        rank_value = None if raw_value in ("", "Not Ranked") else _int_or_none(raw_value)
        bayes_raw = rank_el.get("bayesaverage", "")
        ranks.append(
            RankRecord(
                rank_type=rank_el.get("type", ""),
                rank_name=rank_el.get("name", ""),
                friendly_name=rank_el.get("friendlyname", ""),
                rank_value=rank_value,
                bayes_average=_float_or_none(bayes_raw),
            )
        )

    return GameStats(
        game_id=game_id,
        users_rated=_int_or_none(_attr(stats_el, "usersrated")),
        average_rating=_float_or_none(_attr(stats_el, "average")),
        bayes_average=_float_or_none(_attr(stats_el, "bayesaverage")),
        stddev=_float_or_none(_attr(stats_el, "stddev")),
        owned=_int_or_none(_attr(stats_el, "owned")),
        trading=_int_or_none(_attr(stats_el, "trading")),
        wanting=_int_or_none(_attr(stats_el, "wanting")),
        wishing=_int_or_none(_attr(stats_el, "wishing")),
        num_comments=_int_or_none(_attr(stats_el, "numcomments")),
        num_weights=_int_or_none(_attr(stats_el, "numweights")),
        average_weight=_float_or_none(_attr(stats_el, "averageweight")),
        ranks=ranks,
        fetched_at=fetched_at,
    )
