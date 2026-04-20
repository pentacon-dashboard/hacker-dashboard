"""SQLAlchemy ORM 모델 — week-3 에서 Holding/PortfolioSnapshot 재설계."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, func
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

    watchlist: Mapped[list["WatchlistItem"]] = relationship(back_populates="user")


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
