"""업로드 API 통합 테스트 — sprint-08 Phase B-5."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Column, DateTime, Integer, MetaData, Numeric, String, Table, Text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import get_db
from app.main import app


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


def _csv_bytes(
    rows: list[str], header: str = "date,market,code,quantity,avg_cost,currency,note"
) -> bytes:
    lines = [header] + rows
    return "\n".join(lines).encode("utf-8")


def _create_upload_import_tables(conn: Any) -> None:
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
        Column("currency", String(4), nullable=False, default="USD"),
        Column("import_batch_key", String(128), nullable=True),
        Column("source_row", Integer, nullable=True),
        Column("source_columns", Text, nullable=True),
        Column("source_client_id", String(64), nullable=True),
        Column("created_at", DateTime(timezone=True)),
        Column("updated_at", DateTime(timezone=True)),
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
        Column("warnings", Text, nullable=False),
        Column("created_at", DateTime(timezone=True)),
        Column("updated_at", DateTime(timezone=True)),
    )
    metadata.create_all(conn)


@pytest.fixture
async def upload_import_client() -> AsyncGenerator[AsyncClient, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(_create_upload_import_tables)

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
# POST /upload/csv
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upload_csv_200(client: AsyncClient) -> None:
    """정상 CSV → 200 + UploadValidationResult."""
    content = _csv_bytes(
        [
            "2024-01-15,yahoo,AAPL,10,182.50,USD,note",
            "2024-03-22,upbit,KRW-BTC,0.05,85000000,KRW,note",
        ]
    )
    resp = await client.post(
        "/upload/csv",
        files={"file": ("test.csv", content, "text/csv")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "upload_id" in body
    assert body["total_rows"] == 2
    assert body["valid_rows"] == 2
    assert body["error_rows"] == 0
    assert isinstance(body["preview"], list)
    assert len(body["preview"]) <= 5
    assert "schema_fingerprint" in body
    assert "created_at" in body


@pytest.mark.asyncio
async def test_upload_csv_with_errors(client: AsyncClient) -> None:
    """오류 포함 CSV → 200 + 오류 목록."""
    content = _csv_bytes(
        [
            "2024-01-15,yahoo,AAPL,10,182.50,USD,정상",
            "bad-date,yahoo,AAPL,-5,150.00,BTC,다중오류",
        ]
    )
    resp = await client.post(
        "/upload/csv",
        files={"file": ("test.csv", content, "text/csv")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["error_rows"] > 0
    assert len(body["errors"]) > 0


@pytest.mark.asyncio
async def test_upload_csv_returns_upload_id(client: AsyncClient) -> None:
    """upload_id 는 UUID 형식."""
    import uuid

    content = _csv_bytes(["2024-01-15,yahoo,AAPL,10,150.00,USD,note"])
    resp = await client.post(
        "/upload/csv",
        files={"file": ("test.csv", content, "text/csv")},
    )
    assert resp.status_code == 200
    upload_id = resp.json()["upload_id"]
    parsed = uuid.UUID(upload_id)
    assert str(parsed) == upload_id


@pytest.mark.asyncio
async def test_upload_csv_returns_hash_candidates_and_normalized_preview(
    client: AsyncClient,
) -> None:
    """Upload review exposes the contract needed for PB mapping confirmation."""
    content = b"ticker,shares,average cost,currency\n005930,10,72000,KRW\n"
    resp = await client.post(
        "/upload/csv",
        files={"file": ("mapping-review.csv", content, "text/csv")},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["file_content_hash"]
    assert len(body["file_content_hash"]) == 64
    assert body["normalized_preview"][0]["source_row"] == 2
    quantity_candidates = next(
        item for item in body["mapping_candidates"] if item["standard_field"] == "quantity"
    )
    assert quantity_candidates["candidates"][0]["type"] == "column"
    assert quantity_candidates["candidates"][0]["column"] == "shares"
    market_candidates = next(
        item for item in body["mapping_candidates"] if item["standard_field"] == "market"
    )
    assert any(
        candidate["type"] == "derived" and candidate["method"] == "symbol_pattern"
        for candidate in market_candidates["candidates"]
    )


@pytest.mark.asyncio
async def test_upload_csv_preview_max_5(client: AsyncClient) -> None:
    """preview 최대 5행."""
    rows = [f"2024-01-{i:02d},yahoo,AAPL,{i},150.00,USD,note" for i in range(1, 11)]
    content = _csv_bytes(rows)
    resp = await client.post(
        "/upload/csv",
        files={"file": ("test.csv", content, "text/csv")},
    )
    assert resp.status_code == 200
    assert len(resp.json()["preview"]) <= 5


@pytest.mark.asyncio
async def test_upload_import_persists_normalized_holdings(
    upload_import_client: AsyncClient,
) -> None:
    """자동 매핑 가능한 CSV 는 holdings DB에 저장한다."""
    content = (
        "고객ID,계좌번호,종목코드,종목명,보유수량,평균단가,통화\n"
        "client-777,123-45,005930,삼성전자,10,72000,KRW\n"
    ).encode()
    upload_resp = await upload_import_client.post(
        "/upload/csv",
        files={"file": ("korean-broker.csv", content, "text/csv")},
    )
    assert upload_resp.status_code == 200

    import_resp = await upload_import_client.post(
        "/upload/import",
        json={"upload_id": upload_resp.json()["upload_id"], "client_id": "client-777"},
    )

    assert import_resp.status_code == 200
    body = import_resp.json()
    assert body["status"] == "imported"
    assert body["imported_count"] == 1
    assert body["holdings"][0]["client_id"] == "client-777"
    assert body["holdings"][0]["market"] == "naver_kr"
    assert body["holdings"][0]["code"] == "005930"

    holdings_resp = await upload_import_client.get("/portfolio/holdings?client_id=client-777")
    assert holdings_resp.status_code == 200
    holdings = holdings_resp.json()
    assert len(holdings) == 1
    assert holdings[0]["code"] == "005930"
    assert holdings[0]["quantity"] == "10.00000000"


@pytest.mark.asyncio
async def test_upload_import_uses_selected_client_over_source_client_id(
    upload_import_client: AsyncClient,
) -> None:
    content = (
        b"date,client_id,market,code,quantity,avg_cost,currency\n"
        b"2026-05-01,client-777,naver_kr,005930,10,72000,KRW\n"
    )
    upload_resp = await upload_import_client.post(
        "/upload/csv",
        files={"file": ("selected-client.csv", content, "text/csv")},
    )
    assert upload_resp.status_code == 200

    import_resp = await upload_import_client.post(
        "/upload/import",
        json={"upload_id": upload_resp.json()["upload_id"], "client_id": "client-002"},
    )

    assert import_resp.status_code == 200
    body = import_resp.json()
    assert body["status"] == "imported"
    assert body["client_id"] == "client-002"
    assert body["holdings"][0]["client_id"] == "client-002"
    assert body["normalized_holdings"][0]["client_id"] == "client-777"
    assert any(
        "source client_id 'client-777' imported into selected client 'client-002'" in warning
        for warning in body["normalization_warnings"]
    )

    selected_holdings_resp = await upload_import_client.get(
        "/portfolio/holdings?client_id=client-002"
    )
    assert selected_holdings_resp.status_code == 200
    assert len(selected_holdings_resp.json()) == 1

    source_holdings_resp = await upload_import_client.get(
        "/portfolio/holdings?client_id=client-777"
    )
    assert source_holdings_resp.status_code == 200
    assert source_holdings_resp.json() == []


@pytest.mark.asyncio
async def test_upload_import_accepts_confirmed_mapping_for_arbitrary_column_names(
    upload_import_client: AsyncClient,
) -> None:
    content = (
        b"Security ID,Units Held,Book Price,Settlement CCY,Venue\n005930,10,72000,KRW,naver_kr\n"
    )
    upload_resp = await upload_import_client.post(
        "/upload/csv",
        files={"file": ("arbitrary-columns.csv", content, "text/csv")},
    )
    assert upload_resp.status_code == 200

    import_resp = await upload_import_client.post(
        "/upload/import",
        json={
            "upload_id": upload_resp.json()["upload_id"],
            "client_id": "client-880",
            "confirmed_mapping": {
                "symbol": {"type": "column", "column": "Security ID"},
                "quantity": {"type": "column", "column": "Units Held"},
                "avg_cost": {"type": "column", "column": "Book Price"},
                "currency": {"type": "column", "column": "Settlement CCY"},
                "market": {"type": "column", "column": "Venue"},
            },
        },
    )

    assert import_resp.status_code == 200
    body = import_resp.json()
    assert body["status"] == "imported"
    assert body["imported_count"] == 1
    assert body["holdings"][0]["client_id"] == "client-880"
    assert body["holdings"][0]["market"] == "naver_kr"
    assert body["holdings"][0]["code"] == "005930"
    assert body["import_batch_key"]


@pytest.mark.asyncio
async def test_upload_import_blocks_invalid_rows_after_confirmed_mapping(
    upload_import_client: AsyncClient,
) -> None:
    content = (
        b"Security ID,Units Held,Book Price,Settlement CCY,Venue\n005930,-10,72000,KRW,naver_kr\n"
    )
    upload_resp = await upload_import_client.post(
        "/upload/csv",
        files={"file": ("invalid-arbitrary-columns.csv", content, "text/csv")},
    )
    assert upload_resp.status_code == 200

    import_resp = await upload_import_client.post(
        "/upload/import",
        json={
            "upload_id": upload_resp.json()["upload_id"],
            "client_id": "client-881",
            "confirmed_mapping": {
                "symbol": {"type": "column", "column": "Security ID"},
                "quantity": {"type": "column", "column": "Units Held"},
                "avg_cost": {"type": "column", "column": "Book Price"},
                "currency": {"type": "column", "column": "Settlement CCY"},
                "market": {"type": "column", "column": "Venue"},
            },
        },
    )

    assert import_resp.status_code == 200
    body = import_resp.json()
    assert body["status"] == "needs_confirmation"
    assert body["imported_count"] == 0
    assert body["holdings"] == []
    assert body["blocking_errors"][0]["row"] == 2
    assert body["blocking_errors"][0]["code"] == "invalid_quantity"


@pytest.mark.asyncio
async def test_upload_import_replaces_matching_import_batch(
    upload_import_client: AsyncClient,
) -> None:
    content = b"code,quantity,avg_cost\n005930,10,72000\n"
    upload_resp = await upload_import_client.post(
        "/upload/csv",
        files={"file": ("same-source.csv", content, "text/csv")},
    )
    assert upload_resp.status_code == 200
    request_body = {
        "upload_id": upload_resp.json()["upload_id"],
        "client_id": "client-882",
        "confirmed_mapping": {
            "symbol": {"type": "column", "column": "code"},
            "quantity": {"type": "column", "column": "quantity"},
            "avg_cost": {"type": "column", "column": "avg_cost"},
            "currency": {"type": "derived", "method": "symbol_pattern"},
            "market": {"type": "derived", "method": "symbol_pattern"},
        },
    }

    first_import = await upload_import_client.post("/upload/import", json=request_body)
    second_import = await upload_import_client.post("/upload/import", json=request_body)

    assert first_import.status_code == 200
    assert second_import.status_code == 200
    assert first_import.json()["status"] == "imported"
    assert second_import.json()["status"] == "imported"
    assert first_import.json()["import_batch_key"] == second_import.json()["import_batch_key"]

    holdings_resp = await upload_import_client.get("/portfolio/holdings?client_id=client-882")
    assert holdings_resp.status_code == 200
    holdings = holdings_resp.json()
    assert len(holdings) == 1
    assert holdings[0]["code"] == "005930"


@pytest.mark.asyncio
async def test_upload_import_batch_replacement_preserves_manual_holdings(
    upload_import_client: AsyncClient,
) -> None:
    manual_resp = await upload_import_client.post(
        "/portfolio/holdings",
        json={
            "client_id": "client-883",
            "market": "upbit",
            "code": "KRW-BTC",
            "quantity": "0.1",
            "avg_cost": "80000000",
            "currency": "KRW",
        },
    )
    assert manual_resp.status_code == 201

    content = b"code,quantity,avg_cost\n005930,10,72000\n"
    upload_resp = await upload_import_client.post(
        "/upload/csv",
        files={"file": ("same-source-with-manual.csv", content, "text/csv")},
    )
    request_body = {
        "upload_id": upload_resp.json()["upload_id"],
        "client_id": "client-883",
        "confirmed_mapping": {
            "symbol": {"type": "column", "column": "code"},
            "quantity": {"type": "column", "column": "quantity"},
            "avg_cost": {"type": "column", "column": "avg_cost"},
            "currency": {"type": "derived", "method": "symbol_pattern"},
            "market": {"type": "derived", "method": "symbol_pattern"},
        },
    }

    await upload_import_client.post("/upload/import", json=request_body)
    await upload_import_client.post("/upload/import", json=request_body)

    holdings_resp = await upload_import_client.get("/portfolio/holdings?client_id=client-883")
    assert holdings_resp.status_code == 200
    holdings = holdings_resp.json()
    assert sorted(holding["code"] for holding in holdings) == ["005930", "KRW-BTC"]


@pytest.mark.asyncio
async def test_upload_import_needs_confirmation_does_not_persist(
    upload_import_client: AsyncClient,
) -> None:
    """중복 후보처럼 PB 확인이 필요한 CSV 는 저장하지 않는다."""
    content = b"symbol,ticker,quantity,avg_cost,currency\nAAPL,MSFT,3,180,USD\n"
    upload_resp = await upload_import_client.post(
        "/upload/csv",
        files={"file": ("ambiguous.csv", content, "text/csv")},
    )
    assert upload_resp.status_code == 200

    import_resp = await upload_import_client.post(
        "/upload/import",
        json={"upload_id": upload_resp.json()["upload_id"], "client_id": "client-777"},
    )

    assert import_resp.status_code == 200
    body = import_resp.json()
    assert body["status"] == "needs_confirmation"
    assert body["imported_count"] == 0
    assert body["holdings"] == []

    holdings_resp = await upload_import_client.get("/portfolio/holdings?client_id=client-777")
    assert holdings_resp.status_code == 200
    assert holdings_resp.json() == []


@pytest.mark.asyncio
async def test_upload_import_invalid_upload_id_404(client: AsyncClient) -> None:
    """없는 upload_id 는 일반 JSON API 오류로 반환한다."""
    resp = await client.post(
        "/upload/import",
        json={"upload_id": "00000000-0000-0000-0000-000000000000"},
    )

    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "UPLOAD_NOT_FOUND"


# ──────────────────────────────────────────────────────────────────────────────
# POST /upload/analyze (SSE)
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upload_analyze_sse_events(client: AsyncClient) -> None:
    """SSE 스트림 → 최소 5개 이벤트 수신."""
    # 먼저 파일 업로드
    content = _csv_bytes(["2024-01-15,yahoo,AAPL,10,150.00,USD,note"])
    upload_resp = await client.post(
        "/upload/csv",
        files={"file": ("test.csv", content, "text/csv")},
    )
    assert upload_resp.status_code == 200
    upload_id = upload_resp.json()["upload_id"]

    # SSE 분석 요청
    analyze_resp = await client.post(
        "/upload/analyze",
        json={
            "upload_id": upload_id,
            "config": {
                "analyzer": "portfolio",
                "period_days": 365,
                "base_currency": "KRW",
                "include_fx": False,
            },
        },
    )
    assert analyze_resp.status_code == 200
    assert "text/event-stream" in analyze_resp.headers.get("content-type", "")

    # SSE 이벤트 파싱
    events = []
    text = analyze_resp.text
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("data:") and "[DONE]" not in line:
            payload = json.loads(line[5:].strip())
            events.append(payload)

    # 5단계 × 2(running + pass) = 10 이벤트 기대, 최소 5개 이상
    assert len(events) >= 5


@pytest.mark.asyncio
async def test_upload_analyze_event_schema(client: AsyncClient) -> None:
    """각 SSE 이벤트가 AnalyzeProgressEvent 스키마 준수."""
    content = _csv_bytes(["2024-01-15,yahoo,AAPL,10,150.00,USD,note"])
    upload_resp = await client.post(
        "/upload/csv",
        files={"file": ("test.csv", content, "text/csv")},
    )
    upload_id = upload_resp.json()["upload_id"]

    analyze_resp = await client.post(
        "/upload/analyze",
        json={
            "upload_id": upload_id,
            "config": {
                "analyzer": "portfolio",
                "period_days": 365,
                "base_currency": "KRW",
                "include_fx": False,
            },
        },
    )
    text = analyze_resp.text
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("data:") and "[DONE]" not in line:
            payload = json.loads(line[5:].strip())
            assert "step" in payload
            assert "status" in payload
            assert "message" in payload
            assert "elapsed_ms" in payload
            assert payload["status"] in ("running", "pass", "fail", "pending")


@pytest.mark.asyncio
async def test_upload_analyze_invalid_upload_id(client: AsyncClient) -> None:
    """존재하지 않는 upload_id → 첫 이벤트 fail."""
    analyze_resp = await client.post(
        "/upload/analyze",
        json={
            "upload_id": "00000000-0000-0000-0000-000000000000",
            "config": {
                "analyzer": "portfolio",
                "period_days": 365,
                "base_currency": "KRW",
                "include_fx": False,
            },
        },
    )
    assert analyze_resp.status_code == 200  # SSE 는 항상 200
    text = analyze_resp.text
    events = []
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("data:") and "[DONE]" not in line:
            payload = json.loads(line[5:].strip())
            events.append(payload)
    # 첫 이벤트 fail
    assert len(events) >= 1
    assert events[0]["status"] == "fail"


# ──────────────────────────────────────────────────────────────────────────────
# GET /upload/template
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upload_template_200(client: AsyncClient) -> None:
    """GET /upload/template → 200 + CSV."""
    resp = await client.get("/upload/template")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_upload_template_has_required_headers(client: AsyncClient) -> None:
    """템플릿 CSV 에 필수 컬럼 존재."""
    resp = await client.get("/upload/template")
    assert resp.status_code == 200
    first_line = resp.text.strip().split("\n")[0].lower()
    for col in ["date", "market", "code", "quantity", "avg_cost", "currency"]:
        assert col in first_line


@pytest.mark.asyncio
async def test_upload_template_has_sample_rows(client: AsyncClient) -> None:
    """템플릿 CSV 에 샘플 데이터 존재 (헤더 제외 최소 1행)."""
    resp = await client.get("/upload/template")
    assert resp.status_code == 200
    lines = [line for line in resp.text.strip().split("\n") if line.strip()]
    assert len(lines) >= 2  # 헤더 + 최소 1행
