"""week3-portfolio: Holding/PortfolioSnapshot 테이블 재설계.

week-3 요구사항:
- holdings: user_id→str, market/code 분리, currency 추가, created_at 추가
- portfolio_snapshots: snapshot_date(date unique), total_value_krw, total_pnl_krw, JSONB 컬럼 추가

Revision ID: 002_week3_portfolio
Revises: 001_week2_watchlist
Create Date: 2026-04-19
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "002_week3_portfolio"
down_revision = "001_week2_watchlist"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ──────── holdings 테이블 재설계 ────────
    # 기존 테이블 삭제 후 새로 생성 (스키마 변경 범위가 크므로)
    op.drop_table("holdings")
    op.create_table(
        "holdings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(50), nullable=False, server_default="demo"),
        sa.Column("market", sa.String(20), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("quantity", sa.Numeric(24, 8), nullable=False),
        sa.Column("avg_cost", sa.Numeric(24, 8), nullable=False),
        sa.Column("currency", sa.String(4), nullable=False, server_default="USD"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # ──────── portfolio_snapshots 테이블 재설계 ────────
    op.drop_table("portfolio_snapshots")
    op.create_table(
        "portfolio_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(50), nullable=False, server_default="demo"),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("total_value_krw", sa.Numeric(24, 4), nullable=False),
        sa.Column("total_pnl_krw", sa.Numeric(24, 4), nullable=False),
        sa.Column(
            "asset_class_breakdown",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "holdings_detail",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "snapshot_date", name="uq_snapshot_user_date"),
    )

    # ──────── 데모용 더미 스냅샷 7건 시드 ────────
    # 그래프가 비어보이지 않도록 지난 7일 더미 데이터 삽입
    op.execute(
        sa.text("""
        INSERT INTO portfolio_snapshots
            (user_id, snapshot_date, total_value_krw, total_pnl_krw,
             asset_class_breakdown, holdings_detail)
        SELECT
            'demo',
            CURRENT_DATE - (n || ' days')::interval,
            5000000 + (n * 50000),
            -50000 + (n * 10000),
            '{"crypto": "0.6000", "stock_us": "0.4000"}'::jsonb,
            '[]'::jsonb
        FROM generate_series(1, 7) AS n
        ON CONFLICT (user_id, snapshot_date) DO NOTHING
        """)
    )


def downgrade() -> None:
    op.drop_table("portfolio_snapshots")
    op.drop_table("holdings")

    # week-2 스키마로 롤백
    op.create_table(
        "holdings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("asset_class", sa.String(20), nullable=False),
        sa.Column("quantity", sa.Numeric(20, 8), nullable=False),
        sa.Column("avg_cost", sa.Numeric(20, 8), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "portfolio_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("snapshot_json", sa.Text(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
