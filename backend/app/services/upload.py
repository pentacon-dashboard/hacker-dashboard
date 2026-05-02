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
import re
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from app.schemas.upload import (
    AnalyzeProgressEvent,
    CsvFieldMapping,
    NormalizedCsvHolding,
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

_VALID_CURRENCIES = {"KRW", "USD", "USDT", "EUR", "JPY"}
_AUTO_MAP_THRESHOLD = 0.95

_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "symbol": (
        "symbol",
        "ticker",
        "code",
        "pair",
        "issue code",
        "종목코드",
        "종목 코드",
        "티커",
        "종목번호",
        "단축코드",
    ),
    "name": ("name", "asset name", "asset_name", "종목명", "상품명", "상품 이름", "종목"),
    "quantity": (
        "qty",
        "quantity",
        "shares",
        "units",
        "보유수량",
        "보유 수량",
        "수량",
        "잔고수량",
        "보유량",
    ),
    "avg_cost": (
        "avg_price",
        "avg_cost",
        "average_price",
        "average cost",
        "매입가",
        "평균단가",
        "평균 단가",
        "평균매입단가",
        "매수가",
        "취득단가",
    ),
    "price": ("price", "close", "trade_price", "current_price", "현재가", "평가가격", "평가단가"),
    "currency": ("currency", "ccy", "통화", "결제통화"),
    "market": ("market", "exchange", "broker", "거래소", "시장"),
    "account": ("account", "account_no", "account number", "계좌", "계좌번호", "계좌 번호"),
    "client_id": ("client_id", "customer_id", "고객id", "고객 id", "고객번호"),
    "broker": ("broker", "증권사", "브로커"),
    "date": ("date", "trade_date", "as_of_date", "기준일", "거래일", "일자"),
}

_REQUIRED_IMPORT_FIELDS = ("symbol", "quantity")
_FULL_IMPORT_FIELDS = ("symbol", "quantity", "avg_cost", "currency")


@dataclass(frozen=True)
class PortfolioSchemaDetection:
    field_mappings: list[CsvFieldMapping]
    mapped_columns: dict[str, str]
    review_fields: set[str] = field(default_factory=set)
    missing_required_fields: list[str] = field(default_factory=list)
    unmapped_columns: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CsvNormalizationResult:
    status: Literal["imported", "needs_confirmation", "insufficient_data"]
    holdings: list[NormalizedCsvHolding]
    warnings: list[str] = field(default_factory=list)


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


def _normalize_column_name(value: object) -> str:
    return str(value).strip().lower()


def _alias_key(value: object) -> str:
    text = _normalize_column_name(value)
    return re.sub(r"[\s_\-./()]+", "", text)


def _original_column(df: Any, column: str) -> str:
    original_columns = getattr(df, "attrs", {}).get("original_columns", {})
    if isinstance(original_columns, dict):
        return str(original_columns.get(column, column))
    return column


def _column_candidates(columns: list[str], standard_field: str) -> list[tuple[str, float, str]]:
    aliases = {_alias_key(a) for a in _FIELD_ALIASES[standard_field]}
    exact = standard_field
    candidates: list[tuple[str, float, str]] = []
    for column in columns:
        column_key = _alias_key(column)
        if column == exact:
            candidates.append((column, 1.0, f"standard field '{standard_field}' exact match"))
        elif column_key in aliases:
            candidates.append((column, 0.98, f"known alias for '{standard_field}'"))
    return candidates


