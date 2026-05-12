"""durable partial import schema foundation

Revision ID: 010_durable_partial_import_core
Revises: 009_client_registry
Create Date: 2026-05-13
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "010_durable_partial_import_core"
down_revision = "009_client_registry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "holdings",
        "avg_cost",
        existing_type=sa.Numeric(24, 8),
        nullable=True,
    )
    op.add_column(
        "holdings",
        sa.Column(
            "cost_basis_status",
            sa.String(length=32),
            nullable=False,
            server_default="provided",
        ),
    )
    op.create_check_constraint(
        "ck_holdings_cost_basis_status",
        "holdings",
        "cost_basis_status IN ('provided', 'missing', 'derived', 'needs_review')",
    )

    op.create_table(
        "portfolio_import_rows",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(length=50), nullable=False, server_default="pb-demo"),
        sa.Column("client_id", sa.String(length=50), nullable=False),
        sa.Column("import_batch_key", sa.String(length=128), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=False),
        sa.Column("row_status", sa.String(length=32), nullable=False),
        sa.Column(
            "raw_row_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "normalized_payload_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "reason_codes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("linked_holding_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.CheckConstraint(
            "row_status IN ('imported', 'recoverable', 'quarantined', 'garbage')",
            name="ck_portfolio_import_rows_status",
        ),
        sa.ForeignKeyConstraint(
            ["import_batch_key"],
            ["portfolio_import_batches.import_batch_key"],
            name="fk_portfolio_import_rows_import_batch_key",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["linked_holding_id"],
            ["holdings.id"],
            name="fk_portfolio_import_rows_linked_holding_id",
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_portfolio_import_rows_import_batch_key",
        "portfolio_import_rows",
        ["import_batch_key"],
    )
    op.create_index(
        "ix_portfolio_import_rows_client_id",
        "portfolio_import_rows",
        ["client_id"],
    )
    op.create_index(
        "ix_portfolio_import_rows_row_status",
        "portfolio_import_rows",
        ["row_status"],
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM holdings WHERE avg_cost IS NULL) THEN
                    RAISE EXCEPTION
                        'Cannot downgrade: holdings.avg_cost contains NULL cost basis rows';
                END IF;
            END $$
            """
        )
    )

    op.drop_index("ix_portfolio_import_rows_row_status", table_name="portfolio_import_rows")
    op.drop_index("ix_portfolio_import_rows_client_id", table_name="portfolio_import_rows")
    op.drop_index(
        "ix_portfolio_import_rows_import_batch_key",
        table_name="portfolio_import_rows",
    )
    op.drop_table("portfolio_import_rows")

    op.drop_constraint("ck_holdings_cost_basis_status", "holdings", type_="check")
    op.drop_column("holdings", "cost_basis_status")
    op.alter_column(
        "holdings",
        "avg_cost",
        existing_type=sa.Numeric(24, 8),
        nullable=False,
    )
