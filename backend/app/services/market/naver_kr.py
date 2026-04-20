"""Naver 국내주식 어댑터.

비공식 API: GET https://m.stock.naver.com/api/search/all?keyword={q}
공모전 MVP 허용 범위 내에서 사용.
네트워크/파싱 에러 시 빈 리스트 반환 (silent fail).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.schemas.market import OhlcBar, Quote, SymbolInfo
from app.services.market.base import MarketAdapter

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://m.stock.naver.com/api/search/all"

# 스텁 aliases — fetch_quote 용도로만 잔존. 검색은 실 API + aliases 모듈로 처리.
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
                item.get("itemCode")
                or item.get("reutersCode")
                or item.get("symbol")
                or ""
            )
            # 종목명
            name: str = (
                item.get("stockName")
                or item.get("name")
                or item.get("itemName")
                or ""
            )
            if not item_code or not name:
                continue

            # 국가/마켓 분류
            nation: str = (item.get("nationType") or item.get("nation") or "").upper()
            market_raw: str = (item.get("market") or item.get("marketName") or "").upper()

            if nation in ("KR", "KOREA", "") and not any(
                x in market_raw for x in ("NYSE", "NASDAQ", "NAS", "AMEX", "NYSEMKT")
            ):
                # 국내 종목 → Yahoo Finance(.KS/.KQ) 로 라우팅
                # → 워치리스트 추가 후 Yahoo 어댑터를 통해 시세/OHLC 정상 조회 가능
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
        """스텁: 실 네트워크 없이 고정 응답 반환."""
        name = _find_name(symbol)
        ts = datetime.now(timezone.utc).isoformat()
        return Quote(
            symbol=symbol,
            market=self.market,
            price=1.0,  # stub
            change=0.0,
            change_pct=0.0,
            volume=None,
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
        """스텁: 빈 리스트 반환. TODO: 실 API 연동."""
        return []

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


def _find_name(symbol: str) -> str:
    for item in _STUB_SYMBOLS:
        if item["symbol"] == symbol:
            return item["name"]
    return symbol
