"""
Market 엔드포인트.

Week-2: 시장 데이터 어댑터 + 심볼 검색 + Watchlist CRUD 연동.
Sprint-08 B-3/B-4: Symbol indicators + Market analysis 엔드포인트.
"""
from __future__ import annotations

import asyncio
import math
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas.market import (
    BollingerBands,
    CommodityItem,
    IndexSnapshot,
    IndicatorBundle,
    IndicatorMetrics,
    IndicatorPoint,
    MacdPoint,
    OhlcBar,
    Quote,
    SectorKpi,
    StochasticPoint,
    Symbol,
    SymbolInfo,
    WatchlistItemCreate,
    WatchlistItemResponse,
    WorldHeatmapRegion,
)
from app.services import indicators as ind_svc
from app.services import market_fixtures as fixtures
from app.services.market import get_adapter
from app.services.market.aliases import lookup as alias_lookup
from app.services.market.cache import cache_get, cache_set, ohlc_key, quote_key
from app.services.watchlist import sparkline_7d

router = APIRouter(prefix="/market", tags=["market"])

# 워치리스트 in-memory 스토어 (demo 고정 user_id="demo")
# 실제 DB 연결 시 SQLAlchemy session으로 교체
_watchlist: dict[int, dict[str, Any]] = {}
_next_id: int = 1

_SAMPLE_SYMBOLS: list[Symbol] = [
    Symbol(symbol="AAPL", name="Apple Inc.", asset_class="stock", exchange="NASDAQ", market="yahoo"),
    Symbol(symbol="BTC-USD", name="Bitcoin", asset_class="crypto", exchange=None, market="yahoo"),
    Symbol(symbol="KRW-BTC", name="Bitcoin/KRW", asset_class="crypto", exchange="Upbit", market="upbit"),
    Symbol(symbol="BTCUSDT", name="Bitcoin/USDT", asset_class="crypto", exchange="Binance", market="binance"),
    Symbol(symbol="USD-KRW", name="USD/KRW", asset_class="fx", exchange=None, market="yahoo"),
]


@router.get("/symbols", response_model=list[Symbol])
async def list_symbols() -> list[Symbol]:
    """지원 심볼 목록 (데모 고정 샘플)"""
    return _SAMPLE_SYMBOLS


@router.get("/symbols/search", response_model=list[SymbolInfo])
async def search_symbols(
    q: str = Query(..., min_length=1, description="검색 키워드"),
) -> list[SymbolInfo]:
    """심볼 통합 검색 (upbit + yahoo + naver_kr + alias).

    - 4개 소스를 asyncio.gather 로 병렬 호출
    - (market, symbol) 기준 dedupe, 높은 score 유지
    - score 내림차순 정렬 후 상위 50개 반환
    - score 필드는 응답에 포함되지 않음 (SymbolInfo.score 는 exclude=True)
    """

    async def _search_adapter(market_name: str) -> list[SymbolInfo]:
        try:
            adapter = get_adapter(market_name)
            return await adapter.search_symbols(q)
        except Exception:
            return []

    async def _alias_search() -> list[tuple[SymbolInfo, int]]:
        return alias_lookup(q)

    upbit_task = asyncio.create_task(_search_adapter("upbit"))
    yahoo_task = asyncio.create_task(_search_adapter("yahoo"))
    naver_task = asyncio.create_task(_search_adapter("naver_kr"))
    alias_task = asyncio.create_task(_alias_search())

    upbit_res, yahoo_res, naver_res, alias_res = await asyncio.gather(
        upbit_task, yahoo_task, naver_task, alias_task
    )

    def _assign_adapter_scores(
        items: list[SymbolInfo], base: int
    ) -> list[tuple[SymbolInfo, int]]:
        scored = []
        total = len(items)
        for i, item in enumerate(items):
            rank_score = base - int((i / max(total, 1)) * (base // 2))
            scored.append((item, rank_score))
        return scored

    all_scored: list[tuple[SymbolInfo, int]] = []
    all_scored.extend(_assign_adapter_scores(upbit_res, 200))
    all_scored.extend(_assign_adapter_scores(yahoo_res, 200))
    all_scored.extend(_assign_adapter_scores(naver_res, 200))
    all_scored.extend(alias_res)

    best: dict[tuple[str, str], tuple[SymbolInfo, int]] = {}
    for item, score in all_scored:
        key = (item.market, item.symbol)
        if key not in best or score > best[key][1]:
            best[key] = (item, score)

    ranked = sorted(best.values(), key=lambda x: x[1], reverse=True)

    result: list[SymbolInfo] = []
    for item, _score in ranked[:50]:
        item.score = _score
        result.append(item)

    return result


@router.get("/quotes/{symbol}", response_model=Quote)
async def get_quote(symbol: str) -> Quote:
    """단일 심볼 시세 조회 (stub -- legacy 호환)"""
    return Quote(
        symbol=symbol,
        market="unknown",
        price=100.0,
        change=0.0,
        change_pct=0.0,
        volume=None,
        currency="USD",
        timestamp=datetime.now(UTC).isoformat(),
    )


@router.get(
    "/quotes/{market}/{code}",
    response_model=Quote,
    responses={404: {"description": "market 또는 code 를 찾을 수 없음"}},
)
async def get_market_quote(market: str, code: str) -> Quote:
    """market별 단일 심볼 현재가 조회. Redis 캐시(TTL 5s) 적용."""
    cache_k = quote_key(market, code)
    cached = await cache_get(cache_k)
    if cached is not None:
        return Quote(**cached)

    try:
        adapter = get_adapter(market)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        quote = await adapter.fetch_quote(code)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "UPSTREAM_ERROR", "detail": str(exc)},
        ) from exc

    await cache_set(cache_k, quote.model_dump(), ttl=5)
    return quote


