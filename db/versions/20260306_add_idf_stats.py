"""Add IDF statistics tables for mechanic and category weighting.

Revision ID: 20260306_add_idf_stats
Revises: 8b21be6d2927
Create Date: 2026-03-06
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = "20260306_add_idf_stats"
down_revision = "8b21be6d2927"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create mechanic_stats and category_stats tables for IDF weights."""
    # Create mechanic_stats table
    op.create_table(
        "mechanic_stats",
        sa.Column("mechanic_id", sa.Integer(), nullable=False),
        sa.Column("mechanic_name", sa.Text(), nullable=False),
        sa.Column("document_frequency", sa.Integer(), nullable=False,
                  comment="Number of games using this mechanic"),
        sa.Column("idf_weight", sa.Float(), nullable=False,
                  comment="IDF weight: log((N + 1) / (df + 1))"),
        sa.Column("computed_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(
            ["mechanic_id"],
            ["bgg.mechanics.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("mechanic_id"),
        schema="bgg",
    )

    # Create category_stats table
    op.create_table(
        "category_stats",
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("category_name", sa.Text(), nullable=False),
        sa.Column("document_frequency", sa.Integer(), nullable=False,
                  comment="Number of games using this category"),
        sa.Column("idf_weight", sa.Float(), nullable=False,
                  comment="IDF weight: log((N + 1) / (df + 1))"),
        sa.Column("computed_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["bgg.categories.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("category_id"),
        schema="bgg",
    )

    # Create indexes for faster lookups
    op.create_index(
        "ix_mechanic_stats_mechanic_name",
        "mechanic_stats",
        ["mechanic_name"],
        schema="bgg",
    )
    op.create_index(
        "ix_category_stats_category_name",
        "category_stats",
        ["category_name"],
        schema="bgg",
    )


def downgrade() -> None:
    """Drop IDF statistics tables."""
    op.drop_index("ix_category_stats_category_name", table_name="category_stats", schema="bgg")
    op.drop_index("ix_mechanic_stats_mechanic_name", table_name="mechanic_stats", schema="bgg")
    op.drop_table("category_stats", schema="bgg")
    op.drop_table("mechanic_stats", schema="bgg")
