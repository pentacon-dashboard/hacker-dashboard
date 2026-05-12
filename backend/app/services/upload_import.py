"""Persist normalized upload CSV holdings into the portfolio store."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Holding, PortfolioImportBatch, PortfolioImportRow
from app.schemas.portfolio import HoldingResponse
from app.schemas.upload import (
    ConfirmedCsvMapping,
    NormalizedCsvHolding,
    UploadErrorDetail,
    UploadImportResponse,
    UploadImportRow,
)
from app.services.clients import ensure_client_registry, normalize_client_name
from app.services.upload import (
    _schema_from_confirmed_mapping,
    build_mapping_candidates,
    build_normalized_preview,
    detect_portfolio_schema,
    normalize_holdings_from_csv,
)

ImportStatus = Literal["imported", "partial_imported", "needs_confirmation", "insufficient_data"]

_DEMO_USER = "pb-demo"
_DEFAULT_CLIENT_ID = "client-001"
_SUPPORTED_MARKETS = {"upbit", "binance", "yahoo", "naver_kr"}
_SUPPORTED_CURRENCIES = {"KRW", "USD", "USDT", "EUR", "JPY"}


def _client_name(client_id: str) -> str:
    if client_id.startswith("client-"):
        suffix = client_id.removeprefix("client-")
        if suffix.isdigit():
            index = int(suffix) - 1
            if 0 <= index < 26:
                return f"Client {chr(ord('A') + index)}"
    return client_id


def _holding_to_response(h: Holding) -> HoldingResponse:
    return HoldingResponse(
        id=h.id,
        user_id=h.user_id,
        client_id=getattr(h, "client_id", _DEFAULT_CLIENT_ID),
        client_name=_client_name(getattr(h, "client_id", _DEFAULT_CLIENT_ID)),
        market=h.market,
        code=h.code,
        quantity=h.quantity,
        avg_cost=h.avg_cost,
        currency=h.currency,
        created_at=(
            h.created_at.isoformat() if isinstance(h.created_at, datetime) else str(h.created_at)
        ),
        updated_at=(
            h.updated_at.isoformat() if isinstance(h.updated_at, datetime) else str(h.updated_at)
        ),
    )


def _decimal_from_text(
    value: str, *, field_name: str, source_row: int
) -> tuple[Decimal, str | None]:
    try:
        parsed = Decimal(value)
    except InvalidOperation:
        return Decimal("0"), f"row {source_row}: {field_name} is not a decimal"
    if parsed <= 0:
        return Decimal("0"), f"row {source_row}: {field_name} must be greater than zero"
    return parsed, None


def _blocking_warnings(holding: NormalizedCsvHolding) -> list[str]:
    warnings: list[str] = []
    if holding.market is None:
        warnings.append(f"row {holding.source_row}: market missing")
    elif holding.market not in _SUPPORTED_MARKETS:
        warnings.append(f"row {holding.source_row}: unsupported market '{holding.market}'")
    if holding.currency is None:
        warnings.append(f"row {holding.source_row}: currency missing")
    elif holding.currency.upper() not in _SUPPORTED_CURRENCIES:
        warnings.append(f"row {holding.source_row}: unsupported currency '{holding.currency}'")
    return warnings


def _selected_client_warnings(
    holdings: list[NormalizedCsvHolding],
    *,
    selected_client_id: str,
) -> list[str]:
    warnings: list[str] = []
    for holding in holdings:
        source_client_id = holding.client_id
        if source_client_id and source_client_id != selected_client_id:
            warnings.append(
                f"row {holding.source_row}: source client_id '{source_client_id}' "
                f"imported into selected client '{selected_client_id}'"
            )
    return warnings


def _source_client_names(holdings: list[NormalizedCsvHolding]) -> list[str]:
    names_by_key: dict[str, str] = {}
    for holding in holdings:
        if not holding.client_name:
            continue
        normalized = normalize_client_name(holding.client_name)
        if normalized:
            names_by_key.setdefault(normalized, holding.client_name)
    return sorted(names_by_key.values())


def _mapping_payload(confirmed_mapping: dict[str, ConfirmedCsvMapping] | None) -> dict[str, Any]:
    if not confirmed_mapping:
        return {}
    return {
        field_name: mapping.model_dump(mode="json", exclude_none=True)
        for field_name, mapping in sorted(confirmed_mapping.items())
    }


def _confirmed_mapping_hash(confirmed_mapping: dict[str, ConfirmedCsvMapping] | None) -> str:
    payload = json.dumps(_mapping_payload(confirmed_mapping), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _import_batch_key(
    *,
    client_id: str,
    file_content_hash: str,
    confirmed_mapping_hash: str,
) -> str:
    raw = f"{client_id}:{file_content_hash}:{confirmed_mapping_hash}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _response(
    *,
    status: ImportStatus,
    client_id: str,
    imported: list[Holding],
    normalized: list[NormalizedCsvHolding],
    field_mappings: list[Any],
    mapping_candidates: list[Any],
    unmapped_columns: list[str],
    normalized_preview: list[dict[str, Any]],
    warnings: list[str],
    blocking_errors: list[UploadErrorDetail],
    imported_rows: list[UploadImportRow] | None = None,
    recoverable_rows: list[UploadImportRow] | None = None,
    quarantined_rows: list[UploadImportRow] | None = None,
    garbage_rows: list[UploadImportRow] | None = None,
    import_batch_key: str | None = None,
) -> UploadImportResponse:
    return UploadImportResponse(
        status=status,
        client_id=client_id,
        imported_count=len(imported),
        import_batch_key=import_batch_key,
        holdings=[_holding_to_response(h) for h in imported],
        field_mappings=field_mappings,
        mapping_candidates=mapping_candidates,
        unmapped_columns=unmapped_columns,
        normalized_preview=normalized_preview,
        normalized_holdings=normalized,
        normalization_warnings=warnings,
        blocking_errors=blocking_errors,
        imported_rows=imported_rows or [],
        recoverable_rows=recoverable_rows or [],
        quarantined_rows=quarantined_rows or [],
        garbage_rows=garbage_rows or [],
    )


async def _upsert_import_batch(
    db: AsyncSession,
    *,
    client_id: str,
    import_batch_key: str,
    file_name: str,
    file_content_hash: str,
    confirmed_mapping_hash: str,
    confirmed_mapping: dict[str, ConfirmedCsvMapping] | None,
    status: ImportStatus,
    warnings: list[str],
) -> None:
    payload = json.dumps(_mapping_payload(confirmed_mapping), sort_keys=True, ensure_ascii=False)
    warnings_payload = json.dumps(warnings, ensure_ascii=False)
    result = await db.execute(
        select(PortfolioImportBatch).where(
            PortfolioImportBatch.import_batch_key == import_batch_key
        )
    )
    batch = result.scalar_one_or_none()
    now = datetime.now(UTC)
    if batch is None:
        db.add(
            PortfolioImportBatch(
                user_id=_DEMO_USER,
                client_id=client_id,
                import_batch_key=import_batch_key,
                file_name=file_name,
                file_content_hash=file_content_hash,
                confirmed_mapping_hash=confirmed_mapping_hash,
                confirmed_mapping=payload,
                status=status,
                warnings=warnings_payload,
                created_at=now,
                updated_at=now,
            )
        )
        return
    batch.status = status
    batch.warnings = warnings_payload
    batch.confirmed_mapping = payload
    batch.updated_at = now


def _row_reason_codes(row: UploadImportRow) -> list[str]:
    reason_codes: list[str] = []
    if row.reason_code:
        reason_codes.append(row.reason_code)
    for error in row.errors:
        if error.code not in reason_codes:
            reason_codes.append(error.code)
    return reason_codes


def _row_ledger(
    row: UploadImportRow,
    *,
    client_id: str,
    import_batch_key: str,
    linked_holding_id: int | None,
    created_at: datetime,
) -> PortfolioImportRow:
    return PortfolioImportRow(
        user_id=_DEMO_USER,
        client_id=client_id,
        import_batch_key=import_batch_key,
        source_row=row.source_row,
        row_status=row.classification,
        raw_row_json=dict(row.source_columns),
        normalized_payload_json=(
            row.normalized_holding.model_dump(mode="json")
            if row.normalized_holding is not None
            else None
        ),
        reason_codes=_row_reason_codes(row),
        linked_holding_id=linked_holding_id,
        created_at=created_at,
    )


async def import_holdings_from_df(
    df: Any,
    *,
    db: AsyncSession,
    client_id: str,
    file_content_hash: str = "",
    file_name: str = "upload.csv",
    confirmed_mapping: dict[str, ConfirmedCsvMapping] | None = None,
) -> UploadImportResponse:
    """Import normalized holdings only when mapping and row values are deterministic."""
    schema = (
        _schema_from_confirmed_mapping(df, confirmed_mapping)
        if confirmed_mapping
        else detect_portfolio_schema(df)
    )
    normalized = normalize_holdings_from_csv(df, schema)
    warnings = list(normalized.warnings)
    warnings.extend(
        _selected_client_warnings(
            normalized.holdings,
            selected_client_id=client_id,
        )
    )
    source_client_names = _source_client_names(normalized.holdings)
    if len(source_client_names) > 1:
        warnings.append(
            "multiple source client_name values imported into selected client "
            f"'{client_id}': {', '.join(source_client_names)}"
        )
    mapping_candidates = build_mapping_candidates(df, schema)
    normalized_preview = build_normalized_preview(df, schema)
    mapping_hash = _confirmed_mapping_hash(confirmed_mapping)
    import_batch_key = _import_batch_key(
        client_id=client_id,
        file_content_hash=file_content_hash,
        confirmed_mapping_hash=mapping_hash,
    )
    import_status: ImportStatus = normalized.status
    has_partial_row_ledger = bool(
        normalized.imported_rows
        and (
            normalized.recoverable_rows
            or normalized.quarantined_rows
            or normalized.garbage_rows
        )
    )
    if normalized.status in {"imported", "partial_imported"} and has_partial_row_ledger:
        import_status = "partial_imported"

    if import_status not in {"imported", "partial_imported"}:
        return _response(
            status=import_status,
            client_id=client_id,
            imported=[],
            normalized=normalized.holdings,
            field_mappings=schema.field_mappings,
            mapping_candidates=mapping_candidates,
            unmapped_columns=schema.unmapped_columns,
            normalized_preview=normalized_preview,
            warnings=warnings,
            blocking_errors=normalized.blocking_errors,
            imported_rows=normalized.imported_rows,
            recoverable_rows=normalized.recoverable_rows,
            quarantined_rows=normalized.quarantined_rows,
            garbage_rows=normalized.garbage_rows,
            import_batch_key=import_batch_key if confirmed_mapping else None,
        )

    blocking: list[str] = []
    for normalized_holding in normalized.holdings:
        blocking.extend(_blocking_warnings(normalized_holding))
        _, quantity_warning = _decimal_from_text(
            normalized_holding.quantity,
            field_name="quantity",
            source_row=normalized_holding.source_row,
        )
        if quantity_warning is not None:
            blocking.append(quantity_warning)
        if normalized_holding.avg_cost is not None:
            _, avg_cost_warning = _decimal_from_text(
                normalized_holding.avg_cost,
                field_name="avg_cost",
                source_row=normalized_holding.source_row,
            )
            if avg_cost_warning is not None:
                blocking.append(avg_cost_warning)

    if blocking:
        blocking_errors = [
            UploadErrorDetail(row=0, column=None, code="blocking_warning", message=warning)
            for warning in blocking
        ]
        return _response(
            status="needs_confirmation",
            client_id=client_id,
            imported=[],
            normalized=normalized.holdings,
            field_mappings=schema.field_mappings,
            mapping_candidates=mapping_candidates,
            unmapped_columns=schema.unmapped_columns,
            normalized_preview=normalized_preview,
            warnings=warnings + blocking,
            blocking_errors=blocking_errors,
            imported_rows=normalized.imported_rows,
            recoverable_rows=normalized.recoverable_rows,
            quarantined_rows=normalized.quarantined_rows,
            garbage_rows=normalized.garbage_rows,
            import_batch_key=import_batch_key,
        )

    await db.execute(
        delete(PortfolioImportRow).where(
            PortfolioImportRow.user_id == _DEMO_USER,
            PortfolioImportRow.client_id == client_id,
            PortfolioImportRow.import_batch_key == import_batch_key,
        )
    )
    await db.execute(
        delete(Holding).where(
            Holding.user_id == _DEMO_USER,
            Holding.client_id == client_id,
            Holding.import_batch_key == import_batch_key,
        )
    )

    now = datetime.now(UTC)
    imported: list[Holding] = []
    for normalized_holding in normalized.holdings:
        assert normalized_holding.market is not None
        assert normalized_holding.currency is not None
        quantity, _ = _decimal_from_text(
            normalized_holding.quantity,
            field_name="quantity",
            source_row=normalized_holding.source_row,
        )
        avg_cost: Decimal | None = None
        if normalized_holding.avg_cost is not None:
            avg_cost, _ = _decimal_from_text(
                normalized_holding.avg_cost,
                field_name="avg_cost",
                source_row=normalized_holding.source_row,
            )
        cost_basis_status = normalized_holding.cost_basis_status or (
            "missing" if avg_cost is None else "provided"
        )
        holding = Holding(
            user_id=_DEMO_USER,
            client_id=client_id,
            market=normalized_holding.market,
            code=normalized_holding.code,
            quantity=quantity,
            avg_cost=avg_cost,
            cost_basis_status=cost_basis_status,
            currency=normalized_holding.currency.upper(),
            import_batch_key=import_batch_key,
            source_row=normalized_holding.source_row,
            source_columns=json.dumps(normalized_holding.source_columns, ensure_ascii=False),
            source_client_id=normalized_holding.client_id,
            created_at=now,
            updated_at=now,
        )
        db.add(holding)
        imported.append(holding)

    await db.flush()
    await _upsert_import_batch(
        db,
        client_id=client_id,
        import_batch_key=import_batch_key,
        file_name=file_name,
        file_content_hash=file_content_hash,
        confirmed_mapping_hash=mapping_hash,
        confirmed_mapping=confirmed_mapping,
        status=import_status,
        warnings=warnings,
    )
    await db.flush()
    holdings_by_source_row = {holding.source_row: holding for holding in imported}
    for row in (
        *normalized.imported_rows,
        *normalized.recoverable_rows,
        *normalized.quarantined_rows,
        *normalized.garbage_rows,
    ):
        linked_holding = holdings_by_source_row.get(row.source_row)
        db.add(
            _row_ledger(
                row,
                client_id=client_id,
                import_batch_key=import_batch_key,
                linked_holding_id=linked_holding.id if linked_holding is not None else None,
                created_at=now,
            )
        )
    await ensure_client_registry(
        db,
        user_id=_DEMO_USER,
        client_id=client_id,
        display_name=source_client_names[0] if len(source_client_names) == 1 else None,
        source_names=source_client_names,
    )

    await db.commit()
    for holding in imported:
        await db.refresh(holding)

    return _response(
        status=import_status,
        client_id=client_id,
        imported=imported,
        normalized=normalized.holdings,
        field_mappings=schema.field_mappings,
        mapping_candidates=mapping_candidates,
        unmapped_columns=schema.unmapped_columns,
        normalized_preview=normalized_preview,
        warnings=warnings,
        blocking_errors=[],
        imported_rows=normalized.imported_rows,
        recoverable_rows=normalized.recoverable_rows,
        quarantined_rows=normalized.quarantined_rows,
        garbage_rows=normalized.garbage_rows,
        import_batch_key=import_batch_key,
    )