@router.get(
    "/ohlc/{market}/{code}",
    response_model=list[OhlcBar],
    responses={404: {"description": "market 또는 code 를 찾을 수 없음"}},
)
async def get_ohlc(
    market: str,
    code: str,
    interval: str = Query(default="1d", pattern="^(1d|1m)$"),
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[OhlcBar]:
    """OHLC 캔들 조회. Redis 캐시(TTL 60s) 적용."""
    cache_k = ohlc_key(market, code, interval, limit)
    cached = await cache_get(cache_k)
    if cached is not None:
        return [OhlcBar(**bar) for bar in cached]

    try:
        adapter = get_adapter(market)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        bars = await adapter.fetch_ohlc(code, interval=interval, limit=limit)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "UPSTREAM_ERROR", "detail": str(exc)},
        ) from exc

    await cache_set(cache_k, [b.model_dump() for b in bars], ttl=60)
    return bars


# ─────────────────────── Watchlist CRUD ───────────────────────────────

@router.get("/watchlist/items", response_model=list[WatchlistItemResponse])
async def list_watchlist() -> list[WatchlistItemResponse]:
    """워치리스트 조회 (user_id='demo' 고정). pnl_7d 스파크라인 포함."""
    result = []
    for item in _watchlist.values():
        pnl = sparkline_7d(str(item["market"]), str(item["code"]))
        result.append(WatchlistItemResponse(**item, pnl_7d=pnl))  # type: ignore[arg-type]
    return result


@router.post(
    "/watchlist/items",
    response_model=WatchlistItemResponse,
    status_code=201,
    responses={400: {"description": "JSON 파싱 실패"}},
)
async def add_watchlist(body: WatchlistItemCreate) -> WatchlistItemResponse:
    """워치리스트에 심볼 추가."""
    global _next_id

    # market 유효성 확인
    try:
        get_adapter(body.market)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=[{"msg": str(exc), "type": "value_error", "loc": ["body", "market"]}],
        ) from exc

    item_id = _next_id
    _next_id += 1
    ts = datetime.now(UTC).isoformat()
    record: dict[str, Any] = {
        "id": item_id,
        "market": body.market,
        "code": body.code,
        "memo": body.memo,
        "created_at": ts,
    }
    _watchlist[item_id] = record
    return WatchlistItemResponse(**record)  # type: ignore[arg-type]


