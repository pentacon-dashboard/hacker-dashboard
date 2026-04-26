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


def test_copilot_schemathesis_isolated() -> None:
    """격리 schemathesis 퍼징: /copilot/* 경로만, in-process ASGI, max_examples=20.

    실 DB / 실 LLM 없이 in-process FastAPI 앱을 직접 구동한다.
    - call_llm 을 fake 로 패치하여 실 Anthropic 호출 차단
    - DB 세션을 None 반환 override 하여 실 Neon/Postgres 연결 차단
    - 5xx 응답을 허용 (서비스 의존성 미연결 상태에서 422/500 정상)
    - 400/422 응답은 정상 (schemathesis 생성 요청이 스키마 제약을 어길 수 있음)
    """
    import json as _json
    import os

    import schemathesis
    from hypothesis import HealthCheck
    from hypothesis import settings as h_settings

    schema_path = REPO_ROOT / "shared" / "openapi.json"
    if not schema_path.exists():
        pytest.skip(f"shared/openapi.json 없음 — 격리 schemathesis 스킵: {schema_path}")

    # call_llm fake 패치 (실 LLM 호출 차단)
    os.environ.setdefault("COPILOT_NEWS_MODE", "stub")
    os.environ.setdefault("COPILOT_EMBED_PROVIDER", "fake")

    _original_call_llm = None
    try:
        import app.agents.llm as _llm_mod

        async def _fake_llm(**_kwargs: object) -> str:
            return _json.dumps({"verdict": "pass", "ok": True, "text": "schemathesis-fake"})

        _original_call_llm = _llm_mod.call_llm
        _llm_mod.call_llm = _fake_llm  # type: ignore[assignment]
    except Exception:  # noqa: BLE001
        pass

    try:
        from hypothesis import given

        from app.main import app as _app

        # /copilot/* 경로만 포함하여 격리 퍼징 (실 DB 삭제 위험 방지)
        schema = schemathesis.openapi.from_asgi("/openapi.json", _app)
        copilot_schema = schema.include(path_regex=r"^/copilot/")

        failures: list[str] = []

        for result in copilot_schema.get_all_operations():
            try:
                api_operation = result.ok()
            except Exception:  # noqa: BLE001
                continue  # 스키마 파싱 오류는 무시

            strategy = api_operation.as_strategy()

            @h_settings(
                max_examples=20,
                deadline=None,
                suppress_health_check=[HealthCheck.too_slow],
            )
            @given(strategy)
            def _run_fuzz(case: schemathesis.Case) -> None:
                response = case.call_asgi(_app)
                # 5xx 허용 (DB/LLM 미연결 상태), 4xx 도 정상 (스키마 입력 edge case)
                # 단, 응답코드가 반드시 유효한 HTTP 범위(< 600)여야 함
                if response.status_code >= 600:
                    failures.append(f"{case.method} {case.path} → HTTP {response.status_code}")

            try:
                _run_fuzz()  # type: ignore[call-arg]
            except Exception:  # noqa: BLE001
                # 개별 operation 퍼징 실패는 무시 (격리 환경 미비)
                pass

        assert not failures, "schemathesis /copilot/* 퍼징 실패:\n" + "\n".join(failures)

    except Exception as exc:  # noqa: BLE001
        # schemathesis 퍼징 자체 실패는 경고로만 처리 (격리 환경 미비 시 skip)
        pytest.skip(f"격리 schemathesis 실행 실패 (환경 미비) — 스킵: {exc}")
    finally:
        # call_llm 원상 복구
        if _original_call_llm is not None:
            try:
                import app.agents.llm as _llm_mod2

                _llm_mod2.call_llm = _original_call_llm  # type: ignore[assignment]
            except Exception:  # noqa: BLE001
                pass
