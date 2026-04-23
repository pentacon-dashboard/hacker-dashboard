"""포트폴리오 API — week-3.

Holdings CRUD + 집계 요약 + 스냅샷 조회 + 리밸런싱 제안.
user_id = "demo" 고정 (단일 사용자 데모).
"""
from __future__ import annotations

import logging
import time
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Holding, PortfolioSnapshot
from app.db.session import get_db
from app.schemas.portfolio import (
    HoldingCreate,
    HoldingResponse,
    HoldingUpdate,
    PortfolioSummary,
    SnapshotResponse,
)
from app.schemas.rebalance import (
    LLMAnalysis,
    RebalanceMeta,
    RebalanceRequest,
    RebalanceResponse,
    RebalanceSummary,
)
from app.services.market import get_adapter
from app.services.portfolio import compute_summary, get_period_snapshot, get_prev_snapshot
from app.services.rebalance import (
    build_expected_allocation,
    build_summary,
    calculate_rebalance_actions,
    compute_current_allocation,
    compute_drift,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

_DEMO_USER = "demo"


def _holding_to_response(h: Holding) -> HoldingResponse:
    return HoldingResponse(
        id=h.id,
        user_id=h.user_id,
        market=h.market,
        code=h.code,
        quantity=h.quantity,
        avg_cost=h.avg_cost,
        currency=h.currency,
        created_at=h.created_at.isoformat() if isinstance(h.created_at, datetime) else str(h.created_at),
        updated_at=h.updated_at.isoformat() if isinstance(h.updated_at, datetime) else str(h.updated_at),
    )


# ────────────────────── Holdings CRUD ──────────────────────


@router.post("/holdings", response_model=HoldingResponse, status_code=201)
async def create_holding(
    body: HoldingCreate,
    db: AsyncSession = Depends(get_db),
) -> HoldingResponse:
    """보유 종목 추가."""
    # market 유효성 확인
    try:
        get_adapter(body.market)
    except ValueError as exc:
        # HTTPValidationError 스키마 호환: detail 은 반드시 array
        raise HTTPException(
            status_code=422,
            detail=[{"msg": str(exc), "type": "value_error", "loc": ["body", "market"]}],
        ) from exc

    now = datetime.now(timezone.utc)
    holding = Holding(
        user_id=_DEMO_USER,
        market=body.market,
        code=body.code,
        quantity=body.quantity,
        avg_cost=body.avg_cost,
        currency=body.currency.upper(),
        created_at=now,
        updated_at=now,
    )
    db.add(holding)
    await db.commit()
    await db.refresh(holding)
    return _holding_to_response(holding)


@router.get("/holdings", response_model=list[HoldingResponse])
async def list_holdings(
    db: AsyncSession = Depends(get_db),
) -> list[HoldingResponse]:
    """보유 종목 전체 조회."""
    result = await db.execute(
        select(Holding).where(Holding.user_id == _DEMO_USER).order_by(Holding.id)
    )
    holdings = result.scalars().all()
    return [_holding_to_response(h) for h in holdings]


@router.patch(
    "/holdings/{holding_id}",
    response_model=HoldingResponse,
    responses={404: {"description": "Holding not found"}},
)
async def update_holding(
    body: HoldingUpdate,
    holding_id: int = Path(..., ge=1, le=2_147_483_647, description="보유 종목 ID"),
    db: AsyncSession = Depends(get_db),
) -> HoldingResponse:
    """수량/평단가 수정."""
    result = await db.execute(
        select(Holding).where(Holding.id == holding_id, Holding.user_id == _DEMO_USER)
    )
    holding = result.scalar_one_or_none()
    if holding is None:
        raise HTTPException(status_code=404, detail=f"holding {holding_id} not found")

    if body.quantity is not None:
        holding.quantity = body.quantity
    if body.avg_cost is not None:
        holding.avg_cost = body.avg_cost
    holding.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(holding)
    return _holding_to_response(holding)


@router.delete(
    "/holdings/{holding_id}",
    status_code=204,
    responses={404: {"description": "Holding not found"}},
)
async def delete_holding(
    holding_id: int = Path(..., ge=1, le=2_147_483_647, description="보유 종목 ID"),
    db: AsyncSession = Depends(get_db),
) -> None:
    """보유 종목 삭제."""
    result = await db.execute(
        select(Holding).where(Holding.id == holding_id, Holding.user_id == _DEMO_USER)
    )
    holding = result.scalar_one_or_none()
    if holding is None:
        raise HTTPException(status_code=404, detail=f"holding {holding_id} not found")

    await db.delete(holding)
    await db.commit()


# ────────────────────── Portfolio 집계 ──────────────────────


@router.get("/summary", response_model=PortfolioSummary)
async def get_summary(
    period_days: int = Query(
        30,
        ge=1,
        le=365,
        description="period_change_pct 계산 기간 (일). 기본 30일.",
    ),
    db: AsyncSession = Depends(get_db),
) -> PortfolioSummary:
    """포트폴리오 집계 요약 (현재가 기반 실시간 계산).

    6개 KPI + 자산군 비중 + 디멘션 breakdown + TOP 종목을 한 번에 반환.
    """
    result = await db.execute(
        select(Holding).where(Holding.user_id == _DEMO_USER)
    )
    holdings = result.scalars().all()

    prev_snap = await get_prev_snapshot(db, user_id=_DEMO_USER)
    period_snap = await get_period_snapshot(
        db, user_id=_DEMO_USER, period_days=period_days
    )
    summary = await compute_summary(
        list(holdings),
        prev_snapshot=prev_snap,
        period_snapshot=period_snap,
        period_days=period_days,
    )
    return summary


# ────────────────────── Snapshots ──────────────────────


_SNAPSHOT_DATE_SCHEMA = {
    "schema": {
        "type": "string",
        "pattern": r"^\d{4}-\d{2}-\d{2}$",
        "title": "date",
    }
}


@router.get(
    "/snapshots",
    response_model=list[SnapshotResponse],
    openapi_extra={
        "parameters": [
            {
                "name": "from",
                "in": "query",
                "required": False,
                "description": "시작 날짜 (YYYY-MM-DD)",
                **_SNAPSHOT_DATE_SCHEMA,
            },
            {
                "name": "to",
                "in": "query",
                "required": False,
                "description": "종료 날짜 (YYYY-MM-DD)",
                **_SNAPSHOT_DATE_SCHEMA,
            },
        ]
    },
)
async def list_snapshots(
    from_str: str | None = Query(None, alias="from"),
    to_str: str | None = Query(None, alias="to"),
    db: AsyncSession = Depends(get_db),
) -> list[SnapshotResponse]:
    """포트폴리오 스냅샷 조회 (날짜 범위 필터)."""
    # "null" 리터럴 문자열은 미전달과 동일하게 처리 (schemathesis nullable 생성 대응)
    from_date: date | None = (
        date.fromisoformat(from_str) if from_str and from_str != "null" else None
    )
    to_date: date | None = (
        date.fromisoformat(to_str) if to_str and to_str != "null" else None
    )
    stmt = select(PortfolioSnapshot).where(PortfolioSnapshot.user_id == _DEMO_USER)
    if from_date:
        stmt = stmt.where(PortfolioSnapshot.snapshot_date >= from_date)
    if to_date:
        stmt = stmt.where(PortfolioSnapshot.snapshot_date <= to_date)
    stmt = stmt.order_by(PortfolioSnapshot.snapshot_date)

    result = await db.execute(stmt)
    snapshots = result.scalars().all()

    return [
        SnapshotResponse(
            id=s.id,
            user_id=s.user_id,
            snapshot_date=str(s.snapshot_date),
            total_value_krw=str(s.total_value_krw),
            total_pnl_krw=str(s.total_pnl_krw),
            asset_class_breakdown=s.asset_class_breakdown,
            holdings_detail=s.holdings_detail,
            created_at=s.created_at.isoformat() if isinstance(s.created_at, datetime) else str(s.created_at),
        )
        for s in snapshots
    ]


# ────────────────────── 리밸런싱 제안 ──────────────────────


@router.post("/rebalance", response_model=RebalanceResponse)
async def rebalance(
    body: RebalanceRequest,
    http_request: Request,
    http_response: Response,
    db: AsyncSession = Depends(get_db),
) -> RebalanceResponse:
    """리밸런싱 제안 생성.

    결정적 계산(순수함수)으로 actions 배열을 생성하고,
    LLM 해석(RebalanceAnalyzer)을 옵션으로 추가.
    LLM 실패 시 llm_analysis=None, status="degraded" 로 graceful degrade.
    """
    t_start = time.monotonic()

    request_id = http_request.headers.get("X-Request-ID") or str(uuid.uuid4())
    http_response.headers["X-Request-ID"] = request_id

    # 1. holdings 로드
    result = await db.execute(
        select(Holding).where(Holding.user_id == _DEMO_USER).order_by(Holding.id)
    )
    holdings = list(result.scalars().all())

    # 2. 빈 포트폴리오 처리
    if not holdings:
        empty_alloc = {k: 0.0 for k in ["stock_kr", "stock_us", "crypto", "cash", "fx"]}
        target_dict = body.target_allocation.model_dump()
        return RebalanceResponse(
            request_id=request_id,
            status="ok",
            current_allocation=empty_alloc,
            target_allocation=target_dict,
            drift={k: -v for k, v in target_dict.items()},
            actions=[],
            expected_allocation=empty_alloc,
            summary=RebalanceSummary(
                total_trades=0,
                total_sell_value_krw=Decimal("0"),
                total_buy_value_krw=Decimal("0"),
                rebalance_cost_estimate_krw=Decimal("0"),
            ),
            llm_analysis=None,
            meta=RebalanceMeta(
                latency_ms=int((time.monotonic() - t_start) * 1000),
                gates={"schema_gate": "skip", "domain_gate": "skip", "critique_gate": "skip"},
                evidence_snippets=[],
            ),
        )

    # 3. 현재가 조회 (compute_summary 재사용하여 value_krw, price 추출)
    prev_snap = await get_prev_snapshot(db, user_id=_DEMO_USER)
    summary = await compute_summary(list(holdings), prev_snapshot=prev_snap)

    # holding id → value_krw, unit_price_krw 매핑 구성
    current_values_krw: dict[int, Decimal] = {}
    current_prices_krw: dict[int, Decimal] = {}

    for detail in summary.holdings:
        h_id = detail.id
        try:
            current_values_krw[h_id] = Decimal(detail.value_krw)
        except Exception:
            current_values_krw[h_id] = Decimal("0")
        try:
            current_prices_krw[h_id] = Decimal(detail.current_price_krw)
        except Exception:
            current_prices_krw[h_id] = Decimal("0")

    total_value = Decimal(summary.total_value_krw)

    # 4. 순수함수로 리밸런싱 계산
    current_alloc = compute_current_allocation(holdings, current_values_krw, total_value)
    target_dict = body.target_allocation.model_dump()
    drift = compute_drift(current_alloc, target_dict)
    actions = calculate_rebalance_actions(
        holdings=holdings,
        current_values_krw=current_values_krw,
        current_prices_krw=current_prices_krw,
        target=body.target_allocation,
        constraints=body.constraints,
        total_value_krw=total_value,
    )
    expected_alloc = build_expected_allocation(
        current_values_krw=current_values_krw,
        holdings=holdings,
        actions=actions,
        current_prices_krw=current_prices_krw,
        total_value_krw=total_value,
    )
    rebalance_summary = build_summary(actions)

    # 5. LLM 해석 — Track B(RebalanceAnalyzer) 호출, 실패 시 graceful degrade
    llm_analysis: LLMAnalysis | None = None
    gates: dict[str, str] = {
        "schema_gate": "pending",
        "domain_gate": "pending",
        "critique_gate": "pending",
    }
    try:
        from app.agents.analyzers.rebalance import RebalanceAnalyzer  # type: ignore[import]

        analyzer = RebalanceAnalyzer()
        llm_analysis, gates = await analyzer.analyze(
            actions=actions,
            drift=drift,
            current_allocation=current_alloc,
            target_allocation=target_dict,
            constraints=body.constraints,
        )
    except ImportError:
        logger.debug("RebalanceAnalyzer 아직 미구현 — llm_analysis=None (graceful degrade)")
    except Exception as exc:
        logger.warning("rebalance LLM analysis failed: %s", exc)

    status: str = "ok" if llm_analysis is not None else "degraded"
    latency_ms = int((time.monotonic() - t_start) * 1000)

    # evidence_snippets: drift 상위 자산군 요약
    evidence_snippets: list[str] = []
    for ac, d in sorted(drift.items(), key=lambda x: abs(x[1]), reverse=True)[:3]:
        if abs(d) > 0.01:
            cur_pct = current_alloc.get(ac, 0.0) * 100
            tgt_pct = target_dict.get(ac, 0.0) * 100
            evidence_snippets.append(
                f"{ac} 현재 {cur_pct:.1f}% vs 목표 {tgt_pct:.1f}%"
            )

    return RebalanceResponse(
        request_id=request_id,
        status=status,  # type: ignore[arg-type]
        current_allocation=current_alloc,
        target_allocation=target_dict,
        drift=drift,
        actions=actions,
        expected_allocation=expected_alloc,
        summary=rebalance_summary,
        llm_analysis=llm_analysis,
        meta=RebalanceMeta(
            latency_ms=latency_ms,
            gates=gates,
            evidence_snippets=evidence_snippets,
        ),
    )
