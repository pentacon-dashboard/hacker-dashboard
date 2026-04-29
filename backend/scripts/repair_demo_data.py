"""Repair demo portfolio/watchlist data after malformed local inserts.

The script keeps existing demo holding row identities when possible and rewrites
unusable symbol/currency values into a coherent multi-asset portfolio.
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.core.config import settings  # noqa: E402
from app.db.models import Holding, WatchlistAlert  # noqa: E402
from app.services.portfolio import compute_summary  # noqa: E402

_USER_ID = "demo"
_CLIENT_ID = "client-001"

_HOLDING_SEEDS = [
    ("yahoo", "NVDA", "6", "850", "USD"),
    ("yahoo", "AAPL", "12", "180", "USD"),
    ("yahoo", "MSFT", "8", "420", "USD"),
    ("yahoo", "AMZN", "10", "170", "USD"),
    ("yahoo", "GOOGL", "9", "150", "USD"),
    ("yahoo", "META", "5", "480", "USD"),
    ("yahoo", "TSLA", "7", "220", "USD"),
    ("upbit", "KRW-BTC", "0.08", "85000000", "KRW"),
    ("upbit", "KRW-ETH", "1.2", "4600000", "KRW"),
    ("upbit", "KRW-XRP", "1200", "800", "KRW"),
    ("naver_kr", "005930", "80", "72000", "KRW"),
    ("naver_kr", "000660", "25", "135000", "KRW"),
    ("naver_kr", "035420", "20", "190000", "KRW"),
    ("naver_kr", "035720", "30", "52000", "KRW"),
]

_ALERT_SEEDS = [
    ("yahoo", "NVDA", "above", "900.0000"),
    ("upbit", "KRW-BTC", "below", "80000000.0000"),
    ("naver_kr", "005930", "above", "80000.0000"),
]

_FX_TO_KRW = {
    "KRW": Decimal("1"),
    "USD": Decimal("1350"),
    "USDT": Decimal("1350"),
}


def _seed_value_krw() -> Decimal:
    total = Decimal("0")
    for _market, _code, quantity, avg_cost, currency in _HOLDING_SEEDS:
        total += Decimal(quantity) * Decimal(avg_cost) * _FX_TO_KRW[currency]
    return total.quantize(Decimal("0.01"))


async def repair_holdings(session) -> int:
    result = await session.execute(
        select(Holding)
        .where(Holding.user_id == _USER_ID, Holding.client_id == _CLIENT_ID)
        .order_by(Holding.id)
    )
    rows = list(result.scalars().all())

    if not rows:
        now = datetime.now(UTC)
        for market, code, quantity, avg_cost, currency in _HOLDING_SEEDS:
            session.add(
                Holding(
                    user_id=_USER_ID,
                    client_id=_CLIENT_ID,
                    market=market,
                    code=code,
                    quantity=Decimal(quantity),
                    avg_cost=Decimal(avg_cost),
                    currency=currency,
                    created_at=now,
                    updated_at=now,
                )
            )
        return len(_HOLDING_SEEDS)

    now = datetime.now(UTC)
    for row, seed in zip(rows, _HOLDING_SEEDS, strict=False):
        market, code, quantity, avg_cost, currency = seed
        row.market = market
        row.code = code
        row.quantity = Decimal(quantity)
        row.avg_cost = Decimal(avg_cost)
        row.currency = currency
        row.updated_at = now

    for row in rows[len(_HOLDING_SEEDS) :]:
        market, code, quantity, avg_cost, currency = _HOLDING_SEEDS[-1]
        row.market = market
        row.code = code
        row.quantity = Decimal(quantity)
        row.avg_cost = Decimal(avg_cost)
        row.currency = currency
        row.updated_at = now

    return len(rows)


async def _current_portfolio_value(session) -> Decimal:
    result = await session.execute(
        select(Holding)
        .where(Holding.user_id == _USER_ID, Holding.client_id == _CLIENT_ID)
        .order_by(Holding.id)
    )
    rows = list(result.scalars().all())
    try:
        summary = await compute_summary(
            rows,
            user_id=_USER_ID,
            client_id=_CLIENT_ID,
            client_name="Client A",
        )
        return Decimal(summary.total_value_krw)
    except Exception:
        return _seed_value_krw()


async def repair_snapshots(session, baseline: Decimal) -> int:
    start = date.today() - timedelta(days=30)
    breakdown = json.dumps({"stock_us": "0.5600", "crypto": "0.2800", "stock_kr": "0.1600"})
    rows = 0

    for offset in range(31):
        snapshot_date = start + timedelta(days=offset)
        progress = Decimal(offset) / Decimal("30")
        value = (baseline * (Decimal("0.965") + progress * Decimal("0.035"))).quantize(
            Decimal("0.01")
        )
        pnl = (value - baseline).quantize(Decimal("0.01"))
        await session.execute(
            text(
                """
                INSERT INTO portfolio_snapshots
                    (user_id, client_id, snapshot_date, total_value_krw, total_pnl_krw,
                     asset_class_breakdown, holdings_detail)
                VALUES
                    (:user_id, :client_id, :snapshot_date, :value, :pnl,
                     CAST(:breakdown AS jsonb), '[]'::jsonb)
                ON CONFLICT (user_id, client_id, snapshot_date)
                DO UPDATE SET
                    total_value_krw = EXCLUDED.total_value_krw,
                    total_pnl_krw = EXCLUDED.total_pnl_krw,
                    asset_class_breakdown = EXCLUDED.asset_class_breakdown,
                    holdings_detail = EXCLUDED.holdings_detail
                """
            ),
            {
                "user_id": _USER_ID,
                "client_id": _CLIENT_ID,
                "snapshot_date": snapshot_date,
                "value": str(value),
                "pnl": str(pnl),
                "breakdown": breakdown,
            },
        )
        rows += 1
    return rows


async def repair_alerts(session) -> int:
    await session.execute(
        delete(WatchlistAlert).where(
            WatchlistAlert.user_id == _USER_ID,
            WatchlistAlert.client_id == _CLIENT_ID,
        )
    )
    now = datetime.now(UTC)
    for market, symbol, direction, threshold in _ALERT_SEEDS:
        session.add(
            WatchlistAlert(
                user_id=_USER_ID,
                client_id=_CLIENT_ID,
                market=market,
                symbol=symbol,
                direction=direction,
                threshold=Decimal(threshold),
                enabled=True,
                created_at=now,
            )
        )
    return len(_ALERT_SEEDS)


async def main() -> None:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        holdings = await repair_holdings(session)
        await session.flush()
        baseline = await _current_portfolio_value(session)
        snapshots = await repair_snapshots(session, baseline)
        alerts = await repair_alerts(session)
        await session.commit()
    await engine.dispose()
    print(f"repaired holdings={holdings} snapshots={snapshots} alerts={alerts}")


if __name__ == "__main__":
    asyncio.run(main())
