"""포트폴리오 집계 서비스 단위 테스트 — compute_summary."""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from app.services.portfolio import _classify_asset, compute_summary

# ──────────── 테스트용 더미 Holding ────────────

def _make_holding(
    id: int,
    market: str,
    code: str,
    quantity: str,
    avg_cost: str,
    currency: str,
) -> dict[str, Any]:
    now = datetime.now(UTC)
    return {
        "id": id,
        "user_id": "demo",
        "market": market,
        "code": code,
        "quantity": Decimal(quantity),
        "avg_cost": Decimal(avg_cost),
        "currency": currency,
        "created_at": now,
        "updated_at": now,
    }


def _mock_quote(price: float, currency: str) -> Any:
    from datetime import datetime

    from app.schemas.market import Quote

    return Quote(
        symbol="TEST",
        market="test",
        price=price,
        change=0.0,
        change_pct=0.0,
        currency=currency,
        timestamp=datetime.now(UTC).isoformat(),
    )


# ──────────── 테스트 케이스 ────────────

@pytest.mark.asyncio
async def test_compute_summary_empty_holdings() -> None:
    """빈 holdings → 모든 값 0."""
    summary = await compute_summary([])
    assert summary.total_value_krw == "0.00"
    assert summary.total_pnl_krw == "0.00"
    assert summary.holdings == []


@pytest.mark.asyncio
async def test_compute_summary_single_krw_holding() -> None:
    """KRW 단일 보유 — 환율 변환 없이 직접 계산."""
    holdings = [
        _make_holding(1, "upbit", "KRW-BTC", "0.5", "50000000", "KRW")
    ]

    with (
        patch("app.services.portfolio.get_adapter") as mock_registry,
        patch("app.services.portfolio.get_rate", return_value=1.0),
    ):
        adapter = AsyncMock()
        adapter.fetch_quote = AsyncMock(return_value=_mock_quote(60000000, "KRW"))
        mock_registry.return_value = adapter

        summary = await compute_summary(holdings)

    assert summary.user_id == "demo"
    # 평가금액: 60,000,000 * 0.5 = 30,000,000 KRW
    assert Decimal(summary.total_value_krw) == Decimal("30000000.00")
    # 원가: 50,000,000 * 0.5 = 25,000,000 KRW
    assert Decimal(summary.total_cost_krw) == Decimal("25000000.00")
    # 손익: 5,000,000 KRW
    assert Decimal(summary.total_pnl_krw) == Decimal("5000000.00")
    assert len(summary.holdings) == 1


@pytest.mark.asyncio
async def test_compute_summary_usd_holding_with_fx() -> None:
    """USD 보유 종목 KRW 환산."""
    holdings = [
        _make_holding(1, "yahoo", "AAPL", "10", "150", "USD")
    ]

    async def mock_get_rate(base: str, quote: str) -> float:
        if base == "USD" and quote == "KRW":
            return 1300.0
        return 1.0

    with (
        patch("app.services.portfolio.get_adapter") as mock_registry,
        patch("app.services.portfolio.get_rate", side_effect=mock_get_rate),
    ):
        adapter = AsyncMock()
        adapter.fetch_quote = AsyncMock(return_value=_mock_quote(160.0, "USD"))
        mock_registry.return_value = adapter

        summary = await compute_summary(holdings)

    # 평가금액: 160 * 10 * 1300 = 2,080,000 KRW
    assert Decimal(summary.total_value_krw) == Decimal("2080000.00")
    # 원가: 150 * 10 * 1300 = 1,950,000 KRW
    assert Decimal(summary.total_cost_krw) == Decimal("1950000.00")
    # 손익: 130,000 KRW
    assert Decimal(summary.total_pnl_krw) == Decimal("130000.00")


