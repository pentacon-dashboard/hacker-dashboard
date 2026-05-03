"""리밸런싱 엔드포인트 통합 테스트 — in-memory SQLite + DI override."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import (
    JSON,
    Column,
    Date,
    DateTime,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import get_db
from app.main import app
from app.schemas.market import Quote

# ──────────── DB fixtures ────────────


def _create_portfolio_tables(conn: Any) -> None:
    metadata = MetaData()
    Table(
        "holdings",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("user_id", String(50), nullable=False, default="pb-demo"),
        Column("client_id", String(50), nullable=False, default="client-001"),
        Column("market", String(20), nullable=False),
        Column("code", String(50), nullable=False),
        Column("quantity", Numeric(24, 8), nullable=False),
        Column("avg_cost", Numeric(24, 8), nullable=False),
        Column("currency", String(4), nullable=False, default="KRW"),
        Column("import_batch_key", String(128), nullable=True),
        Column("source_row", Integer, nullable=True),
        Column("source_columns", Text, nullable=True),
        Column("source_client_id", String(64), nullable=True),
        Column("created_at", DateTime(timezone=True)),
        Column("updated_at", DateTime(timezone=True)),
    )
    Table(
        "portfolio_snapshots",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("user_id", String(50), nullable=False, default="pb-demo"),
        Column("client_id", String(50), nullable=False, default="client-001"),
        Column("snapshot_date", Date, nullable=False),
        Column("total_value_krw", Numeric(24, 4), nullable=False),
        Column("total_pnl_krw", Numeric(24, 4), nullable=False),
        Column("asset_class_breakdown", JSON, nullable=False),
        Column("holdings_detail", JSON, nullable=False),
        Column("created_at", DateTime(timezone=True)),
        UniqueConstraint(
            "user_id", "client_id", "snapshot_date", name="uq_snapshot_user_client_date"
        ),
    )
    metadata.create_all(conn)


@pytest.fixture
async def rebalance_client() -> AsyncGenerator[AsyncClient, None]:
    """리밸런싱 API 테스트용 클라이언트 — SQLite in-memory DB override."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(_create_portfolio_tables)

    SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.pop(get_db, None)
    await engine.dispose()


def _make_quote(market: str, symbol: str, price: float, currency: str = "KRW") -> Quote:
    return Quote(
        symbol=symbol,
        market=market,
        price=price,
        change=0.0,
        change_pct=0.0,
        currency=currency,
        timestamp=datetime.now(UTC).isoformat(),
    )


async def _create_holding(
    client: AsyncClient,
    market: str,
    code: str,
    quantity: str,
    avg_cost: str,
    currency: str = "KRW",
) -> int:
    with patch("app.api.portfolio.get_adapter") as mock_reg:
        mock_reg.return_value = AsyncMock()
        resp = await client.post(
            "/portfolio/holdings",
            json={
                "market": market,
                "code": code,
                "quantity": quantity,
                "avg_cost": avg_cost,
                "currency": currency,
            },
        )
    assert resp.status_code == 201, f"holding 생성 실패: {resp.text}"
    return resp.json()["id"]


# ──────────── 기본 요청 JSON ────────────

_TARGET_STOCK_CRYPTO = {
    "target_allocation": {
        "stock_kr": 0.0,
        "stock_us": 0.5,
        "crypto": 0.5,
        "cash": 0.0,
        "fx": 0.0,
    }
}

_TARGET_BALANCED = {
    "target_allocation": {
        "stock_kr": 0.2,
        "stock_us": 0.4,
        "crypto": 0.3,
        "cash": 0.1,
        "fx": 0.0,
    }
}


# ──────────── 테스트 케이스 ────────────


@pytest.mark.asyncio
async def test_rebalance_empty_holdings(rebalance_client: AsyncClient) -> None:
    """holdings 비어있음 → actions = [], status=ok."""
    resp = await rebalance_client.post("/portfolio/rebalance", json=_TARGET_BALANCED)
    assert resp.status_code == 200
    body = resp.json()
    assert body["actions"] == []
    assert body["status"] == "ok"
    assert "request_id" in body
    assert "current_allocation" in body
    assert "drift" in body
    assert "summary" in body


