"""sprint-02: pgvector extension + documents/document_chunks 테이블.

Revision ID: 003_sprint02_pgvector_documents
Revises: 002_week3_portfolio
Create Date: 2026-04-22 11:00:00.000000

변경 이유: News/Filing RAG 인프라 구축.
  - pgvector extension 활성화 (이미 존재해도 무해)
  - documents 테이블: 원문 문서 메타데이터
  - document_chunks 테이블: 청킹 단위 + VECTOR(1024) 임베딩 컬럼
  - ivfflat 인덱스: L2 거리 기반 ANN 검색
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "003_sprint02_pgvector_documents"
down_revision = "002_week3_portfolio"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # pgvector extension 활성화 — 이미 존재해도 무해
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # documents 테이블
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_url", name="uq_documents_source_url"),
    )

    # document_chunks 테이블
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        # VECTOR(1024) 컬럼 — pgvector extension 필요
        sa.Column(
            "embedding",
            sa.Text().with_variant(
                sa.Text(), "sqlite"
            ),  # SQLite 폴백 (로컬 테스트용)
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"], ["documents.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_document_chunks_document_id",
        "document_chunks",
        ["document_id"],
    )

    # embedding 컬럼을 VECTOR(1024) 로 ALTER (Postgres 환경에서만 동작)
    op.execute(
        "ALTER TABLE document_chunks "
        "ALTER COLUMN embedding TYPE VECTOR(1024) "
        "USING embedding::VECTOR(1024)"
    )

    # ivfflat 인덱스: L2 거리 기반 ANN 검색 (lists=100 은 ~100k 문서 기준 권장값)
    op.execute(
        "CREATE INDEX ix_document_chunks_embedding_ivfflat "
        "ON document_chunks USING ivfflat (embedding vector_l2_ops) "
        "WITH (lists = 100)"
    )


def downgrade() -> None:
    op.execute(
        "DROP INDEX IF EXISTS ix_document_chunks_embedding_ivfflat"
    )
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")
    op.drop_table("document_chunks")
    op.drop_table("documents")
    # extension 은 다른 테이블이 의존할 수 있으므로 DROP 하지 않음
