"""Naver 뉴스 검색 API 어댑터.

엔드포인트: GET https://openapi.naver.com/v1/search/news.json
헤더: X-Naver-Client-Id, X-Naver-Client-Secret
무료 한도: 25,000 req/day per app

응답 title/description 의 <b> 강조 태그는 strip 후 Citation 으로 매핑.
"""

from __future__ import annotations

import logging
import os
import re
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from app.core.config import settings
from app.schemas.news import Citation

logger = logging.getLogger(__name__)

_BASE_URL = "https://openapi.naver.com/v1/search/news.json"
_TAG_RE = re.compile(r"</?b>", re.IGNORECASE)
_HTML_ENTITY_RE = re.compile(r"&(quot|amp|lt|gt|apos|nbsp|#\d+);")
_ENTITY_MAP = {"&quot;": '"', "&amp;": "&", "&lt;": "<", "&gt;": ">", "&apos;": "'", "&nbsp;": " "}


def is_naver_configured() -> bool:
    """Naver API credential 환경변수가 모두 설정됐는지."""
    return bool(_get_client_id()) and bool(_get_client_secret())


def _get_client_id() -> str:
    return os.environ.get("NAVER_CLIENT_ID") or settings.naver_client_id


def _get_client_secret() -> str:
    return os.environ.get("NAVER_CLIENT_SECRET") or settings.naver_client_secret


def _strip_html(text: str) -> str:
    """`<b>` 태그 + HTML entity 정규화."""
    text = _TAG_RE.sub("", text)
    return _HTML_ENTITY_RE.sub(lambda m: _ENTITY_MAP.get(m.group(0), m.group(0)), text)


def _parse_pubdate(rfc822: str) -> str:
    """RFC 822 → ISO-8601 변환. 실패 시 원본 반환."""
    try:
        return parsedate_to_datetime(rfc822).isoformat()
    except Exception:  # noqa: BLE001
        return rfc822


# 종목 코드 → 한국어 검색어 매핑 (네이버 검색은 영문 ticker 대신 한글이 hit 잘 됨)
_SYMBOL_KO_MAP: dict[str, str] = {
    "005930": "삼성전자",
    "000660": "SK하이닉스",
    "035720": "카카오",
    "035420": "네이버",
    "207940": "삼성바이오로직스",
    "KRW-BTC": "비트코인",
    "KRW-ETH": "이더리움",
    "BTC-USD": "비트코인",
    "BTCUSDT": "비트코인",
    "AAPL": "Apple",
    "TSLA": "Tesla",
    "NVDA": "NVIDIA",
    "MSFT": "Microsoft",
    "AMZN": "Amazon",
    "META": "Meta",
    "GOOGL": "Google",
}


def _split_query(query: str) -> list[str]:
    """`A OR B OR C` 형태를 [A,B,C] 로 분리. 단일 쿼리면 그대로 1개 리스트."""
    parts = [p.strip() for p in query.split(" OR ")]
    return [p for p in parts if p]


def _resolve_korean(term: str) -> str:
    """ticker → 한국어 검색어 변환 (없으면 원본 반환)."""
    return _SYMBOL_KO_MAP.get(term, term)


async def _fetch_one(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    query: str,
    display: int,
    sort: str,
) -> list[dict[str, Any]]:
    params: dict[str, str | int] = {"query": query, "display": display, "sort": sort}
    try:
        r = await client.get(_BASE_URL, headers=headers, params=params)
        r.raise_for_status()
        return list(r.json().get("items", []))
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "naver HTTP %d for %r: %s", exc.response.status_code, query, exc.response.text[:160]
        )
        return []
    except Exception as exc:  # noqa: BLE001
        logger.warning("naver fetch failed for %r: %s", query, exc)
        return []


async def search_naver_news(
    query: str,
    *,
    display: int = 5,
    sort: str = "date",
    timeout: float = 8.0,
) -> list[Citation]:
    """네이버 뉴스 검색 → Citation 리스트.

    - `A OR B OR C` 형태는 분할 후 각 단어별로 호출 → 결과 머지 + dedupe
    - 종목 ticker 는 한국어 매핑 (예: AAPL → Apple, 005930 → 삼성전자)
    - 실패 / 빈 결과 시 빈 리스트 반환 (호출자가 fixture 폴백)
    """
    client_id = _get_client_id()
    client_secret = _get_client_secret()
    if not client_id or not client_secret:
        return []

    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }
    sort_norm = sort if sort in ("sim", "date") else "date"
    queries = [_resolve_korean(q) for q in _split_query(query)]
    if not queries:
        return []

    # multi-query: per-symbol 결과를 모아 dedupe
    per_query_display = max(2, display // max(len(queries), 1))
    seen_urls: set[str] = set()
    citations: list[Citation] = []

    async with httpx.AsyncClient(timeout=timeout) as client:
        for q in queries:
            items = await _fetch_one(client, headers, q, per_query_display, sort_norm)
            for item in items:
                url = item.get("originallink") or item.get("link", "")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                citations.append(
                    Citation(
                        doc_id=10_000 + len(citations),
                        chunk_id=20_000 + len(citations),
                        source_url=url,
                        title=_strip_html(item.get("title", "")),
                        published_at=_parse_pubdate(item.get("pubDate", "")),
                        excerpt=_strip_html(item.get("description", "")),
                        score=0.0,
                        thumbnail_url=None,
                    )
                )
                if len(citations) >= display:
                    return citations
    return citations
