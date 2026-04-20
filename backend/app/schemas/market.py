from __future__ import annotations

from pydantic import BaseModel, Field


class Symbol(BaseModel):
    symbol: str = Field(..., description="티커 심볼 (예: AAPL, KRW-BTC)")
    name: str = Field(..., description="자산 이름")
    asset_class: str = Field(..., description="stock | crypto | fx | macro")
    exchange: str | None = Field(None, description="거래소 코드")
    market: str | None = Field(None, description="upbit | binance | yahoo | naver_kr")


class SymbolInfo(BaseModel):
    """심볼 검색 결과"""

    symbol: str
    name: str
    asset_class: str
    exchange: str | None = None
    market: str
    currency: str | None = None
    score: int | None = Field(default=None, exclude=True, description="내부 랭킹 점수 — 응답에 포함되지 않음")


class Quote(BaseModel):
    symbol: str
    market: str = Field(default="unknown", description="upbit | binance | yahoo | naver_kr")
    price: float = Field(..., gt=0)
    change: float = Field(default=0.0, description="전일 대비 변화량")
    change_pct: float = Field(default=0.0, description="전일 대비 변화율(%)")
    volume: float | None = None
    currency: str = Field(default="USD", description="KRW | USD | USDT 등")
    timestamp: str = Field(..., description="ISO-8601 UTC")


class OhlcBar(BaseModel):
    """OHLC 캔들 하나"""

    ts: str = Field(..., description="ISO-8601 UTC")
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None


class WatchlistItemCreate(BaseModel):
    market: str = Field(..., description="upbit | binance | yahoo | naver_kr")
    code: str = Field(..., description="심볼/코드 (예: KRW-BTC, AAPL)")
    memo: str | None = None


class WatchlistItemResponse(BaseModel):
    id: int
    market: str
    code: str
    memo: str | None = None
    created_at: str = Field(..., description="ISO-8601 UTC")
