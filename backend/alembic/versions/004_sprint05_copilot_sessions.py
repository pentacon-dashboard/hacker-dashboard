"""sprint-05: copilot_sessions + copilot_turns 테이블.

Revision ID: 004_sprint05_copilot_sessions
Revises: 003_sprint02_pgvector_documents
Create Date: 2026-04-22 12:00:00.000000

변경 이유: 세션 메모리 + follow-up 라우팅 인프라 구축.
  - copilot_sessions: 세션 메타데이터 (id, created_at, updated_at, last_turn_id)
  - copilot_turns: 세션별 턴 데이터 (jsonb 컬럼)
  - TTL/max_turns 는 애플리케이션 레이어에서 관리 (DB 레벨 삭제 없음)
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "004_sprint05_copilot_sessions"
down_revision = "003_sprint02_pgvector_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # copilot_sessions 테이블
    op.create_table(
        "copilot_sessions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("last_turn_id", sa.String(64), nullable=True),
    )

    # copilot_turns 테이블
    op.create_table(
        "copilot_turns",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(64),
            sa.ForeignKey("copilot_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("turn_idx", sa.Integer, nullable=False, default=0),
        sa.Column("query", sa.Text, nullable=False),
        sa.Column("plan_id", sa.String(64), nullable=True),
        sa.Column(
            "final_card",
            sa.dialects.postgresql.JSONB,
            nullable=True,
        ),
        sa.Column(
            "citations",
            sa.dialects.postgresql.JSONB,
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "active_context",
            sa.dialects.postgresql.JSONB,
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # 인덱스
    op.create_index(
        "ix_copilot_turns_session_id",
        "copilot_turns",
        ["session_id", "turn_idx"],
    )
    op.create_index(
        "ix_copilot_sessions_updated_at",
        "copilot_sessions",
        ["updated_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_copilot_turns_session_id", table_name="copilot_turns")
    op.drop_index("ix_copilot_sessions_updated_at", table_name="copilot_sessions")
    op.drop_table("copilot_turns")
    op.drop_table("copilot_sessions")
