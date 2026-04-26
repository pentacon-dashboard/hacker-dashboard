"""Generate a 30-day mixed-asset portfolio CSV for dashboard demo."""
from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

OUT = Path(r"C:\Users\ehgus\Downloads\portfolio-sample-2026-04.csv")

ASSETS = [
    # asset_id, asset_type, start_price, daily_vol%, volume_base, currency, exchange, mcap_usd
    ("AAPL",     "stock",  185.20, 0.014,    60_000_000, "USD",  "NASDAQ", 2_890_000_000_000),
    ("TSLA",     "stock",  249.75, 0.035,   100_000_000, "USD",  "NASDAQ",   795_000_000_000),
    ("005930",   "stock",   71800, 0.015,    15_000_000, "KRW",  "KRX",      420_000_000_000),
    ("NVDA",     "stock",  495.80, 0.028,    45_000_000, "USD",  "NASDAQ", 1_220_000_000_000),
    ("KRW-BTC",  "crypto", 57_100_000, 0.030,       130, "KRW",  "Upbit",    850_000_000_000),
    ("USDT-ETH", "crypto", 2235.80, 0.032,     16_000,   "USDT", "Binance",  268_000_000_000),
    ("USDT-SOL", "crypto",   99.90, 0.045,    350_000,   "USDT", "Binance",   42_000_000_000),
]

START = date(2024, 1, 2)
DAYS = 30  # business-ish days (we'll skip weekends below)

def business_days(start: date, count: int) -> list[date]:
    out: list[date] = []
    cur = start
    while len(out) < count:
        if cur.weekday() < 5:  # Mon..Fri
            out.append(cur)
        cur += timedelta(days=1)
    return out

def gen_prices(start_price: float, vol: float, n: int, rng: random.Random) -> list[float]:
    """Geometric-ish random walk with mild drift."""
    prices: list[float] = []
    p = start_price
    for _ in range(n):
        drift = 0.0005  # +0.05% / day mild uptrend
        shock = rng.gauss(0, vol)
        p = max(p * (1 + drift + shock), start_price * 0.5)
        prices.append(p)
    return prices

def fmt_price(asset_id: str, asset_type: str, p: float) -> str:
    # 원화 기반 한국주식/KRW 코인은 정수, 나머지는 소수 둘째자리
    if asset_id == "005930" or asset_id == "KRW-BTC":
        return str(int(round(p)))
    return f"{p:.2f}"

def fmt_volume(base_vol: int, rng: random.Random) -> str:
    jitter = rng.uniform(0.6, 1.4)
    v = base_vol * jitter
    if v >= 1000:
        return str(int(v))
    return f"{v:.4f}"

def fmt_mcap(base_mcap: int, price: float, start_price: float) -> int:
    return int(base_mcap * (price / start_price))

def main() -> None:
    rng = random.Random(42)
    days = business_days(START, DAYS)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "asset_id", "asset_type", "date", "price", "volume",
            "currency", "exchange", "market_cap_usd",
        ])
        for aid, atype, sp, vol, base_vol, ccy, exch, base_mcap in ASSETS:
            prices = gen_prices(sp, vol, len(days), rng)
            for d, p in zip(days, prices):
                w.writerow([
                    aid, atype, d.isoformat(),
                    fmt_price(aid, atype, p),
                    fmt_volume(base_vol, rng),
                    ccy, exch, fmt_mcap(base_mcap, p, sp),
                ])

    size = OUT.stat().st_size
    rows = sum(1 for _ in OUT.open(encoding="utf-8-sig")) - 1
    print(f"OK: {OUT} ({size} bytes, {rows} rows, {len(ASSETS)} assets x {len(days)} days)")

if __name__ == "__main__":
    main()
