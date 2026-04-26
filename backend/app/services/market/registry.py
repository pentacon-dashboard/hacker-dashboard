"""마켓 어댑터 레지스트리.

get_adapter(market) → MarketAdapter 인스턴스 (싱글턴).
"""

from __future__ import annotations

from app.services.market.base import MarketAdapter

_registry: dict[str, MarketAdapter] = {}


def _build_registry() -> dict[str, MarketAdapter]:
    # 지연 임포트: httpx client 가 아직 초기화 안 됐을 수도 있으므로
    from app.services.market.binance import BinanceAdapter
    from app.services.market.naver_kr import NaverKrAdapter
    from app.services.market.upbit import UpbitAdapter
    from app.services.market.yahoo import YahooAdapter

    return {
        "upbit": UpbitAdapter(),
        "binance": BinanceAdapter(),
        "yahoo": YahooAdapter(),
        "naver_kr": NaverKrAdapter(),
    }


def get_adapter(market: str) -> MarketAdapter:
    """market 문자열로 어댑터를 반환. 최초 호출 시 레지스트리를 빌드한다."""
    global _registry
    if not _registry:
        _registry = _build_registry()
    if market not in _registry:
        raise ValueError(f"알 수 없는 market: {market!r}. 지원: {list(_registry)}")
    return _registry[market]
