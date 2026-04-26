"""업로드 파이프라인 API — sprint-08 Phase B-5.

엔드포인트:
  POST /upload/csv       → UploadValidationResult
  POST /upload/analyze   → SSE 스트림 of AnalyzeProgressEvent
  GET  /upload/template  → sample_portfolio.csv FileResponse
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from app.schemas.upload import (
    AnalyzeStartRequest,
    UploadValidationResult,
)
from app.services.upload import (
    build_validation_result,
    parse_csv,
    run_analyze_stream,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["upload"])

_STATIC_DIR = Path(__file__).parent.parent / "static"
_SAMPLE_CSV = _STATIC_DIR / "sample_portfolio.csv"

_MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


# ──────────────────────────────────────────────────────────────────────────────
# POST /upload/csv
# ──────────────────────────────────────────────────────────────────────────────


@router.post(
    "/csv",
    response_model=UploadValidationResult,
    summary="CSV 파일 업로드 및 검증",
    description=(
        "multipart/form-data 로 CSV 파일을 업로드한다. "
        "필수 컬럼 (date, market, code, quantity, avg_cost, currency) 검증 후 "
        "UploadValidationResult 반환. upload_id 는 30분간 서버 메모리에 캐시된다."
    ),
)
async def upload_csv(
    file: UploadFile,
) -> UploadValidationResult:
    """CSV 업로드 + 검증."""
    if file.content_type and "csv" not in file.content_type and "text" not in file.content_type:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_CONTENT_TYPE", "detail": "CSV 파일만 지원합니다."},
        )

    content = await file.read()
    if len(content) > _MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail={"code": "FILE_TOO_LARGE", "detail": "파일 크기는 50MB 이하여야 합니다."},
        )

    filename = file.filename or "upload.csv"
    df, errors = parse_csv(content, filename=filename)
    result = build_validation_result(df, errors, filename=filename)

    logger.info(
        "upload_csv: upload_id=%s total=%d valid=%d errors=%d",
        result.upload_id,
        result.total_rows,
        result.valid_rows,
        result.error_rows,
    )
    return result


# ──────────────────────────────────────────────────────────────────────────────
# POST /upload/analyze  (SSE)
# ──────────────────────────────────────────────────────────────────────────────


@router.post(
    "/analyze",
    summary="업로드 데이터 분석 (SSE 스트림)",
    description=(
        "upload_id 와 분석 설정을 받아 3단 게이트 분석 진행 이벤트를 SSE 로 스트리밍한다. "
        "media_type: text/event-stream. 각 이벤트는 data: {JSON} 형식."
    ),
    responses={
        200: {"content": {"text/event-stream": {}}},
        404: {"description": "upload_id 미존재 또는 만료"},
    },
)
async def analyze_upload(
    body: AnalyzeStartRequest,
) -> StreamingResponse:
    """업로드 분석 SSE 스트림."""

    async def _event_generator() -> AsyncGenerator[str, None]:
        async for event in run_analyze_stream(body.upload_id, body.config):
            payload = event.model_dump()
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        # SSE 종료 신호
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ──────────────────────────────────────────────────────────────────────────────
# GET /upload/template
# ──────────────────────────────────────────────────────────────────────────────


@router.get(
    "/template",
    summary="샘플 포트폴리오 CSV 다운로드",
    description="업로드 형식을 확인할 수 있는 샘플 CSV 파일을 다운로드한다.",
    response_class=FileResponse,
)
async def get_template() -> FileResponse:
    """샘플 포트폴리오 CSV 다운로드."""
    if not _SAMPLE_CSV.exists():
        raise HTTPException(
            status_code=404,
            detail={"code": "TEMPLATE_NOT_FOUND", "detail": "샘플 파일을 찾을 수 없습니다."},
        )
    return FileResponse(
        path=str(_SAMPLE_CSV),
        media_type="text/csv",
        filename="sample_portfolio.csv",
    )
