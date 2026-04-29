"""포트폴리오 집계 서비스 — week-3.

compute_summary(holdings) → PortfolioSummary:
  - 각 holding 현재가: registry.get_adapter(market).fetch_quote(code)
  - fx 로 KRW 정규화
  - 종목별 손익 계산
  - 자산군 분포 계산
  - 전일 스냅샷 대비 일간 변동
"""

from __future__ import annotations

import logging
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.portfolio import DimensionItem, HoldingDetail, PortfolioSummary
from app.services.fx import get_rate
from app.services.market import get_adapter
from app.services.portfolio_service import build_market_leaders, calc_win_rate
from app.services.sector_map import get_sector

logger = logging.getLogger(__name__)

# market prefix → asset_class 매핑
_MARKET_TO_ASSET_CLASS: dict[str, str] = {
    "upbit": "crypto",
    "binance": "crypto",
    "yahoo": "stock_us",  # yahoo는 US 주식/ETF 중심
    "naver_kr": "stock_kr",
    "krx": "stock_kr",
    "nasdaq": "stock_us",
    "nyse": "stock_us",
}


def _classify_asset(market: str) -> str:
    return _MARKET_TO_ASSET_CLASS.get(market.lower(), "other")


def _d(v: Any) -> Decimal:
    """안전하게 Decimal 변환."""
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


def _fmt(v: Decimal, places: int = 2) -> str:
    quant = Decimal(10) ** -places
    return str(v.quantize(quant, rounding=ROUND_HALF_UP))


class HoldingInput:
    """DB Holding 또는 dict 모두 처리하는 얇은 래퍼."""

    def __init__(self, data: Any) -> None:
        self.id: int = int(data.id) if hasattr(data, "id") else int(data["id"])
        self.client_id: str = (
            data.client_id if hasattr(data, "client_id") else data.get("client_id", "client-001")
        )
        self.market: str = data.market if hasattr(data, "market") else data["market"]
        self.code: str = data.code if hasattr(data, "code") else data["code"]
        self.quantity: Decimal = _d(
            data.quantity if hasattr(data, "quantity") else data["quantity"]
        )
        self.avg_cost: Decimal = _d(
            data.avg_cost if hasattr(data, "avg_cost") else data["avg_cost"]
        )
        self.currency: str = data.currency if hasattr(data, "currency") else data["currency"]


