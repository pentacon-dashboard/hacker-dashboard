"""Stock Analyzer — 국내/해외 주식 시계열 해석."""
from __future__ import annotations

from app.agents.analyzers.base import BaseAnalyzer


class StockAnalyzer(BaseAnalyzer):
    asset_class = "stock"
    prompt_name = "stock_system"
