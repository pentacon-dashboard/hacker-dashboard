"""SQLAlchemy ORM 모델 — week-3 에서 Holding/PortfolioSnapshot 재설계."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    watchlist: Mapped[list[WatchlistItem]] = relationship(back_populates="user")


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    asset_class: Mapped[str] = mapped_column(String(20), nullable=False)  # stock/crypto/fx/macro
    # week-2: market 어댑터 식별자 및 코드 추가
    market: Mapped[str | None] = mapped_column(String(20), nullable=True)
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="watchlist")


class Holding(Base):
    """week-3: 포트폴리오 보유 종목. user_id='demo' 고정 (데모 단일 사용자)."""

    __tablename__ = "holdings"

    id: Mapped[int] = mapped_column(primary_key=True)
    # demo 환경 — integer FK 대신 string user_id 사용
    user_id: Mapped[str] = mapped_column(String(50), nullable=False, default="demo")
    market: Mapped[str] = mapped_column(String(20), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    avg_cost: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    currency: Mapped[str] = mapped_column(String(4), nullable=False, default="USD")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PortfolioSnapshot(Base):
    """week-3: 일간 포트폴리오 스냅샷."""

    __tablename__ = "portfolio_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(50), nullable=False, default="demo")
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_value_krw: Mapped[Decimal] = mapped_column(Numeric(24, 4), nullable=False)
    total_pnl_krw: Mapped[Decimal] = mapped_column(Numeric(24, 4), nullable=False)
    # {"crypto": 0.5, "stock_us": 0.3, "stock_kr": 0.2}
    asset_class_breakdown: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # [{"market": "upbit", "code": "KRW-BTC", "value_krw": ..., "pnl_krw": ...}]
    holdings_detail: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("user_id", "snapshot_date", name="uq_snapshot_user_date"),
    )


# ---------------------------------------------------------------------------
# sprint-02: News/Filing RAG 인프라
# ---------------------------------------------------------------------------

class Document(Base):
    """뉴스·공시 원문 문서. source_url 을 유니크 키로 사용해 중복 적재를 방지한다."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_url: Mapped[str] = mapped_column(String(2048), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    chunks: Mapped[list[DocumentChunk]] = relationship(
        "DocumentChunk", back_populates="document", cascade="all, delete-orphan"
    )


class DocumentChunk(Base):
    """문서를 청킹한 단위. embedding VECTOR(1024) 컬럼에 벡터 저장."""

    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # pgvector VECTOR(1024)
    embedding: Mapped[str | None] = mapped_column(
        Vector(1024),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    document: Mapped[Document] = relationship("Document", back_populates="chunks")
