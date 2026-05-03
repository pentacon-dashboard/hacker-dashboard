"""portfolio CSV import batch audit

Revision ID: 008_portfolio_import_batches
Revises: 007_b2b_multi_client
Create Date: 2026-05-02
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "008_portfolio_import_batches"
down_revision = "007_b2b_multi_client"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portfolio_import_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(length=50), nullable=False, server_default="pb-demo"),
        sa.Column("client_id", sa.String(length=50), nullable=False),
        sa.Column("import_batch_key", sa.String(length=128), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_content_hash", sa.String(length=64), nullable=False),
        sa.Column("confirmed_mapping_hash", sa.String(length=64), nullable=False),
        sa.Column("confirmed_mapping", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("warnings", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.UniqueConstraint("import_batch_key", name="uq_portfolio_import_batches_key"),
    )
    op.create_index(
        "ix_portfolio_import_batches_client_id",
        "portfolio_import_batches",
        ["client_id"],
    )

    op.add_column("holdings", sa.Column("import_batch_key", sa.String(length=128), nullable=True))
    op.add_column("holdings", sa.Column("source_row", sa.Integer(), nullable=True))
    op.add_column("holdings", sa.Column("source_columns", sa.Text(), nullable=True))
    op.add_column("holdings", sa.Column("source_client_id", sa.String(length=64), nullable=True))
    op.create_index("ix_holdings_import_batch_key", "holdings", ["import_batch_key"])


def downgrade() -> None:
    op.drop_index("ix_holdings_import_batch_key", table_name="holdings")
    op.drop_column("holdings", "source_client_id")
    op.drop_column("holdings", "source_columns")
    op.drop_column("holdings", "source_row")
    op.drop_column("holdings", "import_batch_key")

    op.drop_index("ix_portfolio_import_batches_client_id", table_name="portfolio_import_batches")
    op.drop_table("portfolio_import_batches")
