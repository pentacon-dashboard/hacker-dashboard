"""포트폴리오 API 통합 테스트 — in-memory SQLite + DI override."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
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

# ──────────── in-memory DB fixtures ────────────


def _create_portfolio_tables(conn: Any) -> None:
    metadata = MetaData()
    Table(
        "clients",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("user_id", String(50), nullable=False, default="pb-demo"),
        Column("client_id", String(50), nullable=False),
        Column("label", String(128), nullable=True),
        Column("display_name", String(128), nullable=True),
        Column("normalized_label", String(128), nullable=True),
        Column("normalized_name", String(128), nullable=True),
        Column("status", String(32), nullable=False, default="active"),
        Column("created_at", DateTime(timezone=True)),
        Column("updated_at", DateTime(timezone=True)),
    )
    Table(
        "client_aliases",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("user_id", String(50), nullable=False, default="pb-demo"),
        Column("client_id", String(50), nullable=False),
        Column("alias_type", String(32), nullable=False),
        Column("alias_value", String(128), nullable=False),
        Column("normalized_value", String(128), nullable=False),
        Column("created_at", DateTime(timezone=True)),
    )
    Table(
        "holdings",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("user_id", String(50), nullable=False, default="pb-demo"),
        Column("client_id", String(50), nullable=False, default="client-001"),
        Column("market", String(20), nullable=False),
        Column("code", String(50), nullable=False),
        Column("quantity", Numeric(24, 8), nullable=False),
        Column("avg_cost", Numeric(24, 8), nullable=True),
        Column("cost_basis_status", String(32), nullable=False, server_default="provided"),
        Column("currency", String(4), nullable=False, default="USD"),
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
        Column("total_pnl_krw", Numeric(24, 4), nullable=True),
        Column("asset_class_breakdown", JSON, nullable=False),
        Column("holdings_detail", JSON, nullable=False),
        Column("created_at", DateTime(timezone=True)),
        UniqueConstraint(
            "user_id", "client_id", "snapshot_date", name="uq_snapshot_user_client_date"
        ),
    )
    Table(
        "portfolio_import_batches",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("user_id", String(50), nullable=False, default="pb-demo"),
        Column("client_id", String(50), nullable=False),
        Column("import_batch_key", String(128), nullable=False, unique=True),
        Column("file_name", String(255), nullable=False),
        Column("file_content_hash", String(64), nullable=False),
        Column("confirmed_mapping_hash", String(64), nullable=False),
        Column("confirmed_mapping", Text, nullable=False),
        Column("status", String(32), nullable=False),
        Column("warnings", Text, nullable=False, default="[]"),
        Column("created_at", DateTime(timezone=True)),
        Column("updated_at", DateTime(timezone=True)),
    )
    Table(
        "portfolio_import_rows",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("user_id", String(50), nullable=False, default="pb-demo"),
        Column("client_id", String(50), nullable=False),
        Column(
            "import_batch_key",
            String(128),
            ForeignKey("portfolio_import_batches.import_batch_key", ondelete="CASCADE"),
            nullable=False,
        ),
        Column("source_row", Integer, nullable=False),
        Column("row_status", String(32), nullable=False),
        Column("raw_row_json", JSON, nullable=False),
        Column("normalized_payload_json", JSON, nullable=True),
        Column("reason_codes", JSON, nullable=False),
        Column("linked_holding_id", Integer, nullable=True),
        Column("created_at", DateTime(timezone=True)),
    )
    Table(
        "watchlist_alerts",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("user_id", String(50), nullable=False, default="pb-demo"),
        Column("client_id", String(50), nullable=False, default="client-001"),
        Column("symbol", String(50), nullable=False),
        Column("market", String(20), nullable=False),
        Column("direction", String(10), nullable=False),
        Column("threshold", Numeric(18, 4), nullable=False),
        Column("enabled", Boolean, nullable=False, default=True),
        Column("created_at", DateTime(timezone=True)),
    )
    metadata.create_all(conn)


@pytest.fixture
async def portfolio_client() -> AsyncGenerator[AsyncClient, None]:
    """포트폴리오 API 테스트용 클라이언트 — SQLite in-memory DB override."""
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


# ──────────── Holdings CRUD 테스트 ────────────


@pytest.mark.asyncio
async def test_create_holding(portfolio_client: AsyncClient) -> None:
    """POST /portfolio/holdings → 201 + HoldingResponse."""
    with patch("app.api.portfolio.get_adapter") as mock_reg:
        mock_reg.return_value = AsyncMock()
        resp = await portfolio_client.post(
            "/portfolio/holdings",
            json={
                "market": "upbit",
                "code": "KRW-BTC",
                "quantity": "1.5",
                "avg_cost": "50000000",
                "currency": "KRW",
            },
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["market"] == "upbit"
    assert body["code"] == "KRW-BTC"
    assert body["user_id"] == "pb-demo"
    assert body["client_id"] == "client-001"
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body


@pytest.mark.asyncio
async def test_list_holdings_empty(portfolio_client: AsyncClient) -> None:
    """GET /portfolio/holdings → 빈 배열."""
    resp = await portfolio_client.get("/portfolio/holdings")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_holdings_after_create(portfolio_client: AsyncClient) -> None:
    """POST 후 GET → 1건 반환."""
    with patch("app.api.portfolio.get_adapter") as mock_reg:
        mock_reg.return_value = AsyncMock()
        await portfolio_client.post(
            "/portfolio/holdings",
            json={
                "market": "binance",
                "code": "BTCUSDT",
                "quantity": "0.5",
                "avg_cost": "40000",
                "currency": "USDT",
            },
        )

    resp = await portfolio_client.get("/portfolio/holdings")
    assert resp.status_code == 200
    holdings = resp.json()
    assert len(holdings) == 1
    assert holdings[0]["code"] == "BTCUSDT"


@pytest.mark.asyncio
async def test_list_holdings_filters_by_client_id(portfolio_client: AsyncClient) -> None:
    """client_id 쿼리는 기본 고객과 다른 고객 보유 종목을 분리한다."""
    with patch("app.api.portfolio.get_adapter") as mock_reg:
        mock_reg.return_value = AsyncMock()
        await portfolio_client.post(
            "/portfolio/holdings",
            json={
                "client_id": "client-002",
                "market": "yahoo",
                "code": "MSFT",
                "quantity": "2",
                "avg_cost": "300",
                "currency": "USD",
            },
        )

    default_resp = await portfolio_client.get("/portfolio/holdings")
    client_resp = await portfolio_client.get("/portfolio/holdings?client_id=client-002")

    assert default_resp.status_code == 200
    assert default_resp.json() == []
    assert client_resp.status_code == 200
    holdings = client_resp.json()
    assert len(holdings) == 1
    assert holdings[0]["client_id"] == "client-002"
    assert holdings[0]["code"] == "MSFT"


@pytest.mark.asyncio
async def test_update_holding(portfolio_client: AsyncClient) -> None:
    """PATCH /portfolio/holdings/{id} → 수량/평단가 수정."""
    with patch("app.api.portfolio.get_adapter") as mock_reg:
        mock_reg.return_value = AsyncMock()
        create_resp = await portfolio_client.post(
            "/portfolio/holdings",
            json={
                "market": "upbit",
                "code": "KRW-ETH",
                "quantity": "2.0",
                "avg_cost": "3000000",
                "currency": "KRW",
            },
        )
    holding_id = create_resp.json()["id"]

    resp = await portfolio_client.patch(
        f"/portfolio/holdings/{holding_id}",
        json={"quantity": "3.0", "avg_cost": "3100000"},
    )
    assert resp.status_code == 200
    body = resp.json()
    # DB Numeric(24,8) 직렬화 형식 수용 (3.0 or 3.00000000)
    assert Decimal(body["quantity"]) == Decimal("3.0")
    assert Decimal(body["avg_cost"]) == Decimal("3100000")


@pytest.mark.asyncio
async def test_update_holding_not_found(portfolio_client: AsyncClient) -> None:
    """PATCH 존재하지 않는 ID → 404."""
    resp = await portfolio_client.patch("/portfolio/holdings/9999", json={"quantity": "1.0"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_holding(portfolio_client: AsyncClient) -> None:
    """DELETE /portfolio/holdings/{id} → 204."""
    with patch("app.api.portfolio.get_adapter") as mock_reg:
        mock_reg.return_value = AsyncMock()
        create_resp = await portfolio_client.post(
            "/portfolio/holdings",
            json={
                "market": "yahoo",
                "code": "AAPL",
                "quantity": "10",
                "avg_cost": "150",
                "currency": "USD",
            },
        )
    holding_id = create_resp.json()["id"]

    resp = await portfolio_client.delete(f"/portfolio/holdings/{holding_id}")
    assert resp.status_code == 204

    # 삭제 후 목록 확인
    list_resp = await portfolio_client.get("/portfolio/holdings")
    assert list_resp.json() == []


@pytest.mark.asyncio
async def test_delete_holding_not_found(portfolio_client: AsyncClient) -> None:
    """DELETE 존재하지 않는 ID → 404."""
    resp = await portfolio_client.delete("/portfolio/holdings/9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_holding_invalid_market(portfolio_client: AsyncClient) -> None:
    """잘못된 market → 422."""
    resp = await portfolio_client.post(
        "/portfolio/holdings",
        json={
            "market": "invalid_exchange",
            "code": "XYZ",
            "quantity": "1",
            "avg_cost": "100",
            "currency": "USD",
        },
    )
    assert resp.status_code == 422


# ──────────── Summary 테스트 ────────────


@pytest.mark.asyncio
async def test_get_summary_empty(portfolio_client: AsyncClient) -> None:
    """빈 holdings → summary 반환 (0 값)."""
    with patch("app.services.portfolio.get_adapter") as mock_reg:
        mock_reg.return_value = AsyncMock()
        with patch("app.services.portfolio.get_rate", return_value=1.0):
            resp = await portfolio_client.get("/portfolio/summary")

    assert resp.status_code == 200
    body = resp.json()
    assert "total_value_krw" in body
    assert "total_pnl_krw" in body
    assert "holdings" in body
    assert body["total_value_krw"] == "0.00"


@pytest.mark.asyncio
async def test_get_summary_with_holdings(portfolio_client: AsyncClient) -> None:
    """holdings 있을 때 summary 계산."""
    # holding 생성
    with patch("app.api.portfolio.get_adapter") as mock_reg:
        mock_reg.return_value = AsyncMock()
        await portfolio_client.post(
            "/portfolio/holdings",
            json={
                "market": "upbit",
                "code": "KRW-BTC",
                "quantity": "1.0",
                "avg_cost": "50000000",
                "currency": "KRW",
            },
        )

    from app.schemas.market import Quote

    mock_quote = Quote(
        symbol="KRW-BTC",
        market="upbit",
        price=60000000.0,
        change=0.0,
        change_pct=0.0,
        currency="KRW",
        timestamp=datetime.now(UTC).isoformat(),
    )

    with (
        patch("app.services.portfolio.get_adapter") as mock_adp,
        patch("app.services.portfolio.get_rate", return_value=1.0),
    ):
        adapter = AsyncMock()
        adapter.fetch_quote = AsyncMock(return_value=mock_quote)
        mock_adp.return_value = adapter

        resp = await portfolio_client.get("/portfolio/summary")

    assert resp.status_code == 200
    body = resp.json()
    assert Decimal(body["total_value_krw"]) == Decimal("60000000.00")
    assert len(body["holdings"]) == 1


@pytest.mark.asyncio
async def test_get_clients_empty(portfolio_client: AsyncClient) -> None:
    """GET /portfolio/clients returns an empty client book when no ledger exists."""
    resp = await portfolio_client.get("/portfolio/clients")

    assert resp.status_code == 200
    body = resp.json()
    assert body["user_id"] == "pb-demo"
    assert body["client_count"] == 0
    assert body["clients"] == []


@pytest.mark.asyncio
async def test_reset_customer_data_requires_confirmation(
    portfolio_client: AsyncClient,
) -> None:
    """POST /portfolio/customer-data/reset rejects accidental destructive requests."""
    resp = await portfolio_client.post(
        "/portfolio/customer-data/reset",
        json={"confirmation": "wrong"},
    )

    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_reset_customer_data_deletes_customer_ledger(
    portfolio_client: AsyncClient,
) -> None:
    """Confirmed reset removes PB customer holdings, snapshots, imports, registry, and alerts."""
    with patch("app.api.portfolio.get_adapter") as mock_reg:
        mock_reg.return_value = AsyncMock()
        created = await portfolio_client.post(
            "/portfolio/holdings",
            json={
                "client_id": "client-002",
                "market": "yahoo",
                "code": "MSFT",
                "quantity": "2",
                "avg_cost": "300",
                "currency": "USD",
            },
        )
    holding_id = created.json()["id"]

    from app.db.models import (
        Client,
        ClientAlias,
        PortfolioImportBatch,
        PortfolioImportRow,
        PortfolioSnapshot,
        WatchlistAlert,
    )

    async for db in app.dependency_overrides[get_db]():
        now = datetime.now(UTC)
        db.add_all(
            [
                Client(
                    user_id="pb-demo",
                    client_id="client-002",
                    label="Client B",
                    status="active",
                    created_at=now,
                    updated_at=now,
                ),
                ClientAlias(
                    user_id="pb-demo",
                    client_id="client-002",
                    alias_type="label",
                    alias_value="Client B",
                    normalized_value="clientb",
                    created_at=now,
                ),
                PortfolioSnapshot(
                    user_id="pb-demo",
                    client_id="client-002",
                    snapshot_date=now.date(),
                    total_value_krw=Decimal("1000"),
                    total_pnl_krw=Decimal("10"),
                    asset_class_breakdown={},
                    holdings_detail=[],
                    created_at=now,
                ),
                PortfolioImportBatch(
                    user_id="pb-demo",
                    client_id="client-002",
                    import_batch_key="batch-1",
                    file_name="sample.csv",
                    file_content_hash="hash",
                    confirmed_mapping_hash="mapping",
                    confirmed_mapping="{}",
                    status="imported",
                    warnings="[]",
                    created_at=now,
                    updated_at=now,
                ),
                PortfolioImportRow(
                    user_id="pb-demo",
                    client_id="client-002",
                    import_batch_key="batch-1",
                    source_row=2,
                    row_status="imported",
                    raw_row_json={},
                    normalized_payload_json={},
                    reason_codes=[],
                    linked_holding_id=holding_id,
                    created_at=now,
                ),
                WatchlistAlert(
                    user_id="pb-demo",
                    client_id="client-002",
                    symbol="MSFT",
                    market="yahoo",
                    direction="above",
                    threshold=Decimal("400"),
                    enabled=True,
                    created_at=now,
                ),
            ]
        )
        await db.commit()

    resp = await portfolio_client.post(
        "/portfolio/customer-data/reset",
        json={"confirmation": "CLEAR_CUSTOMER_DATA"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "cleared"
    assert body["deleted_holdings"] == 1
    assert body["deleted_snapshots"] == 1
    assert body["deleted_import_rows"] == 1
    assert body["deleted_import_batches"] == 1
    assert body["deleted_clients"] == 1
    assert body["deleted_client_aliases"] == 1
    assert body["deleted_watchlist_alerts"] == 1

    clients_resp = await portfolio_client.get("/portfolio/clients")
    assert clients_resp.json()["clients"] == []


@pytest.mark.asyncio
@pytest.mark.skip(reason="client briefing report endpoint is out of scope for this PR")
async def test_client_briefing_report_success(portfolio_client: AsyncClient) -> None:
    """고객 브리핑 리포트는 섹션별 evidence와 export_ready를 반환한다."""
    with patch("app.api.portfolio.get_adapter") as mock_reg:
        mock_reg.return_value = AsyncMock()
        await portfolio_client.post(
            "/portfolio/holdings",
            json={
                "market": "upbit",
                "code": "KRW-BTC",
                "quantity": "1.0",
                "avg_cost": "50000000",
                "currency": "KRW",
            },
        )

    from app.schemas.market import Quote

    mock_quote = Quote(
        symbol="KRW-BTC",
        market="upbit",
        price=60000000.0,
        change=0.0,
        change_pct=0.0,
        currency="KRW",
        timestamp=datetime.now(UTC).isoformat(),
    )

    with (
        patch("app.services.portfolio.get_adapter") as mock_adp,
        patch("app.services.portfolio.get_rate", return_value=1.0),
    ):
        adapter = AsyncMock()
        adapter.fetch_quote = AsyncMock(return_value=mock_quote)
        mock_adp.return_value = adapter

        resp = await portfolio_client.post(
            "/portfolio/reports/client-briefing",
            json={"client_id": "client-001"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert body["client_context"]["client_id"] == "client-001"
    assert len(body["sections"]) == 5
    assert all(section["evidence"] for section in body["sections"])
    assert body["gate_results"]["evidence_gate"] == "pass"
    assert body["export_ready"] is True
    assert body["report_script"]


@pytest.mark.asyncio
@pytest.mark.skip(reason="client briefing report endpoint is out of scope for this PR")
async def test_client_briefing_report_insufficient_data(portfolio_client: AsyncClient) -> None:
    """보유 종목이 없으면 리포트는 근거 부족 상태로 fail closed 한다."""
    resp = await portfolio_client.post(
        "/portfolio/reports/client-briefing",
        json={"client_id": "client-001"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "insufficient_data"
    assert body["export_ready"] is False
    assert body["sections"] == []
    assert body["gate_results"]["evidence_gate"].startswith("fail")


# ──────────── Snapshots 테스트 ────────────


@pytest.mark.asyncio
async def test_list_snapshots_empty(portfolio_client: AsyncClient) -> None:
    """스냅샷 없으면 빈 배열."""
    resp = await portfolio_client.get("/portfolio/snapshots")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_snapshots_with_date_filter(portfolio_client: AsyncClient) -> None:
    """날짜 필터 파라미터 동작 확인."""
    resp = await portfolio_client.get("/portfolio/snapshots?from=2026-01-01&to=2026-12-31")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_holdings_currency_uppercase(portfolio_client: AsyncClient) -> None:
    """currency 는 대문자로 저장됨."""
    with patch("app.api.portfolio.get_adapter") as mock_reg:
        mock_reg.return_value = AsyncMock()
        resp = await portfolio_client.post(
            "/portfolio/holdings",
            json={
                "market": "binance",
                "code": "ETHUSDT",
                "quantity": "5",
                "avg_cost": "2000",
                "currency": "usdt",
            },
        )
    assert resp.status_code == 201
    assert resp.json()["currency"] == "USDT"
