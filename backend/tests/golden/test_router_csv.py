"""
CSV 업로드 Router heuristic 회귀 테스트 (Week-4 Task #16).

목적:
- CSV 업로드 래퍼(`{"rows":[...], "columns":[...], "source":"csv_upload"}`) 가
  오면 router heuristic 이 LLM 호출 없이 자산군을 결정해야 한다.
- 4종 신규 샘플(crypto/stock/portfolio/mixed) 에 대해 결정률 100% 검증.
- router 가 downstream 으로 전달하는 state 의 `input_data` 는 언래핑된 실제
  rows 여야 한다 (analyzer 호환).
"""

from __future__ import annotations

from typing import Any

import pytest

from app.agents import llm as llm_module
from app.agents.router import (
    _is_csv_upload_wrapper,
    _unwrap_csv_upload,
    heuristic_classify,
    router_node,
)

CSV_SAMPLES = [
    "csv_upload_crypto",
    "csv_upload_stock_kr",
    "csv_upload_portfolio",
    "csv_upload_mixed",
]


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


# ─────────── heuristic pure-function tests ───────────


def test_csv_wrapper_detection() -> None:
    rows = [{"rows": [{"a": 1}], "columns": ["a"], "source": "csv_upload"}]
    assert _is_csv_upload_wrapper(rows) is True


def test_csv_wrapper_unwrap() -> None:
    rows = [
        {
            "rows": [{"symbol": "AAPL", "close": 1}],
            "columns": ["symbol", "close"],
            "source": "csv_upload",
        }
    ]
    inner, cols = _unwrap_csv_upload(rows)
    assert inner == [{"symbol": "AAPL", "close": 1}]
    assert cols == ["symbol", "close"]


def test_heuristic_csv_crypto() -> None:
    rows = [
        {
            "rows": [
                {"symbol": "KRW-BTC", "close": 95000000},
                {"symbol": "KRW-ETH", "close": 4200000},
            ],
            "columns": ["symbol", "close"],
            "source": "csv_upload",
        }
    ]
    ac, reason, _ = heuristic_classify(rows)
    assert ac == "crypto"
    assert "heuristic" in reason


def test_heuristic_csv_stock_kr() -> None:
    rows = [
        {
            "rows": [
                {"symbol": "005930.KS", "close": 74000},
                {"symbol": "000660.KS", "close": 155000},
            ],
            "columns": ["symbol", "close"],
            "source": "csv_upload",
        }
    ]
    ac, reason, _ = heuristic_classify(rows)
    assert ac == "stock"
    assert "heuristic" in reason


def test_heuristic_csv_portfolio() -> None:
    rows = [
        {
            "rows": [
                {
                    "market": "yahoo",
                    "code": "AAPL",
                    "quantity": 10,
                    "avg_cost": 150,
                    "currency": "USD",
                },
                {
                    "market": "upbit",
                    "code": "KRW-BTC",
                    "quantity": 0.05,
                    "avg_cost": 50000000,
                    "currency": "KRW",
                },
            ],
            "columns": ["market", "code", "quantity", "avg_cost", "currency"],
            "source": "csv_upload",
        }
    ]
    ac, reason, _ = heuristic_classify(rows)
    assert ac == "portfolio"
    assert "heuristic" in reason


def test_heuristic_csv_mixed() -> None:
    rows = [
        {
            "rows": [
                {"symbol": "AAPL", "close": 180},
                {"symbol": "KRW-BTC", "close": 92000000},
            ],
            "columns": ["symbol", "close"],
            "source": "csv_upload",
        }
    ]
    ac, reason, _ = heuristic_classify(rows)
    assert ac == "mixed"
    assert "heuristic" in reason


def test_heuristic_csv_empty_patterns_falls_back() -> None:
    """CSV 업로드이지만 아무 패턴도 없으면 LLM 위임."""
    rows = [
        {
            "rows": [{"random_col": "blob"}],
            "columns": ["random_col"],
            "source": "csv_upload",
        }
    ]
    ac, reason, _ = heuristic_classify(rows)
    assert ac is None
    assert "LLM" in reason


# ─────────── router_node end-to-end ───────────


@pytest.mark.asyncio
@pytest.mark.parametrize("sample_id", CSV_SAMPLES)
async def test_router_csv_samples_heuristic_only(
    golden_samples: dict[str, dict[str, Any]],
    sample_id: str,
) -> None:
    """
    4종 CSV 샘플은 LLM 호출 없이 heuristic 으로 100% 결정되어야 한다.
    확인 방법: anthropic 클라이언트 주입 없이 실행 → LLM 경로로 가면 LLMUnavailableError.
    """
    # 안전망: 테스트 시작 시 DI 클라이언트 없음을 보장
    llm_module.set_client(None)

    sample = golden_samples[sample_id]
    state = _initial_state(sample)
    result = await router_node(state)  # type: ignore[arg-type]

    assert result["asset_class"] == sample["expected_asset_class"], (
        f"{sample_id}: expected {sample['expected_asset_class']}, "
        f"got {result['asset_class']} (reason={result['router_reason']})"
    )
    # heuristic 마커 필수
    assert "(heuristic)" in result["router_reason"], (
        f"{sample_id}: router_reason 에 heuristic 마커 누락: {result['router_reason']}"
    )
    # sample 의 기대 키워드도 포함
    assert sample["expected_router_reason_keyword"] in result["router_reason"]


@pytest.mark.asyncio
@pytest.mark.parametrize("sample_id", CSV_SAMPLES)
async def test_router_csv_unwraps_input_data(
    golden_samples: dict[str, dict[str, Any]],
    sample_id: str,
) -> None:
    """
    router 는 downstream 으로 언래핑된 실제 rows 를 넘겨야 한다 (analyzer 호환).
    """
    sample = golden_samples[sample_id]
    state = _initial_state(sample)
    result = await router_node(state)  # type: ignore[arg-type]

    unwrapped = result["input_data"]
    assert isinstance(unwrapped, list)
    assert unwrapped, "unwrapped input_data 는 비어있으면 안됨"
    # 첫 원소는 래퍼 구조가 아니어야 한다
    first = unwrapped[0]
    assert first.get("source") != "csv_upload"
    assert "rows" not in first or not isinstance(first.get("rows"), list)


@pytest.mark.asyncio
async def test_router_csv_coverage_summary(
    golden_samples: dict[str, dict[str, Any]],
) -> None:
    """
    커버리지 리포트: 4종 CSV 샘플 모두 heuristic 결정이어야 한다 → LLM 호출 0.
    """
    llm_module.set_client(None)

    decided_by_heuristic = 0
    for sample_id in CSV_SAMPLES:
        sample = golden_samples[sample_id]
        state = _initial_state(sample)
        result = await router_node(state)  # type: ignore[arg-type]
        if "(heuristic)" in result["router_reason"]:
            decided_by_heuristic += 1

    assert decided_by_heuristic == len(CSV_SAMPLES), (
        f"heuristic 결정률 {decided_by_heuristic}/{len(CSV_SAMPLES)} — 100% 필요"
    )
