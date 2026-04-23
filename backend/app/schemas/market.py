from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# 지원 마켓 리터럴 타입 (portfolio 등에서 import)
MarketLiteral = Literal["upbit", "binance", "yahoo", "naver_kr", "krx", "nasdaq", "nyse", "unknown"]


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
    score: int | None = Field(
        default=None,
        exclude=True,
        description="내부 랭킹 점수 -- 응답에 포함되지 않음",
    )


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
    pnl_7d: list[float] = Field(default_factory=list, description="7일 종가 스파크라인")
    created_at: str = Field(..., description="ISO-8601 UTC")


# ─────────────────── Symbol Indicators (B-3) ───────────────────────────────


class IndicatorPoint(BaseModel):
    t: str = Field(..., description="ISO timestamp")
    v: float


class MacdPoint(BaseModel):
    t: str
    macd: float
    signal: float
    histogram: float


class BollingerBands(BaseModel):
    upper: list[IndicatorPoint]
    mid: list[IndicatorPoint]
    lower: list[IndicatorPoint]


class StochasticPoint(BaseModel):
    t: str
    k: float
    d: float


class IndicatorMetrics(BaseModel):
    rsi_latest: float
    macd_latest: float
    macd_signal: str = Field(..., description="golden_cross | dead_cross | neutral")
    bollinger_position: str = Field(..., description="upper | mid | lower")
    ma20_latest: float | None = Field(None, description="MA-20 최신값")
    ma60_latest: float | None = Field(None, description="MA-60 최신값")


class IndicatorBundle(BaseModel):
    interval: str = Field(..., description="1m | 5m | 15m | 60m | day | week | month")
    period: int
    rsi_14: list[IndicatorPoint]
    macd: list[MacdPoint]
    bollinger: BollingerBands
    stochastic: list[StochasticPoint]
    ma20: list[IndicatorPoint] = Field(default_factory=list, description="MA-20 시계열")
    ma60: list[IndicatorPoint] = Field(default_factory=list, description="MA-60 시계열")
    metrics: IndicatorMetrics
    signal: str = Field(..., description="buy | hold | sell")


# ─────────────────── Market Analysis (B-4) ───────────────────────────────


class IndexSnapshot(BaseModel):
    ticker: str = Field(..., description="예: ^GSPC")
    display_name: str = Field(..., description="예: S&P 500")
    value: str
    change_pct: str
    change_abs: str
    sparkline_7d: list[float]


class SectorKpi(BaseModel):
    name: str = Field(..., description="예: 반도체")
    change_pct: str
    constituents: int = Field(..., description="포함 종목 수")
    leaders: list[str] = Field(..., description="예: ['AAPL', 'MSFT']")


class CommodityItem(BaseModel):
    symbol: str = Field(..., description="예: GC=F")
    name: str = Field(..., description="예: 금")
    price: str
    change_pct: str
    unit: str = Field(..., description="예: USD/oz")


class WorldHeatmapRegion(BaseModel):
    country_code: str = Field(..., description="ISO 2자리 예: US")
    country_name: str
    change_pct: str
    market_cap_usd: str
