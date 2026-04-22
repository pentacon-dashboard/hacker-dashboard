"""Copilot API 라우터 — sprint-01: POST /copilot/plan.

SSE 스트리밍(/copilot/query)은 sprint-04 범위이므로 이 파일에 stub 만 남긴다.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.agents.planner import build_copilot_plan
from app.schemas.copilot import CopilotPlan, CopilotPlanRequest

router = APIRouter(prefix="/copilot", tags=["copilot"])


@router.post(
    "/plan",
    response_model=CopilotPlan,
    summary="NL Query → CopilotPlan",
    description=(
        "자연어 질의를 받아 멀티-스텝 에이전트 실행 계획(CopilotPlan)을 반환한다. "
        "LLM(copilot_planner_system)이 plan을 생성하고 3단 게이트(schema/domain/critique)를 통과한 결과만 반환. "
        "SSE 스트리밍 없이 단일 JSON 응답 (디버그/테스트용)."
    ),
)
async def create_copilot_plan(body: CopilotPlanRequest) -> CopilotPlan:
    """자연어 질의 → CopilotPlan (no-stream JSON)."""
    return await build_copilot_plan(
        query=body.query,
        session_id=body.session_id,
    )
