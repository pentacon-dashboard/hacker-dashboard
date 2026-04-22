"""Copilot API 라우터 — sprint-01: POST /copilot/plan, sprint-04: POST /copilot/query (SSE).

SSE 스트리밍(/copilot/query) 은 sprint-04 에서 추가.
포맷: data-only SSE (`data: {json}\\n\\n`), `event:` 라인 없음 (revision 2 결정).
"""
from __future__ import annotations

import uuid as _uuid
from typing import Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agents.planner import build_copilot_plan
from app.schemas.copilot import CopilotPlan, CopilotPlanRequest

router = APIRouter(prefix="/copilot", tags=["copilot"])


# ── POST /copilot/plan (sprint-01) ──────────────────────────────────────────


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


# ── POST /copilot/query (sprint-04) ─────────────────────────────────────────


class QueryRequest(BaseModel):
    """POST /copilot/query 요청 본문.

    `harness_step_delay_ms` (JSON 키: `_harness_step_delay_ms`):
    숨김 파라미터. OpenAPI 스키마 제외. 오케스트레이터가 각 step 진입 시
    `asyncio.sleep(delay_ms / 1000)` 으로 변환. 결정론적 병렬 테스트용.
    """

    query: str = Field(..., description="자연어 질의", min_length=1)
    session_id: str | None = Field(default=None, description="기존 세션 ID (옵션)")
    context: dict[str, Any] | None = Field(default=None, description="추가 컨텍스트 (옵션)")
    harness_step_delay_ms: int = Field(
        default=0,
        alias="_harness_step_delay_ms",
        description="[harness-only] 각 step 실행 전 지연 ms. 병렬 결정론적 테스트용.",
    )

    model_config = {
        "populate_by_name": True,
    }

    @classmethod
    def model_json_schema(cls, **kwargs: Any) -> dict[str, Any]:
        """OpenAPI 스키마에서 `_harness_step_delay_ms`(`harness_step_delay_ms`) 제거."""
        schema = super().model_json_schema(**kwargs)
        props = schema.get("properties", {})
        # alias '_harness_step_delay_ms' 또는 필드명 'harness_step_delay_ms' 제거
        for key in ("_harness_step_delay_ms", "harness_step_delay_ms"):
            props.pop(key, None)
        return schema


@router.post(
    "/query",
    summary="자연어 질의 → SSE 스트림",
    description=(
        "자연어 질의를 받아 멀티-스텝 에이전트 오케스트레이션을 실행하고 결과를 "
        "Server-Sent Events 로 스트리밍한다. "
        "각 이벤트는 `data: <JSON>\\n\\n` 포맷 (data-only SSE). "
        "JSON 은 CopilotEvent discriminated union."
    ),
    responses={
        200: {
            "content": {
                "text/event-stream": {
                    "schema": {"type": "string"},
                    "description": (
                        "Server-Sent Events. 각 이벤트는 `data: <JSON>\\n\\n` 포맷. "
                        "JSON 은 CopilotEvent discriminated union. "
                        "이벤트 타입: plan.ready | step.start | step.token | step.gate | "
                        "step.result | final.card | error | done"
                    ),
                }
            }
        }
    },
)
async def query_copilot(body: QueryRequest) -> StreamingResponse:
    """자연어 질의 → SSE 스트림 (data-only, `event:` 라인 없음).

    응답 헤더 `X-Copilot-Session-Id` 에 세션 ID 포함.
    session_id 미전송 시 UUID4 자동 생성.
    """
    from app.services.copilot.orchestrator import stream_copilot_query

    resolved_session_id = body.session_id or str(_uuid.uuid4())
    delay_ms = body.harness_step_delay_ms

    async def _gen():  # type: ignore[return]
        async for chunk in stream_copilot_query(
            query=body.query,
            session_id=resolved_session_id,
            context=body.context,
            harness_step_delay_ms=delay_ms,
        ):
            yield chunk

    return StreamingResponse(
        _gen(),
        media_type="text/event-stream",
        headers={
            "X-Copilot-Session-Id": resolved_session_id,
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
