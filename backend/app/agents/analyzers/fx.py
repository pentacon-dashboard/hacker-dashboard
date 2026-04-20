"""FX Analyzer — USDKRW=X, EURUSD 등 외환 시계열 해석."""
from __future__ import annotations

from app.agents.analyzers.base import BaseAnalyzer


class FxAnalyzer(BaseAnalyzer):
    asset_class = "fx"
    prompt_name = "fx_system"
