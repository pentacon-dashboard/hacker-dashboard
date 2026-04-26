"""sprint-08 Phase 2-D: watchlist_alerts 테이블.

Revision ID: 005_sprint08_watchlist_alerts
Revises: 004_sprint05_copilot_sessions
Create Date: 2026-04-24 00:00:00.000000

변경 이유: 워치리스트 알림 설정 CRUD 인프라 구축.
  - watchlist_alerts: 사용자별 가격 알림 (symbol/market/direction/threshold/enabled)
  - user_id 인덱스: demo user 조회 최적화
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "005_sprint08_watchlist_alerts"
down_revision = "004_sprint05_copilot_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "watchlist_alerts",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(50), nullable=False, server_default="demo"),
        sa.Column("symbol", sa.String(50), nullable=False),
        sa.Column("market", sa.String(20), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),  # "above" | "below"
        sa.Column("threshold", sa.Numeric(18, 4), nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index(
        "ix_watchlist_alerts_user_id",
        "watchlist_alerts",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_watchlist_alerts_user_id", table_name="watchlist_alerts")
    op.drop_table("watchlist_alerts")
