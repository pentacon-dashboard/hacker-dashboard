"""Copilot Planner 스키마.

sprint-01: NL Query Planner — CopilotPlan, CopilotStep, GatePolicy 정의.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# 9개 허용 에이전트 리터럴 (plan.md / contract.md 기준)
CopilotStepAgent = Literal[
    "stock",
    "crypto",
    "fx",
    "macro",
    "portfolio",
    "rebalance",
    "comparison",
    "simulator",
    "news-rag",
]


class GatePolicy(BaseModel):
    """각 step 에 적용할 3단 게이트 정책.

    `schema` 는 Pydantic BaseModel 의 클래스메서드명과 충돌하므로
    내부 필드명은 `schema_check` 를 사용하고 JSON alias 를 "schema" 로 유지한다.
    """

    model_config = ConfigDict(populate_by_name=True)

    schema_check: bool = Field(True, alias="schema")
    domain: bool = True
    critique: bool = True


class CopilotStep(BaseModel):
    """플랜의 단일 실행 단계."""

    step_id: str
    agent: CopilotStepAgent
    inputs: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    gate_policy: GatePolicy = Field(default_factory=lambda: GatePolicy.model_validate({"schema": True}))


class CopilotPlan(BaseModel):
    """자연어 질의로부터 생성된 멀티-스텝 에이전트 실행 계획.

    POST /copilot/plan 응답 스키마로도 사용됨.
    gate_results 는 3단 게이트 통과 여부 (옵션 필드).
    """

    plan_id: str
    session_id: str
    steps: list[CopilotStep]
    created_at: str  # ISO 8601 문자열
    gate_results: dict[str, str] = Field(
        default_factory=dict,
        description="schema/domain/critique gate 통과 여부",
    )


class CopilotPlanRequest(BaseModel):
    """POST /copilot/plan 요청 본문."""

    query: str = Field(..., description="자연어 질의", min_length=1)
    session_id: str | None = Field(default=None, description="기존 세션 ID (옵션)")


# 하위 호환 alias — 내부 모듈이 CopilotPlanResponse 를 참조하는 경우를 위해 유지
CopilotPlanResponse = CopilotPlan
