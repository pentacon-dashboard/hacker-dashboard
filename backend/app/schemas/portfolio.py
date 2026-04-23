"""포트폴리오 관련 Pydantic 스키마 — week-3."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_serializer


class HoldingCreate(BaseModel):
    market: str = Field(..., min_length=1, description="upbit | binance | yahoo | naver_kr")
    code: str = Field(..., min_length=1, description="심볼/코드 (예: KRW-BTC, AAPL)")
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


class DimensionItem(BaseModel):
    """디멘션 분석 바 차트의 단일 항목 (자산군·섹터·통화 등 차원별 집계)."""
    label: str = Field(..., description="표시 라벨 (예: 'stock_us', 'crypto')")
    weight_pct: str = Field(..., description="비중 %% (예: '43.20')")
    pnl_pct: str = Field(..., description="해당 차원의 가중 수익률 %% (예: '+3.40')")


class PortfolioSummary(BaseModel):
    """GET /portfolio/summary 응답.

    week-3 기본 필드 + sprint-07 대시보드 확장 필드 (holdings_count,
    worst_asset_pct, risk_score_pct, period_change_pct, dimension_breakdown).
    """
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
    # ── 대시보드 KPI 확장 ─────────────────────────────
    holdings_count: int = Field(0, description="보유 종목 수")
    worst_asset_pct: str = Field(
        "0.00", description="보유 종목 중 최저 손익률 %% (예: '-3.85')"
    )
    risk_score_pct: str = Field(
        "0.00",
        description="HHI 기반 집중도 리스크 점수 %% (0: 완전분산 ~ 100: 단일자산)",
    )
    period_change_pct: str = Field(
        "0.00",
        description="period_days 전 스냅샷 대비 수익률 %% (기본 30일)",
    )
    period_days: int = Field(30, description="period_change_pct 계산에 쓰인 기간(일)")
    dimension_breakdown: list[DimensionItem] = Field(
        default_factory=list,
        description="자산군 차원 비중 + 수익률 (바차트용)",
    )


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
