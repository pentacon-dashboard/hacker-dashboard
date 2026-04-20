"""build_portfolio_context 헬퍼 smoke 테스트.

Phase D 에서 본격 확장 예정. 여기서는 세 가지 핵심 경로만 검증:
1. holdings 빈 리스트 → None 반환
2. holdings 2개 + target 매칭 → matched_holding 세팅 확인
3. compute_summary 예외 → None 반환 (graceful degrade)
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.analyze import PortfolioContext


# ──────────── 더미 Holding 팩토리 ────────────


def _make_orm_holding(
    id_: int,
    market: str,
    code: str,
    quantity: str,
    avg_cost: str,
    currency: str,
    user_id: str = "demo",
) -> Any:
    """SQLAlchemy Holding 객체를 흉내내는 Mock."""
    h = MagicMock()
    h.id = id_
    h.user_id = user_id
    h.market = market
    h.code = code
    h.quantity = Decimal(quantity)
    h.avg_cost = Decimal(avg_cost)
    h.currency = currency
    h.created_at = datetime.now(timezone.utc)
    h.updated_at = datetime.now(timezone.utc)
    return h


def _make_db_session(holdings: list[Any]) -> AsyncMock:
    """AsyncSession을 흉내내는 mock. scalars().all() 이 holdings를 반환."""
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = holdings

    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock

    session = AsyncMock()
    session.execute = AsyncMock(return_value=result_mock)
    return session


def _mock_quote(price: float, currency: str) -> Any:
    from app.schemas.market import Quote

    return Quote(
        symbol="TEST",
        market="test",
        price=price,
        change=0.0,
        change_pct=0.0,
        currency=currency,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


# ──────────── 테스트 케이스 ────────────


@pytest.mark.asyncio
async def test_build_portfolio_context_empty_holdings_returns_none() -> None:
    """DB에 holdings가 없으면 None 반환."""
    from app.services.portfolio import build_portfolio_context

    db = _make_db_session(holdings=[])

    result = await build_portfolio_context(db, user_id="demo")

    assert result is None


@pytest.mark.asyncio
async def test_build_portfolio_context_with_target_match() -> None:
    """holdings 2개 + target code 매칭 → matched_holding이 정확히 세팅됨."""
    from app.services.portfolio import build_portfolio_context

    holdings = [
        _make_orm_holding(1, "yahoo", "AAPL", "5", "185", "USD"),
        _make_orm_holding(2, "upbit", "KRW-BTC", "0.01", "50000000", "KRW"),
    ]
    db = _make_db_session(holdings=holdings)

    async def mock_get_rate(base: str, quote: str) -> float:
        if base in ("USD",) and quote == "KRW":
            return 1350.0
        return 1.0

    with (
        patch("app.services.portfolio.get_adapter") as mock_registry,
        patch("app.services.portfolio.get_rate", side_effect=mock_get_rate),
        patch("app.services.portfolio.get_prev_snapshot", new_callable=AsyncMock, return_value=None),
    ):
        async def side_effect_fetch_quote(code: str) -> Any:
            prices = {
                "AAPL": (190.0, "USD"),
                "KRW-BTC": (60000000.0, "KRW"),
            }
            p, c = prices.get(code, (100.0, "USD"))
            return _mock_quote(p, c)

        adapter = AsyncMock()
        adapter.fetch_quote = AsyncMock(side_effect=side_effect_fetch_quote)
        mock_registry.return_value = adapter

        result = await build_portfolio_context(
            db,
            user_id="demo",
            target_market="yahoo",
            target_code="AAPL",
        )

    assert result is not None
    assert isinstance(result, PortfolioContext)
    assert result.matched_holding is not None
    assert result.matched_holding.market == "yahoo"
    assert result.matched_holding.code == "AAPL"
    assert result.matched_holding.quantity == Decimal("5")
    # holdings 전체는 2개
    assert len(result.holdings) == 2
    # total_value_krw > 0
    assert result.total_value_krw > 0
    # asset_class_breakdown 에 stock_us, crypto 존재
    assert "stock_us" in result.asset_class_breakdown
    assert "crypto" in result.asset_class_breakdown


@pytest.mark.asyncio
async def test_build_portfolio_context_no_match_when_target_missing() -> None:
    """target이 holdings에 없으면 matched_holding=None."""
    from app.services.portfolio import build_portfolio_context

    holdings = [
        _make_orm_holding(1, "yahoo", "AAPL", "5", "185", "USD"),
    ]
    db = _make_db_session(holdings=holdings)

    with (
        patch("app.services.portfolio.get_adapter") as mock_registry,
        patch("app.services.portfolio.get_rate", return_value=1350.0),
        patch("app.services.portfolio.get_prev_snapshot", new_callable=AsyncMock, return_value=None),
    ):
        adapter = AsyncMock()
        adapter.fetch_quote = AsyncMock(return_value=_mock_quote(190.0, "USD"))
        mock_registry.return_value = adapter

        result = await build_portfolio_context(
            db,
            user_id="demo",
            target_market="upbit",
            target_code="KRW-BTC",
        )

    assert result is not None
    assert result.matched_holding is None


@pytest.mark.asyncio
async def test_build_portfolio_context_compute_summary_exception_returns_none() -> None:
    """compute_summary 예외 발생 시 None 반환 (graceful degrade)."""
    from app.services.portfolio import build_portfolio_context

    holdings = [
        _make_orm_holding(1, "yahoo", "AAPL", "5", "185", "USD"),
    ]
    db = _make_db_session(holdings=holdings)

    with (
        patch(
            "app.services.portfolio.compute_summary",
            new_callable=AsyncMock,
            side_effect=RuntimeError("market API down"),
        ),
        patch("app.services.portfolio.get_prev_snapshot", new_callable=AsyncMock, return_value=None),
    ):
        result = await build_portfolio_context(db, user_id="demo")

    assert result is None


@pytest.mark.asyncio
async def test_build_portfolio_context_db_exception_returns_none() -> None:
    """DB 조회 자체가 실패하면 None 반환."""
    from app.services.portfolio import build_portfolio_context

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=Exception("DB connection error"))

    result = await build_portfolio_context(session, user_id="demo")

    assert result is None
