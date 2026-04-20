"""MarketAdapter 추상 기반 클래스."""
from __future__ import annotations

import abc
from typing import Any

import httpx

from app.schemas.market import OhlcBar, Quote, SymbolInfo

# 공유 httpx 클라이언트 — lifespan에서 초기화
_shared_client: httpx.AsyncClient | None = None


def set_http_client(client: httpx.AsyncClient | None) -> None:
    """테스트/lifespan DI 주입."""
    global _shared_client
    _shared_client = client


def get_http_client() -> httpx.AsyncClient:
    """공유 클라이언트. 없으면 즉석 생성(fallback).

    Yahoo Finance 는 User-Agent 없이 요청하면 429 로 거부하므로 기본 헤더에 포함.
    """
    if _shared_client is not None:
        return _shared_client
    return httpx.AsyncClient(
        timeout=5.0,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
        },
    )


class MarketAdapter(abc.ABC):
    """자산군별 거래소 어댑터 추상 인터페이스."""

    market: str  # "upbit" | "binance" | "yahoo" | "naver_kr"

    @abc.abstractmethod
    async def fetch_quote(self, symbol: str) -> Quote:
        """단일 심볼 현재가 조회."""
        ...

    @abc.abstractmethod
    async def fetch_ohlc(
        self,
        symbol: str,
        *,
        interval: str = "1d",
        limit: int = 100,
    ) -> list[OhlcBar]:
        """OHLC 캔들 조회. interval: 1d | 1m"""
        ...

    @abc.abstractmethod
    async def search_symbols(self, query: str) -> list[SymbolInfo]:
        """심볼 검색."""
        ...

    # ────────────────── 공통 HTTP 헬퍼 ──────────────────

    async def _get(self, url: str, params: dict[str, Any] | None = None) -> Any:
        """GET 요청. 타임아웃 3s, 재시도 1회."""
        client = get_http_client()
        exc_last: Exception | None = None
        for attempt in range(2):  # 최대 2회 (초기 + 1회 재시도)
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
            except (httpx.TimeoutException, httpx.HTTPStatusError) as exc:
                exc_last = exc
                if attempt == 0:
                    continue  # 1회 재시도
                raise
            except Exception:
                raise
        raise exc_last  # type: ignore[misc]
