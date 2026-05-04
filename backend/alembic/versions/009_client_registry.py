"""client registry and aliases

Revision ID: 009_client_registry
Revises: 008_portfolio_import_batches
Create Date: 2026-05-04
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "009_client_registry"
down_revision = "008_portfolio_import_batches"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "clients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(length=50), nullable=False, server_default="pb-demo"),
        sa.Column("client_id", sa.String(length=50), nullable=False),
        sa.Column("label", sa.String(length=128), nullable=True),
        sa.Column("display_name", sa.String(length=128), nullable=True),
        sa.Column("normalized_label", sa.String(length=128), nullable=True),
        sa.Column("normalized_name", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.UniqueConstraint("user_id", "client_id", name="uq_clients_user_client_id"),
    )
    op.create_index("ix_clients_user_id", "clients", ["user_id"])
    op.create_index("ix_clients_client_id", "clients", ["client_id"])
    op.create_index("ix_clients_normalized_label", "clients", ["normalized_label"])
    op.create_index("ix_clients_normalized_name", "clients", ["normalized_name"])

    op.create_table(
        "client_aliases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(length=50), nullable=False, server_default="pb-demo"),
        sa.Column("client_id", sa.String(length=50), nullable=False),
        sa.Column("alias_type", sa.String(length=32), nullable=False),
        sa.Column("alias_value", sa.String(length=128), nullable=False),
        sa.Column("normalized_value", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.UniqueConstraint(
            "user_id",
            "client_id",
            "alias_type",
            "normalized_value",
            name="uq_client_aliases_user_client_type_value",
        ),
    )
    op.create_index("ix_client_aliases_user_id", "client_aliases", ["user_id"])
    op.create_index("ix_client_aliases_client_id", "client_aliases", ["client_id"])
    op.create_index(
        "ix_client_aliases_normalized_value",
        "client_aliases",
        ["normalized_value"],
    )

    op.execute(
        sa.text(
            """
            WITH source_clients AS (
                SELECT user_id, client_id FROM holdings
                UNION
                SELECT user_id, client_id FROM portfolio_snapshots
                UNION
                SELECT user_id, client_id FROM portfolio_import_batches
            ),
            labeled AS (
                SELECT
                    user_id,
                    client_id,
                    CASE
                        WHEN client_id ~ '^client-[0-9]{3}$'
                             AND substring(client_id FROM 8)::integer BETWEEN 1 AND 26
                        THEN '고객 ' || chr(64 + substring(client_id FROM 8)::integer)
                        ELSE client_id
                    END AS label
                FROM source_clients
                WHERE user_id IS NOT NULL AND client_id IS NOT NULL
            )
            INSERT INTO clients (
                user_id,
                client_id,
                label,
                normalized_label,
                status,
                created_at,
                updated_at
            )
            SELECT
                user_id,
                client_id,
                label,
                regexp_replace(lower(label), '[\\s_\\-.:/()]+', '', 'g'),
                'active',
                NOW(),
                NOW()
            FROM labeled
            ON CONFLICT ON CONSTRAINT uq_clients_user_client_id DO NOTHING
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO client_aliases (
                user_id,
                client_id,
                alias_type,
                alias_value,
                normalized_value,
                created_at
            )
            SELECT
                user_id,
                client_id,
                'label',
                label,
                normalized_label,
                NOW()
            FROM clients
            WHERE label IS NOT NULL AND normalized_label IS NOT NULL
            ON CONFLICT ON CONSTRAINT uq_client_aliases_user_client_type_value DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_client_aliases_normalized_value", table_name="client_aliases")
    op.drop_index("ix_client_aliases_client_id", table_name="client_aliases")
    op.drop_index("ix_client_aliases_user_id", table_name="client_aliases")
    op.drop_table("client_aliases")

    op.drop_index("ix_clients_normalized_name", table_name="clients")
    op.drop_index("ix_clients_normalized_label", table_name="clients")
    op.drop_index("ix_clients_client_id", table_name="clients")
    op.drop_index("ix_clients_user_id", table_name="clients")
    op.drop_table("clients")
