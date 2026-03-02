"""initial_bgg_schema

Revision ID: 8b21be6d2927
Revises:
Create Date: 2026-03-01

Creates the full bgg schema:
  - Lookup tables: categories, mechanics, designers, publishers, artists, game_families
  - Core table: games
  - Alternate names: game_names
  - Junction tables: game_categories, game_mechanics, game_designers,
                     game_publishers, game_artists, game_family_links
  - Partitioned stats tables (RANGE by fetched_at):
      game_stats, game_ranks
  - Initial monthly partitions for 2026-03 through 2026-06

The features schema is also created here (empty for now — pending review).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "8b21be6d2927"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Schemas
    # ------------------------------------------------------------------
    op.execute("CREATE SCHEMA IF NOT EXISTS bgg")
    op.execute("CREATE SCHEMA IF NOT EXISTS features")

    # ------------------------------------------------------------------
    # bgg.games — core game record
    # ------------------------------------------------------------------
    op.create_table(
        "games",
        sa.Column("id", sa.Integer(), nullable=False, comment="BGG game ID"),
        sa.Column("primary_name", sa.Text(), nullable=False),
        sa.Column("year_published", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("thumbnail_url", sa.Text(), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("min_players", sa.Integer(), nullable=True),
        sa.Column("max_players", sa.Integer(), nullable=True),
        sa.Column("playing_time", sa.Integer(), nullable=True),
        sa.Column("min_playtime", sa.Integer(), nullable=True),
        sa.Column("max_playtime", sa.Integer(), nullable=True),
        sa.Column("min_age", sa.Integer(), nullable=True),
        sa.Column(
            "ingested_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema="bgg",
    )
    op.create_index("ix_bgg_games_year_published", "games", ["year_published"], schema="bgg")
    op.create_index(
        "ix_bgg_games_player_counts",
        "games",
        ["min_players", "max_players"],
        schema="bgg",
    )

    # ------------------------------------------------------------------
    # bgg.game_names — alternate/primary names
    # ------------------------------------------------------------------
    op.create_table(
        "game_names",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("name_type", sa.Text(), nullable=False, comment="'primary' or 'alternate'"),
        sa.Column("sort_index", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["game_id"], ["bgg.games.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="bgg",
    )
    op.create_index("ix_bgg_game_names_game_id", "game_names", ["game_id"], schema="bgg")

    # ------------------------------------------------------------------
    # bgg.categories
    # ------------------------------------------------------------------
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False, comment="BGG category ID"),
        sa.Column("name", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_categories_name"),
        schema="bgg",
    )

    op.create_table(
        "game_categories",
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["bgg.categories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["game_id"], ["bgg.games.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("game_id", "category_id"),
        schema="bgg",
    )

    # ------------------------------------------------------------------
    # bgg.mechanics
    # ------------------------------------------------------------------
    op.create_table(
        "mechanics",
        sa.Column("id", sa.Integer(), nullable=False, comment="BGG mechanic ID"),
        sa.Column("name", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_mechanics_name"),
        schema="bgg",
    )

    op.create_table(
        "game_mechanics",
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("mechanic_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["mechanic_id"], ["bgg.mechanics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["game_id"], ["bgg.games.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("game_id", "mechanic_id"),
        schema="bgg",
    )

    # ------------------------------------------------------------------
    # bgg.designers
    # ------------------------------------------------------------------
    op.create_table(
        "designers",
        sa.Column("id", sa.Integer(), nullable=False, comment="BGG designer ID"),
        sa.Column("name", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema="bgg",
    )

    op.create_table(
        "game_designers",
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("designer_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["designer_id"], ["bgg.designers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["game_id"], ["bgg.games.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("game_id", "designer_id"),
        schema="bgg",
    )

    # ------------------------------------------------------------------
    # bgg.publishers
    # ------------------------------------------------------------------
    op.create_table(
        "publishers",
        sa.Column("id", sa.Integer(), nullable=False, comment="BGG publisher ID"),
        sa.Column("name", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema="bgg",
    )

    op.create_table(
        "game_publishers",
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("publisher_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["publisher_id"], ["bgg.publishers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["game_id"], ["bgg.games.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("game_id", "publisher_id"),
        schema="bgg",
    )

    # ------------------------------------------------------------------
    # bgg.artists
    # ------------------------------------------------------------------
    op.create_table(
        "artists",
        sa.Column("id", sa.Integer(), nullable=False, comment="BGG artist ID"),
        sa.Column("name", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema="bgg",
    )

    op.create_table(
        "game_artists",
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("artist_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["artist_id"], ["bgg.artists.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["game_id"], ["bgg.games.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("game_id", "artist_id"),
        schema="bgg",
    )

    # ------------------------------------------------------------------
    # bgg.game_families
    # ------------------------------------------------------------------
    op.create_table(
        "game_families",
        sa.Column("id", sa.Integer(), nullable=False, comment="BGG family ID"),
        sa.Column("name", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema="bgg",
    )

    op.create_table(
        "game_family_links",
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("family_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["family_id"], ["bgg.game_families.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["game_id"], ["bgg.games.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("game_id", "family_id"),
        schema="bgg",
    )

    # ------------------------------------------------------------------
    # bgg.game_stats — partitioned by RANGE(fetched_at), append-only
    #
    # SQLAlchemy cannot emit PARTITION BY via op.create_table, so raw DDL
    # is used for the parent table and per-partition creation.
    # ------------------------------------------------------------------
    op.execute("""
        CREATE TABLE bgg.game_stats (
            game_id        INTEGER      NOT NULL REFERENCES bgg.games(id) ON DELETE CASCADE,
            users_rated    INTEGER,
            average_rating NUMERIC(6,3),
            bayes_average  NUMERIC(6,3),
            stddev         NUMERIC(6,3),
            owned          INTEGER,
            trading        INTEGER,
            wanting        INTEGER,
            wishing        INTEGER,
            num_comments   INTEGER,
            num_weights    INTEGER,
            average_weight NUMERIC(4,2),
            fetched_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            PRIMARY KEY (game_id, fetched_at)
        ) PARTITION BY RANGE (fetched_at)
    """)
    op.execute("""
        CREATE TABLE bgg.game_stats_2026_03
        PARTITION OF bgg.game_stats
        FOR VALUES FROM ('2026-03-01') TO ('2026-04-01')
    """)
    op.execute("""
        CREATE TABLE bgg.game_stats_2026_04
        PARTITION OF bgg.game_stats
        FOR VALUES FROM ('2026-04-01') TO ('2026-05-01')
    """)
    op.execute("""
        CREATE TABLE bgg.game_stats_2026_05
        PARTITION OF bgg.game_stats
        FOR VALUES FROM ('2026-05-01') TO ('2026-06-01')
    """)
    op.execute("""
        CREATE TABLE bgg.game_stats_2026_06
        PARTITION OF bgg.game_stats
        FOR VALUES FROM ('2026-06-01') TO ('2026-07-01')
    """)
    # Indexes on the parent table are inherited by all partitions automatically.
    op.execute("CREATE INDEX ix_bgg_game_stats_average_rating ON bgg.game_stats (average_rating)")
    op.execute("CREATE INDEX ix_bgg_game_stats_users_rated ON bgg.game_stats (users_rated)")

    # ------------------------------------------------------------------
    # bgg.game_ranks — partitioned by RANGE(fetched_at), append-only
    # ------------------------------------------------------------------
    op.execute("""
        CREATE TABLE bgg.game_ranks (
            game_id       INTEGER      NOT NULL REFERENCES bgg.games(id) ON DELETE CASCADE,
            rank_type     TEXT         NOT NULL,
            rank_name     TEXT         NOT NULL,
            friendly_name TEXT,
            rank_value    INTEGER,
            bayes_average NUMERIC(6,3),
            fetched_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            PRIMARY KEY (game_id, rank_name, fetched_at)
        ) PARTITION BY RANGE (fetched_at)
    """)
    op.execute("""
        CREATE TABLE bgg.game_ranks_2026_03
        PARTITION OF bgg.game_ranks
        FOR VALUES FROM ('2026-03-01') TO ('2026-04-01')
    """)
    op.execute("""
        CREATE TABLE bgg.game_ranks_2026_04
        PARTITION OF bgg.game_ranks
        FOR VALUES FROM ('2026-04-01') TO ('2026-05-01')
    """)
    op.execute("""
        CREATE TABLE bgg.game_ranks_2026_05
        PARTITION OF bgg.game_ranks
        FOR VALUES FROM ('2026-05-01') TO ('2026-06-01')
    """)
    op.execute("""
        CREATE TABLE bgg.game_ranks_2026_06
        PARTITION OF bgg.game_ranks
        FOR VALUES FROM ('2026-06-01') TO ('2026-07-01')
    """)
    op.execute(
        "CREATE INDEX ix_bgg_game_ranks_rank_name_value ON bgg.game_ranks (rank_name, rank_value)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS bgg.game_ranks CASCADE")
    op.execute("DROP TABLE IF EXISTS bgg.game_stats CASCADE")
    op.drop_table("game_family_links", schema="bgg")
    op.drop_table("game_families", schema="bgg")
    op.drop_table("game_artists", schema="bgg")
    op.drop_table("artists", schema="bgg")
    op.drop_table("game_publishers", schema="bgg")
    op.drop_table("publishers", schema="bgg")
    op.drop_table("game_designers", schema="bgg")
    op.drop_table("designers", schema="bgg")
    op.drop_table("game_mechanics", schema="bgg")
    op.drop_table("mechanics", schema="bgg")
    op.drop_table("game_categories", schema="bgg")
    op.drop_table("categories", schema="bgg")
    op.drop_table("game_names", schema="bgg")
    op.drop_table("games", schema="bgg")
    op.execute("DROP SCHEMA IF EXISTS features CASCADE")
    op.execute("DROP SCHEMA IF EXISTS bgg CASCADE")