@pytest.mark.asyncio
async def test_compute_summary_multiple_currencies() -> None:
    """복수 통화 holdings → 올바른 KRW 집계."""
    holdings = [
        _make_holding(1, "upbit", "KRW-ETH", "2", "3000000", "KRW"),   # KRW
        _make_holding(2, "yahoo", "TSLA", "5", "200", "USD"),           # USD
        _make_holding(3, "binance", "BTCUSDT", "0.1", "40000", "USDT"), # USDT
    ]

    async def mock_get_rate(base: str, quote: str) -> float:
        if base in ("USD", "USDT") and quote == "KRW":
            return 1350.0
        if base == "KRW" and quote == "KRW":
            return 1.0
        return 1.0

    with (
        patch("app.services.portfolio.get_adapter") as mock_registry,
        patch("app.services.portfolio.get_rate", side_effect=mock_get_rate),
    ):
        async def side_effect_fetch_quote(code: str) -> Any:
            prices = {
                "KRW-ETH": (3500000, "KRW"),
                "TSLA": (220.0, "USD"),
                "BTCUSDT": (45000.0, "USDT"),
            }
            p, c = prices.get(code, (100.0, "USD"))
            return _mock_quote(p, c)

        adapter = AsyncMock()
        adapter.fetch_quote = AsyncMock(side_effect=side_effect_fetch_quote)
        mock_registry.return_value = adapter

        summary = await compute_summary(holdings)

    # 전체 holdings 3개 확인
    assert len(summary.holdings) == 3
    # 총 평가금액 > 0
    assert Decimal(summary.total_value_krw) > 0
    # asset_class_breakdown 에 crypto, stock_us 존재
    assert "crypto" in summary.asset_class_breakdown
    assert "stock_us" in summary.asset_class_breakdown


@pytest.mark.asyncio
async def test_compute_summary_quote_failure_uses_avg_cost() -> None:
    """현재가 조회 실패 시 avg_cost 로 대체 — 손익 0."""
    holdings = [
        _make_holding(1, "upbit", "KRW-BTC", "1", "50000000", "KRW")
    ]

    with (
        patch("app.services.portfolio.get_adapter") as mock_registry,
        patch("app.services.portfolio.get_rate", return_value=1.0),
    ):
        adapter = AsyncMock()
        adapter.fetch_quote = AsyncMock(side_effect=Exception("network error"))
        mock_registry.return_value = adapter

        summary = await compute_summary(holdings)

    # 가격 = avg_cost → 손익 0
    assert Decimal(summary.total_pnl_krw) == Decimal("0.00")


@pytest.mark.asyncio
async def test_compute_summary_with_prev_snapshot() -> None:
    """전일 스냅샷 있을 때 일간 변동 계산."""
    holdings = [
        _make_holding(1, "upbit", "KRW-BTC", "1", "50000000", "KRW")
    ]

    class FakeSnapshot:
        total_value_krw = Decimal("55000000")

    with (
        patch("app.services.portfolio.get_adapter") as mock_registry,
        patch("app.services.portfolio.get_rate", return_value=1.0),
    ):
        adapter = AsyncMock()
        adapter.fetch_quote = AsyncMock(return_value=_mock_quote(60000000, "KRW"))
        mock_registry.return_value = adapter

        summary = await compute_summary(holdings, prev_snapshot=FakeSnapshot())

    # 현재: 60,000,000, 전일: 55,000,000 → +5,000,000
    assert Decimal(summary.daily_change_krw) == Decimal("5000000.00")
    assert Decimal(summary.daily_change_pct) > 0


def test_classify_asset() -> None:
    """market → asset_class 분류 검증."""
    assert _classify_asset("upbit") == "crypto"
    assert _classify_asset("binance") == "crypto"
    assert _classify_asset("yahoo") == "stock_us"
    assert _classify_asset("naver_kr") == "stock_kr"
    assert _classify_asset("unknown_market") == "other"


@pytest.mark.asyncio
async def test_decimal_precision() -> None:
    """Decimal 정밀도 — 부동소수점 누적 오차 없음."""
    # 소수점이 많은 암호화폐 수량
    holdings = [
        _make_holding(1, "binance", "BTCUSDT", "0.00000001", "30000", "USDT")
    ]

    async def mock_get_rate(base: str, quote: str) -> float:
        return 1350.0

    with (
        patch("app.services.portfolio.get_adapter") as mock_registry,
        patch("app.services.portfolio.get_rate", side_effect=mock_get_rate),
    ):
        adapter = AsyncMock()
        adapter.fetch_quote = AsyncMock(return_value=_mock_quote(35000.0, "USDT"))
        mock_registry.return_value = adapter

        summary = await compute_summary(holdings)

    # 결과가 str 로 직렬화됨 (Decimal 정밀도 유지)
    assert isinstance(summary.total_value_krw, str)
    assert "." in summary.total_value_krw
