"""
Market 엔드포인트.

Week-2: 시장 데이터 어댑터 + 심볼 검색 + Watchlist CRUD 연동.
"""
from __future__ import annotations

import asyncio
from datetime import UTC

from fastapi import APIRouter, HTTPException, Query

from app.schemas.market import (
    OhlcBar,
    Quote,
    Symbol,
    SymbolInfo,
    WatchlistItemCreate,
    WatchlistItemResponse,
)
from app.services.market import get_adapter
from app.services.market.aliases import lookup as alias_lookup
from app.services.market.cache import cache_get, cache_set, ohlc_key, quote_key

router = APIRouter(prefix="/market", tags=["market"])

# 워치리스트 in-memory 스토어 (demo 고정 user_id="demo")
# 실제 DB 연결 시 SQLAlchemy session으로 교체
_watchlist: dict[int, dict] = {}
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

    # 병렬 호출: 3개 어댑터 + alias lookup (alias는 동기 → 코루틴으로 래핑)
    async def _alias_search() -> list[tuple[SymbolInfo, int]]:
        return alias_lookup(q)

    upbit_task = asyncio.create_task(_search_adapter("upbit"))
    yahoo_task = asyncio.create_task(_search_adapter("yahoo"))
    naver_task = asyncio.create_task(_search_adapter("naver_kr"))
    alias_task = asyncio.create_task(_alias_search())

    upbit_res, yahoo_res, naver_res, alias_res = await asyncio.gather(
        upbit_task, yahoo_task, naver_task, alias_task
    )

    # 점수 할당 — 어댑터 결과는 순서 기반 점수 부여 (랭킹 없는 경우 기본 10)
    # upbit 어댑터는 이미 내부 score 없음 → 순서 기반 200~1 할당
    def _assign_adapter_scores(items: list[SymbolInfo], base: int) -> list[tuple[SymbolInfo, int]]:
        scored = []
        total = len(items)
        for i, item in enumerate(items):
            # 위에 있을수록 높은 점수. base에서 순위에 비례해 감소
            rank_score = base - int((i / max(total, 1)) * (base // 2))
            scored.append((item, rank_score))
        return scored

    all_scored: list[tuple[SymbolInfo, int]] = []
    all_scored.extend(_assign_adapter_scores(upbit_res, 200))
    all_scored.extend(_assign_adapter_scores(yahoo_res, 200))
    all_scored.extend(_assign_adapter_scores(naver_res, 200))
    all_scored.extend(alias_res)  # alias는 이미 (SymbolInfo, score) 형태

    # dedupe: (market, symbol) 기준, 높은 score 유지
    best: dict[tuple[str, str], tuple[SymbolInfo, int]] = {}
    for item, score in all_scored:
        key = (item.market, item.symbol)
        if key not in best or score > best[key][1]:
            best[key] = (item, score)

    # score 내림차순 정렬
    ranked = sorted(best.values(), key=lambda x: x[1], reverse=True)

    # score 필드는 SymbolInfo.score 가 exclude=True 이므로 응답 직렬화 시 자동 제외
    # 내부 score 를 SymbolInfo 에 임시 주입 (응답 모델이 exclude 처리)
    result: list[SymbolInfo] = []
    for item, _score in ranked[:50]:
        item.score = _score  # type: ignore[assignment]
        result.append(item)

    return result


@router.get("/quotes/{symbol}", response_model=Quote)
async def get_quote(symbol: str) -> Quote:
    """단일 심볼 시세 조회 (stub — legacy 호환)"""
    from datetime import datetime
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
    """워치리스트 조회 (user_id='demo' 고정)."""
    return [
        WatchlistItemResponse(**item)
        for item in _watchlist.values()
    ]


@router.post(
    "/watchlist/items",
    response_model=WatchlistItemResponse,
    status_code=201,
    responses={400: {"description": "JSON 파싱 실패"}},
)
async def add_watchlist(body: WatchlistItemCreate) -> WatchlistItemResponse:
    """워치리스트에 심볼 추가."""
    global _next_id
    from datetime import datetime

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
    record = {
        "id": item_id,
        "market": body.market,
        "code": body.code,
        "memo": body.memo,
        "created_at": ts,
    }
    _watchlist[item_id] = record
    return WatchlistItemResponse(**record)


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
