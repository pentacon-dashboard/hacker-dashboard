"""
Router 결정률 회귀 테스트.

모든 golden sample 에 대해:
- router_node 가 기대 asset_class 를 결정하는가
- router_reason 에 기대 키워드가 포함되는가

결정적 heuristic 이 대부분을 커버하므로 LLM 호출은 최소화된다.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.agents.router import heuristic_classify, router_node


def _initial_state(sample: dict[str, Any]) -> dict[str, Any]:
    inp = sample["input"]
    return {
        "input_data": inp.get("data", []),
        "query": inp.get("query"),
        "asset_class_hint": None,
        "asset_class": "",
        "router_reason": "",
        "analyzer_output": None,
        "gates": {
            "schema_gate": "pending",
            "domain_gate": "pending",
            "critique_gate": "pending",
        },
        "error": None,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "sample_id",
    [
        "stock_kr",
        "stock_us",
        "crypto_upbit",
        "crypto_binance",
        "crypto_btcusd",
        "fx_usdkrw",
        "fx_eurusd",
        "mixed",
        "edge_negative_price",
        "edge_future_date",
        "edge_empty_input",
        "edge_critique_hallucinated",
    ],
)
async def test_router_classifies_all_samples(
    golden_samples: dict[str, dict[str, Any]],
    sample_id: str,
) -> None:
    sample = golden_samples[sample_id]
    state = _initial_state(sample)
    result = await router_node(state)  # type: ignore[arg-type]

    assert result["asset_class"] == sample["expected_asset_class"], (
        f"{sample_id}: expected {sample['expected_asset_class']}, "
        f"got {result['asset_class']} (reason={result['router_reason']})"
    )

    keyword = sample["expected_router_reason_keyword"]
    # "mixed" 는 키워드 자체가 reason 에 들어가므로 그대로 매칭
    assert keyword in result["router_reason"], (
        f"{sample_id}: expected keyword '{keyword}' in router_reason, got '{result['router_reason']}'"
    )


@pytest.mark.asyncio
async def test_router_respects_hint() -> None:
    """asset_class_hint 가 있으면 heuristic 보다 우선."""
    state = {
        "input_data": [{"symbol": "AAPL"}],
        "query": None,
        "asset_class_hint": "crypto",
        "asset_class": "",
        "router_reason": "",
        "analyzer_output": None,
        "gates": {"schema_gate": "pending", "domain_gate": "pending", "critique_gate": "pending"},
        "error": None,
    }
    result = await router_node(state)  # type: ignore[arg-type]
    assert result["asset_class"] == "crypto"
    assert "hint" in result["router_reason"]


@pytest.mark.asyncio
async def test_router_empty_rows_falls_back() -> None:
    """빈 입력은 LLM 위임 경로로 간다. fake_client 기본값으로 'stock' 반환."""
    state = {
        "input_data": [],
        "query": None,
        "asset_class_hint": None,
        "asset_class": "",
        "router_reason": "",
        "analyzer_output": None,
        "gates": {"schema_gate": "pending", "domain_gate": "pending", "critique_gate": "pending"},
        "error": None,
    }
    result = await router_node(state)  # type: ignore[arg-type]
    # 빈 입력은 heuristic 이 None 을 반환 → LLM 호출 시도 → fake client 가 없으면 'stock'
    assert result["asset_class"] in {"stock", "crypto", "fx", "macro", "mixed"}


def test_heuristic_classify_crypto() -> None:
    rows = [{"symbol": "KRW-BTC"}, {"symbol": "USDT-ETH"}]
    ac, reason, symbols = heuristic_classify(rows)
    assert ac == "crypto"
    assert "KRW-BTC" in symbols


def test_heuristic_classify_mixed() -> None:
    rows = [{"symbol": "005930.KS"}, {"symbol": "KRW-BTC"}]
    ac, reason, _ = heuristic_classify(rows)
    assert ac == "mixed"
    assert "mixed" in reason.lower()


def test_heuristic_classify_fx() -> None:
    rows = [{"symbol": "USDKRW=X"}]
    ac, _reason, _ = heuristic_classify(rows)
    assert ac == "fx"


def test_heuristic_classify_macro_columns() -> None:
    rows = [{"date": "2024-01-01", "cpi": 3.1, "gdp": 2.4}]
    ac, _reason, _ = heuristic_classify(rows)
    assert ac == "macro"


def test_heuristic_classify_unknown_returns_none() -> None:
    rows = [{"random": "blob"}]
    ac, _reason, _ = heuristic_classify(rows)
    assert ac is None
