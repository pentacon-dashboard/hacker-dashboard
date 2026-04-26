from typing import Any, TypedDict


class GateState(TypedDict):
    schema_gate: str  # ok | fail | pending
    domain_gate: str  # ok | fail | pending
    critique_gate: str  # ok | fail | pending


class AgentState(TypedDict, total=False):
    """LangGraph 그래프 전역 상태 — 모든 노드가 이 dict 를 읽고 쓴다."""

    # Router 입력
    input_data: list[dict[str, Any]]
    query: str | None
    asset_class_hint: str | None

    # Router 출력
    asset_class: str  # stock | crypto | fx | macro | mixed | portfolio
    router_reason: str  # Router 가 선택한 이유

    # Analyzer 출력
    analyzer_output: dict[str, Any] | None

    # 3단 품질 게이트 상태
    gates: GateState

    # 에러 전파
    error: str | None

    # 포트폴리오 analyzer 용 — holdings 시계열(선택). BE 의 /portfolio/snapshots 응답 그대로.
    snapshots: list[dict[str, Any]] | None

    # 개인화 포트폴리오 컨텍스트 — include_portfolio_context=True 시 주입.
    # PortfolioContext.model_dump() 결과 또는 None.
    portfolio_context: dict[str, Any] | None

    # ── sprint-01: Copilot Planner 확장 키 (기존 키 변경 금지) ─────────────
    # plan.md AgentState 확장 명세 준수.
    # copilot_plan 은 CopilotPlan.model_dump() dict 로 직렬화해서 저장한다
    # (LangGraph StateGraph 가 런타임에 type_hints 를 resolve 하므로 순환 import 방지).
    copilot_plan: dict[str, Any] | None  # CopilotPlan.model_dump()
    copilot_step_results: dict[str, Any]  # step_id → CopilotCard.model_dump()
    copilot_session_id: str | None
    copilot_citations: list[dict[str, Any]]  # Citation list
    copilot_turn_id: str | None

    # ── sprint-05: follow-up 라우팅용 세션 컨텍스트 (WARN-1 해소) ─────────────
    # ActiveContext.model_dump() dict 로 저장 (순환 import 방지).
    # 최초 턴에는 None, follow-up 턴에는 ActiveContext dict.
    active_context: dict[str, Any] | None
