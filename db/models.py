"""SQLAlchemy ORM models for the boardflow project.

Schema layout:
  bgg.*   — raw data ingested from the BGG XML API
  features.* — engineered features for ML (deferred, pending review)
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Column,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    Numeric,
    Text,
    TIMESTAMP,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, relationship

# Separate metadata per schema so Alembic can manage them cleanly.
bgg_metadata = MetaData(schema="bgg")


class BggBase(DeclarativeBase):
    metadata = bgg_metadata


# ---------------------------------------------------------------------------
# Lookup / entity tables
# ---------------------------------------------------------------------------


class Game(BggBase):
    """Core board game record. One row per BGG game id."""

    __tablename__ = "games"
    __table_args__ = {"schema": "bgg"}

    id = Column(Integer, primary_key=True, comment="BGG game ID")
    primary_name = Column(Text, nullable=False)
    year_published = Column(Integer)
    description = Column(Text)
    thumbnail_url = Column(Text)
    image_url = Column(Text)
    min_players = Column(Integer)
    max_players = Column(Integer)
    playing_time = Column(Integer)
    min_playtime = Column(Integer)
    max_playtime = Column(Integer)
    min_age = Column(Integer)
    ingested_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=datetime.utcnow)

    # Relationships
    names = relationship("GameName", back_populates="game", cascade="all, delete-orphan")
    game_categories = relationship("GameCategory", back_populates="game", cascade="all, delete-orphan")
    game_mechanics = relationship("GameMechanic", back_populates="game", cascade="all, delete-orphan")
    game_designers = relationship("GameDesigner", back_populates="game", cascade="all, delete-orphan")
    game_publishers = relationship("GamePublisher", back_populates="game", cascade="all, delete-orphan")
    game_artists = relationship("GameArtist", back_populates="game", cascade="all, delete-orphan")
    game_family_links = relationship("GameFamilyLink", back_populates="game", cascade="all, delete-orphan")


class GameName(BggBase):
    """Alternate and primary names for a game."""

    __tablename__ = "game_names"
    __table_args__ = {"schema": "bgg"}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    game_id = Column(Integer, ForeignKey("bgg.games.id", ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    name_type = Column(Text, nullable=False, comment="'primary' or 'alternate'")
    sort_index = Column(Integer)

    game = relationship("Game", back_populates="names")


class Category(BggBase):
    """BGG category lookup (e.g. 'Card Game', 'Fantasy')."""

    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("name", name="uq_categories_name"), {"schema": "bgg"})

    id = Column(Integer, primary_key=True, comment="BGG category ID")
    name = Column(Text, nullable=False)

    game_categories = relationship("GameCategory", back_populates="category")


class GameCategory(BggBase):
    """Junction: game ↔ category."""

    __tablename__ = "game_categories"
    __table_args__ = {"schema": "bgg"}

    game_id = Column(
        Integer,
        ForeignKey("bgg.games.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    category_id = Column(
        Integer,
        ForeignKey("bgg.categories.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )

    game = relationship("Game", back_populates="game_categories")
    category = relationship("Category", back_populates="game_categories")


class Mechanic(BggBase):
    """BGG mechanic lookup (e.g. 'Worker Placement', 'Deck Building')."""

    __tablename__ = "mechanics"
    __table_args__ = (UniqueConstraint("name", name="uq_mechanics_name"), {"schema": "bgg"})

    id = Column(Integer, primary_key=True, comment="BGG mechanic ID")
    name = Column(Text, nullable=False)

    game_mechanics = relationship("GameMechanic", back_populates="mechanic")


class GameMechanic(BggBase):
    """Junction: game ↔ mechanic."""

    __tablename__ = "game_mechanics"
    __table_args__ = {"schema": "bgg"}

    game_id = Column(
        Integer,
        ForeignKey("bgg.games.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    mechanic_id = Column(
        Integer,
        ForeignKey("bgg.mechanics.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )

    game = relationship("Game", back_populates="game_mechanics")
    mechanic = relationship("Mechanic", back_populates="game_mechanics")


class Designer(BggBase):
    """BGG designer lookup."""

    __tablename__ = "designers"
    __table_args__ = {"schema": "bgg"}

    id = Column(Integer, primary_key=True, comment="BGG designer ID")
    name = Column(Text, nullable=False)

    game_designers = relationship("GameDesigner", back_populates="designer")


class GameDesigner(BggBase):
    """Junction: game ↔ designer."""

    __tablename__ = "game_designers"
    __table_args__ = {"schema": "bgg"}

    game_id = Column(
        Integer,
        ForeignKey("bgg.games.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    designer_id = Column(
        Integer,
        ForeignKey("bgg.designers.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )

    game = relationship("Game", back_populates="game_designers")
    designer = relationship("Designer", back_populates="game_designers")


class Publisher(BggBase):
    """BGG publisher lookup."""

    __tablename__ = "publishers"
    __table_args__ = {"schema": "bgg"}

    id = Column(Integer, primary_key=True, comment="BGG publisher ID")
    name = Column(Text, nullable=False)

    game_publishers = relationship("GamePublisher", back_populates="publisher")


class GamePublisher(BggBase):
    """Junction: game ↔ publisher."""

    __tablename__ = "game_publishers"
    __table_args__ = {"schema": "bgg"}

    game_id = Column(
        Integer,
        ForeignKey("bgg.games.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    publisher_id = Column(
        Integer,
        ForeignKey("bgg.publishers.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )

    game = relationship("Game", back_populates="game_publishers")
    publisher = relationship("Publisher", back_populates="game_publishers")


class Artist(BggBase):
    """BGG artist lookup."""

    __tablename__ = "artists"
    __table_args__ = {"schema": "bgg"}

    id = Column(Integer, primary_key=True, comment="BGG artist ID")
    name = Column(Text, nullable=False)

    game_artists = relationship("GameArtist", back_populates="artist")


class GameArtist(BggBase):
    """Junction: game ↔ artist."""

    __tablename__ = "game_artists"
    __table_args__ = {"schema": "bgg"}

    game_id = Column(
        Integer,
        ForeignKey("bgg.games.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    artist_id = Column(
        Integer,
        ForeignKey("bgg.artists.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )

    game = relationship("Game", back_populates="game_artists")
    artist = relationship("Artist", back_populates="game_artists")


class GameFamily(BggBase):
    """BGG family lookup (e.g. 'Catan', 'Ticket to Ride')."""

    __tablename__ = "game_families"
    __table_args__ = {"schema": "bgg"}

    id = Column(Integer, primary_key=True, comment="BGG family ID")
    name = Column(Text, nullable=False)

    game_family_links = relationship("GameFamilyLink", back_populates="family")


class GameFamilyLink(BggBase):
    """Junction: game ↔ game family."""

    __tablename__ = "game_family_links"
    __table_args__ = {"schema": "bgg"}

    game_id = Column(
        Integer,
        ForeignKey("bgg.games.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    family_id = Column(
        Integer,
        ForeignKey("bgg.game_families.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )

    game = relationship("Game", back_populates="game_family_links")
    family = relationship("GameFamily", back_populates="game_family_links")


# ---------------------------------------------------------------------------
# Stats tables — append-only, partitioned by fetched_at
#
# NOTE: SQLAlchemy's declarative system does not natively emit the
# PARTITION BY clause; the initial Alembic migration contains raw SQL
# for creating these as partitioned tables along with an initial
# monthly partition.
# ---------------------------------------------------------------------------


class GameStat(BggBase):
    """Aggregate stats snapshot per game per fetch run.

    Partitioned by RANGE(fetched_at) — one partition per month.
    Rows are appended, never updated.
    """

    __tablename__ = "game_stats"
    __table_args__ = {"schema": "bgg"}

    game_id = Column(
        Integer,
        ForeignKey("bgg.games.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    users_rated = Column(Integer)
    average_rating = Column(Numeric(6, 3))
    bayes_average = Column(Numeric(6, 3))
    stddev = Column(Numeric(6, 3))
    owned = Column(Integer)
    trading = Column(Integer)
    wanting = Column(Integer)
    wishing = Column(Integer)
    num_comments = Column(Integer)
    num_weights = Column(Integer)
    average_weight = Column(Numeric(4, 2))
    fetched_at = Column(
        TIMESTAMP(timezone=True),
        primary_key=True,
        nullable=False,
        server_default=text("NOW()"),
    )


class GameRank(BggBase):
    """Per-game, per-rank-type rank snapshot.

    One game can have multiple rows per fetch (boardgame rank, strategy rank, etc.).
    Partitioned by RANGE(fetched_at) — one partition per month.
    """

    __tablename__ = "game_ranks"
    __table_args__ = {"schema": "bgg"}

    game_id = Column(
        Integer,
        ForeignKey("bgg.games.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    rank_type = Column(Text, nullable=False, primary_key=True, comment="'subtype' or 'family'")
    rank_name = Column(Text, nullable=False, primary_key=True, comment="e.g. boardgame, strategygames")
    friendly_name = Column(Text, comment="Human-readable rank list name from BGG")
    rank_value = Column(Integer, comment="NULL means 'Not Ranked'")
    bayes_average = Column(Numeric(6, 3))
    fetched_at = Column(
        TIMESTAMP(timezone=True),
        primary_key=True,
        nullable=False,
        server_default=text("NOW()"),
    )


# ---------------------------------------------------------------------------
# IDF Statistics Tables — precomputed term weighting for recommendations
# ---------------------------------------------------------------------------


class MechanicStats(BggBase):
    """IDF (Inverse Document Frequency) weights for mechanics.

    Computed from game_mechanics table. Used to downweight common mechanics
    (e.g., dice rolling) and boost rare mechanics (e.g., deck building).
    """

    __tablename__ = "mechanic_stats"
    __table_args__ = {"schema": "bgg"}

    mechanic_id = Column(
        Integer,
        ForeignKey("bgg.mechanics.id", ondelete="CASCADE"),
        primary_key=True,
    )
    mechanic_name = Column(Text, nullable=False)
    document_frequency = Column(Integer, nullable=False, comment="Games using this mechanic")
    idf_weight = Column(Float, nullable=False, comment="log((N + 1) / (df + 1))")
    computed_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    mechanic = relationship("Mechanic")


class CategoryStats(BggBase):
    """IDF (Inverse Document Frequency) weights for categories.

    Computed from game_categories table. Used to downweight common categories
    and boost distinctive categories.
    """

    __tablename__ = "category_stats"
    __table_args__ = {"schema": "bgg"}

    category_id = Column(
        Integer,
        ForeignKey("bgg.categories.id", ondelete="CASCADE"),
        primary_key=True,
    )
    category_name = Column(Text, nullable=False)
    document_frequency = Column(Integer, nullable=False, comment="Games using this category")
    idf_weight = Column(Float, nullable=False, comment="log((N + 1) / (df + 1))")
    computed_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    category = relationship("Category")
