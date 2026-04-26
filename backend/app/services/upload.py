"""업로드 파이프라인 서비스 — sprint-08 Phase B-5.

parse_csv: multipart 파일 → DataFrame + 검증 오류 목록
run_analyze_stream: upload_id + config → SSE 이벤트 스트림 (AsyncIterator)

업로드 캐시: 서버 메모리 _upload_cache (TTL 30분 asyncio cleanup)
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import logging
import time
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from app.schemas.upload import (
    AnalyzeProgressEvent,
    UploadErrorDetail,
    UploadValidationResult,
)

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────────────
# 업로드 캐시 (서버 메모리, TTL 30분)
# ────────────────────────────────────────────────────────────────────────────

_TTL_SECONDS = 30 * 60  # 30분

# {upload_id: {"df": DataFrame, "expires_at": float}}
_upload_cache: dict[str, dict[str, Any]] = {}

_REQUIRED_COLUMNS = {"date", "market", "code", "quantity", "avg_cost", "currency"}
_VALID_CURRENCIES = {"KRW", "USD", "USDT", "EUR", "JPY"}


async def _cleanup_expired() -> None:
    """만료된 캐시 항목을 제거하는 백그라운드 태스크."""
    while True:
        await asyncio.sleep(60)  # 1분마다 스캔
        now = time.time()
        expired = [k for k, v in _upload_cache.items() if v["expires_at"] < now]
        for k in expired:
            _upload_cache.pop(k, None)
        if expired:
            logger.debug("upload_cache: %d 항목 만료 제거", len(expired))


def start_cache_cleanup() -> None:
    """FastAPI lifespan 에서 호출 — 백그라운드 정리 태스크 시작."""
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(_cleanup_expired())
    except RuntimeError:
        pass  # 이벤트 루프가 없으면 무시 (테스트 환경)


def get_cached_df(upload_id: str) -> Any | None:
    """캐시에서 DataFrame 조회. 만료 또는 미존재 시 None."""
    entry = _upload_cache.get(upload_id)
    if entry is None:
        return None
    if entry["expires_at"] < time.time():
        _upload_cache.pop(upload_id, None)
        return None
    return entry["df"]


# ────────────────────────────────────────────────────────────────────────────
# parse_csv
# ────────────────────────────────────────────────────────────────────────────


def parse_csv(
    content: bytes,
    filename: str = "upload.csv",
) -> tuple[Any, list[UploadErrorDetail]]:
    """CSV bytes → (DataFrame, errors).

    검증 항목:
    1. 필수 컬럼 존재 (lowercase 정규화)
    2. date — ISO 8601 형식
    3. quantity > 0
    4. currency enum (KRW/USD/USDT/EUR/JPY)
    """
    try:
        import pandas as pd
    except ImportError as exc:  # pandas 미설치 환경 대비
        raise RuntimeError("pandas 가 필요합니다: uv add pandas") from exc

    errors: list[UploadErrorDetail] = []

    # BOM 제거 후 파싱
    raw = content.lstrip(b"\xef\xbb\xbf")
    if not raw.strip():
        errors.append(
            UploadErrorDetail(
                row=0, column=None, code="empty_file", message="파일이 비어 있습니다."
            )
        )
        import pandas as pd

        return pd.DataFrame(), errors

    try:
        df = pd.read_csv(io.BytesIO(raw), dtype=str)
    except Exception as exc:
        errors.append(
            UploadErrorDetail(
                row=0, column=None, code="parse_error", message=f"CSV 파싱 실패: {exc}"
            )
        )
        import pandas as pd

        return pd.DataFrame(), errors

    if df.empty:
        # 헤더만 있는 파일
        return df, errors

    # 컬럼명 lowercase 정규화
    df.columns = [c.strip().lower() for c in df.columns]

    # 필수 컬럼 확인
    missing_cols = _REQUIRED_COLUMNS - set(df.columns)
    if missing_cols:
        errors.append(
            UploadErrorDetail(
                row=0,
                column=None,
                code="missing_columns",
                message=f"필수 컬럼 누락: {', '.join(sorted(missing_cols))}",
            )
        )
        return df, errors

    # 행별 검증
    for idx, row in df.iterrows():
        row_num = int(idx) + 2  # 헤더 = 1행, 데이터 시작 = 2행

        # date 형식
        date_val = str(row.get("date", "")).strip()
        if date_val:
            try:
                from datetime import date as _date

                _date.fromisoformat(date_val)
            except ValueError:
                errors.append(
                    UploadErrorDetail(
                        row=row_num,
                        column="date",
                        code="invalid_date",
                        message=f"날짜 형식 오류: '{date_val}' (ISO 8601 YYYY-MM-DD 필요)",
                    )
                )

        # quantity > 0
        qty_val = str(row.get("quantity", "")).strip()
        if qty_val:
            try:
                qty = float(qty_val)
                if qty <= 0:
                    errors.append(
                        UploadErrorDetail(
                            row=row_num,
                            column="quantity",
                            code="negative_quantity",
                            message=f"수량은 0보다 커야 합니다: {qty_val}",
                        )
                    )
            except ValueError:
                errors.append(
                    UploadErrorDetail(
                        row=row_num,
                        column="quantity",
                        code="invalid_quantity",
                        message=f"수량 형식 오류: '{qty_val}'",
                    )
                )

        # currency enum
        currency_val = str(row.get("currency", "")).strip().upper()
        if currency_val and currency_val not in _VALID_CURRENCIES:
            errors.append(
                UploadErrorDetail(
                    row=row_num,
                    column="currency",
                    code="unknown_currency",
                    message=f"지원하지 않는 통화: '{currency_val}' (KRW/USD/USDT/EUR/JPY)",
                )
            )

    return df, errors


def _make_schema_fingerprint(df: Any) -> str:
    """CSV 헤더를 SHA-256 해시로 변환 (8자리 hex)."""
    cols_str = ",".join(sorted(str(c) for c in df.columns))
    return hashlib.sha256(cols_str.encode()).hexdigest()[:8]


def build_validation_result(
    df: Any,
    errors: list[UploadErrorDetail],
    filename: str = "upload.csv",
) -> UploadValidationResult:
    """DataFrame + 오류 목록으로 UploadValidationResult 생성 및 캐시 저장."""
    upload_id = str(uuid.uuid4())
    total_rows = len(df) if not df.empty else 0
    error_rows = len({e.row for e in errors if e.row > 0})
    valid_rows = max(0, total_rows - error_rows)

    # preview: 상위 5행
    preview: list[dict[str, Any]] = []
    if not df.empty:
        preview = df.head(5).fillna("").to_dict(orient="records")

    fingerprint = _make_schema_fingerprint(df) if not df.empty else "00000000"

    result = UploadValidationResult(
        upload_id=upload_id,
        total_rows=total_rows,
        valid_rows=valid_rows,
        error_rows=error_rows,
        warning_rows=0,
        errors=errors,
        preview=preview,
        schema_fingerprint=fingerprint,
        created_at=datetime.now(UTC).isoformat(),
    )

    # 캐시 저장 (TTL 30분)
    _upload_cache[upload_id] = {
        "df": df,
        "expires_at": time.time() + _TTL_SECONDS,
    }

    return result


# ────────────────────────────────────────────────────────────────────────────
# run_analyze_stream (SSE 이벤트 생성)
# ────────────────────────────────────────────────────────────────────────────

_STEP_SEQUENCE = [
    ("router", "라우터 분석 중..."),
    ("schema_gate", "스키마 검증 중..."),
    ("domain_gate", "도메인 sanity check 중..."),
    ("critique_gate", "근거 인용 검증 중..."),
    ("complete", "분석 완료"),
]


async def run_analyze_stream(
    upload_id: str,
    config: Any,
) -> AsyncIterator[AnalyzeProgressEvent]:
    """SSE 이벤트 생성기 — 5단계 분석 진행 상황 스트림.

    실제 3단 게이트(gates/)가 구현되면 연결. 현재는 시연용 stub.
    각 단계 200~500ms 간격.
    """
    start_ms = int(time.time() * 1000)

    df = get_cached_df(upload_id)
    if df is None:
        yield AnalyzeProgressEvent(
            step="router",
            status="fail",
            message=f"upload_id '{upload_id}' 를 찾을 수 없습니다. 먼저 /upload/csv 를 호출하세요.",
            elapsed_ms=0,
        )
        return

    for step_name, step_msg in _STEP_SEQUENCE:
        # "running" 이벤트
        elapsed = int(time.time() * 1000) - start_ms
        yield AnalyzeProgressEvent(
            step=step_name,
            status="running",
            message=step_msg,
            elapsed_ms=elapsed,
        )

        # 시연용 딜레이 (200~500ms)
        await asyncio.sleep(0.3)

        # 실제 게이트 로직 (stub: 항상 pass)
        gate_status: str = "pass"
        done_msg: str = ""

        if step_name == "router":
            analyzer = config.analyzer if hasattr(config, "analyzer") else "portfolio"
            done_msg = f"분석기 선택: {analyzer}"
        elif step_name == "schema_gate":
            done_msg = "스키마 검증 통과"
        elif step_name == "domain_gate":
            done_msg = "도메인 sanity check 통과"
        elif step_name == "critique_gate":
            done_msg = "근거 인용 검증 통과 (stub 모드)"
        elif step_name == "complete":
            done_msg = f"분석 완료 ({df.shape[0]}행 처리)"

        elapsed = int(time.time() * 1000) - start_ms
        yield AnalyzeProgressEvent(
            step=step_name,
            status=gate_status,
            message=done_msg,
            elapsed_ms=elapsed,
        )
