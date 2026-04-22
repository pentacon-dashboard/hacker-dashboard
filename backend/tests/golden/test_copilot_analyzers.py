"""
골든 샘플 회귀 테스트 — sprint-03 Copilot Sub-agents (comparison / simulator / news-rag).

samples/copilot/_baseline_copilot_*.json 을 각 analyzer.run() 에 직접 투입하고
기대 gate_results 및 카드 타입을 검증한다.

결정론 보장:
  - comparison: 결정론적 fake 계산 (LLM 없이)
  - simulator:  결정론적 수학 계산
  - news-rag:   COPILOT_NEWS_MODE=stub + fixture corpus (fake embedding)
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

_SAMPLES_DIR = Path(__file__).parent / "samples" / "copilot"

os.environ.setdefault("COPILOT_NEWS_MODE", "stub")


def _load_copilot_samples() -> list[tuple[str, dict[str, Any]]]:
    out: list[tuple[str, dict[str, Any]]] = []
    for path in sorted(_SAMPLES_DIR.glob("_baseline_copilot_*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        out.append((data["id"], data))
    return out


_SAMPLES = _load_copilot_samples()


# ─────────────────────────────────────── helpers ────────────────────────────


def _make_step(sample: dict[str, Any]):
    """sample.step dict → CopilotStep."""
    from app.schemas.copilot import CopilotStep

    return CopilotStep.model_validate(sample["step"])


def _gate_matches(expected: dict[str, str], actual: dict[str, str]) -> bool:
    """기대값이 'skip' 이 아닌 항목만 비교한다."""
    for key, exp_val in expected.items():
        if exp_val == "skip":
            continue
        act_val = actual.get(key, "")
        if act_val != exp_val:
            return False
    return True


# ─────────────────────────────────── comparison ─────────────────────────────


def _load_comparison_samples() -> list[tuple[str, dict[str, Any]]]:
    return [(sid, s) for sid, s in _SAMPLES if s["agent"] == "comparison"]


@pytest.mark.parametrize("sample_id,sample", _load_comparison_samples())
def test_comparison_golden(sample_id: str, sample: dict[str, Any]) -> None:
    from app.agents.analyzers.comparison import run

    step = _make_step(sample)
    outcome = run(step)

    card = outcome["card"]
    gate_results = outcome["gate_results"]

    assert card["type"] == sample["expected_card_type"], (
        f"{sample_id}: card type mismatch. got={card['type']}"
    )
    assert _gate_matches(sample["expected_gate_results"], gate_results), (
        f"{sample_id}: gate mismatch. expected={sample['expected_gate_results']} "
        f"got={gate_results}"
    )
    if sample.get("expected_degraded") is True:
        assert card.get("degraded") is True, f"{sample_id}: expected degraded=True"
    elif sample.get("expected_degraded") is False:
        assert not card.get("degraded"), f"{sample_id}: expected degraded=False"

    if "expected_symbols" in sample:
        assert card["symbols"] == sample["expected_symbols"], (
            f"{sample_id}: symbol list mismatch"
        )


# ─────────────────────────────────── simulator ──────────────────────────────


def _load_simulator_samples() -> list[tuple[str, dict[str, Any]]]:
    return [(sid, s) for sid, s in _SAMPLES if s["agent"] == "simulator"]


@pytest.mark.parametrize("sample_id,sample", _load_simulator_samples())
def test_simulator_golden(sample_id: str, sample: dict[str, Any]) -> None:
    from app.agents.analyzers.simulator import run

    step = _make_step(sample)
    outcome = run(step)

    card = outcome["card"]
    gate_results = outcome["gate_results"]

    assert card["type"] == sample["expected_card_type"], (
        f"{sample_id}: card type mismatch. got={card['type']}"
    )
    assert _gate_matches(sample["expected_gate_results"], gate_results), (
        f"{sample_id}: gate mismatch. expected={sample['expected_gate_results']} "
        f"got={gate_results}"
    )
    if sample.get("expected_degraded") is True:
        assert card.get("degraded") is True, f"{sample_id}: expected degraded=True"
    elif sample.get("expected_degraded") is False:
        assert not card.get("degraded"), f"{sample_id}: expected degraded=False"

    if "expected_base_value" in sample:
        assert abs(card["base_value"] - sample["expected_base_value"]) < 1.0, (
            f"{sample_id}: base_value mismatch. expected={sample['expected_base_value']} "
            f"got={card['base_value']}"
        )
    if "expected_shocked_value" in sample:
        assert abs(card["shocked_value"] - sample["expected_shocked_value"]) < 1.0, (
            f"{sample_id}: shocked_value mismatch. expected={sample['expected_shocked_value']} "
            f"got={card['shocked_value']}"
        )
    if "expected_twr_change_pct" in sample:
        assert abs(card["twr_change_pct"] - sample["expected_twr_change_pct"]) < 0.5, (
            f"{sample_id}: twr_change_pct mismatch. expected={sample['expected_twr_change_pct']} "
            f"got={card['twr_change_pct']}"
        )


# ─────────────────────────────────── news-rag ───────────────────────────────


def _load_news_rag_samples() -> list[tuple[str, dict[str, Any]]]:
    return [(sid, s) for sid, s in _SAMPLES if s["agent"] == "news-rag"]


@pytest.mark.parametrize("sample_id,sample", _load_news_rag_samples())
def test_news_rag_golden(
    sample_id: str, sample: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("COPILOT_NEWS_MODE", "stub")

    from app.agents.analyzers.news_rag import run

    step = _make_step(sample)
    outcome = run(step)

    card = outcome["card"]
    gate_results = outcome["gate_results"]

    assert card["type"] == sample["expected_card_type"], (
        f"{sample_id}: card type mismatch. got={card['type']}"
    )
    assert _gate_matches(sample["expected_gate_results"], gate_results), (
        f"{sample_id}: gate mismatch. expected={sample['expected_gate_results']} "
        f"got={gate_results}"
    )
    if sample.get("expected_degraded") is True:
        assert card.get("degraded") is True, f"{sample_id}: expected degraded=True"
    elif sample.get("expected_degraded") is False:
        assert not card.get("degraded"), f"{sample_id}: expected degraded=False"

    min_cit = sample.get("expected_min_citations", 0)
    if min_cit > 0:
        actual_cit = len(card.get("citations", []))
        assert actual_cit >= min_cit, (
            f"{sample_id}: expected >= {min_cit} citations, got {actual_cit}"
        )
        for c in card["citations"]:
            assert c["source_url"].startswith(("http://", "https://")), (
                f"{sample_id}: citation source_url invalid: {c['source_url']}"
            )
