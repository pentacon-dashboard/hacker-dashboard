"""리밸런싱 제안 Pydantic 스키마.

결정적 계산(수학)과 LLM 해석을 분리하는 구조:
- actions: 순수함수로 계산 (환각 불가)
- llm_analysis: LLM이 생성 (3단 게이트 적용)
"""
from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, StrictBool, StrictFloat, field_validator

ActionType = Literal["buy", "sell"]
AssetClassKey = Literal["stock_kr", "stock_us", "crypto", "cash", "fx"]


class TargetAllocation(BaseModel):
    """자산군별 목표 비중. 합계 1.0 (±0.001 허용)."""

    stock_kr: float = Field(0.0, ge=0, le=1)
    stock_us: float = Field(0.0, ge=0, le=1)
    crypto: float = Field(0.0, ge=0, le=1)
    cash: float = Field(0.0, ge=0, le=1)
    fx: float = Field(0.0, ge=0, le=1)

    @field_validator("fx", mode="after")
    @classmethod
    def _check_sum(cls, v: float, info: object) -> float:
        data = info.data  # type: ignore[attr-defined]
        total = (
            data.get("stock_kr", 0.0)
            + data.get("stock_us", 0.0)
            + data.get("crypto", 0.0)
            + data.get("cash", 0.0)
            + v
        )
        if abs(total - 1.0) > 0.001:
            raise ValueError(
                f"target_allocation 합계는 1.0이어야 합니다 (현재: {total:.4f})"
            )
        return v


class RebalanceConstraints(BaseModel):
    max_single_weight: StrictFloat = Field(
        0.5, ge=0, le=1, description="단일 종목 최대 비중"
    )
    min_trade_krw: Decimal = Field(
        Decimal("100000"), ge=0, description="최소 거래액(KRW)"
    )
    allow_fractional: StrictBool = Field(
        True, description="소수점 수량 허용 (주식은 기본 False 권장)"
    )


class RebalanceRequest(BaseModel):
    target_allocation: TargetAllocation
    constraints: RebalanceConstraints = Field(default_factory=RebalanceConstraints)


class RebalanceAction(BaseModel):
    action: ActionType
    market: str
    code: str
    asset_class: str
    quantity: Decimal
    estimated_value_krw: Decimal | None = None
    reason: str


class RebalanceSummary(BaseModel):
    total_trades: int
    total_sell_value_krw: Decimal
    total_buy_value_krw: Decimal
    rebalance_cost_estimate_krw: Decimal  # 거래비용 추정 (매매총액의 0.25% 가정)


class LLMAnalysis(BaseModel):
    headline: str
    narrative: str
    warnings: list[str] = Field(default_factory=list)
    confidence: float = Field(0.0, ge=0, le=1)


class RebalanceMeta(BaseModel):
    latency_ms: int | None = None
    gates: dict[str, str]
    evidence_snippets: list[str] = Field(default_factory=list)


class RebalanceResponse(BaseModel):
    request_id: str
    status: Literal["ok", "degraded", "error"]
    current_allocation: dict[str, float]
    target_allocation: dict[str, float]
    drift: dict[str, float]  # current - target (양수 = 과도, 음수 = 부족)
    actions: list[RebalanceAction]
    expected_allocation: dict[str, float]
    summary: RebalanceSummary
    llm_analysis: LLMAnalysis | None = None
    meta: RebalanceMeta
