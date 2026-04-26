"""업로드 API 통합 테스트 — sprint-08 Phase B-5."""

from __future__ import annotations

import json

import pytest
from httpx import ASGITransport, AsyncClient

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