@router.delete(
    "/watchlist/items/{item_id}",
    status_code=204,
    responses={404: {"description": "워치리스트 항목을 찾을 수 없음"}},
)
async def delete_watchlist(item_id: int) -> None:
    """워치리스트 항목 삭제."""
    if item_id not in _watchlist:
        raise HTTPException(status_code=404, detail=f"watchlist item {item_id} not found")
    del _watchlist[item_id]


# ─────────────────── Symbol Indicators (B-3) ───────────────────────────────

_VALID_INTERVALS = {"1m", "5m", "15m", "60m", "day", "week", "month"}

_INTERVAL_TO_OHLC_LIMIT: dict[str, int] = {
    "1m": 60,
    "5m": 60,
    "15m": 60,
    "60m": 60,
    "day": 120,
    "week": 52,
    "month": 24,
}

_INTERVAL_DELTA: dict[str, timedelta] = {
    "1m": timedelta(minutes=1),
    "5m": timedelta(minutes=5),
    "15m": timedelta(minutes=15),
    "60m": timedelta(hours=1),
    "day": timedelta(days=1),
    "week": timedelta(weeks=1),
    "month": timedelta(days=30),
}


def _generate_stub_ohlc(market: str, code: str, interval: str, n: int) -> list[OhlcBar]:
    """deterministic stub OHLC 생성."""
    seed = sum(ord(c) for c in (market + code + interval))
    base = 100.0 + (seed % 400)
    delta = _INTERVAL_DELTA.get(interval, timedelta(days=1))
    now = datetime(2026, 4, 23, 9, 0, 0, tzinfo=UTC)
    bars = []
    price = base
    for i in range(n):
        ts = now - delta * (n - i)
        chg = (
            math.sin(i * 0.3 + seed * 0.05) * base * 0.02
            + ((seed * (i + 1)) % 11 - 5) * base * 0.003
        )
        close = max(price + chg, base * 0.3)
        high = close * (1 + abs(math.sin(i * 0.7)) * 0.01)
        low = close * (1 - abs(math.cos(i * 0.7)) * 0.01)
        open_ = price
        price = close
        bars.append(OhlcBar(
            ts=ts.isoformat(),
            open=round(open_, 4),
            high=round(high, 4),
            low=round(low, 4),
            close=round(close, 4),
            volume=round(1_000_000 + (seed * i % 500_000), 0),
        ))
    return bars