async def compute_summary(
    holdings: list[Any],
    prev_snapshot: Any | None = None,
    period_snapshot: Any | None = None,
    period_days: int = 30,
    user_id: str = "pb-demo",
    client_id: str = "client-001",
    client_name: str | None = None,
    pb_aum_krw: str | None = None,
) -> PortfolioSummary:
    """holdings 목록으로 포트폴리오 집계.

    Args:
        holdings: DB Holding 객체 또는 dict 목록
        prev_snapshot: 전일 PortfolioSnapshot (없으면 일간 변동 = 0)
        period_snapshot: period_days 전 스냅샷 (없으면 period_change_pct = 0)
        period_days: period_change_pct 계산에 쓰인 기간 (기본 30일)
    """
    items = [HoldingInput(h) for h in holdings]

    total_value = Decimal("0")
    total_cost = Decimal("0")
    asset_class_values: dict[str, Decimal] = {}
    sector_values: dict[str, Decimal] = {}
    holding_details: list[HoldingDetail] = []

    for item in items:
        # 현재가 조회
        try:
            adapter = get_adapter(item.market)
            quote = await adapter.fetch_quote(item.code)
            current_price = _d(quote.price)
            price_currency = quote.currency.upper()
        except Exception as exc:
            logger.warning(
                "현재가 조회 실패 (%s/%s): %s — avg_cost 로 대체", item.market, item.code, exc
            )
            current_price = item.avg_cost
            price_currency = item.currency

        # KRW 환산
        rate = await get_rate(price_currency, "KRW")
        rate_d = _d(rate)

        current_price_krw = current_price * rate_d
        value_krw = current_price_krw * item.quantity

        cost_rate = await get_rate(item.currency, "KRW")
        cost_krw = item.avg_cost * _d(cost_rate) * item.quantity

        pnl_krw = value_krw - cost_krw
        pnl_pct = (pnl_krw / cost_krw * 100) if cost_krw != 0 else Decimal("0")

        total_value += value_krw
        total_cost += cost_krw

        ac = _classify_asset(item.market)
        asset_class_values[ac] = asset_class_values.get(ac, Decimal("0")) + value_krw
        sector = get_sector(item.code)
        sector_values[sector] = sector_values.get(sector, Decimal("0")) + value_krw

        holding_details.append(
            HoldingDetail(
                id=item.id,
                market=item.market,
                code=item.code,
                quantity=_fmt(item.quantity, 8),
                avg_cost=_fmt(item.avg_cost, 4),
                currency=item.currency,
                current_price=_fmt(current_price, 4),
                current_price_krw=_fmt(current_price_krw, 2),
                value_krw=_fmt(value_krw, 2),
                cost_krw=_fmt(cost_krw, 2),
                pnl_krw=_fmt(pnl_krw, 2),
                pnl_pct=_fmt(pnl_pct, 2),
            )
        )

    total_pnl_krw = total_value - total_cost
    total_pnl_pct = (total_pnl_krw / total_cost * 100) if total_cost != 0 else Decimal("0")

    # 자산군 비율
    breakdown: dict[str, str] = {}
    for ac, val in asset_class_values.items():
        ratio = (val / total_value) if total_value != 0 else Decimal("0")
        breakdown[ac] = _fmt(ratio, 4)

    sector_breakdown: dict[str, str] = {}
    for sector, val in sector_values.items():
        ratio = (val / total_value) if total_value != 0 else Decimal("0")
        sector_breakdown[sector] = _fmt(ratio, 4)

    # 일간 변동
    daily_change_krw = Decimal("0")
    daily_change_pct = Decimal("0")
    if prev_snapshot is not None:
        prev_value = _d(
            prev_snapshot.total_value_krw
            if hasattr(prev_snapshot, "total_value_krw")
            else prev_snapshot["total_value_krw"]
        )
        daily_change_krw = total_value - prev_value
        daily_change_pct = (
            (daily_change_krw / prev_value * 100) if prev_value != 0 else Decimal("0")
        )

    # 기간 변동 (N일 전 스냅샷 대비)
    period_change_pct = Decimal("0")
    if period_snapshot is not None:
        period_value = _d(
            period_snapshot.total_value_krw
            if hasattr(period_snapshot, "total_value_krw")
            else period_snapshot["total_value_krw"]
        )
        if period_value != 0:
            period_change_pct = (total_value - period_value) / period_value * 100

    # 최저 단일 종목 수익률
    worst_asset_pct = Decimal("0")
    if holding_details:
        try:
            worst_asset_pct = min(_d(hd.pnl_pct) for hd in holding_details)
        except Exception:
            worst_asset_pct = Decimal("0")

    # HHI 기반 집중도 리스크 점수 (0~100)
    # HHI = Σ(share_i)^2 ∈ [1/n, 1]. 단일자산 100%, 완전 분산 ≈ 1/n*100%.
    risk_score = Decimal("0")
    if asset_class_values and total_value != 0:
        hhi = sum(
            ((v / total_value) ** 2 for v in asset_class_values.values()),
            start=Decimal("0"),
        )
        risk_score = hhi * 100

    # 차원(자산군)별 바 차트용 집계 — asset_class 별 가중 pnl
    class_totals: dict[str, Decimal] = {}
    class_pnls: dict[str, Decimal] = {}
    for detail in holding_details:
        ac = _classify_asset(detail.market)
        v = _d(detail.value_krw)
        p = _d(detail.pnl_krw)
        class_totals[ac] = class_totals.get(ac, Decimal("0")) + v
        class_pnls[ac] = class_pnls.get(ac, Decimal("0")) + p

    dimension_breakdown: list[DimensionItem] = []
    for ac in sorted(class_totals.keys(), key=lambda k: class_totals[k], reverse=True):
        v = class_totals[ac]
        p = class_pnls.get(ac, Decimal("0"))
        weight = (v / total_value * 100) if total_value != 0 else Decimal("0")
        cost = v - p
        class_pnl_pct = (p / cost * 100) if cost != 0 else Decimal("0")
        dimension_breakdown.append(
            DimensionItem(
                label=ac,
                weight_pct=_fmt(weight, 2),
                pnl_pct=_fmt(class_pnl_pct, 2),
            )
        )

    # sprint-08 B-1: win_rate_pct + market_leaders
    win_rate_pct = calc_win_rate(holding_details)
    market_leaders = build_market_leaders(holding_details)

    return PortfolioSummary(
        user_id=user_id,
        client_id=client_id,
        client_name=client_name,
        pb_aum_krw=pb_aum_krw,
        total_value_krw=_fmt(total_value, 2),
        total_cost_krw=_fmt(total_cost, 2),
        total_pnl_krw=_fmt(total_pnl_krw, 2),
        total_pnl_pct=_fmt(total_pnl_pct, 2),
        daily_change_krw=_fmt(daily_change_krw, 2),
        daily_change_pct=_fmt(daily_change_pct, 2),
        asset_class_breakdown=breakdown,
        sector_breakdown=sector_breakdown,
        holdings=holding_details,
        holdings_count=len(holding_details),
        worst_asset_pct=_fmt(worst_asset_pct, 2),
        risk_score_pct=_fmt(risk_score, 2),
        period_change_pct=_fmt(period_change_pct, 2),
        period_days=period_days,
        dimension_breakdown=dimension_breakdown,
        win_rate_pct=win_rate_pct,
        market_leaders=market_leaders,
    )


