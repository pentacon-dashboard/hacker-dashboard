"""
워치리스트 관련 Pydantic 스키마 — Sprint-08 B-2 + Phase 2-D (알림 CRUD).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, StrictBool

_NO_NUL_PATTERN = r"^[^\x00]+$"
_MAX_ALERT_THRESHOLD = Decimal("100000000000000")
_ALERT_THRESHOLD_STEP = 0.0001


class WatchlistItem(BaseModel):
    id: int
    market: str
    code: str
    name: str = Field(..., description="종목명 (예: 삼성전자)")
    current_price: str = Field(..., description="현재가 문자열 (예: ₩92,000)")
    change_pct: str = Field(..., description="등락률 (예: +1.23)")
    change_abs: str = Field(..., description="등락액 (예: +1,120)")
    volume_24h: str = Field(..., description="24시간 거래량 (예: 1.2M)")
    market_cap: str | None = Field(None, description="시가총액 (예: 549조)")
    pnl_7d: list[float] = Field(..., description="7일 종가 스파크라인")
    added_at: str = Field(..., description="ISO-8601 UTC 추가 시각")


class WatchlistSummary(BaseModel):
    watched_count: int = Field(..., description="워치리스트 종목 수")
    up_avg_pct: str = Field(..., description="상승 종목 평균 등락률 (예: +6.42)")
    down_avg_pct: str = Field(..., description="하락 종목 평균 등락률 (예: -4.33)")
    top_gainer_name: str = Field(..., description="최대 상승 종목명 (예: 삼성전자)")
    top_gainer_pct: str = Field(..., description="최대 상승률 (예: +12.4)")


class TopListItem(BaseModel):
    rank: int
    ticker: str
    name: str
    change_pct: str = Field(..., description="등락률 문자열 (예: +3.21)")
    views_24h: int | None = Field(None, description="24시간 조회수 (popular 전용)")


# ── Phase 2-D: 알림 CRUD 스키마 ──────────────────────────────────────────────


class WatchlistAlertCreate(BaseModel):
    """POST /watchlist/alerts 요청 본문."""

    symbol: str = Field(
        ...,
        min_length=1,
        max_length=50,
        pattern=_NO_NUL_PATTERN,
        description="심볼 (예: NVDA, KRW-BTC)",
    )
    market: str = Field(
        ...,
        min_length=1,
        max_length=20,
        pattern=_NO_NUL_PATTERN,
        description="마켓 (yahoo | upbit | naver_kr | binance)",
    )
    direction: Literal["above", "below"] = Field(..., description="above | below")
    threshold: Decimal = Field(
        ...,
        gt=Decimal("0"),
        lt=_MAX_ALERT_THRESHOLD,
        multiple_of=_ALERT_THRESHOLD_STEP,
        max_digits=18,
        decimal_places=4,
        description="알림 임계가격",
    )


class WatchlistAlertUpdate(BaseModel):
    """PATCH /watchlist/alerts/{id} 요청 본문 (부분 업데이트)."""

    enabled: StrictBool | None = Field(None, description="알림 활성화 여부")
    threshold: Decimal | None = Field(
        None,
        gt=Decimal("0"),
        lt=_MAX_ALERT_THRESHOLD,
        multiple_of=_ALERT_THRESHOLD_STEP,
        max_digits=18,
        decimal_places=4,
        description="임계가격 변경",
    )


class WatchlistAlertResponse(BaseModel):
    """GET/POST/PATCH /watchlist/alerts 응답."""

    id: int
    user_id: str
    symbol: str
    market: str
    direction: str
    threshold: str = Field(..., description="Decimal 문자열")
    enabled: bool
    created_at: str = Field(..., description="ISO-8601 UTC")

    model_config = {"from_attributes": True}
