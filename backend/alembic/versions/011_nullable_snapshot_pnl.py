"""allow portfolio snapshots without cost-basis pnl

Revision ID: 011_nullable_snapshot_pnl
Revises: 010_durable_partial_import_core
Create Date: 2026-05-13
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "011_nullable_snapshot_pnl"
down_revision = "010_durable_partial_import_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "portfolio_snapshots",
        "total_pnl_krw",
        existing_type=sa.Numeric(24, 4),
        nullable=True,
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM portfolio_snapshots WHERE total_pnl_krw IS NULL
                ) THEN
                    RAISE EXCEPTION
                        'Cannot downgrade: portfolio_snapshots.total_pnl_krw contains NULL rows';
                END IF;
            END $$
            """
        )
    )
    op.alter_column(
        "portfolio_snapshots",
        "total_pnl_krw",
        existing_type=sa.Numeric(24, 4),
        nullable=False,
    )
