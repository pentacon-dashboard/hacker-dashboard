"""Crypto Analyzer — KRW-*, USDT-* 등 암호화폐 시계열 해석."""

from __future__ import annotations

from app.agents.analyzers.base import BaseAnalyzer


class CryptoAnalyzer(BaseAnalyzer):
    asset_class = "crypto"
    prompt_name = "crypto_system"
