"""
Market analysis stub 픽스처 — Sprint-08 B-4.

deterministic seed 기반. 테스트에서도 직접 import 가능.
"""

from __future__ import annotations

import math


def _sparkline(seed: int, base: float = 100.0) -> list[float]:
    """deterministic 7일 스파크라인 생성."""
    result: list[float] = []
    for i in range(7):
        offset = math.sin(i * 0.9 + seed * 0.07) * base * 0.025
        noise = ((seed * (i + 3)) % 13 - 6) * base * 0.003
        result.append(round(base + offset + noise, 2))
    return result


INDEX_SNAPSHOTS = [
    {
        "ticker": "^KS11",
        "display_name": "KOSPI",
        "value": "2,631.45",
        "change_pct": "+0.82",
        "change_abs": "+21.34",
        "sparkline_7d": _sparkline(1, 2631.45),
    },
    {
        "ticker": "^KQ11",
        "display_name": "KOSDAQ",
        "value": "864.12",
        "change_pct": "+1.24",
        "change_abs": "+10.57",
        "sparkline_7d": _sparkline(2, 864.12),
    },
    {
        "ticker": "^GSPC",
        "display_name": "S&P 500",
        "value": "5,298.71",
        "change_pct": "+0.45",
        "change_abs": "+23.88",
        "sparkline_7d": _sparkline(3, 5298.71),
    },
    {
        "ticker": "^IXIC",
        "display_name": "NASDAQ",
        "value": "16,742.39",
        "change_pct": "+0.78",
        "change_abs": "+129.45",
        "sparkline_7d": _sparkline(4, 16742.39),
    },
    {
        "ticker": "^DJI",
        "display_name": "DOW Jones",
        "value": "39,234.56",
        "change_pct": "-0.12",
        "change_abs": "-47.12",
        "sparkline_7d": _sparkline(5, 39234.56),
    },
    {
        "ticker": "^VIX",
        "display_name": "VIX (공포 지수)",
        "value": "14.23",
        "change_pct": "-3.41",
        "change_abs": "-0.50",
        "sparkline_7d": _sparkline(6, 14.23),
    },
    {
        "ticker": "USDKRW",
        "display_name": "USD/KRW",
        "value": "1,352.40",
        "change_pct": "+0.23",
        "change_abs": "+3.10",
        "sparkline_7d": _sparkline(7, 1352.40),
    },
]

SECTOR_KPIS = [
    {
        "name": "정보기술",
        "change_pct": "+1.82",
        "constituents": 75,
        "leaders": ["AAPL", "MSFT", "NVDA"],
    },
    {
        "name": "반도체",
        "change_pct": "+2.45",
        "constituents": 30,
        "leaders": ["NVDA", "AMD", "005930"],
    },
    {
        "name": "헬스케어",
        "change_pct": "+0.34",
        "constituents": 60,
        "leaders": ["JNJ", "PFE", "UNH"],
    },
    {"name": "금융", "change_pct": "-0.21", "constituents": 65, "leaders": ["JPM", "BAC", "GS"]},
    {
        "name": "임의소비재",
        "change_pct": "+0.87",
        "constituents": 50,
        "leaders": ["AMZN", "TSLA", "HD"],
    },
    {
        "name": "필수소비재",
        "change_pct": "+0.12",
        "constituents": 38,
        "leaders": ["PG", "KO", "WMT"],
    },
    {"name": "에너지", "change_pct": "-1.05", "constituents": 28, "leaders": ["XOM", "CVX", "COP"]},
    {"name": "소재", "change_pct": "+0.56", "constituents": 25, "leaders": ["LIN", "APD", "SHW"]},
    {"name": "산업재", "change_pct": "+0.43", "constituents": 72, "leaders": ["HON", "MMM", "GE"]},
    {
        "name": "통신서비스",
        "change_pct": "+1.12",
        "constituents": 26,
        "leaders": ["GOOGL", "META", "VZ"],
    },
    {
        "name": "유틸리티",
        "change_pct": "-0.33",
        "constituents": 28,
        "leaders": ["NEE", "DUK", "SO"],
    },
]

