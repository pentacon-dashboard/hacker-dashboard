"""
워치리스트 관련 Pydantic 스키마 — Sprint-08 B-2.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


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
