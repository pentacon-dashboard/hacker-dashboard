"""SQLAlchemy ORM 모델 — week-3 에서 Holding/PortfolioSnapshot 재설계."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="watchlist")


class Client(Base):
    """PB-managed client registry.

    `client_id` is the canonical key used by portfolio ledgers. `label` is a
    work label such as "Client C" or "고객 C"; `display_name` is the real client
    name when the PB has confirmed it.
    """

    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(50), nullable=False, default="pb-demo", index=True)
    client_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    normalized_label: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    normalized_name: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("user_id", "client_id", name="uq_clients_user_client_id"),
    )


class ClientAlias(Base):
    """Additional deterministic client lookup terms.

    alias_type separates `name`, `label`, `upload_source`, and manual aliases so
    the resolver can apply the correct precedence without treating labels as
    real names.
    """

    __tablename__ = "client_aliases"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(50), nullable=False, default="pb-demo", index=True)
    client_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    alias_type: Mapped[str] = mapped_column(String(32), nullable=False)
    alias_value: Mapped[str] = mapped_column(String(128), nullable=False)
    normalized_value: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "client_id",
            "alias_type",
            "normalized_value",
            name="uq_client_aliases_user_client_type_value",
        ),
    )


class Holding(Base):
    """week-3: 포트폴리오 보유 종목. user_id='demo' 고정 (데모 단일 사용자)."""

    __tablename__ = "holdings"

    id: Mapped[int] = mapped_column(primary_key=True)
    # demo 환경 — integer FK 대신 string user_id 사용
    user_id: Mapped[str] = mapped_column(String(50), nullable=False, default="pb-demo")
    client_id: Mapped[str] = mapped_column(
        String(50), nullable=False, default="client-001", index=True
    )
    market: Mapped[str] = mapped_column(String(20), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    avg_cost: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    currency: Mapped[str] = mapped_column(String(4), nullable=False, default="USD")
    import_batch_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    source_row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_columns: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_client_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PortfolioImportBatch(Base):
    """Durable audit record for one confirmed CSV import batch."""

    __tablename__ = "portfolio_import_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(50), nullable=False, default="pb-demo")
    client_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    import_batch_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    confirmed_mapping_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    confirmed_mapping: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    warnings: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PortfolioSnapshot(Base):
    """week-3: 일간 포트폴리오 스냅샷."""

    __tablename__ = "portfolio_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(50), nullable=False, default="pb-demo")
    client_id: Mapped[str] = mapped_column(
        String(50), nullable=False, default="client-001", index=True
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_value_krw: Mapped[Decimal] = mapped_column(Numeric(24, 4), nullable=False)
    total_pnl_krw: Mapped[Decimal] = mapped_column(Numeric(24, 4), nullable=False)
    # {"crypto": 0.5, "stock_us": 0.3, "stock_kr": 0.2}
    asset_class_breakdown: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    # [{"market": "upbit", "code": "KRW-BTC", "value_krw": ..., "pnl_krw": ...}]
    holdings_detail: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "user_id", "client_id", "snapshot_date", name="uq_snapshot_user_client_date"
        ),
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    document: Mapped[Document] = relationship("Document", back_populates="chunks")


# ---------------------------------------------------------------------------
# sprint-08 Phase 2-D: Watchlist Alerts
# ---------------------------------------------------------------------------


class WatchlistAlert(Base):
    """워치리스트 알림 설정 — 지정 가격 초과/미달 시 알림."""

    __tablename__ = "watchlist_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True, default="pb-demo")
    client_id: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, default="client-001"
    )
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)  # "NVDA", "KRW-BTC"
    market: Mapped[str] = mapped_column(String(20), nullable=False)  # "yahoo", "upbit", "naver_kr"
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # "above" | "below"
    threshold: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# migration 006: UserSettings DB 영속화
# ---------------------------------------------------------------------------


class UserSettings(Base):
    """사용자 설정 — uvicorn 재시작 후에도 유지되어야 하는 모든 설정 값.

    user_id: 데모 환경에서는 'demo-user' 고정. 실 운영 시 OAuth sub 값.
    JSONB 컬럼(theme/notifications/data/connected_accounts)은 deep merge 패턴으로 PATCH 처리.
    """

    __tablename__ = "user_settings"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, default="Demo User")
    email: Mapped[str] = mapped_column(String(256), nullable=False, default="demo@demo.com")
    language: Mapped[str] = mapped_column(String(8), nullable=False, default="ko")
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Asia/Seoul")
    # JSONB 컬럼 — dict 타입으로 매핑
    theme: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=lambda: {"mode": "system", "accent": "violet"},
    )
    notifications: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=lambda: {
            "email_alerts": True,
            "push_alerts": False,
            "price_threshold_pct": 5.0,
            "daily_digest": True,
        },
    )
    data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=lambda: {
            "refresh_interval_sec": 60,
            "auto_refresh": True,
            "auto_backup": False,
            "cache_size_mb": 256,
        },
    )
    connected_accounts: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
