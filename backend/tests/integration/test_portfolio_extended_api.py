"""포트폴리오 확장 API 통합 테스트 — sprint-08 Phase B-1.

신규 엔드포인트:
  GET /portfolio/sectors/heatmap
  GET /portfolio/monthly-returns
  GET /portfolio/ai-insight
기존 /portfolio/summary 에 win_rate_pct, market_leaders 추가 확인.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Column, Date, DateTime, Integer, JSON, Numeric, String, UniqueConstraint
from sqlalchemy import MetaData, Table
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app
from app.db.session import get_db


# ──────────────────────────────────────────────────────────────────────────────
# in-memory DB fixture (portfolio_client 패턴 재사용)
# ──────────────────────────────────────────────────────────────────────────────

def _create_tables(conn: Any) -> None:
    metadata = MetaData()
    Table(
        "holdings",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("user_id", String(50), nullable=False, default="demo"),
        Column("market", String(20), nullable=False),
        Column("code", String(50), nullable=False),
        Column("quantity", Numeric(24, 8), nullable=False),
        Column("avg_cost", Numeric(24, 8), nullable=False),
        Column("currency", String(3), nullable=False, default="USD"),
        Column("created_at", DateTime(timezone=True)),
        Column("updated_at", DateTime(timezone=True)),
    )
    Table(
        "portfolio_snapshots",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("user_id", String(50), nullable=False, default="demo"),
        Column("snapshot_date", Date, nullable=False),
        Column("total_value_krw", Numeric(24, 4), nullable=False),
        Column("total_pnl_krw", Numeric(24, 4), nullable=False),
        Column("asset_class_breakdown", JSON, nullable=False),
        Column("holdings_detail", JSON, nullable=False),
        Column("created_at", DateTime(timezone=True)),
        UniqueConstraint("user_id", "snapshot_date", name="uq_snapshot_user_date_ext"),
    )
    metadata.create_all(conn)


@pytest.fixture
async def portfolio_client() -> AsyncGenerator[AsyncClient, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(_create_tables)

    SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.pop(get_db, None)
    await engine.dispose()


# ──────────────────────────────────────────────────────────────────────────────
# GET /portfolio/summary — win_rate_pct + market_leaders 필드 확인
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_summary_has_win_rate_pct(portfolio_client: AsyncClient) -> None:
    """GET /portfolio/summary → win_rate_pct 필드 포함."""
    with patch("app.services.portfolio.get_adapter") as mock_adp, \
         patch("app.services.portfolio.get_rate", return_value=1.0):
        mock_adp.return_value.fetch_quote = AsyncMock()
        resp = await portfolio_client.get("/portfolio/summary")

    assert resp.status_code == 200
    body = resp.json()
    assert "win_rate_pct" in body


@pytest.mark.asyncio
async def test_summary_has_market_leaders(portfolio_client: AsyncClient) -> None:
    """GET /portfolio/summary → market_leaders 필드 포함."""
    with patch("app.services.portfolio.get_adapter") as mock_adp, \
         patch("app.services.portfolio.get_rate", return_value=1.0):
        mock_adp.return_value.fetch_quote = AsyncMock()
        resp = await portfolio_client.get("/portfolio/summary")

    assert resp.status_code == 200
    body = resp.json()
    assert "market_leaders" in body
    assert isinstance(body["market_leaders"], list)


@pytest.mark.asyncio
async def test_summary_empty_portfolio_fallback_leaders(portfolio_client: AsyncClient) -> None:
    """빈 포트폴리오 → market_leaders 에 fallback top3 포함."""
    with patch("app.services.portfolio.get_adapter") as mock_adp, \
         patch("app.services.portfolio.get_rate", return_value=1.0):
        mock_adp.return_value.fetch_quote = AsyncMock()
        resp = await portfolio_client.get("/portfolio/summary")

    assert resp.status_code == 200
    body = resp.json()
    leaders = body["market_leaders"]
    assert len(leaders) == 3
    tickers = [l["ticker"] for l in leaders]
    # S&P top3 fallback
    assert "NVDA" in tickers
    assert "AAPL" in tickers
    assert "MSFT" in tickers


@pytest.mark.asyncio
async def test_summary_empty_win_rate(portfolio_client: AsyncClient) -> None:
    """빈 포트폴리오 → win_rate_pct '0.00'."""
    with patch("app.services.portfolio.get_adapter") as mock_adp, \
         patch("app.services.portfolio.get_rate", return_value=1.0):
        mock_adp.return_value.fetch_quote = AsyncMock()
        resp = await portfolio_client.get("/portfolio/summary")

    assert resp.status_code == 200
    assert resp.json()["win_rate_pct"] == "0.00"


# ──────────────────────────────────────────────────────────────────────────────
# GET /portfolio/sectors/heatmap
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sector_heatmap_200_empty(portfolio_client: AsyncClient) -> None:
    """빈 포트폴리오 → 200 + 빈 배열."""
    with patch("app.services.portfolio.get_adapter") as mock_adp, \
         patch("app.services.portfolio.get_rate", return_value=1.0):
        mock_adp.return_value.fetch_quote = AsyncMock()
        resp = await portfolio_client.get("/portfolio/sectors/heatmap")

    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_sector_heatmap_schema(portfolio_client: AsyncClient) -> None:
    """heatmap 응답 스키마: sector, weight_pct, pnl_pct, intensity."""
    # holding 추가
    with patch("app.api.portfolio.get_adapter") as mock_reg:
        mock_reg.return_value = AsyncMock()
        await portfolio_client.post(
            "/portfolio/holdings",
            json={"market": "yahoo", "code": "AAPL", "quantity": "10", "avg_cost": "150", "currency": "USD"},
        )

    from app.schemas.market import Quote
    mock_quote = Quote(
        symbol="AAPL", market="yahoo",
        price=180.0, change=0.0, change_pct=0.0,
        currency="USD", timestamp=datetime.now(UTC).isoformat(),
    )
    with patch("app.services.portfolio.get_adapter") as mock_adp, \
         patch("app.services.portfolio.get_rate", return_value=1330.0):
        adapter = AsyncMock()
        adapter.fetch_quote = AsyncMock(return_value=mock_quote)
        mock_adp.return_value = adapter
        resp = await portfolio_client.get("/portfolio/sectors/heatmap")

    assert resp.status_code == 200
    tiles = resp.json()
    if tiles:
        tile = tiles[0]
        assert "sector" in tile
        assert "weight_pct" in tile
        assert "pnl_pct" in tile
        assert "intensity" in tile


# ──────────────────────────────────────────────────────────────────────────────
# GET /portfolio/monthly-returns
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_monthly_returns_200(portfolio_client: AsyncClient) -> None:
    """GET /portfolio/monthly-returns → 200."""
    with patch("app.services.portfolio.get_adapter") as mock_adp, \
         patch("app.services.portfolio.get_rate", return_value=1.0):
        mock_adp.return_value.fetch_quote = AsyncMock()
        resp = await portfolio_client.get("/portfolio/monthly-returns")

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_monthly_returns_has_365_cells(portfolio_client: AsyncClient) -> None:
    """연도 지정 → 해당 연도 일수만큼 셀 반환."""
    with patch("app.services.portfolio.get_adapter") as mock_adp, \
         patch("app.services.portfolio.get_rate", return_value=1.0):
        mock_adp.return_value.fetch_quote = AsyncMock()
        resp = await portfolio_client.get("/portfolio/monthly-returns?year=2025")

    assert resp.status_code == 200
    cells = resp.json()
    assert len(cells) == 365  # 2025년 평년


@pytest.mark.asyncio
async def test_monthly_returns_schema(portfolio_client: AsyncClient) -> None:
    """각 셀 스키마: date, return_pct, cell_level."""
    with patch("app.services.portfolio.get_adapter") as mock_adp, \
         patch("app.services.portfolio.get_rate", return_value=1.0):
        mock_adp.return_value.fetch_quote = AsyncMock()
        resp = await portfolio_client.get("/portfolio/monthly-returns?year=2025")

    cells = resp.json()
    first = cells[0]
    assert "date" in first
    assert "return_pct" in first
    assert "cell_level" in first
    assert first["date"] == "2025-01-01"


# ──────────────────────────────────────────────────────────────────────────────
# GET /portfolio/ai-insight
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ai_insight_200(portfolio_client: AsyncClient) -> None:
    """GET /portfolio/ai-insight → 200."""
    with patch("app.services.portfolio.get_adapter") as mock_adp, \
         patch("app.services.portfolio.get_rate", return_value=1.0):
        mock_adp.return_value.fetch_quote = AsyncMock()
        resp = await portfolio_client.get("/portfolio/ai-insight")

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_ai_insight_stub_mode(portfolio_client: AsyncClient) -> None:
    """ai-insight → stub_mode=True."""
    with patch("app.services.portfolio.get_adapter") as mock_adp, \
         patch("app.services.portfolio.get_rate", return_value=1.0):
        mock_adp.return_value.fetch_quote = AsyncMock()
        resp = await portfolio_client.get("/portfolio/ai-insight")

    assert resp.status_code == 200
    body = resp.json()
    assert body["stub_mode"] is True


@pytest.mark.asyncio
async def test_ai_insight_gates_pass(portfolio_client: AsyncClient) -> None:
    """ai-insight → gates 모두 'pass'."""
    with patch("app.services.portfolio.get_adapter") as mock_adp, \
         patch("app.services.portfolio.get_rate", return_value=1.0):
        mock_adp.return_value.fetch_quote = AsyncMock()
        resp = await portfolio_client.get("/portfolio/ai-insight")

    body = resp.json()
    gates = body["gates"]
    assert gates["schema"] == "pass"
    assert gates["domain"] == "pass"
    assert gates["critique"] == "pass"


@pytest.mark.asyncio
async def test_ai_insight_schema(portfolio_client: AsyncClient) -> None:
    """ai-insight 응답 필드: summary, bullets, generated_at, stub_mode, gates."""
    with patch("app.services.portfolio.get_adapter") as mock_adp, \
         patch("app.services.portfolio.get_rate", return_value=1.0):
        mock_adp.return_value.fetch_quote = AsyncMock()
        resp = await portfolio_client.get("/portfolio/ai-insight")

    body = resp.json()
    assert "summary" in body
    assert "bullets" in body
    assert "generated_at" in body
    assert "stub_mode" in body
    assert "gates" in body
    assert len(body["bullets"]) == 3
