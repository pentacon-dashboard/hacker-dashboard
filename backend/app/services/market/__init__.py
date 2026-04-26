"""시장 데이터 어댑터 패키지."""

from __future__ import annotations

from app.services.market.registry import get_adapter

__all__ = ["get_adapter"]