def detect_portfolio_schema(df: Any) -> PortfolioSchemaDetection:
    """CSV columns 를 표준 portfolio holding 필드로 결정적으로 매핑한다."""
    columns = [str(c) for c in getattr(df, "columns", [])]
    mappings: list[CsvFieldMapping] = []
    mapped_columns: dict[str, str] = {}
    review_fields: set[str] = set()
    candidate_columns: set[str] = set()

    for standard_field in _FIELD_ALIASES:
        candidates = _column_candidates(columns, standard_field)
        candidate_columns.update(column for column, _confidence, _reason in candidates)

        if not candidates:
            if standard_field in _REQUIRED_IMPORT_FIELDS:
                mappings.append(
                    CsvFieldMapping(
                        standard_field=standard_field,
                        source_column=None,
                        confidence=0.0,
                        needs_review=True,
                        mapping_reason=f"no source column matched '{standard_field}'",
                    )
                )
            continue

        if len(candidates) > 1:
            first_column = candidates[0][0]
            review_fields.add(standard_field)
            mappings.append(
                CsvFieldMapping(
                    standard_field=standard_field,
                    source_column=_original_column(df, first_column),
                    confidence=0.8,
                    needs_review=True,
                    mapping_reason=(
                        f"multiple candidates for '{standard_field}': "
                        + ", ".join(_original_column(df, c[0]) for c in candidates)
                    ),
                )
            )
            continue

        column, confidence, reason = candidates[0]
        needs_review = confidence < _AUTO_MAP_THRESHOLD
        if needs_review:
            review_fields.add(standard_field)
        else:
            mapped_columns[standard_field] = column
        mappings.append(
            CsvFieldMapping(
                standard_field=standard_field,
                source_column=_original_column(df, column),
                confidence=confidence,
                needs_review=needs_review,
                mapping_reason=reason,
            )
        )

    missing_required = [
        field_name
        for field_name in _REQUIRED_IMPORT_FIELDS
        if field_name not in mapped_columns and field_name not in review_fields
    ]
    warnings: list[str] = []
    if "client_id" not in mapped_columns:
        warnings.append("client_id column not mapped; portfolio-level import only")
    if any(field_name not in mapped_columns for field_name in _FULL_IMPORT_FIELDS):
        warnings.append("some import fields are missing or need review")

    mapped_values = set(mapped_columns.values())
    unmapped = [
        _original_column(df, column)
        for column in columns
        if column not in mapped_values and column not in candidate_columns
    ]

    return PortfolioSchemaDetection(
        field_mappings=mappings,
        mapped_columns=mapped_columns,
        review_fields=review_fields,
        missing_required_fields=missing_required,
        unmapped_columns=unmapped,
        warnings=warnings,
    )


def _string_value(value: Any) -> str | None:
    if value is None:
        return None
    try:
        import pandas as pd

        if pd.isna(value):
            return None
    except Exception:  # noqa: BLE001
        pass
    text = str(value).strip()
    return text or None


def _parse_decimal(value: Any) -> Decimal | None:
    text = _string_value(value)
    if text is None:
        return None
    negative = text.startswith("(") and text.endswith(")")
    cleaned = (
        text.strip("()")
        .replace(",", "")
        .replace("₩", "")
        .replace("$", "")
        .replace("주", "")
        .replace("원", "")
        .strip()
    )
    if not cleaned:
        return None
    try:
        parsed = Decimal(cleaned)
    except InvalidOperation:
        return None
    return -parsed if negative else parsed


def _format_decimal(value: Decimal) -> str:
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def _normalize_market(value: str | None) -> str | None:
    if not value:
        return None
    key = value.strip().lower()
    aliases = {
        "upbit": "upbit",
        "업비트": "upbit",
        "binance": "binance",
        "바이낸스": "binance",
        "yahoo": "yahoo",
        "nasdaq": "yahoo",
        "nyse": "yahoo",
        "krx": "naver_kr",
        "kospi": "naver_kr",
        "kosdaq": "naver_kr",
        "naver_kr": "naver_kr",
        "한국거래소": "naver_kr",
    }
    return aliases.get(key, key)


def _infer_market(symbol: str) -> str | None:
    code = symbol.strip().upper()
    if code.startswith("KRW-"):
        return "upbit"
    if "/USDT" in code or code.endswith("-USDT") or code.endswith("USDT"):
        return "binance"
    if re.fullmatch(r"\d{6}(\.KS|\.KQ)?", code):
        return "naver_kr"
    if re.fullmatch(r"[A-Z]{1,5}", code):
        return "yahoo"
    return None


