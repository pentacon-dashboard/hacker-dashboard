"""자산군별 Analyzer 서브그래프 모듈."""
from __future__ import annotations

from app.agents.analyzers.base import BaseAnalyzer
from app.agents.analyzers.crypto import CryptoAnalyzer
from app.agents.analyzers.fx import FxAnalyzer
from app.agents.analyzers.macro import MacroAnalyzer
from app.agents.analyzers.mixed import MixedAnalyzer
from app.agents.analyzers.portfolio import PortfolioAnalyzer
from app.agents.analyzers.stock import StockAnalyzer

# asset_class → Analyzer 인스턴스 라우팅 테이블
_REGISTRY: dict[str, BaseAnalyzer] = {
    "stock": StockAnalyzer(),
    "crypto": CryptoAnalyzer(),
    "fx": FxAnalyzer(),
    "macro": MacroAnalyzer(),
    "mixed": MixedAnalyzer(),
    "portfolio": PortfolioAnalyzer(),
}


def get_analyzer(asset_class: str) -> BaseAnalyzer:
    """
    asset_class 에 맞는 Analyzer 를 반환한다.
    등록되지 않은 타입은 stock 으로 폴백하고, 상위 노드가 fallback 플래그를 얹도록 한다.
    """
    return _REGISTRY.get(asset_class, _REGISTRY["stock"])


__all__ = [
    "BaseAnalyzer",
    "CryptoAnalyzer",
    "FxAnalyzer",
    "MacroAnalyzer",
    "MixedAnalyzer",
    "PortfolioAnalyzer",
    "StockAnalyzer",
    "get_analyzer",
]
