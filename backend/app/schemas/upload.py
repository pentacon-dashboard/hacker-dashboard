"""업로드 파이프라인 Pydantic 스키마 — sprint-08 Phase B-5."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class UploadErrorDetail(BaseModel):
    row: int
    column: str | None = None
    code: str               # "invalid_date" | "negative_quantity" | "unknown_currency"
    message: str


class UploadValidationResult(BaseModel):
    upload_id: str          # uuid4
    total_rows: int
    valid_rows: int
    error_rows: int
    warning_rows: int
    errors: list[UploadErrorDetail]
    preview: list[dict[str, Any]]   # 상위 5행 dict
    schema_fingerprint: str         # CSV 헤더 해시
    created_at: str


class UploadAnalyzerConfig(BaseModel):
    analyzer: Literal["portfolio", "crypto", "stock"]
    period_days: int = Field(default=365, ge=1, le=3650)  # 1~10년
    base_currency: Literal["KRW", "USD"] = "KRW"
    include_fx: bool = False


class AnalyzeStartRequest(BaseModel):
    upload_id: str
    config: UploadAnalyzerConfig


class AnalyzeProgressEvent(BaseModel):
    step: Literal["router", "schema_gate", "domain_gate", "critique_gate", "complete"]
    status: Literal["pending", "running", "pass", "fail"]
    message: str
    elapsed_ms: int
