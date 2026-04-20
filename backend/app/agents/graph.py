"""
LangGraph 오케스트레이션.
엣지(흐름): Router → Analyzer → SchemaGate → DomainGate → CritiqueGate → END

게이트 분기:
  schema_gate  → pass → domain_gate  / fail → END
  domain_gate  → pass → critique_gate / fail → END
  critique_gate → END (언제나)

노드 본체는 analyzer-designer 구현. 엣지 구조는 backend-engineer 가 소유.
"""
from __future__ import annotations

from typing import Literal

from langgraph.graph import END, StateGraph

from app.agents.analyzers import get_analyzer
from app.agents.gates import critique_gate, domain_gate, schema_gate
from app.agents.router import router_node
from app.agents.state import AgentState


async def analyzer_node(state: AgentState) -> AgentState:
    """asset_class 에 맞는 Analyzer 를 dispatch. 결과를 analyzer_output 에 병합."""
    analyzer = get_analyzer(state.get("asset_class") or "stock")
    try:
        output = await analyzer.run(state)
    except Exception as exc:  # noqa: BLE001 — 외부 LLM 경계
        # 분석 실패는 schema gate 가 걸러내도록 에러 플래그만 심음
        output = {
            "asset_class": analyzer.asset_class,
            "_analyzer_error": f"{type(exc).__name__}: {exc}",
        }
    return {**state, "analyzer_output": output}


def _route_after_gate(gate_name: str) -> object:
    """게이트 이름을 받아 분기 함수를 반환하는 팩토리."""

    def _route(state: AgentState) -> Literal["next", "end"]:
        status = state.get("gates", {}).get(gate_name, "fail")
        return "next" if isinstance(status, str) and status == "pass" else "end"

    _route.__name__ = f"route_after_{gate_name}"
    return _route


def build_graph() -> StateGraph:
    """컴파일된 그래프를 반환. API 레이어에서 ainvoke(state) 로 호출."""
    graph = StateGraph(AgentState)

    graph.add_node("router", router_node)
    graph.add_node("analyzer", analyzer_node)
    graph.add_node("schema_gate", schema_gate)
    graph.add_node("domain_gate", domain_gate)
    graph.add_node("critique_gate", critique_gate)

    graph.set_entry_point("router")
    graph.add_edge("router", "analyzer")
    graph.add_edge("analyzer", "schema_gate")

    # schema_gate: pass → domain_gate, fail → END
    graph.add_conditional_edges(
        "schema_gate",
        _route_after_gate("schema_gate"),
        {"next": "domain_gate", "end": END},
    )

    # domain_gate: pass → critique_gate, fail → END
    graph.add_conditional_edges(
        "domain_gate",
        _route_after_gate("domain_gate"),
        {"next": "critique_gate", "end": END},
    )

    # critique_gate: 결과에 관계없이 END
    graph.add_edge("critique_gate", END)

    return graph.compile()
