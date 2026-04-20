"""
3단 게이트 회귀 테스트.

각 게이트가 독립적으로 의도대로 pass/fail 하는지 확인한다.
그리고 전체 파이프라인(build_graph) 통합 테스트로 golden sample 의
기대 gate 상태를 검증한다.
"""
from __future__ import annotations

from typing import Any

import pytest

from app.agents.gates import critique_gate, domain_gate, schema_gate
from app.agents.graph import build_graph


def _base_state(**overrides: Any) -> dict[str, Any]:
    state = {
        "input_data": [],
        "query": None,
        "asset_class_hint": None,
        "asset_class": "stock",
        "router_reason": "test",
        "analyzer_output": None,
        "gates": {
            "schema_gate": "pending",
            "domain_gate": "pending",
            "critique_gate": "pending",
        },
        "error": None,
    }
    state.update(overrides)
    return state


# ────────────────────────── Schema gate ─────────────────────────────


@pytest.mark.asyncio
async def test_schema_gate_passes_valid_output() -> None:
    output = {
        "asset_class": "stock",
        "summary": "테스트 요약",
        "highlights": ["h1"],
        "metrics": {"latest_close": 100},
        "evidence": [{"claim": "c", "rows": [0]}],
    }
    state = _base_state(analyzer_output=output)
    result = await schema_gate(state)  # type: ignore[arg-type]
    assert result["gates"]["schema_gate"] == "pass"


@pytest.mark.asyncio
async def test_schema_gate_fails_missing_summary(fake_client) -> None:
    # summary 누락 + 재시도도 실패하도록 fake_client 응답도 비어있게 유지
    fake_client.responses["analyzer"] = {"asset_class": "stock"}  # summary 없음
    output = {"asset_class": "stock"}
    state = _base_state(analyzer_output=output)
    result = await schema_gate(state)  # type: ignore[arg-type]
    assert result["gates"]["schema_gate"].startswith("fail")


@pytest.mark.asyncio
async def test_schema_gate_retries_with_correction(fake_client) -> None:
    """첫 출력이 불완전하면 교정 재시도로 복구된다."""
    # 교정 재시도 응답을 완전본으로 세팅
    fake_client.responses["analyzer"] = {
        "asset_class": "stock",
        "summary": "corrected",
        "highlights": [],
        "metrics": {},
        "evidence": [],
    }
    bad_output = {"asset_class": "stock"}  # summary 없음
    state = _base_state(analyzer_output=bad_output)
    result = await schema_gate(state)  # type: ignore[arg-type]
    assert result["gates"]["schema_gate"] == "pass"
    assert result["analyzer_output"]["summary"] == "corrected"


@pytest.mark.asyncio
async def test_schema_gate_rejects_parse_error() -> None:
    output = {"_parse_error": "bad json", "_raw": "not json"}
    state = _base_state(analyzer_output=output)
    result = await schema_gate(state)  # type: ignore[arg-type]
    assert result["gates"]["schema_gate"].startswith("fail")
    assert "parse error" in result["gates"]["schema_gate"]


# ────────────────────────── Domain gate ─────────────────────────────


@pytest.mark.asyncio
async def test_domain_gate_passes_valid_series() -> None:
    state = _base_state(
        input_data=[
            {"symbol": "AAPL", "date": "2024-01-01", "close": 180},
            {"symbol": "AAPL", "date": "2024-01-02", "close": 182},
        ],
        analyzer_output={
            "asset_class": "stock",
            "summary": "...",
            "highlights": [],
            "metrics": {"period_return_pct": 1.1},
            "evidence": [],
        },
    )
    result = await domain_gate(state)  # type: ignore[arg-type]
    assert result["gates"]["domain_gate"] == "pass"


@pytest.mark.asyncio
async def test_domain_gate_fails_negative_price() -> None:
    state = _base_state(
        input_data=[{"symbol": "AAPL", "close": -1.0}],
    )
    result = await domain_gate(state)  # type: ignore[arg-type]
    assert result["gates"]["domain_gate"].startswith("fail")
    assert "not positive" in result["gates"]["domain_gate"]


@pytest.mark.asyncio
async def test_domain_gate_fails_future_date() -> None:
    state = _base_state(
        input_data=[{"symbol": "AAPL", "date": "2099-01-01", "close": 180}],
    )
    result = await domain_gate(state)  # type: ignore[arg-type]
    assert result["gates"]["domain_gate"].startswith("fail")
    assert "future" in result["gates"]["domain_gate"]


@pytest.mark.asyncio
async def test_domain_gate_fails_nonmonotonic_dates() -> None:
    state = _base_state(
        input_data=[
            {"date": "2024-01-01", "close": 100},
            {"date": "2024-01-05", "close": 101},
            {"date": "2024-01-03", "close": 102},  # 뒤로 간다 → 비단조
        ],
    )
    result = await domain_gate(state)  # type: ignore[arg-type]
    assert result["gates"]["domain_gate"].startswith("fail")
    assert "monotonic" in result["gates"]["domain_gate"]


@pytest.mark.asyncio
async def test_domain_gate_fails_extreme_return() -> None:
    state = _base_state(
        input_data=[{"close": 100}, {"close": 200}],
        analyzer_output={
            "asset_class": "stock",
            "summary": "...",
            "highlights": [],
            "metrics": {"period_return_pct": 1500.0},  # 1000% 초과
            "evidence": [],
        },
    )
    result = await domain_gate(state)  # type: ignore[arg-type]
    assert result["gates"]["domain_gate"].startswith("fail")
    assert "1000%" in result["gates"]["domain_gate"]


