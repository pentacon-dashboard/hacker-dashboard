from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.schemas.market import Quote
from app.services.market.kiwoom import KiwoomAdapter


class _Response:
    def __init__(self, payload: dict[str, Any], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeClient:
    def __init__(self) -> None:
        expires = (datetime.now(UTC) + timedelta(hours=1)).strftime("%Y%m%d%H%M%S")
        self.calls: list[dict[str, Any]] = []
        self._responses = [
            _Response({"token": "token-123", "expires_dt": expires, "token_type": "Bearer"}),
            _Response(
                {
                    "stk_cd": "005930",
                    "stk_nm": "Samsung Electronics",
                    "cur_prc": "+72,100",
                    "pred_pre": "-400",
                    "flu_rt": "-0.55",
                    "trde_qty": "12,345,678",
                }
            ),
        ]

    async def post(self, url: str, **kwargs: Any) -> _Response:
        self.calls.append({"url": url, **kwargs})
        return self._responses.pop(0)


class _FallbackAdapter:
    market = "naver_kr"

    async def fetch_quote(self, symbol: str) -> Quote:
        return Quote(
            symbol=symbol,
            market=self.market,
            price=50000.0,
            change=0.0,
            change_pct=0.0,
            volume=1000.0,
            currency="KRW",
            timestamp=datetime.now(UTC).isoformat(),
        )

    async def fetch_ohlc(self, symbol: str, *, interval: str = "1d", limit: int = 100) -> list[Any]:
        return []

    async def search_symbols(self, query: str) -> list[Any]:
        return []


@pytest.mark.asyncio
async def test_kiwoom_quote_uses_token_and_normalizes_response(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_client = _FakeClient()
    monkeypatch.setattr("app.services.market.kiwoom.get_http_client", lambda: fake_client)
    monkeypatch.setattr("app.services.market.kiwoom.settings.kiwoom_app_key", "app-key")
    monkeypatch.setattr("app.services.market.kiwoom.settings.kiwoom_secret_key", "secret-key")
    monkeypatch.setattr("app.services.market.kiwoom.settings.kiwoom_base_url", "https://mockapi.kiwoom.com")

    adapter = KiwoomAdapter(market="krx", fallback=_FallbackAdapter())
    quote = await adapter.fetch_quote("005930.KS")

    assert quote.symbol == "005930"
    assert quote.market == "krx"
    assert quote.price == 72100.0
    assert quote.change == -400.0
    assert quote.change_pct == -0.55
    assert quote.volume == 12345678.0
    assert quote.currency == "KRW"

    token_call, quote_call = fake_client.calls
    assert token_call["url"] == "https://mockapi.kiwoom.com/oauth2/token"
    assert token_call["json"] == {
        "grant_type": "client_credentials",
        "appkey": "app-key",
        "secretkey": "secret-key",
    }
    assert quote_call["url"] == "https://mockapi.kiwoom.com/api/dostk/stkinfo"
    assert quote_call["headers"]["Authorization"] == "Bearer token-123"
    assert quote_call["headers"]["api-id"] == "ka10001"
    assert quote_call["json"] == {"stk_cd": "005930"}


@pytest.mark.asyncio
async def test_kiwoom_quote_falls_back_without_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.market.kiwoom.settings.kiwoom_app_key", "")
    monkeypatch.setattr("app.services.market.kiwoom.settings.kiwoom_secret_key", "")

    adapter = KiwoomAdapter(market="naver_kr", fallback=_FallbackAdapter())
    quote = await adapter.fetch_quote("005930")

    assert quote.symbol == "005930"
    assert quote.market == "naver_kr"
    assert quote.price == 50000.0
