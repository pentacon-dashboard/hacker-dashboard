from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """
    구조화 예외 베이스 — 상위로 전파하지 않고 HTTP 응답으로 변환.

    사용법:
      raise AppError("메시지")              # 기본 500
      raise AppError("메시지", code="...", status_code=400)
      raise AppError(status_code=413, code="FILE_TOO_LARGE", detail="...")
    """

    _default_status_code: int = 500
    _default_code: str = "INTERNAL_ERROR"

    def __init__(
        self,
        message: str = "",
        *,
        code: str | None = None,
        status_code: int | None = None,
        detail: str | None = None,
    ) -> None:
        # detail 이 있으면 message 로 사용 (편의 인자)
        resolved_message = detail if detail is not None else message
        super().__init__(resolved_message)
        self.message = resolved_message
        self.code = code if code is not None else self._default_code
        self.status_code = status_code if status_code is not None else self._default_status_code


class ValidationError(AppError):
    _default_status_code = 422
    _default_code = "VALIDATION_ERROR"


class AnalysisError(AppError):
    _default_status_code = 500
    _default_code = "ANALYSIS_ERROR"


class GateRejectionError(AppError):
    """3단 품질 게이트 중 하나가 거부했을 때"""

    _default_status_code = 422
    _default_code = "GATE_REJECTION"

    def __init__(self, gate: str, reason: str) -> None:
        super().__init__(f"Gate '{gate}' rejected: {reason}")
        self.gate = gate
        self.reason = reason


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )
