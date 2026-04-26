"""Upbit 시장 데이터 어댑터.

API 문서: https://docs.upbit.com/reference/
엔드포인트:
  - GET https://api.upbit.com/v1/ticker?markets=KRW-BTC
  - GET https://api.upbit.com/v1/candles/days?market=KRW-BTC&count=100
  - GET https://api.upbit.com/v1/market/all
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.schemas.market import OhlcBar, Quote, SymbolInfo
from app.services.market.base import MarketAdapter

_BASE = "https://api.upbit.com/v1"

_INTERVAL_MAP = {
    "1d": "/candles/days",
    "1m": "/candles/minutes/1",
}


def _score_upbit(item: dict[str, Any], query: str) -> int:
    """Upbit 심볼 검색 점수 산출.

    점수 기준:
    - symbol 정확일치(대소문자 무시): 1000
    - base_symbol 정확일치 (KRW-BTC 에서 BTC 부분): 950
    - korean_name 정확일치: 900
    - english_name 정확일치: 850
    - symbol.startswith(q): 500
    - korean_name.startswith(q): 400
    - english_name.startswith(q): 350
    - substring: 100
    - KRW 마켓 보너스: +50
    """
    market_id: str = item.get("market", "")
    korean_name: str = item.get("korean_name", "")
    english_name: str = item.get("english_name", "")

    q_upper = query.upper()
    q_lower = query.lower()

    market_upper = market_id.upper()
    korean_lower = korean_name.lower()
    english_lower = english_name.lower()

    # base_symbol: "KRW-BTC" → "BTC", "BTC-XRP" → "XRP"
    base_symbol = market_id.split("-")[-1] if "-" in market_id else market_id

    score = 0

    # 정확일치
    if market_upper == q_upper:
        score = max(score, 1000)
    elif base_symbol.upper() == q_upper:
        # 베이스 심볼 정확일치 (KRW-BTC 에서 BTC 검색)
        score = max(score, 950)
    elif korean_lower == q_lower:
        score = max(score, 900)
    elif english_lower == q_lower:
        score = max(score, 850)
    # startswith
    elif market_upper.startswith(q_upper):
        score = max(score, 500)
    elif korean_lower.startswith(q_lower):
        score = max(score, 400)
    elif english_lower.startswith(q_lower):
        score = max(score, 350)
    # substring
    elif q_upper in market_upper or q_lower in korean_lower or q_lower in english_lower:
        score = max(score, 100)

    if score == 0:
        return 0

    # KRW 마켓 보너스
    if market_id.startswith("KRW-"):
        score += 50

    return score


class UpbitAdapter(MarketAdapter):
    market = "upbit"

    async def fetch_quote(self, symbol: str) -> Quote:
        data: list[dict[str, Any]] = await self._get(
            f"{_BASE}/ticker",
            params={"markets": symbol},
        )
        if not data:
            raise ValueError(f"Upbit: no ticker data for {symbol}")
        t = data[0]
        ts = _parse_upbit_ts(t.get("trade_date_kst", ""), t.get("trade_time_kst", ""))
        return Quote(
            symbol=symbol,
            market=self.market,
            price=float(t["trade_price"]),
            change=float(t.get("signed_change_price", 0)),
            change_pct=float(t.get("signed_change_rate", 0)) * 100,
            volume=float(t.get("acc_trade_volume_24h", 0)) or None,
            currency="KRW" if symbol.startswith("KRW-") else "BTC",
            timestamp=ts,
        )

    async def fetch_ohlc(
        self,
        symbol: str,
        *,
        interval: str = "1d",
        limit: int = 100,
    ) -> list[OhlcBar]:
        path = _INTERVAL_MAP.get(interval, "/candles/days")
        data: list[dict[str, Any]] = await self._get(
            f"{_BASE}{path}",
            params={"market": symbol, "count": min(limit, 200)},
        )
        bars: list[OhlcBar] = []
        for c in reversed(data):  # Upbit는 최신순 → 오래된 순으로 뒤집기
            bars.append(
                OhlcBar(
                    ts=c.get("candle_date_time_utc", "") + "Z",
                    open=float(c["opening_price"]),
                    high=float(c["high_price"]),
                    low=float(c["low_price"]),
                    close=float(c["trade_price"]),
                    volume=float(c.get("candle_acc_trade_volume", 0)) or None,
                )
            )
        return bars

    async def search_symbols(self, query: str) -> list[SymbolInfo]:
        data: list[dict[str, Any]] = await self._get(f"{_BASE}/market/all")

        # 점수 계산 후 필터링
        scored: list[tuple[int, dict[str, Any]]] = []
        for item in data:
            s = _score_upbit(item, query)
            if s > 0:
                scored.append((s, item))

        # 점수 내림차순 정렬
        scored.sort(key=lambda x: x[0], reverse=True)

        results: list[SymbolInfo] = []
        for score, item in scored[:20]:
            market_id: str = item.get("market", "")
            korean_name: str = item.get("korean_name", "")
            english_name: str = item.get("english_name", "")
            currency = market_id.split("-")[0] if "-" in market_id else "KRW"
            results.append(
                SymbolInfo(
                    symbol=market_id,
                    name=english_name or korean_name,
                    asset_class="crypto",
                    exchange="Upbit",
                    market=self.market,
                    currency=currency,
                )
            )
        return results


def _parse_upbit_ts(date_kst: str, time_kst: str) -> str:
    """YYYYMMDD + HHMMSS KST → ISO-8601 UTC."""
    try:
        dt_str = f"{date_kst} {time_kst}"
        # KST = UTC+9
        from datetime import timedelta

        dt = datetime.strptime(dt_str, "%Y%m%d %H%M%S")
        dt_utc = dt.replace(tzinfo=UTC) - timedelta(hours=9)
        return dt_utc.isoformat()
    except (ValueError, TypeError):
        return datetime.now(UTC).isoformat()