@pytest.mark.asyncio
async def test_domain_gate_fails_asset_class_mismatch() -> None:
    state = _base_state(
        input_data=[{"close": 100}],
        asset_class="stock",
        analyzer_output={
            "asset_class": "crypto",
            "summary": "...",
            "highlights": [],
            "metrics": {},
            "evidence": [],
        },
    )
    result = await domain_gate(state)  # type: ignore[arg-type]
    assert result["gates"]["domain_gate"].startswith("fail")
    assert "mismatch" in result["gates"]["domain_gate"]


# ────────────────────────── Critique gate ───────────────────────────


@pytest.mark.asyncio
async def test_critique_gate_passes_supported(fake_client) -> None:
    fake_client.responses["critique"] = {
        "verdict": "pass",
        "per_claim": [{"claim": "c", "status": "supported"}],
        "reason": "all supported",
    }
    state = _base_state(
        input_data=[{"close": 100}],
        analyzer_output={
            "asset_class": "stock",
            "summary": "...",
            "highlights": [],
            "metrics": {},
            "evidence": [{"claim": "c", "rows": [0]}],
        },
    )
    result = await critique_gate(state)  # type: ignore[arg-type]
    assert result["gates"]["critique_gate"] == "pass"


@pytest.mark.asyncio
async def test_critique_gate_fails_hallucinated(fake_client) -> None:
    fake_client.responses["critique"] = {
        "verdict": "fail",
        "per_claim": [{"claim": "c", "status": "hallucinated"}],
        "reason": "입력에 없는 값 인용",
    }
    state = _base_state(
        input_data=[{"close": 100}],
        analyzer_output={
            "asset_class": "stock",
            "summary": "틀린 주장",
            "highlights": [],
            "metrics": {},
            "evidence": [{"claim": "c", "rows": [0]}],
        },
    )
    result = await critique_gate(state)  # type: ignore[arg-type]
    assert result["gates"]["critique_gate"].startswith("fail")
    assert "없는 값" in result["gates"]["critique_gate"]


@pytest.mark.asyncio
async def test_critique_gate_no_output_fails() -> None:
    state = _base_state(analyzer_output=None)
    result = await critique_gate(state)  # type: ignore[arg-type]
    assert result["gates"]["critique_gate"].startswith("fail")


@pytest.mark.asyncio
async def test_critique_gate_missing_verdict(fake_client) -> None:
    fake_client.responses["critique"] = {"per_claim": [], "reason": "..."}
    state = _base_state(
        analyzer_output={
            "asset_class": "stock",
            "summary": "s",
            "highlights": [],
            "metrics": {},
            "evidence": [],
        }
    )
    result = await critique_gate(state)  # type: ignore[arg-type]
    assert result["gates"]["critique_gate"].startswith("fail")
    assert "verdict" in result["gates"]["critique_gate"]


# ───────────────────── Full pipeline (graph) ────────────────────────


@pytest.mark.asyncio
async def test_pipeline_stock_kr(
    golden_samples: dict[str, dict[str, Any]],
    prime_client_from_sample,
) -> None:
    sample = golden_samples["stock_kr"]
    prime_client_from_sample(sample)

    graph = build_graph()
    initial = {
        "input_data": sample["input"]["data"],
        "query": sample["input"].get("query"),
        "asset_class_hint": None,
        "asset_class": "",
        "router_reason": "",
        "analyzer_output": None,
        "gates": {"schema_gate": "pending", "domain_gate": "pending", "critique_gate": "pending"},
        "error": None,
    }
    final = await graph.ainvoke(initial)

    assert final["asset_class"] == "stock"
    assert final["gates"]["schema_gate"] == "pass"
    assert final["gates"]["domain_gate"] == "pass"
    assert final["gates"]["critique_gate"] == "pass"


@pytest.mark.asyncio
async def test_pipeline_edge_negative_price_halts_at_domain(
    golden_samples: dict[str, dict[str, Any]],
    prime_client_from_sample,
) -> None:
    sample = golden_samples["edge_negative_price"]
    prime_client_from_sample(sample)

    graph = build_graph()
    initial = {
        "input_data": sample["input"]["data"],
        "query": None,
        "asset_class_hint": None,
        "asset_class": "",
        "router_reason": "",
        "analyzer_output": None,
        "gates": {"schema_gate": "pending", "domain_gate": "pending", "critique_gate": "pending"},
        "error": None,
    }
    final = await graph.ainvoke(initial)

    assert final["gates"]["schema_gate"] == "pass"
    assert final["gates"]["domain_gate"].startswith("fail")


@pytest.mark.asyncio
async def test_pipeline_edge_critique_hallucinated(
    golden_samples: dict[str, dict[str, Any]],
    prime_client_from_sample,
) -> None:
    sample = golden_samples["edge_critique_hallucinated"]
    prime_client_from_sample(sample)

    graph = build_graph()
    initial = {
        "input_data": sample["input"]["data"],
        "query": None,
        "asset_class_hint": None,
        "asset_class": "",
        "router_reason": "",
        "analyzer_output": None,
        "gates": {"schema_gate": "pending", "domain_gate": "pending", "critique_gate": "pending"},
        "error": None,
    }
    final = await graph.ainvoke(initial)

    assert final["gates"]["schema_gate"] == "pass"
    assert final["gates"]["domain_gate"] == "pass"
    assert final["gates"]["critique_gate"].startswith("fail")
