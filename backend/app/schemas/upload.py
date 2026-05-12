"""업로드 파이프라인 Pydantic 스키마 — sprint-08 Phase B-5."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.portfolio import CLIENT_ID_PATTERN, HoldingResponse

CostBasisStatus = Literal["provided", "missing", "derived", "needs_review"]
UploadImportStatus = Literal[
    "imported", "partial_imported", "needs_confirmation", "insufficient_data"
]
UploadRowClassification = Literal["imported", "recoverable", "quarantined", "garbage"]


class UploadErrorDetail(BaseModel):
    row: int
    column: str | None = None
    code: str  # "invalid_date" | "negative_quantity" | "unknown_currency"
    message: str


class CsvFieldMapping(BaseModel):
    standard_field: str
    source_column: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    needs_review: bool = False
    mapping_reason: str


class CsvMappingCandidate(BaseModel):
    type: Literal["column", "derived"]
    column: str | None = None
    method: Literal["symbol_pattern"] | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    needs_review: bool = False
    reason: str


class CsvMappingCandidateGroup(BaseModel):
    standard_field: str
    candidates: list[CsvMappingCandidate] = Field(default_factory=list)


class ConfirmedCsvMapping(BaseModel):
    type: Literal["column", "derived"]
    column: str | None = None
    method: Literal["symbol_pattern"] | None = None


class NormalizedCsvHolding(BaseModel):
    client_id: str | None = None
    client_name: str | None = None
    account: str | None = None
    market: str | None = None
    code: str
    name: str | None = None
    quantity: str
    avg_cost: str | None = None
    cost_basis_status: CostBasisStatus | None = None
    currency: str | None = None
    source_row: int
    source_columns: dict[str, str]

    @model_validator(mode="after")
    def default_cost_basis_status(self) -> NormalizedCsvHolding:
        if self.cost_basis_status is None:
            self.cost_basis_status = "missing" if self.avg_cost is None else "provided"
        return self


class UploadImportRow(BaseModel):
    classification: UploadRowClassification
    source_row: int
    source_columns: dict[str, Any] = Field(default_factory=dict)
    reason_code: str
    message: str
    normalized_holding: NormalizedCsvHolding | None = None
    errors: list[UploadErrorDetail] = Field(default_factory=list)


class UploadValidationResult(BaseModel):
    upload_id: str  # uuid4
    file_content_hash: str = ""
    total_rows: int
    valid_rows: int
    error_rows: int
    warning_rows: int
    errors: list[UploadErrorDetail]
    preview: list[dict[str, Any]]  # 상위 5행 dict
    schema_fingerprint: str  # CSV 헤더 해시
    created_at: str
    import_status: UploadImportStatus = "insufficient_data"
    field_mappings: list[CsvFieldMapping] = Field(default_factory=list)
    mapping_candidates: list[CsvMappingCandidateGroup] = Field(default_factory=list)
    unmapped_columns: list[str] = Field(default_factory=list)
    normalized_preview: list[dict[str, Any]] = Field(default_factory=list)
    normalized_holdings: list[NormalizedCsvHolding] = Field(default_factory=list)
    normalization_warnings: list[str] = Field(default_factory=list)
    imported_rows: list[UploadImportRow] = Field(default_factory=list)
    recoverable_rows: list[UploadImportRow] = Field(default_factory=list)
    quarantined_rows: list[UploadImportRow] = Field(default_factory=list)
    garbage_rows: list[UploadImportRow] = Field(default_factory=list)


class UploadImportRequest(BaseModel):
    upload_id: str
    client_id: str = Field(
        "client-001",
        min_length=1,
        max_length=64,
        pattern=CLIENT_ID_PATTERN,
        description="CSV row에 고객 ID가 없을 때 사용할 PB 선택 고객 ID",
    )

    confirmed_mapping: dict[str, ConfirmedCsvMapping] | None = None


class UploadImportResponse(BaseModel):
    status: UploadImportStatus
    client_id: str
    imported_count: int
    import_batch_key: str | None = None
    holdings: list[HoldingResponse] = Field(default_factory=list)
    field_mappings: list[CsvFieldMapping] = Field(default_factory=list)
    mapping_candidates: list[CsvMappingCandidateGroup] = Field(default_factory=list)
    unmapped_columns: list[str] = Field(default_factory=list)
    normalized_preview: list[dict[str, Any]] = Field(default_factory=list)
    normalized_holdings: list[NormalizedCsvHolding] = Field(default_factory=list)
    normalization_warnings: list[str] = Field(default_factory=list)
    blocking_errors: list[UploadErrorDetail] = Field(default_factory=list)
    imported_rows: list[UploadImportRow] = Field(default_factory=list)
    recoverable_rows: list[UploadImportRow] = Field(default_factory=list)
    quarantined_rows: list[UploadImportRow] = Field(default_factory=list)
    garbage_rows: list[UploadImportRow] = Field(default_factory=list)


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
