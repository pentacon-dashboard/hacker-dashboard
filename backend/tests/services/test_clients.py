from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import JSON, Column, Date, DateTime, Integer, MetaData, Numeric, String, Table
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Client, ClientAlias, Holding, PortfolioImportBatch
from app.services.clients import (
    ensure_client_registry,
    normalize_client_name,
    resolve_client_reference,
)


@pytest.fixture
async def client_db() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    def create_tables(conn: Any) -> None:
        Client.__table__.create(conn)
        ClientAlias.__table__.create(conn)
        Holding.__table__.create(conn)
        PortfolioImportBatch.__table__.create(conn)
        metadata = MetaData()
        Table(
            "portfolio_snapshots",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("user_id", String(50), nullable=False),
            Column("client_id", String(50), nullable=False),
            Column("snapshot_date", Date, nullable=False),
            Column("total_value_krw", Numeric(24, 4), nullable=False),
            Column("total_pnl_krw", Numeric(24, 4), nullable=False),
            Column("asset_class_breakdown", JSON, nullable=False),
            Column("holdings_detail", JSON, nullable=False),
            Column("created_at", DateTime(timezone=True)),
        )
        metadata.create_all(conn)

    async with engine.begin() as conn:
        await conn.run_sync(create_tables)

    SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    async with SessionLocal() as session:
        yield session
    await engine.dispose()


def test_normalize_client_name_keeps_short_customer_label() -> None:
    assert normalize_client_name("김민수 고객") == "김민수"
    assert normalize_client_name("김 민 수님") == "김민수"
    assert normalize_client_name("고객 C") == "고객c"


@pytest.mark.asyncio
async def test_resolve_unique_display_name(client_db: AsyncSession) -> None:
    await ensure_client_registry(
        client_db,
        client_id="client-014",
        label="VIP-14",
        display_name="홍길동",
    )
    await client_db.commit()

    resolution = await resolve_client_reference(
        client_db,
        "홍 길 동 포트폴리오 요약",
        sync_from_portfolio=False,
    )

    assert resolution.status == "resolved"
    assert resolution.client_id == "client-014"
    assert resolution.display_name == "홍길동"


@pytest.mark.asyncio
async def test_label_and_name_mismatch_blocks_resolution(client_db: AsyncSession) -> None:
    await ensure_client_registry(client_db, client_id="client-003", label="고객 C")
    await ensure_client_registry(client_db, client_id="client-014", label="VIP-14", display_name="홍길동")
    await client_db.commit()

    resolution = await resolve_client_reference(
        client_db,
        "고객 C 홍길동 포트폴리오 요약",
        sync_from_portfolio=False,
    )

    assert resolution.status == "mismatch"
    assert {candidate.client_id for candidate in resolution.candidates} == {
        "client-003",
        "client-014",
    }


@pytest.mark.asyncio
async def test_ambiguous_name_candidates_are_sorted(client_db: AsyncSession) -> None:
    now = datetime.now(UTC)
    await ensure_client_registry(client_db, client_id="client-014", label="VIP-14", display_name="김민수")
    await ensure_client_registry(client_db, client_id="client-022", label="VIP-22", display_name="김민수")
    client_db.add(
        Holding(
            user_id="pb-demo",
            client_id="client-022",
            market="yahoo",
            code="AAPL",
            quantity=Decimal("1"),
            avg_cost=Decimal("100"),
            currency="USD",
            created_at=now - timedelta(days=2),
            updated_at=now - timedelta(days=2),
        )
    )
    client_db.add(
        PortfolioImportBatch(
            user_id="pb-demo",
            client_id="client-014",
            import_batch_key="batch-014",
            file_name="recent.csv",
            file_content_hash="hash",
            confirmed_mapping_hash="mapping",
            confirmed_mapping="{}",
            status="imported",
            warnings="[]",
            created_at=now,
            updated_at=now,
        )
    )
    await client_db.commit()

    resolution = await resolve_client_reference(
        client_db,
        "김민수 포트폴리오 요약",
        sync_from_portfolio=False,
    )

    assert resolution.status == "ambiguous"
    assert [candidate.client_id for candidate in resolution.candidates] == [
        "client-014",
        "client-022",
    ]


@pytest.mark.asyncio
async def test_name_resolution_requires_exact_normalized_match(client_db: AsyncSession) -> None:
    await ensure_client_registry(
        client_db,
        client_id="client-018",
        label="VIP-18",
        display_name="Kim",
    )
    await client_db.commit()

    resolution = await resolve_client_reference(
        client_db,
        "Kimber portfolio summary",
        sync_from_portfolio=False,
    )

    assert resolution.status == "not_found"
    assert resolution.candidates == ()


@pytest.mark.asyncio
async def test_confirmed_upload_name_sets_empty_display_name_then_alias(
    client_db: AsyncSession,
) -> None:
    await ensure_client_registry(client_db, client_id="client-030", label="고객 Z")
    await ensure_client_registry(
        client_db,
        client_id="client-030",
        display_name="박지훈",
        source_names=["박지훈"],
    )
    await ensure_client_registry(
        client_db,
        client_id="client-030",
        display_name="Park Jihoon",
        source_names=["Park Jihoon"],
    )
    await client_db.commit()

    client = await client_db.get(Client, 1)
    assert client is not None
    assert client.display_name == "박지훈"

    aliases = (
        await client_db.execute(
            ClientAlias.__table__.select().where(ClientAlias.client_id == "client-030")
        )
    ).all()
    alias_values = {row.alias_value for row in aliases}
    assert {"박지훈", "Park Jihoon", "고객 Z"}.issubset(alias_values)
