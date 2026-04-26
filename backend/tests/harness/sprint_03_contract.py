"""sprint-03 acceptance — comparison / simulator / news-rag sub-agents."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("name", ["comparison", "simulator", "news_rag"])
def test_subagent_module_importable(name: str) -> None:
    mod = importlib.import_module(f"app.agents.analyzers.{name}")
    assert hasattr(mod, "run"), f"{name} must expose run()"


def test_copilot_card_union_shape() -> None:
    from app.schemas.copilot import CopilotCard  # type: ignore

    # Pydantic v2 discriminator 확인
    schema = CopilotCard.model_json_schema()
    defs = schema.get("$defs", {})
    variants = schema.get("oneOf", schema.get("anyOf", []))
    kinds = set()
    for v in variants:
        # Pydantic v2 는 $ref 로 variants 를 참조하는 경우가 있으므로 resolve 한다
        if "$ref" in v:
            ref_key = v["$ref"].removeprefix("#/$defs/")
            v = defs.get(ref_key, v)
        if "properties" in v and "type" in v["properties"]:
            # Literal const in Pydantic v2 JSON schema
            t = (
                v["properties"]["type"].get("const")
                or v["properties"]["type"].get("enum", [None])[0]
            )
            if t:
                kinds.add(t)
    expected = {"text", "chart", "scorecard", "citation", "comparison_table", "simulator_result"}
    assert expected.issubset(kinds), f"missing variants: {expected - kinds}"


def test_news_rag_requires_citations(monkeypatch: pytest.MonkeyPatch) -> None:
    """news-rag 출력에 citations 가 없으면 schema gate 실패."""
    monkeypatch.setenv("COPILOT_NEWS_MODE", "stub")
    from app.agents.analyzers.news_rag import run  # type: ignore
    from app.schemas.copilot import CopilotStep, GatePolicy  # type: ignore

    step = CopilotStep(
        step_id="t",
        agent="news-rag",
        inputs={"query": "apple earnings", "symbols": ["AAPL"]},
        depends_on=[],
        gate_policy=GatePolicy(schema=True, domain=True, critique=True),
    )
    # FakeClient DI는 conftest.py가 담당. run() 은 게이트 결과 dict 를 반환해야 한다.
    outcome = run(step)
    assert outcome["gate_results"]["schema"] == "pass"
    assert len(outcome["card"]["citations"]) >= 1
    for c in outcome["card"]["citations"]:
        assert c["source_url"].startswith(("http://", "https://"))


def test_comparison_validates_symbols_domain(monkeypatch: pytest.MonkeyPatch) -> None:
    """comparison 은 존재하지 않는 심볼이 섞이면 domain gate 에서 degraded."""
    from app.agents.analyzers.comparison import run  # type: ignore
    from app.schemas.copilot import CopilotStep, GatePolicy  # type: ignore

    step = CopilotStep(
        step_id="t",
        agent="comparison",
        inputs={"symbols": ["AAPL", "DEFINITELY_NOT_A_SYMBOL_XYZ"]},
        depends_on=[],
        gate_policy=GatePolicy(schema=True, domain=True, critique=True),
    )
    outcome = run(step)
    assert outcome["gate_results"]["domain"] in ("fail", "retry")
    assert outcome["card"].get("degraded") is True


def test_simulator_bounds_input_assumptions() -> None:
    """시나리오 가정값이 ±99% 를 넘으면 domain gate 실패."""
    from app.agents.analyzers.simulator import run  # type: ignore
    from app.schemas.copilot import CopilotStep, GatePolicy  # type: ignore

    step = CopilotStep(
        step_id="t",
        agent="simulator",
        inputs={
            "holdings": [{"symbol": "AAPL", "quantity": 10, "avg_price": 180.0}],
            "shocks": {"AAPL": 5.0},  # +500% 는 비현실
        },
        depends_on=[],
        gate_policy=GatePolicy(schema=True, domain=True, critique=True),
    )
    outcome = run(step)
    assert outcome["gate_results"]["domain"] == "fail"


def test_graph_registers_exactly_three_new_nodes() -> None:
    from app.agents.graph import build_graph  # type: ignore

    g = build_graph()
    node_names = set(g.nodes.keys()) if hasattr(g, "nodes") else set()
    for need in ("comparison", "simulator", "news_rag"):
        assert need in node_names, f"node {need} not registered"


def test_golden_copilot_analyzers_green() -> None:
    """`pytest backend/tests/golden/test_copilot_analyzers.py` 가 diff=0 통과."""
    import subprocess

    result = subprocess.run(
        ["uv", "run", "pytest", "-q", "tests/golden/test_copilot_analyzers.py", "--tb=short"],
        cwd=REPO_ROOT / "backend",
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert result.returncode == 0, result.stdout + result.stderr
