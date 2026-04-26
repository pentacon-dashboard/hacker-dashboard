"""006: user_settings 테이블 — uvicorn 재시작 후 설정 영속화.

Revision ID: 006_user_settings
Revises: 005_sprint08_watchlist_alerts
Create Date: 2026-04-24 00:00:00.000000

변경 이유: 기존 in-memory dict 기반 UserSettings 는 uvicorn 재시작 시 초기화되어
심사 데모 도중 설정이 날아가는 문제가 있다. Postgres 영속화로 전환한다.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "006_user_settings"
down_revision = "005_sprint08_watchlist_alerts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # JSONB DEFAULT 는 INSERT 시 app default_settings() 가 채우므로 SQL DEFAULT 생략.
    # asyncpg 의 named-param 파서가 JSON 의 `"k":v` 를 placeholder 로 오해해
    # NULL 로 치환되는 버그 회피.
    op.create_table(
        "user_settings",
        sa.Column("user_id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("email", sa.String(256), nullable=False),
        sa.Column("language", sa.String(8), nullable=False, server_default="ko"),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="Asia/Seoul"),
        sa.Column("theme", sa.dialects.postgresql.JSONB, nullable=False),
        sa.Column("notifications", sa.dialects.postgresql.JSONB, nullable=False),
        sa.Column("data", sa.dialects.postgresql.JSONB, nullable=False),
        sa.Column("connected_accounts", sa.dialects.postgresql.JSONB, nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("user_settings")
