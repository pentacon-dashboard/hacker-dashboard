"""sprint-01 acceptance — NL Query Planner.

하네스 임시 파일. 피처 병합 전에 `backend/tests/harness/` 디렉토리 전체를 제거한다.
본 파일은 이전 하네스 런이 남긴 베이스라인 그린 stub 을 **덮어쓴다**. 베이스라인 검증(
ruff/mypy/lint/typecheck/build/openapi-sync/golden)은 contract.md 의 AC-01-0
게이트 명령 묶음으로 Evaluator 가 직접 실행한다.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[3]


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=600)


# ---------- Fake LLM ---------------------------------------------------------

_FAKE_PLAN_COMPARISON: dict[str, Any] = {
    "plan_id": "p-fake-1",
    "session_id": "sess-fake-1",
    "created_at": "2026-04-22T00:00:00Z",
    "steps": [
        {
            "step_id": "s1",
            "agent": "portfolio",
            "inputs": {"holdings": []},
            "depends_on": [],
            "gate_policy": {"schema": True, "domain": True, "critique": True},
        },
        {
            "step_id": "s2",
            "agent": "comparison",
            "inputs": {"anchor": "AAPL", "k": 2},
            "depends_on": ["s1"],
            "gate_policy": {"schema": True, "domain": True, "critique": True},
        },
    ],
}

_FAKE_PLAN_SIMULATOR: dict[str, Any] = {
    "plan_id": "p-fake-2",
    "session_id": "sess-fake-2",
    "created_at": "2026-04-22T00:00:00Z",
    "steps": [
        {
            "step_id": "s1",
            "agent": "simulator",
            "inputs": {"asset": "BTC", "horizon_days": 365},
            "depends_on": [],
            "gate_policy": {"schema": True, "domain": True, "critique": True},
        }
    ],
}


async def _fake_call_llm(
    *,
    system_prompt_name: str,
    user_content: str,
    model: str = "gpt-4o-mini",
    max_tokens: int = 8192,
    temperature: float = 0.2,
) -> str:
    """결정론적 가짜 Planner LLM.

    - system_prompt_name == "copilot_planner_system" 일 때만 plan JSON 반환.
    - 그 외(예: critique gate 의 system prompt) 는 {"ok": true, "reason": ""} 반환.
    """
    if system_prompt_name == "copilot_planner_system":
        if "시뮬" in user_content or "simulator" in user_content.lower():
            return json.dumps(_FAKE_PLAN_SIMULATOR)
        return json.dumps(_FAKE_PLAN_COMPARISON)
    # critique gate 등 다른 LLM 호출이 있으면 통과시킨다
    return json.dumps({"ok": True, "reason": "fake"})


async def _fake_call_llm_unused_steps(
    *,
    system_prompt_name: str,
    user_content: str,
    model: str = "gpt-4o-mini",
    max_tokens: int = 8192,
    temperature: float = 0.2,
) -> str:
    """critique gate 가 verdict=fail(unused steps) 을 돌려주는 FakeClient.

    플랜 생성은 정상, critique gate 호출 시에는 verdict=fail 을 반환해
    unused steps 감지 경로를 테스트한다.
    """
    if system_prompt_name == "copilot_planner_system":
        # 첫 호출(plan 생성) — 질의와 무관하게 비교 플랜 반환
        parsed = json.loads(user_content) if user_content.startswith("{") else {}
        if "instruction" not in parsed:
            # 최초 plan 요청 (instruction 키 없음)
            return json.dumps(_FAKE_PLAN_COMPARISON)
    # critique gate 호출 — verdict=fail 로 "s2는 불필요" 시나리오 시뮬레이션
    return json.dumps({"verdict": "fail", "reason": "step s2 is unused for this query"})


@pytest.fixture
def fake_planner_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    """`backend.app.agents.llm.call_llm` 을 결정론적 FakeClient 로 교체.

    실 Anthropic 호출 경로를 차단해 ANTHROPIC_API_KEY 없이도 0 exit 로 통과시킨다.
    Generator 가 Planner 노드 내부에서 다른 심볼(예: `plan_agent._invoke_llm`)을
    경유한다면 아래 라인에 그 심볼을 추가로 monkeypatch 해야 한다.
    """
    monkeypatch.setattr("app.agents.llm.call_llm", _fake_call_llm, raising=True)
    # Planner 노드가 래퍼를 쓴다면 여기에 추가 monkeypatch 를 등록한다.
    # 예: monkeypatch.setattr("app.agents.planner.plan_agent._invoke_llm", _fake_call_llm)


# ---------- AC-01-1 / AC-01-3 tests -----------------------------------------


def test_copilot_plan_schema_importable() -> None:
    """Pydantic 모델이 정의되고 필수 필드를 가진다."""
    from app.schemas.copilot import CopilotPlan, CopilotStep, GatePolicy  # type: ignore

    step = CopilotStep(
        step_id="s1",
        agent="portfolio",
        inputs={"holdings": []},
        depends_on=[],
        gate_policy=GatePolicy(schema=True, domain=True, critique=True),
    )
    plan = CopilotPlan(
        plan_id="p1",
        session_id="sess-1",
        steps=[step],
        created_at="2026-04-22T00:00:00Z",
    )
    assert plan.steps[0].agent == "portfolio"
    assert plan.steps[0].gate_policy.critique is True


def test_copilot_plan_agent_literal_union() -> None:
    """agent 필드는 정확히 9개 리터럴만 허용한다(news-rag 는 하이픈 포함)."""
    from app.schemas.copilot import CopilotStep, GatePolicy  # type: ignore

    allowed = {
        "stock", "crypto", "fx", "macro",
        "portfolio", "rebalance",
        "comparison", "simulator", "news-rag",
    }
    assert len(allowed) == 9, "CopilotStepAgent must have exactly 9 literals"
    for name in allowed:
        CopilotStep(
            step_id="x",
            agent=name,
            inputs={},
            depends_on=[],
            gate_policy=GatePolicy(schema=True, domain=True, critique=True),
        )
    with pytest.raises(Exception):
        CopilotStep(
            step_id="x",
            agent="totally-unknown-agent",  # type: ignore[arg-type]
            inputs={},
            depends_on=[],
            gate_policy=GatePolicy(schema=True, domain=True, critique=True),
        )


def test_copilot_plan_route_exists_and_in_openapi() -> None:
    """`POST /copilot/plan` 이 openapi 에 등재되어야 한다."""
    from app.main import app  # type: ignore

    client = TestClient(app)
    spec = client.get("/openapi.json").json()
    assert "/copilot/plan" in spec["paths"], "missing /copilot/plan in openapi"
    assert "post" in spec["paths"]["/copilot/plan"], "POST method not declared"


def test_copilot_plan_returns_valid_dag(fake_planner_llm: None) -> None:
    """FakeClient DI 로 LLM 을 차단하고 plan 이 valid DAG 로 반환되는지 검증.

    - 실 Anthropic 호출 금지 (fake_planner_llm fixture 가 `call_llm` 을 교체).
    - ANTHROPIC_API_KEY 환경변수 없이도 0 exit 통과해야 한다.
    - 모든 step 의 agent 는 9개 리터럴 집합에 속해야 한다.
    - 모든 depends_on 은 동일 plan 의 다른 step_id 를 가리켜야 한다(dangling 금지).
    """
    from app.main import app  # type: ignore

    client = TestClient(app)
    resp = client.post(
        "/copilot/plan",
        json={"query": "내 포트폴리오에서 AAPL과 비슷한 규모 경쟁사 2개 비교해줘"},
    )
    assert resp.status_code == 200, resp.text
    plan = resp.json()
    assert "plan_id" in plan and "steps" in plan and "session_id" in plan
    assert len(plan["steps"]) >= 1
    seen = {s["step_id"] for s in plan["steps"]}
    allowed = {
        "stock", "crypto", "fx", "macro",
        "portfolio", "rebalance",
        "comparison", "simulator", "news-rag",
    }
    for s in plan["steps"]:
        for dep in s["depends_on"]:
            assert dep in seen, f"dangling dep {dep}"
        assert s["agent"] in allowed, f"illegal agent literal: {s['agent']}"


def test_copilot_plan_passes_three_gates(fake_planner_llm: None) -> None:
    """3단 게이트(schema/domain/critique) 모듈이 plan 경로에서 재사용 가능해야 한다.

    - 기존 `backend/app/agents/gates/` 의 schema/domain/critique 모듈 재사용 확인.
    - 본 스프린트에서는 모듈 import 가능성 + /copilot/plan 응답이 gate 를 통과한
      결과(200 + valid plan)로 돌아오는지만 검증한다.
    """
    from app.agents.gates import schema as schema_gate  # type: ignore
    from app.agents.gates import domain as domain_gate  # type: ignore
    from app.agents.gates import critique as critique_gate  # type: ignore

    for mod in (schema_gate, domain_gate, critique_gate):
        assert hasattr(mod, "__name__")

    from app.main import app  # type: ignore

    client = TestClient(app)
    resp = client.post(
        "/copilot/plan",
        json={"query": "비트코인 1년 시뮬레이션"},
    )
    assert resp.status_code == 200, resp.text


def test_critique_gate_detects_unused_steps(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-01-6 회귀: critique gate 가 verdict=fail(unused steps) 을 반환하면
    gate_results["critique"] 에 "fail" 이 기록되어야 한다 (plan 자체는 반환).

    stub LLM 이 critique 호출에 {"verdict": "fail", "reason": "step s2 is unused..."} 를
    반환하도록 monkeypatch 해 결정론적으로 fail 경로를 검증한다.
    """
    monkeypatch.setattr(
        "app.agents.llm.call_llm",
        _fake_call_llm_unused_steps,
        raising=True,
    )
    from app.main import app  # type: ignore

    client = TestClient(app)
    resp = client.post(
        "/copilot/plan",
        json={"query": "간단한 주식 질의"},
    )
    assert resp.status_code == 200, resp.text
    plan = resp.json()
    # plan 은 반환되어야 하고 (critique fail = degraded, not 4xx)
    assert "plan_id" in plan and "steps" in plan
    # gate_results 에 critique fail 이 기록되어야 한다
    gate_results = plan.get("gate_results", {})
    assert "critique" in gate_results, "gate_results must contain 'critique' key"
    assert "fail" in gate_results["critique"], (
        f"expected 'fail' in critique gate result, got: {gate_results['critique']!r}"
    )


def test_openapi_in_sync() -> None:
    """`python -m app.export_openapi` 결과가 shared/openapi.json 과 의미적으로 일치.

    WARNING 메모: export 인코딩 차이는 json.loads() 비교로 무시.
    """
    current = (REPO_ROOT / "shared/openapi.json").read_text(encoding="utf-8")
    result = _run(
        ["uv", "run", "python", "-m", "app.export_openapi"],
        cwd=REPO_ROOT / "backend",
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == json.loads(current), (
        "OpenAPI drift — sprint-01 에서 /copilot/plan 추가 후 재 export 필요"
    )