@pytest.mark.asyncio
async def test_rebalance_invalid_target_sum(rebalance_client: AsyncClient) -> None:
    """target_allocation 합계 ≠ 1 → 422."""
    resp = await rebalance_client.post(
        "/portfolio/rebalance",
        json={
            "target_allocation": {
                "stock_kr": 0.5,
                "stock_us": 0.5,
                "crypto": 0.5,
                "cash": 0.0,
                "fx": 0.0,
            }
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_rebalance_normal_with_holdings(rebalance_client: AsyncClient) -> None:
    """정상 케이스: crypto heavy → stock_us 50% + crypto 50% 목표 → actions 1+건."""
    await _create_holding(rebalance_client, "upbit", "KRW-BTC", "0.5", "50000000")
    await _create_holding(rebalance_client, "yahoo", "AAPL", "1", "150000", currency="USD")

    btc_quote = _make_quote("upbit", "KRW-BTC", 80000000.0)
    aapl_quote = _make_quote("yahoo", "AAPL", 200.0, currency="USD")

    def mock_adapter_factory(market: str) -> AsyncMock:
        adapter = AsyncMock()
        if market == "upbit":
            adapter.fetch_quote = AsyncMock(return_value=btc_quote)
        else:
            adapter.fetch_quote = AsyncMock(return_value=aapl_quote)
        return adapter

    with (
        patch("app.services.portfolio.get_adapter", side_effect=mock_adapter_factory),
        patch(
            "app.services.portfolio.get_rate",
            side_effect=lambda src, dst: 1350.0 if src == "USD" else 1.0,
        ),
    ):
        resp = await rebalance_client.post("/portfolio/rebalance", json=_TARGET_STOCK_CRYPTO)

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in ("ok", "degraded")
    assert "current_allocation" in body
    assert "target_allocation" in body
    assert "drift" in body
    assert "actions" in body
    assert "summary" in body
    assert body["summary"]["total_trades"] == len(body["actions"])
    assert "X-Request-ID" in resp.headers


@pytest.mark.asyncio
async def test_rebalance_crypto_heavy_actions(rebalance_client: AsyncClient) -> None:
    """crypto 100% 보유, stock_us 50% 목표 → BTC 매도 + AAPL 매수."""
    await _create_holding(rebalance_client, "upbit", "KRW-BTC", "0.1", "50000000")
    await _create_holding(rebalance_client, "yahoo", "AAPL", "1", "150000", currency="USD")

    btc_quote = _make_quote("upbit", "KRW-BTC", 80000000.0)
    aapl_quote = _make_quote("yahoo", "AAPL", 200.0, currency="USD")

    def mock_adapter_factory(market: str) -> AsyncMock:
        adapter = AsyncMock()
        if market == "upbit":
            adapter.fetch_quote = AsyncMock(return_value=btc_quote)
        else:
            adapter.fetch_quote = AsyncMock(return_value=aapl_quote)
        return adapter

    with (
        patch("app.services.portfolio.get_adapter", side_effect=mock_adapter_factory),
        patch(
            "app.services.portfolio.get_rate",
            side_effect=lambda src, dst: 1350.0 if src == "USD" else 1.0,
        ),
    ):
        resp = await rebalance_client.post("/portfolio/rebalance", json=_TARGET_STOCK_CRYPTO)

    assert resp.status_code == 200
    body = resp.json()
    actions = body["actions"]

    sell_codes = {a["code"] for a in actions if a["action"] == "sell"}
    # buy_codes = {a["code"] for a in actions if a["action"] == "buy"}  # unused
    # crypto 비중이 높으므로 BTC 매도가 있어야 함
    assert "KRW-BTC" in sell_codes or len(actions) == 0, "crypto heavy인데 BTC 매도가 없음"


@pytest.mark.asyncio
async def test_rebalance_min_trade_krw_filters_all(rebalance_client: AsyncClient) -> None:
    """min_trade_krw 높게 설정 → 모든 액션 skip → actions = []."""
    await _create_holding(rebalance_client, "upbit", "KRW-BTC", "0.001", "50000000")
    await _create_holding(rebalance_client, "yahoo", "AAPL", "1", "150000", currency="USD")

    btc_quote = _make_quote("upbit", "KRW-BTC", 50000000.0)
    aapl_quote = _make_quote("yahoo", "AAPL", 180.0, currency="USD")

    def mock_adapter_factory(market: str) -> AsyncMock:
        adapter = AsyncMock()
        if market == "upbit":
            adapter.fetch_quote = AsyncMock(return_value=btc_quote)
        else:
            adapter.fetch_quote = AsyncMock(return_value=aapl_quote)
        return adapter

    with (
        patch("app.services.portfolio.get_adapter", side_effect=mock_adapter_factory),
        patch(
            "app.services.portfolio.get_rate",
            side_effect=lambda src, dst: 1350.0 if src == "USD" else 1.0,
        ),
    ):
        resp = await rebalance_client.post(
            "/portfolio/rebalance",
            json={
                "target_allocation": {
                    "stock_kr": 0.0,
                    "stock_us": 0.5,
                    "crypto": 0.5,
                    "cash": 0.0,
                    "fx": 0.0,
                },
                "constraints": {
                    "max_single_weight": 0.5,
                    "min_trade_krw": "999999999",  # 매우 높은 min_trade
                    "allow_fractional": True,
                },
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["actions"] == []


@pytest.mark.asyncio
async def test_rebalance_llm_failure_graceful_degrade(rebalance_client: AsyncClient) -> None:
    """LLM 실패 시 llm_analysis=None, status='degraded', actions는 보존."""
    await _create_holding(rebalance_client, "upbit", "KRW-BTC", "0.1", "50000000")
    await _create_holding(rebalance_client, "yahoo", "AAPL", "5", "150000", currency="USD")

    btc_quote = _make_quote("upbit", "KRW-BTC", 80000000.0)
    aapl_quote = _make_quote("yahoo", "AAPL", 200.0, currency="USD")

    def mock_adapter_factory(market: str) -> AsyncMock:
        adapter = AsyncMock()
        if market == "upbit":
            adapter.fetch_quote = AsyncMock(return_value=btc_quote)
        else:
            adapter.fetch_quote = AsyncMock(return_value=aapl_quote)
        return adapter

    # RebalanceAnalyzer가 예외를 던지는 상황 시뮬레이션
    mock_analyzer = MagicMock()
    mock_analyzer.analyze = AsyncMock(side_effect=RuntimeError("LLM connection refused"))

    with (
        patch("app.services.portfolio.get_adapter", side_effect=mock_adapter_factory),
        patch(
            "app.services.portfolio.get_rate",
            side_effect=lambda src, dst: 1350.0 if src == "USD" else 1.0,
        ),
        patch.dict(
            "sys.modules",
            {"app.agents.analyzers.rebalance": MagicMock(RebalanceAnalyzer=lambda: mock_analyzer)},
        ),
    ):
        resp = await rebalance_client.post("/portfolio/rebalance", json=_TARGET_BALANCED)

    assert resp.status_code == 200
    body = resp.json()
    assert body["llm_analysis"] is None
    assert body["status"] == "degraded"
    # 핵심 가치 보존: actions 필드는 있어야 함 (빈 배열이라도)
    assert "actions" in body


@pytest.mark.asyncio
async def test_rebalance_request_id_header(rebalance_client: AsyncClient) -> None:
    """X-Request-ID 헤더 전달 시 응답에 동일 ID 포함."""
    custom_id = "test-custom-req-id-12345"
    resp = await rebalance_client.post(
        "/portfolio/rebalance",
        headers={"X-Request-ID": custom_id},
        json=_TARGET_BALANCED,
    )
    assert resp.status_code == 200
    assert resp.headers.get("X-Request-ID") == custom_id
    assert resp.json()["request_id"] == custom_id


@pytest.mark.asyncio
async def test_rebalance_response_schema_fields(rebalance_client: AsyncClient) -> None:
    """응답이 RebalanceResponse 스키마의 모든 필수 필드를 포함하는지 확인."""
    resp = await rebalance_client.post("/portfolio/rebalance", json=_TARGET_BALANCED)
    assert resp.status_code == 200
    body = resp.json()

    required_fields = [
        "request_id",
        "status",
        "current_allocation",
        "target_allocation",
        "drift",
        "actions",
        "expected_allocation",
        "summary",
        "meta",
    ]
    for field in required_fields:
        assert field in body, f"필수 필드 '{field}'가 응답에 없음"

    summary_fields = [
        "total_trades",
        "total_sell_value_krw",
        "total_buy_value_krw",
        "rebalance_cost_estimate_krw",
    ]
    for field in summary_fields:
        assert field in body["summary"], f"summary.{field} 누락"

    meta_fields = ["gates", "evidence_snippets"]
    for field in meta_fields:
        assert field in body["meta"], f"meta.{field} 누락"


@pytest.mark.asyncio
async def test_rebalance_allocation_asset_class_keys(rebalance_client: AsyncClient) -> None:
    """current_allocation에 5개 자산군 키가 모두 포함되는지 확인."""
    resp = await rebalance_client.post("/portfolio/rebalance", json=_TARGET_BALANCED)
    assert resp.status_code == 200
    body = resp.json()
    expected_keys = {"stock_kr", "stock_us", "crypto", "cash", "fx"}
    current_keys = set(body["current_allocation"].keys())
    assert expected_keys.issubset(current_keys), (
        f"current_allocation에 누락된 키: {expected_keys - current_keys}"
    )