def _infer_currency(symbol: str, market: str | None) -> str | None:
    code = symbol.strip().upper()
    if code.startswith("KRW-") or market == "naver_kr":
        return "KRW"
    if "USDT" in code:
        return "USDT"
    if market == "yahoo":
        return "USD"
    return None


def normalize_holdings_from_csv(
    df: Any,
    schema: PortfolioSchemaDetection | None = None,
) -> CsvNormalizationResult:
    """감지된 schema mapping 으로 CSV rows 를 표준 holdings 로 변환한다."""
    schema = schema or detect_portfolio_schema(df)
    warnings = list(schema.warnings)

    if schema.review_fields & set(_REQUIRED_IMPORT_FIELDS):
        return CsvNormalizationResult(status="needs_confirmation", holdings=[], warnings=warnings)
    if schema.missing_required_fields:
        return CsvNormalizationResult(status="insufficient_data", holdings=[], warnings=warnings)

    symbol_col = schema.mapped_columns["symbol"]
    quantity_col = schema.mapped_columns["quantity"]
    avg_cost_col = schema.mapped_columns.get("avg_cost")
    currency_col = schema.mapped_columns.get("currency")
    market_col = schema.mapped_columns.get("market")
    name_col = schema.mapped_columns.get("name")
    account_col = schema.mapped_columns.get("account")
    client_col = schema.mapped_columns.get("client_id")

    holdings: list[NormalizedCsvHolding] = []
    needs_confirmation = bool(schema.review_fields)

    for idx, row in df.iterrows():
        source_row = int(idx) + 2
        code = _string_value(row.get(symbol_col))
        quantity = _parse_decimal(row.get(quantity_col))
        if code is None:
            warnings.append(f"row {source_row}: symbol missing")
            continue
        if quantity is None or quantity <= 0:
            warnings.append(f"row {source_row}: invalid quantity")
            continue

        market = _normalize_market(_string_value(row.get(market_col))) if market_col else None
        if market is None:
            market = _infer_market(code)
            if market is None:
                needs_confirmation = True
                warnings.append(f"row {source_row}: market could not be inferred")

        avg_cost: Decimal | None = None
        if avg_cost_col:
            avg_cost = _parse_decimal(row.get(avg_cost_col))
            if avg_cost is None or avg_cost <= 0:
                needs_confirmation = True
                warnings.append(f"row {source_row}: avg_cost missing or invalid")
                avg_cost = None
        else:
            needs_confirmation = True
            warnings.append("avg_cost column not mapped; PB confirmation required")

        currency_raw = _string_value(row.get(currency_col)) if currency_col else None
        currency = currency_raw.upper() if currency_raw else None
        if currency is None:
            currency = _infer_currency(code, market)
            if currency is None:
                needs_confirmation = True
                warnings.append(f"row {source_row}: currency could not be inferred")

        source_columns = {
            field_name: _original_column(df, column_name)
            for field_name, column_name in schema.mapped_columns.items()
        }
        holdings.append(
            NormalizedCsvHolding(
                client_id=_string_value(row.get(client_col)) if client_col else None,
                account=_string_value(row.get(account_col)) if account_col else None,
                market=market,
                code=code.upper(),
                name=_string_value(row.get(name_col)) if name_col else None,
                quantity=_format_decimal(quantity),
                avg_cost=_format_decimal(avg_cost) if avg_cost is not None else None,
                currency=currency,
                source_row=source_row,
                source_columns=source_columns,
            )
        )

    if not holdings:
        return CsvNormalizationResult(
            status="needs_confirmation" if schema.review_fields else "insufficient_data",
            holdings=[],
            warnings=warnings,
        )
    status: Literal["imported", "needs_confirmation", "insufficient_data"] = (
        "needs_confirmation" if needs_confirmation else "imported"
    )
    return CsvNormalizationResult(status=status, holdings=holdings, warnings=warnings)


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

    # 컬럼명 lowercase 정규화. 원본 컬럼명은 mapping evidence 로 보존한다.
    original_columns = [str(c).strip() for c in df.columns]
    normalized_columns = [_normalize_column_name(c) for c in original_columns]
    df.columns = normalized_columns
    df.attrs["original_columns"] = dict(zip(normalized_columns, original_columns, strict=False))

    schema = detect_portfolio_schema(df)
    if schema.missing_required_fields:
        errors.append(
            UploadErrorDetail(
                row=0,
                column=None,
                code="missing_columns",
                message=(
                    "필수 보유자산 필드 매핑 실패: "
                    + ", ".join(sorted(schema.missing_required_fields))
                ),
            )
        )
        return df, errors

    # 행별 검증
    date_col = schema.mapped_columns.get("date")
    quantity_col = schema.mapped_columns.get("quantity")
    currency_col = schema.mapped_columns.get("currency")
    avg_cost_col = schema.mapped_columns.get("avg_cost")
    price_col = schema.mapped_columns.get("price")
    for idx, row in df.iterrows():
        row_num = int(idx) + 2  # 헤더 = 1행, 데이터 시작 = 2행

        # date 형식
        date_val = str(row.get(date_col, "")).strip() if date_col else ""
        if date_val:
            try:
                from datetime import date as _date

                _date.fromisoformat(date_val)
            except ValueError:
                errors.append(
                    UploadErrorDetail(
                        row=row_num,
                        column=_original_column(df, date_col) if date_col else "date",
                        code="invalid_date",
                        message=f"날짜 형식 오류: '{date_val}' (ISO 8601 YYYY-MM-DD 필요)",
                    )
                )

        # quantity > 0
        qty_val = str(row.get(quantity_col, "")).strip() if quantity_col else ""
        if qty_val:
            qty = _parse_decimal(qty_val)
            if qty is None:
                errors.append(
                    UploadErrorDetail(
                        row=row_num,
                        column=_original_column(df, quantity_col) if quantity_col else "quantity",
                        code="invalid_quantity",
                        message=f"수량 형식 오류: '{qty_val}'",
                    )
                )
            elif qty <= 0:
                errors.append(
                    UploadErrorDetail(
                        row=row_num,
                        column=_original_column(df, quantity_col) if quantity_col else "quantity",
                        code="negative_quantity",
                        message=f"수량은 0보다 커야 합니다: {qty_val}",
                    )
                )

        # avg_cost / price > 0 when explicitly present
        for mapped_col, label in ((avg_cost_col, "avg_cost"), (price_col, "price")):
            if not mapped_col:
                continue
            raw_val = str(row.get(mapped_col, "")).strip()
            if not raw_val:
                continue
            parsed = _parse_decimal(raw_val)
            if parsed is not None and parsed <= 0:
                errors.append(
                    UploadErrorDetail(
                        row=row_num,
                        column=_original_column(df, mapped_col),
                        code=f"invalid_{label}",
                        message=f"{label} 는 0보다 커야 합니다: {raw_val}",
                    )
                )

        # currency enum
        currency_val = str(row.get(currency_col, "")).strip().upper() if currency_col else ""
        if currency_val and currency_val not in _VALID_CURRENCIES:
            errors.append(
                UploadErrorDetail(
                    row=row_num,
                    column=_original_column(df, currency_col) if currency_col else "currency",
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
    schema = detect_portfolio_schema(df) if not df.empty else PortfolioSchemaDetection(
        field_mappings=[],
        mapped_columns={},
        missing_required_fields=list(_REQUIRED_IMPORT_FIELDS),
    )
    normalized = (
        normalize_holdings_from_csv(df, schema)
        if not df.empty
        else CsvNormalizationResult(status="insufficient_data", holdings=[], warnings=[])
    )

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
        warning_rows=len(normalized.warnings),
        errors=errors,
        preview=preview,
        schema_fingerprint=fingerprint,
        created_at=datetime.now(UTC).isoformat(),
        import_status=normalized.status,
        field_mappings=schema.field_mappings,
        unmapped_columns=schema.unmapped_columns,
        normalized_holdings=normalized.holdings,
        normalization_warnings=normalized.warnings,
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