@router.get(
    "/symbol/{market}/{code}/indicators",
    response_model=IndicatorBundle,
    responses={400: {"description": "interval 값이 유효하지 않음"}},
)
async def get_symbol_indicators(
    market: str,
    code: str,
    interval: str = Query(default="day", description="1m|5m|15m|60m|day|week|month"),
    period: int = Query(default=60, ge=10, le=500),
) -> IndicatorBundle:
    """심볼 기술 지표 (RSI-14, MACD, 볼린저, 스토캐스틱).

    실제 OHLC 어댑터 시도 후 실패하면 stub 데이터로 폴백.
    """
    if interval not in _VALID_INTERVALS:
        raise HTTPException(
            status_code=400,
            detail=f"interval '{interval}' is not valid. Use one of {sorted(_VALID_INTERVALS)}",
        )

    n = max(period + 40, _INTERVAL_TO_OHLC_LIMIT.get(interval, 120))
    try:
        adapter = get_adapter(market)
        ohlc_interval = "1d" if interval == "day" else "1m"
        bars = await adapter.fetch_ohlc(code, interval=ohlc_interval, limit=n)
    except Exception:
        bars = _generate_stub_ohlc(market, code, interval, n)

    closes = [b.close for b in bars]
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    timestamps = [b.ts for b in bars]

    # RSI
    rsi_vals = ind_svc.calc_rsi(closes, period=14)
    rsi_ts_offset = len(closes) - len(rsi_vals)
    rsi_14 = [
        IndicatorPoint(t=timestamps[rsi_ts_offset + i], v=round(v, 2))
        for i, v in enumerate(rsi_vals)
    ]

    # MACD
    macd_line, signal_line, histogram = ind_svc.calc_macd(closes)
    macd_ts_offset = len(closes) - len(macd_line)
    macd_points = [
        MacdPoint(
            t=timestamps[macd_ts_offset + i],
            macd=round(macd_line[i], 4),
            signal=round(signal_line[i], 4),
            histogram=round(histogram[i], 4),
        )
        for i in range(len(macd_line))
    ]

    # 볼린저 밴드
    bb_upper, bb_mid, bb_lower = ind_svc.calc_bollinger(closes)
    bb_ts_offset = len(closes) - len(bb_mid)
    bollinger = BollingerBands(
        upper=[
            IndicatorPoint(t=timestamps[bb_ts_offset + i], v=round(v, 4))
            for i, v in enumerate(bb_upper)
        ],
        mid=[
            IndicatorPoint(t=timestamps[bb_ts_offset + i], v=round(v, 4))
            for i, v in enumerate(bb_mid)
        ],
        lower=[
            IndicatorPoint(t=timestamps[bb_ts_offset + i], v=round(v, 4))
            for i, v in enumerate(bb_lower)
        ],
    )

    # 스토캐스틱
    k_vals, d_vals = ind_svc.calc_stochastic(highs, lows, closes)
    stoch_ts_offset = len(closes) - len(k_vals)
    stochastic = [
        StochasticPoint(
            t=timestamps[stoch_ts_offset + i],
            k=round(k_vals[i], 2),
            d=round(d_vals[i], 2),
        )
        for i in range(len(k_vals))
    ]

    # metrics
    rsi_latest = rsi_14[-1].v if rsi_14 else 50.0
    macd_latest = macd_points[-1].macd if macd_points else 0.0
    macd_signal_str = "neutral"
    if len(macd_points) >= 2:
        prev_hist = macd_points[-2].histogram
        curr_hist = macd_points[-1].histogram
        if prev_hist < 0 < curr_hist:
            macd_signal_str = "golden_cross"
        elif prev_hist > 0 > curr_hist:
            macd_signal_str = "dead_cross"

    close_latest = closes[-1] if closes else 0.0
    bb_pos = "mid"
    if bollinger.upper and bollinger.lower:
        upper_val = bollinger.upper[-1].v
        lower_val = bollinger.lower[-1].v
        if close_latest >= upper_val:
            bb_pos = "upper"
        elif close_latest <= lower_val:
            bb_pos = "lower"

    overall_signal = "hold"
    if rsi_latest < 30 and macd_signal_str == "golden_cross":
        overall_signal = "buy"
    elif rsi_latest > 70 and macd_signal_str == "dead_cross":
        overall_signal = "sell"

    return IndicatorBundle(
        interval=interval,
        period=period,
        rsi_14=rsi_14,
        macd=macd_points,
        bollinger=bollinger,
        stochastic=stochastic,
        metrics=IndicatorMetrics(
            rsi_latest=round(rsi_latest, 2),
            macd_latest=round(macd_latest, 6),
            macd_signal=macd_signal_str,
            bollinger_position=bb_pos,
        ),
        signal=overall_signal,
    )


# ─────────────────── Market Analysis (B-4) ───────────────────────────────


@router.get("/indices", response_model=list[IndexSnapshot])
async def get_market_indices() -> list[IndexSnapshot]:
    """KOSPI/KOSDAQ/S&P/NASDAQ/DOW/VIX/USD-KRW 7종 스냅샷 (stub)."""
    return [IndexSnapshot(**row) for row in fixtures.INDEX_SNAPSHOTS]  # type: ignore[arg-type]


@router.get("/sectors", response_model=list[SectorKpi])
async def get_market_sectors() -> list[SectorKpi]:
    """11 GICS 섹터 KPI (stub)."""
    return [SectorKpi(**row) for row in fixtures.SECTOR_KPIS]  # type: ignore[arg-type]


@router.get("/commodities", response_model=list[CommodityItem])
async def get_market_commodities() -> list[CommodityItem]:
    """원유/금/은/구리/천연가스 5종 (stub)."""
    return [CommodityItem(**row) for row in fixtures.COMMODITIES]  # type: ignore[arg-type]


@router.get("/world-heatmap", response_model=list[WorldHeatmapRegion])
async def get_world_heatmap() -> list[WorldHeatmapRegion]:
    """20개국 세계 히트맵 (stub)."""
    return [WorldHeatmapRegion(**row) for row in fixtures.WORLD_HEATMAP]  # type: ignore[arg-type]
