"""Persist normalized upload CSV holdings into the portfolio store."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Holding
from app.schemas.portfolio import HoldingResponse
from app.schemas.upload import NormalizedCsvHolding, UploadImportResponse
from app.services.upload import detect_portfolio_schema, normalize_holdings_from_csv

ImportStatus = Literal["imported", "needs_confirmation", "insufficient_data"]

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


def _decimal_from_text(value: str, *, field_name: str, source_row: int) -> tuple[Decimal, str | None]:
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
    if holding.avg_cost is None:
        warnings.append(f"row {holding.source_row}: avg_cost missing")
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


def _response(
    *,
    status: ImportStatus,
    client_id: str,
    imported: list[Holding],
    normalized: list[NormalizedCsvHolding],
    field_mappings: list[Any],
    unmapped_columns: list[str],
    warnings: list[str],
) -> UploadImportResponse:
    return UploadImportResponse(
        status=status,
        client_id=client_id,
        imported_count=len(imported),
        holdings=[_holding_to_response(h) for h in imported],
        field_mappings=field_mappings,
        unmapped_columns=unmapped_columns,
        normalized_holdings=normalized,
        normalization_warnings=warnings,
    )


async def import_holdings_from_df(
    df: Any,
    *,
    db: AsyncSession,
    client_id: str,
) -> UploadImportResponse:
    """Import normalized holdings only when schema detection is deterministic."""
    schema = detect_portfolio_schema(df)
    normalized = normalize_holdings_from_csv(df, schema)
    warnings = list(normalized.warnings)
    warnings.extend(
        _selected_client_warnings(
            normalized.holdings,
            selected_client_id=client_id,
        )
    )

    if normalized.status != "imported":
        return _response(
            status=normalized.status,
            client_id=client_id,
            imported=[],
            normalized=normalized.holdings,
            field_mappings=schema.field_mappings,
            unmapped_columns=schema.unmapped_columns,
            warnings=warnings,
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
        return _response(
            status="needs_confirmation",
            client_id=client_id,
            imported=[],
            normalized=normalized.holdings,
            field_mappings=schema.field_mappings,
            unmapped_columns=schema.unmapped_columns,
            warnings=warnings + blocking,
        )

    now = datetime.now(UTC)
    imported: list[Holding] = []
    for normalized_holding in normalized.holdings:
        assert normalized_holding.market is not None
        assert normalized_holding.avg_cost is not None
        assert normalized_holding.currency is not None
        quantity, _ = _decimal_from_text(
            normalized_holding.quantity,
            field_name="quantity",
            source_row=normalized_holding.source_row,
        )
        avg_cost, _ = _decimal_from_text(
            normalized_holding.avg_cost,
            field_name="avg_cost",
            source_row=normalized_holding.source_row,
        )
        holding = Holding(
            user_id=_DEMO_USER,
            client_id=client_id,
            market=normalized_holding.market,
            code=normalized_holding.code,
            quantity=quantity,
            avg_cost=avg_cost,
            currency=normalized_holding.currency.upper(),
            created_at=now,
            updated_at=now,
        )
        db.add(holding)
        imported.append(holding)

    await db.commit()
    for holding in imported:
        await db.refresh(holding)

    return _response(
        status="imported",
        client_id=client_id,
        imported=imported,
        normalized=normalized.holdings,
        field_mappings=schema.field_mappings,
        unmapped_columns=schema.unmapped_columns,
        warnings=warnings,
    )
