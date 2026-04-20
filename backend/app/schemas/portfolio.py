"""포트폴리오 관련 Pydantic 스키마 — week-3."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_serializer


class HoldingCreate(BaseModel):
    market: str = Field(..., description="upbit | binance | yahoo | naver_kr")
    code: str = Field(..., description="심볼/코드 (예: KRW-BTC, AAPL)")
    quantity: Decimal = Field(..., gt=Decimal("0"), description="보유 수량")
    avg_cost: Decimal = Field(..., gt=Decimal("0"), description="평균 매입 단가")
    currency: str = Field(..., min_length=3, max_length=4, description="통화 코드 (KRW/USD/USDT/EUR/JPY)")


class HoldingUpdate(BaseModel):
    quantity: Decimal | None = Field(None, gt=Decimal("0"))
    avg_cost: Decimal | None = Field(None, gt=Decimal("0"))


class HoldingResponse(BaseModel):
    id: int
    user_id: str
    market: str
    code: str
    quantity: Decimal
    avg_cost: Decimal
    currency: str
    created_at: str
    updated_at: str

    @field_serializer("quantity", "avg_cost")
    def serialize_decimal(self, v: Decimal) -> str:
        return str(v)

    model_config = {"from_attributes": True}


class HoldingDetail(BaseModel):
    """집계 결과에서 종목별 상세."""
    id: int
    market: str
    code: str
    quantity: str
    avg_cost: str
    currency: str
    current_price: str
    current_price_krw: str
    value_krw: str
    cost_krw: str
    pnl_krw: str
    pnl_pct: str


class PortfolioSummary(BaseModel):
    """GET /portfolio/summary 응답."""
    user_id: str = "demo"
    total_value_krw: str
    total_cost_krw: str
    total_pnl_krw: str
    total_pnl_pct: str
    daily_change_krw: str
    daily_change_pct: str
    asset_class_breakdown: dict[str, str] = Field(
        description="{'crypto': '0.50', 'stock_us': '0.30', ...}"
    )
    holdings: list[HoldingDetail]


class SnapshotResponse(BaseModel):
    id: int
    user_id: str
    snapshot_date: str
    total_value_krw: str
    total_pnl_krw: str
    asset_class_breakdown: dict[str, Any]
    holdings_detail: list[Any]
    created_at: str

    model_config = {"from_attributes": True}
