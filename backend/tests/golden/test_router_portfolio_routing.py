"""
Router 의 portfolio/macro/mixed 라우팅 회귀 테스트.
- holdings 배열(market/code/quantity/avg_cost 포함) → portfolio
- CPI/GDP 키워드 컬럼 → macro
- 쿼리에 '소비자물가' → macro
- stock + crypto 티커 혼합 → mixed
"""
from __future__ import annotations

from typing import Any

import pytest

from app.agents.router import heuristic_classify, router_node


def _initial(rows: list[dict[str, Any]], query: str | None = None, hint: str | None = None) -> dict[str, Any]:
    return {
        "input_data": rows,
        "query": query,
        "asset_class_hint": hint,
        "asset_class": "",
        "router_reason": "",
        "analyzer_output": None,
        "gates": {"schema_gate": "pending", "domain_gate": "pending", "critique_gate": "pending"},
        "error": None,
    }


# ───────── heuristic_classify ─────────


def test_heuristic_detects_holdings() -> None:
    rows = [
        {"market": "upbit", "code": "KRW-BTC", "quantity": 1, "avg_cost": 50_000_000, "currency": "KRW"},
        {"market": "yahoo", "code": "AAPL", "quantity": 10, "avg_cost": 150, "currency": "USD"},
    ]
    ac, reason, _ = heuristic_classify(rows)
    assert ac == "portfolio"
    assert "portfolio" in reason.lower()


def test_heuristic_distinguishes_ohlc_from_holdings() -> None:
    """OHLC 시계열은 portfolio 로 잘못 라우팅되면 안 된다."""
    rows = [
        {"symbol": "AAPL", "date": "2024-01-01", "open": 170, "high": 171, "low": 169, "close": 170.5, "volume": 1000000},
        {"symbol": "AAPL", "date": "2024-01-02", "open": 170, "high": 172, "low": 169, "close": 171.2, "volume": 900000},
    ]
    ac, _reason, _ = heuristic_classify(rows)
    assert ac == "stock"


def test_heuristic_macro_from_query() -> None:
    rows = [{"date": "2024-01-01", "value": 3.1}]
    ac, _reason, _ = heuristic_classify(rows, query="CPI 소비자물가 해석해줘")
    assert ac == "macro"


# ───────── router_node (end-to-end) ─────────


@pytest.mark.asyncio
async def test_router_routes_portfolio() -> None:
    rows = [
        {"market": "upbit", "code": "KRW-BTC", "quantity": 1, "avg_cost": 50_000_000, "currency": "KRW"},
        {"market": "upbit", "code": "KRW-ETH", "quantity": 1, "avg_cost": 3_000_000, "currency": "KRW"},
    ]
    result = await router_node(_initial(rows))  # type: ignore[arg-type]
    assert result["asset_class"] == "portfolio"
    assert "portfolio" in result["router_reason"].lower()


@pytest.mark.asyncio
async def test_router_routes_macro_via_column() -> None:
    rows = [
        {"date": "2024-01-01", "cpi": 3.0},
        {"date": "2024-02-01", "cpi": 3.1},
    ]
    result = await router_node(_initial(rows))  # type: ignore[arg-type]
    assert result["asset_class"] == "macro"


@pytest.mark.asyncio
async def test_router_routes_mixed_from_tickers() -> None:
    rows = [
        {"symbol": "AAPL", "close": 180},
        {"symbol": "KRW-BTC", "close": 60_000_000},
        {"symbol": "USDKRW=X", "rate": 1350},
    ]
    result = await router_node(_initial(rows))  # type: ignore[arg-type]
    assert result["asset_class"] == "mixed"


@pytest.mark.asyncio
async def test_router_respects_portfolio_hint() -> None:
    rows = [{"symbol": "AAPL", "close": 180}]  # stock 이지만 hint 우선
    result = await router_node(_initial(rows, hint="portfolio"))  # type: ignore[arg-type]
    assert result["asset_class"] == "portfolio"
    assert "hint" in result["router_reason"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "sample_id",
    [
        "portfolio_balanced",
        "portfolio_concentrated",
        "portfolio_multi_currency",
        "macro_cpi",
        "mixed_stock_crypto",
    ],
)
async def test_router_matches_expected_for_new_samples(
    golden_samples: dict[str, dict[str, Any]],
    sample_id: str,
) -> None:
    sample = golden_samples[sample_id]
    rows = sample["input"]["data"]
    query = sample["input"].get("query")
    result = await router_node(_initial(rows, query=query))  # type: ignore[arg-type]
    assert result["asset_class"] == sample["expected_asset_class"]
    assert sample["expected_router_reason_keyword"] in result["router_reason"]