async def build_portfolio_context(
    db: AsyncSession,
    user_id: str = "pb-demo",
    client_id: str = "client-001",
    client_name: str | None = None,
    target_market: str | None = None,
    target_code: str | None = None,
) -> Any | None:
    """DB에서 holdings + 최근 스냅샷을 읽어 PortfolioContext 구성.

    target_market/code가 주어지고 holdings에 일치하는 항목이 있으면 matched_holding 세팅.
    holdings가 비어있거나 compute_summary 실패 시 None 반환 (graceful degrade).
    에러(외부 API 다운 등)는 삼키고 None 반환. logger.warning으로만 기록.
    holdings 내용은 debug 레벨에만 기록.
    """
    from app.db.models import Holding
    from app.schemas.analyze import PortfolioContext, PortfolioHolding

    try:
        result = await db.execute(
            select(Holding).where(Holding.user_id == user_id, Holding.client_id == client_id)
        )
        holdings_rows = list(result.scalars().all())
    except Exception as exc:
        logger.warning("build_portfolio_context: holdings 조회 실패 — %s", exc)
        return None

    if not holdings_rows:
        return None

    logger.debug("build_portfolio_context: holdings=%d개", len(holdings_rows))

    try:
        prev = await get_prev_snapshot(db, user_id, client_id=client_id)
        summary = await compute_summary(
            holdings_rows,
            prev_snapshot=prev,
            user_id=user_id,
            client_id=client_id,
            client_name=client_name,
        )
    except Exception as exc:
        logger.warning("build_portfolio_context: compute_summary 실패 — %s", exc)
        return None

    # HoldingDetail → PortfolioHolding 변환
    portfolio_holdings: list[PortfolioHolding] = []
    holding_map: dict[tuple[str, str], PortfolioHolding] = {}

    for detail in summary.holdings:
        # summary.holdings의 원본 market/code 추적을 위해 holdings_rows와 id 매칭
        raw = next(
            (h for h in holdings_rows if str(h.id) == str(detail.id)),
            None,
        )
        if raw is None:
            continue

        try:
            current_value_krw = Decimal(detail.value_krw)
            pnl_pct = float(detail.pnl_pct)
        except Exception:
            current_value_krw = None
            pnl_pct = None

        ph = PortfolioHolding(
            market=detail.market,
            code=detail.code,
            quantity=Decimal(detail.quantity),
            avg_cost=Decimal(detail.avg_cost),
            currency=detail.currency,
            current_value_krw=current_value_krw,
            pnl_pct=pnl_pct,
        )
        portfolio_holdings.append(ph)
        holding_map[(detail.market.lower(), detail.code.lower())] = ph

    # total_value_krw
    try:
        total_value_krw = Decimal(summary.total_value_krw)
    except Exception:
        total_value_krw = Decimal("0")

    # asset_class_breakdown: str → float 변환
    asset_class_breakdown: dict[str, float] = {}
    for ac, ratio_str in summary.asset_class_breakdown.items():
        try:
            asset_class_breakdown[ac] = float(ratio_str)
        except Exception:
            asset_class_breakdown[ac] = 0.0

    # matched_holding 분리
    matched_holding: PortfolioHolding | None = None
    if target_market is not None and target_code is not None:
        matched_holding = holding_map.get((target_market.lower(), target_code.lower()))

    return PortfolioContext(
        client_id=client_id,
        client_name=client_name,
        holdings=portfolio_holdings,
        total_value_krw=total_value_krw,
        asset_class_breakdown=asset_class_breakdown,
        sector_breakdown={
            sector: float(ratio_str) for sector, ratio_str in summary.sector_breakdown.items()
        },
        matched_holding=matched_holding,
    )


