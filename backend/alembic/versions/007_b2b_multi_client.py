"""b2b multi-client portfolio scope

Revision ID: 007_b2b_multi_client
Revises: 006_user_settings
Create Date: 2026-04-30
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "007_b2b_multi_client"
down_revision = "006_user_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "holdings",
        sa.Column(
            "client_id",
            sa.String(length=50),
            nullable=False,
            server_default="client-001",
        ),
    )
    op.create_index("ix_holdings_client_id", "holdings", ["client_id"])

    op.add_column(
        "portfolio_snapshots",
        sa.Column(
            "client_id",
            sa.String(length=50),
            nullable=False,
            server_default="client-001",
        ),
    )
    op.create_index("ix_portfolio_snapshots_client_id", "portfolio_snapshots", ["client_id"])
    op.drop_constraint("uq_snapshot_user_date", "portfolio_snapshots", type_="unique")
    op.create_unique_constraint(
        "uq_snapshot_user_client_date",
        "portfolio_snapshots",
        ["user_id", "client_id", "snapshot_date"],
    )

    op.add_column(
        "watchlist_alerts",
        sa.Column(
            "client_id",
            sa.String(length=50),
            nullable=False,
            server_default="client-001",
        ),
    )
    op.create_index("ix_watchlist_alerts_client_id", "watchlist_alerts", ["client_id"])


def downgrade() -> None:
    op.drop_index("ix_watchlist_alerts_client_id", table_name="watchlist_alerts")
    op.drop_column("watchlist_alerts", "client_id")

    op.drop_constraint("uq_snapshot_user_client_date", "portfolio_snapshots", type_="unique")
    op.create_unique_constraint(
        "uq_snapshot_user_date",
        "portfolio_snapshots",
        ["user_id", "snapshot_date"],
    )
    op.drop_index("ix_portfolio_snapshots_client_id", table_name="portfolio_snapshots")
    op.drop_column("portfolio_snapshots", "client_id")

    op.drop_index("ix_holdings_client_id", table_name="holdings")
    op.drop_column("holdings", "client_id")
