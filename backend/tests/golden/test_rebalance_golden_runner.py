"""
리밸런싱 전용 골든 샘플 회귀 러너.

samples/rebalance_*.json 을 RebalanceAnalyzer.analyze() 에 직접 투입하고
기대 조건(headline_contains_any, must_include/not_include_codes, confidence_range 등)
을 검증한다.

프롬프트 변경 시 이 테스트가 통과해야 PR 허용 (.claude/agents/analyzer-designer.md).
"""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from app.agents.analyzers.rebalance import RebalanceAnalyzer
from app.schemas.rebalance import (
    LLMAnalysis,
    RebalanceAction,
    RebalanceConstraints,
    TargetAllocation,
)

_SAMPLES_DIR = Path(__file__).parent / "samples"

_OUT_PATH = Path(__file__).parent / "_last_rebalance_run.json"


def _load_rebalance_samples() -> list[tuple[str, dict[str, Any]]]:
    out: list[tuple[str, dict[str, Any]]] = []
    for path in sorted(_SAMPLES_DIR.glob("rebalance_*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        out.append((data["id"], data))
    return out


_SAMPLES = _load_rebalance_samples()


def _build_inputs(sample: dict[str, Any]) -> dict[str, Any]:
    inp = sample["input"]
    actions = [RebalanceAction(**a) for a in inp.get("actions", [])]
    target = TargetAllocation(**inp["target_allocation"])
    constraints = RebalanceConstraints(**inp["constraints"])
    drift = {k: float(v) for k, v in inp.get("drift", {}).items()}
    current = {k: float(v) for k, v in inp.get("current_allocation", {}).items()}
    target_dict = {k: float(v) for k, v in inp.get("target_allocation", {}).items()}
    return {
        "actions": actions,
        "drift": drift,
        "current_allocation": current,
        "target_allocation": target,
        "constraints": constraints,
        "target_dict": target_dict,
    }


def _verify_expected(
    *,
    sid: str,
    expected: dict[str, Any],
    actions: list[RebalanceAction],
    analysis: LLMAnalysis,
) -> None:
    """sample.expected 블록 조건 하나씩 검증."""
    # headline_contains_any
    if "headline_contains_any" in expected:
        options = expected["headline_contains_any"]
        assert any(opt in analysis.headline for opt in options), (
            f"{sid}: headline '{analysis.headline}' 에 기대 키워드 중 아무것도 없음 {options}"
        )

    # narrative_must_include_codes
    must_include = expected.get("narrative_must_include_codes", [])
    for code in must_include:
        assert code in analysis.narrative, (
            f"{sid}: narrative 에 필수 코드 '{code}' 누락. narrative={analysis.narrative!r}"
        )

    # narrative_must_not_include_codes
    must_not = expected.get("narrative_must_not_include_codes", [])
    for code in must_not:
        assert code not in analysis.narrative, (
            f"{sid}: narrative 에 금지 코드 '{code}' 포함됨. narrative={analysis.narrative!r}"
        )

    # warnings count bounds
    wmin = expected.get("warnings_min_count", 0)
    wmax = expected.get("warnings_max_count", 100)
    assert wmin <= len(analysis.warnings) <= wmax, (
        f"{sid}: warnings 개수 {len(analysis.warnings)} 가 [{wmin}, {wmax}] 범위 밖"
    )

    # confidence_range
    if "confidence_range" in expected:
        lo, hi = expected["confidence_range"]
        assert lo <= analysis.confidence <= hi, (
            f"{sid}: confidence {analysis.confidence} 가 [{lo}, {hi}] 범위 밖"
        )

    # forbidden_terms
    for term in expected.get("forbidden_terms", []):
        combined = f"{analysis.headline} {analysis.narrative} {' '.join(analysis.warnings)}"
        assert term not in combined, (
            f"{sid}: 금지어 '{term}' 가 응답에 포함됨"
        )


def _prime_llm_for_sample(fake_client, sample: dict[str, Any]) -> None:
    """fake_client 의 'analyzer' 라우트에 샘플의 mock_analyzer_output 을 등록.

    RebalanceAnalyzer 의 프롬프트는 `Rebalance Analyzer` 라는 헤더를 쓰는데, conftest 의
    _detect_route 에는 해당 매칭이 아직 없다 → route 가 'unknown' 으로 빠지고 fallback {} 반환.
    여기서 'unknown' 라우트에 응답을 심어 LLM 호출을 우회한다.
    """
    fake_client.responses.clear()
    mock = sample.get("mock_analyzer_output")
    if mock is not None:
        # analyzer / unknown 둘 다 같은 응답 반환 (route 분류 휴리스틱 안정성 위해)
        fake_client.responses["analyzer"] = mock
        fake_client.responses["unknown"] = mock


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "sid,sample",
    _SAMPLES,
    ids=[sid for sid, _ in _SAMPLES] if _SAMPLES else ["no_samples"],
)
async def test_rebalance_golden_sample(
    sid: str,
    sample: dict[str, Any],
    fake_client,
) -> None:
    inputs = _build_inputs(sample)
    expected = sample.get("expected", {})
    shortcut = bool(expected.get("shortcut"))

    _prime_llm_for_sample(fake_client, sample)

    analyzer = RebalanceAnalyzer()
    analysis, gates = await analyzer.analyze(
        actions=inputs["actions"],
        drift=inputs["drift"],
        current_allocation=inputs["current_allocation"],
        target_allocation=inputs["target_allocation"],
        constraints=inputs["constraints"],
    )

    # shortcut 케이스: LLM 호출이 없어야 한다 (fake_client.calls 에 기록되지 않음).
    if shortcut:
        assert len(fake_client.calls) == 0, (
            f"{sid}: shortcut 이지만 LLM 이 호출됨: {fake_client.calls}"
        )

    # schema gate 기대값
    expected_gates = sample["expected_gates"]
    for gate_name, expected_status in expected_gates.items():
        actual = gates.get(gate_name, "missing")
        if expected_status == "pass":
            assert actual == "pass" or actual.startswith("warn:"), (
                f"{sid}: gate {gate_name} 기대 pass, 실제 '{actual}'"
            )
        else:
            # fail 기대의 경우 정확 매칭 (현재 샘플에는 없음)
            assert actual.startswith(expected_status), (
                f"{sid}: gate {gate_name} 기대 '{expected_status}', 실제 '{actual}'"
            )

    assert analysis is not None, f"{sid}: analysis 가 None 반환됨 (gates={gates})"

    _verify_expected(
        sid=sid,
        expected=expected,
        actions=inputs["actions"],
        analysis=analysis,
    )


@pytest.mark.asyncio
async def test_rebalance_golden_summary(fake_client) -> None:
    """전 리밸런싱 샘플의 실행 결과 스냅샷을 _last_rebalance_run.json 에 기록."""
    results: list[dict[str, Any]] = []
    analyzer = RebalanceAnalyzer()

    for sid, sample in _SAMPLES:
        _prime_llm_for_sample(fake_client, sample)
        inputs = _build_inputs(sample)
        analysis, gates = await analyzer.analyze(
            actions=inputs["actions"],
            drift=inputs["drift"],
            current_allocation=inputs["current_allocation"],
            target_allocation=inputs["target_allocation"],
            constraints=inputs["constraints"],
        )
        results.append(
            {
                "id": sid,
                "gates": gates,
                "headline": analysis.headline if analysis else None,
                "narrative": analysis.narrative if analysis else None,
                "warnings": analysis.warnings if analysis else None,
                "confidence": analysis.confidence if analysis else None,
            }
        )

    _OUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    # 3/3 통과율
    ok = sum(1 for r in results if r["gates"].get("schema_gate") == "pass")
    assert ok == len(results), f"schema_gate 통과율 {ok}/{len(results)}"