COMMODITIES = [
    {
        "symbol": "CL=F",
        "name": "원유 (WTI)",
        "price": "81.23",
        "change_pct": "-0.87",
        "unit": "USD/bbl",
    },
    {"symbol": "GC=F", "name": "금", "price": "2,321.50", "change_pct": "+0.54", "unit": "USD/oz"},
    {"symbol": "SI=F", "name": "은", "price": "27.34", "change_pct": "+1.12", "unit": "USD/oz"},
    {"symbol": "HG=F", "name": "구리", "price": "4.42", "change_pct": "+0.78", "unit": "USD/lb"},
    {
        "symbol": "NG=F",
        "name": "천연가스",
        "price": "2.01",
        "change_pct": "-2.34",
        "unit": "USD/MMBtu",
    },
]

WORLD_HEATMAP = [
    {
        "country_code": "US",
        "country_name": "미국",
        "change_pct": "+0.45",
        "market_cap_usd": "$46.2T",
    },
    {
        "country_code": "CN",
        "country_name": "중국",
        "change_pct": "-0.34",
        "market_cap_usd": "$8.1T",
    },
    {
        "country_code": "JP",
        "country_name": "일본",
        "change_pct": "+0.92",
        "market_cap_usd": "$5.4T",
    },
    {
        "country_code": "KR",
        "country_name": "한국",
        "change_pct": "+0.82",
        "market_cap_usd": "$1.8T",
    },
    {
        "country_code": "GB",
        "country_name": "영국",
        "change_pct": "+0.23",
        "market_cap_usd": "$2.9T",
    },
    {
        "country_code": "DE",
        "country_name": "독일",
        "change_pct": "+0.61",
        "market_cap_usd": "$2.1T",
    },
    {
        "country_code": "FR",
        "country_name": "프랑스",
        "change_pct": "+0.48",
        "market_cap_usd": "$2.8T",
    },
    {
        "country_code": "CA",
        "country_name": "캐나다",
        "change_pct": "+0.31",
        "market_cap_usd": "$2.4T",
    },
    {
        "country_code": "AU",
        "country_name": "호주",
        "change_pct": "+0.17",
        "market_cap_usd": "$1.6T",
    },
    {
        "country_code": "IN",
        "country_name": "인도",
        "change_pct": "+1.43",
        "market_cap_usd": "$3.9T",
    },
    {
        "country_code": "BR",
        "country_name": "브라질",
        "change_pct": "-0.56",
        "market_cap_usd": "$0.7T",
    },
    {
        "country_code": "RU",
        "country_name": "러시아",
        "change_pct": "-1.12",
        "market_cap_usd": "$0.3T",
    },
    {
        "country_code": "ZA",
        "country_name": "남아공",
        "change_pct": "+0.67",
        "market_cap_usd": "$0.3T",
    },
    {
        "country_code": "MX",
        "country_name": "멕시코",
        "change_pct": "+0.33",
        "market_cap_usd": "$0.4T",
    },
    {
        "country_code": "SG",
        "country_name": "싱가포르",
        "change_pct": "+0.54",
        "market_cap_usd": "$0.7T",
    },
    {
        "country_code": "HK",
        "country_name": "홍콩",
        "change_pct": "+1.23",
        "market_cap_usd": "$3.2T",
    },
    {
        "country_code": "TW",
        "country_name": "대만",
        "change_pct": "+1.56",
        "market_cap_usd": "$1.9T",
    },
    {
        "country_code": "SE",
        "country_name": "스웨덴",
        "change_pct": "+0.22",
        "market_cap_usd": "$0.9T",
    },
    {
        "country_code": "CH",
        "country_name": "스위스",
        "change_pct": "+0.43",
        "market_cap_usd": "$1.8T",
    },
    {
        "country_code": "NL",
        "country_name": "네덜란드",
        "change_pct": "+0.35",
        "market_cap_usd": "$1.1T",
    },
]
