"""Copilot API 라우터 — sprint-01: POST /copilot/plan, sprint-04: POST /copilot/query (SSE).
sprint-05: GET/DELETE /copilot/session/{session_id}.

SSE 스트리밍(/copilot/query) 은 sprint-04 에서 추가.
포맷: data-only SSE (`data: {json}\\n\\n`), `event:` 라인 없음 (revision 2 결정).
"""
from __future__ import annotations

import uuid as _uuid
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agents.planner import build_copilot_plan
from app.schemas.copilot import CopilotPlan, CopilotPlanRequest, SessionMeta, SessionResponse
from app.services.copilot.context import build_active_context
from app.services.session import get_session_store

router = APIRouter(prefix="/copilot", tags=["copilot"])


# ── POST /copilot/plan (sprint-01) ──────────────────────────────────────────


@router.post(
    "/plan",
    response_model=CopilotPlan,
    responses={400: {"description": "JSON 파싱 실패"}},
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
    """POST /copilot/query 요청 본문 (OpenAPI 공개 스키마).

    harness 전용 숨김 파라미터 `_harness_step_delay_ms` 는 이 클래스에 없으므로
    OpenAPI 스키마에 노출되지 않는다.
    """

    query: str = Field(..., description="자연어 질의", min_length=1)
    session_id: str | None = Field(default=None, description="기존 세션 ID (옵션)")
    context: dict[str, Any] | None = Field(default=None, description="추가 컨텍스트 (옵션)")


class _InternalQueryRequest(QueryRequest):
    """내부 전용 확장 — OpenAPI 미노출.

    `_harness_step_delay_ms` : 오케스트레이터가 각 step 진입 시
    `asyncio.sleep(delay_ms / 1000)` 으로 변환. 결정론적 병렬 테스트용.

    FastAPI 라우트 파라미터에 이 클래스를 사용하면 `_InternalQueryRequest` 가
    OpenAPI components/schemas 에 등록된다. openapi_extra 의 requestBody override 로
    외부에는 `QueryRequest` 스키마만 노출한다.
    """

    model_config = {"populate_by_name": True}

    harness_step_delay_ms: int = Field(
        default=0,
        alias="_harness_step_delay_ms",
        description="[harness-only] 각 step 실행 전 지연 ms. 병렬 결정론적 테스트용.",
    )


@router.post(
    "/query",
    summary="자연어 질의 → SSE 스트림",
    description=(
        "자연어 질의를 받아 멀티-스텝 에이전트 오케스트레이션을 실행하고 결과를 "
        "Server-Sent Events 로 스트리밍한다. "
        "각 이벤트는 `data: <JSON>\\n\\n` 포맷 (data-only SSE). "
        "JSON 은 CopilotEvent discriminated union."
    ),
    openapi_extra={
        # OpenAPI requestBody 를 공개 QueryRequest 스키마로만 노출.
        # 실제 라우트 파라미터는 _InternalQueryRequest 지만,
        # 문서에서는 harness 전용 필드(_harness_step_delay_ms)를 숨긴다.
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "title": "QueryRequest",
                        "description": "POST /copilot/query 요청 본문.",
                        "type": "object",
                        "required": ["query"],
                        "properties": {
                            "query": {
                                "type": "string",
                                "minLength": 1,
                                "description": "자연어 질의",
                            },
                            "session_id": {
                                "anyOf": [{"type": "string"}, {"type": "null"}],
                                "default": None,
                                "description": "기존 세션 ID (옵션)",
                            },
                            "context": {
                                "anyOf": [
                                    {"type": "object", "additionalProperties": True},
                                    {"type": "null"},
                                ],
                                "default": None,
                                "description": "추가 컨텍스트 (옵션)",
                            },
                        },
                    }
                }
            },
        }
    },
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
async def query_copilot(body: _InternalQueryRequest) -> StreamingResponse:
    """자연어 질의 → SSE 스트림 (data-only, `event:` 라인 없음).

    응답 헤더 `X-Copilot-Session-Id` 에 세션 ID 포함.
    session_id 미전송 시 UUID4 자동 생성.

    파라미터는 `_InternalQueryRequest` 로 받아 `_harness_step_delay_ms` 에 접근.
    FastAPI OpenAPI 문서에는 `openapi_extra.requestBody` 로 `QueryRequest` 만 노출.
    """
    from app.services.copilot.orchestrator import stream_copilot_query

    resolved_session_id = body.session_id or str(_uuid.uuid4())
    delay_ms = body.harness_step_delay_ms

    async def _gen() -> AsyncGenerator[bytes, None]:
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