async def get_latest_snapshot(
    session: AsyncSession, user_id: str = "pb-demo", client_id: str = "client-001"
) -> Any | None:
    """가장 최근 포트폴리오 스냅샷 조회."""
    from sqlalchemy import desc

    from app.db.models import PortfolioSnapshot

    result = await session.execute(
        select(PortfolioSnapshot)
        .where(PortfolioSnapshot.user_id == user_id, PortfolioSnapshot.client_id == client_id)
        .order_by(desc(PortfolioSnapshot.snapshot_date))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_prev_snapshot(
    session: AsyncSession, user_id: str = "pb-demo", client_id: str = "client-001"
) -> Any | None:
    """전일(오늘 제외) 포트폴리오 스냅샷 조회 — 일간 변동 계산용."""
    from datetime import date

    from sqlalchemy import desc

    from app.db.models import PortfolioSnapshot

    today = date.today()
    result = await session.execute(
        select(PortfolioSnapshot)
        .where(
            PortfolioSnapshot.user_id == user_id,
            PortfolioSnapshot.client_id == client_id,
            PortfolioSnapshot.snapshot_date < today,
        )
        .order_by(desc(PortfolioSnapshot.snapshot_date))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_period_snapshot(
    session: AsyncSession,
    user_id: str = "pb-demo",
    period_days: int = 30,
    client_id: str = "client-001",
) -> Any | None:
    """N일 전 시점 이전의 가장 최근 스냅샷 조회 — period_change_pct 계산용.

    정확히 N일 전 스냅샷이 없을 수 있으므로, (오늘 - N일) 이하 날짜 중 가장 최근을 선택.
    """
    from datetime import date, timedelta

    from sqlalchemy import desc

    from app.db.models import PortfolioSnapshot

    anchor = date.today() - timedelta(days=period_days)
    result = await session.execute(
        select(PortfolioSnapshot)
        .where(
            PortfolioSnapshot.user_id == user_id,
            PortfolioSnapshot.client_id == client_id,
            PortfolioSnapshot.snapshot_date <= anchor,
        )
        .order_by(desc(PortfolioSnapshot.snapshot_date))
        .limit(1)
    )
    return result.scalar_one_or_none()
