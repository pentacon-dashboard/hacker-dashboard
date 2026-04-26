# backend/tests/harness/sprint_analyzer_quality_contract.py (임시 파일, 하네스 종료 시 제거)
import json
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = REPO_ROOT / "backend"
GOLDEN_DIR = BACKEND_DIR / "tests" / "golden"
SAMPLES_DIR = GOLDEN_DIR / "samples"


def _run(cmd: list[str], cwd: Path = BACKEND_DIR) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


def test_three_gate_modules_present() -> None:
    """Schema / Domain / Critique 3단 게이트 모듈이 모두 존재해야 한다."""
    gates = BACKEND_DIR / "app" / "agents" / "gates"
    for name in ("schema.py", "domain.py", "critique.py"):
        assert (gates / name).exists(), f"3단 게이트 모듈 누락: {name}"


def test_router_decision_golden_regression() -> None:
    """Router 결정 회귀 테스트가 0 fail."""
    proc = _run(
        [
            "uv",
            "run",
            "pytest",
            "tests/golden/test_router_decisions.py",
            "tests/golden/test_router_csv.py",
            "tests/golden/test_router_portfolio_routing.py",
            "-v",
            "--tb=short",
        ]
    )
    assert proc.returncode == 0, (
        f"Router 골든 회귀 fail:\n{proc.stdout[-3000:]}\n{proc.stderr[-1000:]}"
    )


def test_three_gate_unit_tests_pass() -> None:
    """3단 게이트 단위 테스트(test_gates.py)가 0 fail."""
    proc = _run(["uv", "run", "pytest", "tests/golden/test_gates.py", "-v", "--tb=short"])
    assert proc.returncode == 0, f"gates 테스트 fail:\n{proc.stdout[-3000:]}\n{proc.stderr[-1000:]}"


def test_analyzer_chain_golden_regression() -> None:
    """Analyzer 골든 샘플 회귀 (LLM 응답은 respx fixture 로 고정)."""
    proc = _run(
        [
            "uv",
            "run",
            "pytest",
            "tests/golden/test_portfolio_analyzer.py",
            "tests/golden/test_mixed_analyzer.py",
            "tests/golden/test_copilot_analyzers.py",
            "tests/golden/test_copilot_end_to_end.py",
            "-v",
            "--tb=short",
        ]
    )
    assert proc.returncode == 0, (
        f"Analyzer 골든 회귀 fail:\n{proc.stdout[-3000:]}\n{proc.stderr[-1000:]}"
    )


def test_copilot_end_to_end_uses_respx_fixture() -> None:
    """test_copilot_end_to_end.py 가 respx fixture 를 적용하여 실 LLM 호출이 없어야 한다.

    CI 에 ANTHROPIC_API_KEY 가 없는 환경에서도 통과해야 함.
    """
    src = (GOLDEN_DIR / "test_copilot_end_to_end.py").read_text(encoding="utf-8")
    assert re.search(r"\brespx\b|respx_mock|httpx_mock", src), (
        "test_copilot_end_to_end.py 에 respx/httpx_mock fixture 미사용 — 실 LLM 호출 위험"
    )


def test_regression_diff_runner_clean() -> None:
    """test_regression_runner 가 골든 출력 vs 현재 출력 diff 0."""
    proc = _run(
        [
            "uv",
            "run",
            "pytest",
            "tests/golden/test_regression_runner.py",
            "tests/golden/test_rebalance_golden_runner.py",
            "-v",
            "--tb=short",
        ]
    )
    assert proc.returncode == 0, f"골든 diff 검출:\n{proc.stdout[-3000:]}\n{proc.stderr[-1000:]}"


def test_minimum_golden_sample_count() -> None:
    """규약(.claude/rules/conventions.md)상 골든 샘플 10종 이상 유지.

    samples/ 최상위 + samples/copilot/ 등 모든 하위 디렉토리 포함하여 집계.
    """
    samples = list(SAMPLES_DIR.rglob("*.json"))
    assert len(samples) >= 10, f"골든 샘플 {len(samples)}개 < 10. conventions.md 위반"


@pytest.mark.parametrize(
    "edge_sample",
    [
        "edge_critique_hallucinated.json",
        "edge_empty_input.json",
        "edge_future_date.json",
        "edge_negative_price.json",
    ],
)
def test_edge_case_samples_present(edge_sample: str) -> None:
    """3단 게이트의 fail 경로를 검증하는 edge 샘플이 모두 존재."""
    p = SAMPLES_DIR / edge_sample
    assert p.exists(), f"edge 샘플 누락: {edge_sample}"
    payload = json.loads(p.read_text(encoding="utf-8"))
    assert isinstance(payload, dict) and len(payload) > 0


def test_router_records_decision_rationale_in_state() -> None:
    """backend.md 규약: Router 가 결정 근거를 상태에 `router_reason` 키로 기록해야 한다.

    실제 router.py + state.py 가 사용하는 키는 `router_reason` (router.py L401/411/423/434,
    state.py L20 의 AgentState TypedDict). 이 키 이름이 사라지면 backend.md 규약 위반.
    """
    router_src = (BACKEND_DIR / "app" / "agents" / "router.py").read_text(encoding="utf-8")
    state_src = (BACKEND_DIR / "app" / "agents" / "state.py").read_text(encoding="utf-8")
    assert "router_reason" in router_src, (
        "router.py 가 router_reason 키를 사용하지 않음 — Router decision rationale 기록 규약 위반"
    )
    assert "router_reason" in state_src, "state.py AgentState 가 router_reason 필드를 선언하지 않음"