# ── GET /copilot/sessions (sprint-08 B-7) ───────────────────────────────────


@router.get(
    "/sessions",
    response_model=list[SessionMeta],
    summary="세션 히스토리 목록 조회",
    description=(
        "저장된 코파일럿 세션 목록을 최근순으로 반환한다. "
        "limit/offset 으로 페이지네이션. TTL 만료 세션은 제외."
    ),
)
async def list_sessions(
    limit: int = 20,
    offset: int = 0,
) -> list[SessionMeta]:
    """GET /copilot/sessions — 세션 히스토리 목록 (최근순)."""
    store = get_session_store()
    if hasattr(store, "list_sessions"):
        return store.list_sessions(limit=limit, offset=offset)
    # list_sessions 가 없는 store (PostgresSessionStore 등) 는 빈 목록 반환
    return []


# ── GET /copilot/sessions/{session_id} alias (sprint-08 B-7) ────────────────


@router.get(
    "/sessions/{session_id}",
    response_model=SessionResponse,
    summary="세션 상세 조회 (sessions 경로)",
    description="GET /copilot/session/{session_id} 의 alias. /sessions/ 경로로도 동일하게 접근 가능.",
    responses={404: {"description": "세션을 찾을 수 없거나 TTL 만료"}},
)
async def get_session_alias(session_id: str) -> SessionResponse:
    """GET /copilot/sessions/{session_id} — session 상세 조회 alias."""
    store = get_session_store()

    if hasattr(store, "exists"):
        if not store.exists(session_id):
            raise HTTPException(status_code=404, detail=f"session {session_id!r} not found or expired")
        turns = await store.get_turns(session_id, limit=50)
    else:
        turns = await store.get_turns(session_id, limit=50)
        if not turns:
            raise HTTPException(status_code=404, detail=f"session {session_id!r} not found or expired")

    active_ctx = await build_active_context(
        session_id=session_id,
        user_query="",
        store=store,
    )

    return SessionResponse(
        session_id=session_id,
        turns=turns,
        active_context=active_ctx,
    )


# ── GET /copilot/session/{session_id} (sprint-05) ────────────────────────────


@router.get(
    "/session/{session_id}",
    response_model=SessionResponse,
    summary="세션 메모리 조회",
    description=(
        "세션 메모리를 조회한다. 세션이 없거나 TTL 만료 시 404 를 반환한다. "
        "응답에 최근 50턴 이하의 SessionTurn 목록과 ActiveContext 가 포함된다."
    ),
    responses={404: {"description": "세션을 찾을 수 없거나 TTL 만료"}},
)
async def get_session(session_id: str) -> SessionResponse:
    """GET /copilot/session/{session_id} — 세션 메모리 조회."""
    store = get_session_store()

    # 존재 여부 확인 (InMemorySessionStore: exists() 사용, 그 외: get_turns 결과로 판단)
    if hasattr(store, "exists"):
        if not store.exists(session_id):
            raise HTTPException(status_code=404, detail=f"session {session_id!r} not found or expired")
        turns = await store.get_turns(session_id, limit=50)
    else:
        turns = await store.get_turns(session_id, limit=50)
        if not turns:
            raise HTTPException(status_code=404, detail=f"session {session_id!r} not found or expired")

    active_ctx = await build_active_context(
        session_id=session_id,
        user_query="",
        store=store,
    )

    return SessionResponse(
        session_id=session_id,
        turns=turns,
        active_context=active_ctx,
    )


# ── DELETE /copilot/session/{session_id} (sprint-05) ─────────────────────────


@router.delete(
    "/session/{session_id}",
    status_code=204,
    summary="세션 삭제",
    description="세션과 모든 턴을 삭제한다. 이후 GET 은 404 를 반환한다.",
)
async def delete_session(session_id: str) -> None:
    """DELETE /copilot/session/{session_id} — 세션 삭제."""
    store = get_session_store()
    await store.clear(session_id)
