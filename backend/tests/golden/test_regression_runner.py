"""
프롬프트·게이트 변경 전후 **회귀 diff 스냅샷**.

전체 golden sample 을 파이프라인에 넣어 (asset_class, router_reason keyword,
gates 3개) 요약을 모아 검증한다. 프롬프트를 바꿀 때 이 테스트가 통과 못하면
PR 금지(룰: .claude/agents/analyzer-designer.md).

추가로 각 샘플 수행 결과를 `backend/tests/golden/_last_run.json` 에 기록해
육안 diff 가 쉽게 되도록 한다. CI 는 이 파일을 ignore.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.agents.graph import build_graph

_OUT_PATH = Path(__file__).parent / "_last_run.json"


def _initial(sample: dict[str, Any]) -> dict[str, Any]:
    inp = sample["input"]
    state: dict[str, Any] = {
        "input_data": inp.get("data", []),
        "query": inp.get("query"),
        "asset_class_hint": None,
        "asset_class": "",
        "router_reason": "",
        "analyzer_output": None,
        "gates": {"schema_gate": "pending", "domain_gate": "pending", "critique_gate": "pending"},
        "error": None,
    }
    # 선택적 포트폴리오 컨텍스트 주입 — Phase B 에서 추가된 골든 샘플에서 사용.
    # 없는 샘플에서는 기본값과 byte-identical 한 state 를 유지해야 한다.
    if "portfolio_context" in inp:
        state["portfolio_context"] = inp.get("portfolio_context")
    return state


def _gate_bucket(status: str) -> str:
    if status == "pass":
        return "pass"
    if status == "pending":
        return "pending"
    if status.startswith("fail"):
        return "fail"
    if status.startswith("pass"):  # 'pass: critique unavailable' 등 관용 케이스
        return "pass"
    return status


@pytest.mark.asyncio
async def test_regression_all_samples(
    golden_samples: dict[str, dict[str, Any]],
    prime_client_from_sample,
) -> None:
    graph = build_graph()
    results: list[dict[str, Any]] = []
    passes = 0
    non_edge_total = 0
    non_edge_pass = 0

    for sid, sample in sorted(golden_samples.items()):
        # 리밸런싱 샘플은 다른 파이프라인(RebalanceAnalyzer 직접 호출)을 쓰므로
        # analyzer 그래프 회귀 대상에서 제외한다. test_rebalance_golden_runner.py 가 담당.
        if sample.get("kind") == "rebalance" or sid.startswith("rebalance_"):
            continue
        prime_client_from_sample(sample)
        final = await graph.ainvoke(_initial(sample))

        actual_gates = {k: _gate_bucket(v) for k, v in final["gates"].items()}
        expected_gates = sample["expected_gates"]
        # 'pending' 기대값은 don't-care — 현재 그래프가 조건부 엣지 없이
        # 선형으로 모든 게이트를 실행하므로, 이전 게이트 실패 시 후속 게이트 결과는 무관
        gates_match = all(
            expected_gates[k] == "pending" or actual_gates[k] == expected_gates[k]
            for k in expected_gates
        )
        ok = (
            final["asset_class"] == sample["expected_asset_class"]
            and sample["expected_router_reason_keyword"] in final["router_reason"]
            and gates_match
        )

        is_edge = sid.startswith("edge_")
        if not is_edge:
            non_edge_total += 1
            if ok:
                non_edge_pass += 1
        if ok:
            passes += 1

        results.append(
            {
                "id": sid,
                "ok": ok,
                "actual_asset_class": final["asset_class"],
                "expected_asset_class": sample["expected_asset_class"],
                "actual_router_reason": final["router_reason"],
                "expected_router_reason_keyword": sample["expected_router_reason_keyword"],
                "actual_gates": actual_gates,
                "expected_gates": expected_gates,
            }
        )

    _OUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    # 전체 샘플이 기대대로 동작해야 한다 (엣지 케이스 포함)
    failed = [r for r in results if not r["ok"]]
    assert not failed, f"{len(failed)} samples failed regression: {[r['id'] for r in failed]}"

    # 비-엣지 통과율 95%+ 요구사항
    rate = non_edge_pass / non_edge_total if non_edge_total else 1.0
    assert rate >= 0.95, f"non-edge pass rate {rate:.2%} < 95%"
