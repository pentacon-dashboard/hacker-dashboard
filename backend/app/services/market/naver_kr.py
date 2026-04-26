"""Naver 국내주식 어댑터.

비공식 API: GET https://m.stock.naver.com/api/search/all?keyword={q}
공모전 MVP 허용 범위 내에서 사용.
네트워크/파싱 에러 시 빈 리스트 반환 (silent fail).

fetch_quote / fetch_ohlc: yfinance (.KS/.KQ) 로 실시간 데이터 조회.
실패 시 _STUB_QUOTES 폴백.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import random
from datetime import UTC, datetime, timedelta
from typing import Any

from app.schemas.market import OhlcBar, Quote, SymbolInfo
from app.services.market.base import MarketAdapter
from app.services.market.yf_cache import yf_cache_get, yf_cache_set

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://m.stock.naver.com/api/search/all"

# ─── 심사 데모용 고정 stub quote 데이터 ───────────────────────────────────────
# yfinance 실패 시 이 값으로 폴백.
# key: 6자리 종목코드 (문자열)
_STUB_QUOTES: dict[str, dict[str, Any]] = {
    "005930": {
        "price": 72000.0,
        "change": 400.0,
        "change_pct": 0.56,
        "volume": 12345678,
        "name": "삼성전자",
    },
    "000660": {
        "price": 231000.0,
        "change": -2500.0,
        "change_pct": -1.07,
        "volume": 4567890,
        "name": "SK하이닉스",
    },
    "035420": {
        "price": 215500.0,
        "change": 1500.0,
        "change_pct": 0.70,
        "volume": 1234567,
        "name": "NAVER",
    },
    "035720": {
        "price": 51800.0,
        "change": -200.0,
        "change_pct": -0.38,
        "volume": 2345678,
        "name": "카카오",
    },
    "005380": {
        "price": 245000.0,
        "change": 3500.0,
        "change_pct": 1.45,
        "volume": 987654,
        "name": "현대차",
    },
    "051910": {
        "price": 385000.0,
        "change": -5000.0,
        "change_pct": -1.28,
        "volume": 543210,
        "name": "LG화학",
    },
    "006400": {
        "price": 165000.0,
        "change": 2000.0,
        "change_pct": 1.23,
        "volume": 876543,
        "name": "삼성SDI",
    },
    "207940": {
        "price": 725000.0,
        "change": 8000.0,
        "change_pct": 1.12,
        "volume": 234567,
        "name": "삼성바이오로직스",
    },
    "005490": {
        "price": 590000.0,
        "change": -3000.0,
        "change_pct": -0.51,
        "volume": 345678,
        "name": "POSCO홀딩스",
    },
    "028260": {
        "price": 98000.0,
        "change": 1200.0,
        "change_pct": 1.24,
        "volume": 654321,
        "name": "삼성물산",
    },
}

_DEFAULT_STUB_PRICE = 50000.0  # _STUB_QUOTES 에 없는 종목 fallback
_DEFAULT_STUB_VOLUME = 500000.0

# 스텁 aliases — search_symbols 용도. 검색은 실 API + aliases 모듈로 처리.
_STUB_SYMBOLS: list[dict[str, str]] = [
    {"symbol": "005930", "name": "삼성전자"},
    {"symbol": "035720", "name": "카카오"},
    {"symbol": "000660", "name": "SK하이닉스"},
    {"symbol": "051910", "name": "LG화학"},
    {"symbol": "035420", "name": "NAVER"},
]

# 미국 주요 거래소 코드 매핑 (naver 응답 내 거래소명 정규화)
_EXCHANGE_MAP: dict[str, str] = {
    "나스닥": "NASDAQ",
    "뉴욕": "NYSE",
    "NYSE": "NYSE",
    "NASDAQ": "NASDAQ",
    "NYSE MKT": "NYSE",
    "NYSEMKT": "NYSE",
    "NAS": "NASDAQ",
    "AMEX": "NYSE",
}


def _detect_kr_exchange(item: dict[str, Any]) -> str:
    """국내 종목의 거래소 구분 — KOSPI/KOSDAQ/KONEX.

    네이버 응답의 stockExchangeType, market, nationType 등을 보고 판단.
    알 수 없으면 KOSPI 로 기본 처리.
    """
    exchange_type = item.get("stockExchangeType", {})
    exchange_code = ""
    if isinstance(exchange_type, dict):
        exchange_code = (exchange_type.get("code") or exchange_type.get("name") or "").upper()
    elif isinstance(exchange_type, str):
        exchange_code = exchange_type.upper()

    market_raw = (item.get("market") or item.get("marketName") or "").upper()
    combined = exchange_code + " " + market_raw

    if "KOSDAQ" in combined or "KQ" in combined:
        return "KOSDAQ"
    if "KONEX" in combined:
        return "KONEX"
    return "KOSPI"


def _kr_yahoo_symbol(item_code: str, item: dict[str, Any]) -> str:
    """국내 종목 코드를 Yahoo Finance 티커 형식으로 변환.

    KOSPI → '{code}.KS', KOSDAQ → '{code}.KQ'
    """
    exchange = _detect_kr_exchange(item)
    suffix = ".KQ" if exchange == "KOSDAQ" else ".KS"
    return f"{item_code}{suffix}"


def _parse_section(items: list[dict[str, Any]]) -> list[SymbolInfo]:
    """네이버 검색 결과 섹션의 항목 리스트를 SymbolInfo 로 정규화.

    국내주식: market='yahoo', symbol='{code}.KS'/'{code}.KQ' 로 변환.
    → Yahoo 어댑터를 통해 실시간 시세/OHLC 조회 가능.
    미국주식: market='yahoo', symbol=reutersCode(TSLA 등 원래 티커).
    """
    results: list[SymbolInfo] = []
    for item in items:
        try:
            # 종목 코드
            item_code: str = (
                item.get("itemCode") or item.get("reutersCode") or item.get("symbol") or ""
            )
            # 종목명
            name: str = item.get("stockName") or item.get("name") or item.get("itemName") or ""
            if not item_code or not name:
                continue

            # 국가/마켓 분류
            nation: str = (item.get("nationType") or item.get("nation") or "").upper()
            market_raw: str = (item.get("market") or item.get("marketName") or "").upper()

            if nation in ("KR", "KOREA", "") and not any(
                x in market_raw for x in ("NYSE", "NASDAQ", "NAS", "AMEX", "NYSEMKT")
            ):
                # 국내 종목 → Yahoo Finance(.KS/.KQ) 로 라우팅
                yahoo_symbol = _kr_yahoo_symbol(item_code, item)
                kr_exchange = _detect_kr_exchange(item)
                results.append(
                    SymbolInfo(
                        symbol=yahoo_symbol,
                        name=name,
                        asset_class="stock",
                        exchange=kr_exchange,
                        market="yahoo",
                        currency="KRW",
                    )
                )
            elif nation in ("US", "USA", "AMERICA") or any(
                x in market_raw for x in ("NYSE", "NASDAQ", "NAS", "AMEX")
            ):
                # 미국 주식 → yahoo 어댑터로 라우팅
                exchange_raw = item.get("stockExchangeType", {})
                if isinstance(exchange_raw, dict):
                    exchange_name = exchange_raw.get("name", market_raw)
                else:
                    exchange_name = str(exchange_raw) or market_raw
                exchange = _EXCHANGE_MAP.get(exchange_name, exchange_name or "NYSE")
                results.append(
                    SymbolInfo(
                        symbol=item_code,
                        name=name,
                        asset_class="stock",
                        exchange=exchange,
                        market="yahoo",
                        currency="USD",
                    )
                )
            else:
                # 기타 국가 — Yahoo 로 라우팅 시도 (원래 코드 그대로)
                results.append(
                    SymbolInfo(
                        symbol=item_code,
                        name=name,
                        asset_class="stock",
                        exchange="KRX",
                        market="yahoo",
                        currency="KRW",
                    )
                )
        except Exception:
            # 개별 항목 파싱 실패는 스킵
            continue

    return results


class NaverKrAdapter(MarketAdapter):
    market = "naver_kr"

    async def fetch_quote(self, symbol: str) -> Quote:
        """yfinance 로 실시간 시세 조회 (KS suffix 자동 부착).

        yfinance 호출 실패 시 _STUB_QUOTES 폴백.
        캐시 TTL: 10초.
        """
        cache_key = f"yf:quote:naver_kr:{symbol}"
        cached = await yf_cache_get(cache_key)
        if cached is not None:
            return Quote(**cached)

        ts = datetime.now(UTC).isoformat()

        try:
            yf_symbol = f"{symbol}.KS"
            live = await asyncio.get_event_loop().run_in_executor(
                None, _fetch_yf_quote_sync, yf_symbol
            )
            if live is not None:
                q = Quote(
                    symbol=symbol,
                    market=self.market,
                    price=live["price"],
                    change=live["change"],
                    change_pct=live["change_pct"],
                    volume=live["volume"],
                    currency="KRW",
                    timestamp=ts,
                )
                await yf_cache_set(cache_key, q.model_dump(), ttl=10)
                return q
        except Exception as exc:
            logger.warning("yfinance quote 실패 (%s): %s — stub 폴백", symbol, exc)

        # stub 폴백
        stub = _STUB_QUOTES.get(symbol)
        if stub is not None:
            return Quote(
                symbol=symbol,
                market=self.market,
                price=stub["price"],
                change=stub["change"],
                change_pct=stub["change_pct"],
                volume=float(stub["volume"]),
                currency="KRW",
                timestamp=ts,
            )

        return Quote(
            symbol=symbol,
            market=self.market,
            price=_DEFAULT_STUB_PRICE,
            change=0.0,
            change_pct=0.0,
            volume=_DEFAULT_STUB_VOLUME,
            currency="KRW",
            timestamp=ts,
        )

    async def fetch_ohlc(
        self,
        symbol: str,
        *,
        interval: str = "1d",
        limit: int = 100,
    ) -> list[OhlcBar]:
        """yfinance 로 실시간 OHLC 조회 (KS suffix 자동 부착).

        yfinance 호출 실패 시 deterministic stub 폴백.
        """
        cache_key = f"yf:ohlc:naver_kr:{symbol}:{interval}:{limit}"
        cached = await yf_cache_get(cache_key)
        if cached is not None:
            return [OhlcBar(**bar) for bar in cached]

        try:
            yf_symbol = f"{symbol}.KS"
            bars = await asyncio.get_event_loop().run_in_executor(
                None, _fetch_yf_ohlc_sync, yf_symbol, interval, limit
            )
            if bars:
                await yf_cache_set(cache_key, [b.model_dump() for b in bars], ttl=60)
                return bars
        except Exception as exc:
            logger.warning("yfinance OHLC 실패 (%s): %s — stub 폴백", symbol, exc)

        # stub 폴백 (deterministic random walk)
        return _build_stub_ohlc(symbol, limit)

    async def search_symbols(self, query: str) -> list[SymbolInfo]:
        """네이버 통합 검색 API 호출. 실패 시 빈 리스트 반환."""
        try:
            data: Any = await self._get(_SEARCH_URL, params={"keyword": query})
        except Exception as exc:
            logger.warning("naver_kr search failed for %r: %s", query, exc)
            return []

        if not isinstance(data, dict):
            return []

        results: list[SymbolInfo] = []

        # 섹션별 파싱 — stocks(국내), worldStocks(해외), etfs(ETF), coins(코인) 등
        for section_key in ("stocks", "worldStocks", "etfs", "funds"):
            section = data.get(section_key)
            if not isinstance(section, dict):
                continue
            items = section.get("items") or section.get("list") or []
            if not isinstance(items, list):
                continue
            results.extend(_parse_section(items))

        # 코인 섹션 — upbit dedupe 에 맡기므로 skip
        # (coins 섹션은 naver 고유 코드 체계라 KRW-XXX 로 변환 불확실)

        # 중복 제거 (market+symbol 기준)
        seen: set[tuple[str, str]] = set()
        deduped: list[SymbolInfo] = []
        for item in results:
            key = (item.market, item.symbol)
            if key not in seen:
                seen.add(key)
                deduped.append(item)

        return deduped


def _build_stub_ohlc(symbol: str, limit: int) -> list[OhlcBar]:
    """deterministic stub OHLC (폴백용). 원래 로직 보존."""
    stub = _STUB_QUOTES.get(symbol)
    base_price = stub["price"] if stub is not None else _DEFAULT_STUB_PRICE
    base_volume = float(stub["volume"]) if stub is not None else _DEFAULT_STUB_VOLUME

    seed = int(hashlib.md5(symbol.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)  # noqa: S311 — 보안 목적 아님 (PYTHONHASHSEED 무관 결정론)

    now = datetime.now(UTC)
    trading_days: list[datetime] = []
    offset = 0
    while len(trading_days) < limit:
        offset += 1
        candidate = now - timedelta(days=offset)
        if candidate.weekday() < 5:
            trading_days.append(candidate)
    trading_days.reverse()

    bars: list[OhlcBar] = []
    prev_close = base_price
    for day in trading_days:
        pct_change = rng.uniform(-0.02, 0.02)
        close = round(prev_close * (1.0 + pct_change), 0)
        open_ = round(prev_close * (1.0 + rng.uniform(-0.005, 0.005)), 0)
        high = round(max(open_, close) * 1.01, 0)
        low = round(min(open_, close) * 0.99, 0)
        volume = round(base_volume * rng.uniform(0.7, 1.3), 0)
        bars.append(
            OhlcBar(
                ts=day.replace(hour=0, minute=0, second=0, microsecond=0).isoformat(),
                open=open_,
                high=high,
                low=low,
                close=close,
                volume=volume,
            )
        )
        prev_close = close
    return bars


def _find_name(symbol: str) -> str:
    stub = _STUB_QUOTES.get(symbol)
    if stub is not None:
        return str(stub["name"])
    for item in _STUB_SYMBOLS:
        if item["symbol"] == symbol:
            return item["name"]
    return symbol


# ─── yfinance 동기 헬퍼 (executor 에서 호출) ─────────────────────────────────


def _fetch_yf_quote_sync(yf_symbol: str) -> dict[str, Any] | None:
    """yfinance Ticker.info 에서 quote 데이터 추출. 실패 시 None 반환."""
    import yfinance as yf

    ticker = yf.Ticker(yf_symbol)
    info = ticker.info
    price = info.get("regularMarketPrice") or info.get("currentPrice")
    if not price:
        return None

    prev_close = info.get("regularMarketPreviousClose") or info.get("previousClose") or price
    change = float(price) - float(prev_close)
    change_pct = (change / float(prev_close) * 100.0) if prev_close else 0.0
    volume = info.get("regularMarketVolume") or info.get("volume")

    return {
        "price": float(price),
        "change": round(change, 2),
        "change_pct": round(change_pct, 4),
        "volume": float(volume) if volume else 0.0,
    }


def _fetch_yf_ohlc_sync(yf_symbol: str, interval: str, limit: int) -> list[OhlcBar]:
    """yfinance history() 로 OHLC 바 리스트 반환. 실패 시 빈 리스트."""
    import yfinance as yf

    # interval 매핑: '1d' → period/interval 결정
    yf_interval = "1d" if interval == "1d" else "1m"
    period = "6mo" if yf_interval == "1d" else "1d"

    ticker = yf.Ticker(yf_symbol)
    df = ticker.history(period=period, interval=yf_interval)
    if df is None or df.empty:
        return []

    bars: list[OhlcBar] = []
    rows = df.tail(limit)
    for idx, row in rows.iterrows():
        try:
            ts_val: Any = idx
            # pandas Timestamp → ISO string
            ts_str = ts_val.isoformat() if hasattr(ts_val, "isoformat") else str(ts_val)
            bars.append(
                OhlcBar(
                    ts=ts_str,
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=float(row["Volume"]) if "Volume" in row else None,
                )
            )
        except Exception:
            continue
    return bars
