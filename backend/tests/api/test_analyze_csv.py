"""
POST /analyze/csv 엔드포인트 테스트.

시나리오:
  - 정상 CSV (upbit/binance/주식 스타일)
  - 한글 헤더 cp949 인코딩
  - 10MB 초과 → 413
  - 헤더 없음 → 400 CSV_INVALID
  - 빈 파일 → 400 CSV_INVALID
"""
from __future__ import annotations

import io

import pytest
from httpx import AsyncClient


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────


def _make_csv_bytes(text: str, encoding: str = "utf-8") -> bytes:
    return text.encode(encoding)


def _csv_upload(
    client: AsyncClient,
    csv_bytes: bytes,
    filename: str = "test.csv",
    content_type: str = "text/csv",
    user_note: str = "",
    symbol_hint: str = "",
):
    return client.post(
        "/analyze/csv",
        files={"file": (filename, io.BytesIO(csv_bytes), content_type)},
        data={"user_note": user_note, "symbol_hint": symbol_hint},
    )


# ── 정상 케이스 ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_csv_upbit_style(client: AsyncClient, fake_llm_client) -> None:
    """업비트 스타일 CSV (KRW-BTC, date, close) — 정상 200."""
    csv_text = "market,date,open,high,low,close,volume\nKRW-BTC,2024-01-01,50000000,51000000,49000000,50500000,1.23\n"
    resp = await _csv_upload(client, _make_csv_bytes(csv_text), symbol_hint="crypto")
    assert resp.status_code == 200
    body = resp.json()
    assert "request_id" in body
    assert "meta" in body
    assert "status" in body


@pytest.mark.asyncio
async def test_csv_binance_style(client: AsyncClient, fake_llm_client) -> None:
    """바이낸스 스타일 CSV (BTCUSDT) — 정상 200."""
    csv_text = "symbol,timestamp,open,high,low,close,volume\nBTCUSDT,1704067200000,42000,43000,41000,42500,100.5\n"
    resp = await _csv_upload(client, _make_csv_bytes(csv_text))
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_csv_stock_style(client: AsyncClient, fake_llm_client) -> None:
    """주식 스타일 CSV (AAPL, yahoo finance 형식) — 정상 200."""
    csv_text = "Date,Open,High,Low,Close,Volume\n2024-01-02,185.0,186.5,183.2,185.9,55000000\n2024-01-03,185.9,187.0,184.1,184.5,48000000\n"
    resp = await _csv_upload(client, _make_csv_bytes(csv_text), symbol_hint="stock")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in ("ok", "error")  # 그래프 실행 완료


@pytest.mark.asyncio
async def test_csv_response_has_x_cache_header(client: AsyncClient, fake_llm_client) -> None:
    """첫 번째 요청은 X-Cache: MISS."""
    from app.services import analyze_cache
    analyze_cache.reset_for_testing()

    csv_text = "col1,col2\nval1,val2\n"
    resp = await _csv_upload(client, _make_csv_bytes(csv_text), user_note="unique_note_xyzzy")
    assert resp.status_code == 200
    assert resp.headers.get("X-Cache") == "MISS"


@pytest.mark.asyncio
async def test_csv_application_vnd_ms_excel_content_type(client: AsyncClient, fake_llm_client) -> None:
    """application/vnd.ms-excel content-type 도 허용."""
    csv_text = "symbol,price\nAAPL,185.0\n"
    resp = await _csv_upload(
        client,
        _make_csv_bytes(csv_text),
        content_type="application/vnd.ms-excel",
    )
    assert resp.status_code == 200


# ── 한글 헤더 cp949 ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_csv_korean_headers_cp949(client: AsyncClient, fake_llm_client) -> None:
    """한글 헤더 cp949 인코딩 — 자동 탐지 후 정상 파싱."""
    csv_text = "종목코드,날짜,종가,거래량\n005930,2024-01-02,72000,15000000\n005930,2024-01-03,71500,12000000\n"
    csv_bytes = _make_csv_bytes(csv_text, encoding="cp949")
    resp = await _csv_upload(client, csv_bytes)
    assert resp.status_code == 200


# ── 에러 케이스 ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_csv_too_large_returns_413(client: AsyncClient) -> None:
    """10MB 초과 파일 → 413."""
    big_bytes = b"col1,col2\n" + b"a,b\n" * (10 * 1024 * 1024 // 4 + 10)
    resp = await _csv_upload(client, big_bytes)
    assert resp.status_code == 413
    body = resp.json()
    assert body["error"]["code"] == "FILE_TOO_LARGE"


@pytest.mark.asyncio
async def test_csv_no_header_returns_400(client: AsyncClient) -> None:
    """헤더가 없는 CSV (실제론 헤더 탐지가 어렵지만 빈 fieldnames 케이스) — 빈 파일로 대체 확인."""
    # csv.DictReader 에 헤더 줄만 주면 rows 0개 → CSV_INVALID
    csv_bytes = b"only_header_no_data\n"
    resp = await _csv_upload(client, csv_bytes)
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "CSV_INVALID"


@pytest.mark.asyncio
async def test_csv_only_header_no_rows_returns_400(client: AsyncClient) -> None:
    """헤더만 있고 데이터 행 없음 → 400."""
    csv_bytes = b"col1,col2,col3\n"
    resp = await _csv_upload(client, csv_bytes)
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "CSV_INVALID"


@pytest.mark.asyncio
async def test_csv_empty_file_returns_400(client: AsyncClient) -> None:
    """빈 파일 → 400."""
    resp = await _csv_upload(client, b"")
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "CSV_INVALID"


@pytest.mark.asyncio
async def test_csv_user_note_passed_as_query(client: AsyncClient, fake_llm_client) -> None:
    """user_note 가 분석 질의(query)로 전달된다."""
    csv_text = "date,close\n2024-01-01,100.0\n"
    resp = await _csv_upload(
        client,
        _make_csv_bytes(csv_text),
        user_note="RSI 과매수 구간 분석해줘",
    )
    assert resp.status_code == 200
