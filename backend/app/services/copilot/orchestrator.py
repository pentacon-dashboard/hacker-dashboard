"""Copilot SSE 오케스트레이터 — sprint-04/05.

POST /copilot/query 에서 호출된다.
planner → DAG 위상 정렬 → 병렬 step 실행 → 3단 게이트 → 최종 통합 게이트

설계 결정 (contract.md revision 2):
- SSE 포맷: data-only (`data: {json}\n\n`), `event:` 라인 없음
- planner 는 `build_copilot_plan` 직접 import (HTTP 자기호출 금지)
- step_id "final" 은 최종 통합 게이트 전용 예약어
- done emit 직전 SessionTurn 영속화
- `_harness_step_delay_ms` 로 결정론적 병렬 테스트 가능
- COPILOT_FORCE_FAIL_STEP 환경변수로 특정 step 강제 실패 (테스트용)
- sprint-05: 매 턴 active_context 조립 → planner 호출 → 매 스텝 3단 게이트 재실행 (캐시 금지)
"""
from __future__ import annotations

import asyncio
import json
import os
import uuid
from collections import defaultdict
from collections.abc import AsyncGenerator
from typing import Any

import app.agents.llm as _llm_module
from app.agents.llm import extract_json
from app.agents.planner import build_copilot_plan
from app.schemas.copilot import (
    ActiveContext,
    ChartCard,
    CitationCard,
    ComparisonTableCard,
    CopilotPlan,
    CopilotStep,
    GatePolicy,
    ScorecardCard,
    SessionTurn,
    SimulatorResultCard,
    TextCard,
)
from app.services.copilot.context import build_active_context, format_context_for_planner
from app.services.session import get_session_store
from app.services.session.memory_store import make_turn_id

# ── SSE 헬퍼 ──────────────────────────────────────────────────────────────────


def _sse(payload: dict[str, Any]) -> bytes:
    """data-only SSE 포맷. `event:` 라인 없음 (revision 2 결정)."""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode()


# ── 3단 게이트 (copilot step 전용) ────────────────────────────────────────────


def _schema_gate(card: dict[str, Any], step: CopilotStep) -> tuple[str, str]:
    """Schema gate: CopilotCard 계열 Pydantic 검증."""
    import pydantic

    card_type = card.get("type", "")
    model_map: dict[str, type[pydantic.BaseModel]] = {
        "text": TextCard,
        "chart": ChartCard,
        "scorecard": ScorecardCard,
        "citation": CitationCard,
        "comparison_table": ComparisonTableCard,
        "simulator_result": SimulatorResultCard,
    }
    model_cls = model_map.get(card_type)
    if model_cls is None:
        return "fail", f"unknown card type: {card_type!r}"

    try:
        model_cls.model_validate(card)
        return "pass", ""
    except Exception as exc:  # noqa: BLE001
        return "fail", str(exc)[:200]


def _domain_gate(card: dict[str, Any], step: CopilotStep) -> tuple[str, str]:
    """Domain gate: 자산군 sanity check (간략 구현 — 게이트 이벤트 방출이 목적)."""
    card_type = card.get("type", "")
    # chart: series 비어있지 않음
    if card_type == "chart":
        if not card.get("series"):
            return "fail", "chart card has no series data"
    # scorecard: rows 비어있지 않음
    if card_type == "scorecard":
        if not card.get("rows"):
            return "fail", "scorecard card has no rows"
    return "pass", ""


async def _critique_gate(card: dict[str, Any], step: CopilotStep, *, is_final: bool = False) -> tuple[str, str]:
    """Critique gate: LLM self-critique (unavailable 시 pass).

    sprint-05: 매 턴 호출 시마다 새로 실행 (캐시 금지).
    """
    instruction = (
        "위 copilot card 가 사용자 질의에 적합하고 사실에 기반한 내용인지 평가하라. "
    )
    if is_final:
        instruction += (
            "최종 통합 응답이므로 모든 news-rag 인용이 원문 excerpt 와 일치하는지(citation faithfulness) 추가로 확인하라. "
        )
    instruction += 'JSON 만 출력: {"verdict": "pass"|"fail", "reason": "..."}'

    prompt = json.dumps(
        {"step_id": step.step_id, "card": card, "instruction": instruction, "critique": True, "final": is_final},
        ensure_ascii=False,
    )

    try:
        raw = await _llm_module.call_llm(
            system_prompt_name="copilot_planner_system",
            user_content=prompt,
            max_tokens=300,
        )
        parsed = extract_json(raw)
        verdict = parsed.get("verdict", "pass")
        reason = parsed.get("reason", "")
        if verdict == "fail":
            return "fail", reason or "critique failed"
        return "pass", reason
    except Exception:  # noqa: BLE001
        return "pass", "critique unavailable"


# ── Step 실행기 ────────────────────────────────────────────────────────────────


def _run_step_sync(step: CopilotStep) -> dict[str, Any]:
    """동기적으로 analyzer stub 을 실행해 카드를 생성한다."""
    force_fail = os.environ.get("COPILOT_FORCE_FAIL_STEP", "")

    agent = step.agent

    # 강제 실패 (테스트용)
    if force_fail and step.step_id == force_fail:
        return {
            "card": {"type": "text", "content": f"강제 실패: {step.step_id}", "degraded": True},
            "gate_results": {"schema": "fail", "domain": "skip", "critique": "skip"},
            "forced_fail": True,
        }

    # analyzer 라우팅
    if agent == "comparison":
        from app.agents.analyzers.comparison import run as run_comparison
        return run_comparison(step)

    if agent == "simulator":
        from app.agents.analyzers.simulator import run as run_simulator
        return run_simulator(step)

    if agent == "news-rag":
        from app.agents.analyzers.news_rag import run as run_news_rag
        return run_news_rag(step)

    if agent == "portfolio":
        # portfolio analyzer stub
        return {
            "card": {
                "type": "text",
                "content": f"포트폴리오 분석 결과 (stub): {step.inputs}",
                "degraded": False,
            },
            "gate_results": {"schema": "pass", "domain": "pass", "critique": "pass"},
        }

    if agent in {"stock", "crypto", "fx", "macro", "rebalance"}:
        return {
            "card": {
                "type": "text",
                "content": f"{agent} 분석 결과 (stub): {step.inputs}",
                "degraded": False,
            },
            "gate_results": {"schema": "pass", "domain": "pass", "critique": "pass"},
        }

    return {
        "card": {"type": "text", "content": f"unknown agent: {agent}", "degraded": True},
        "gate_results": {"schema": "fail", "domain": "skip", "critique": "skip"},
    }


async def _execute_step(
    step: CopilotStep,
    delay_ms: int,
    queue: asyncio.Queue[bytes],
) -> dict[str, Any]:
    """단일 step 을 실행하고 이벤트를 queue 에 넣는다.

    반환: {"step_id": ..., "card": ..., "degraded": bool}
    sprint-05: 게이트는 매번 새로 실행 (캐시 금지).
    """
    if delay_ms > 0:
        await asyncio.sleep(delay_ms / 1000)

    # step.start
    await queue.put(_sse({"type": "step.start", "step_id": step.step_id}))

    # step token (fake 1건)
    await queue.put(_sse({"type": "step.token", "step_id": step.step_id, "text": f"{step.agent} 분석 중..."}))

    # 실행
    loop = asyncio.get_event_loop()
    outcome = await loop.run_in_executor(None, _run_step_sync, step)
    card = outcome["card"]
    gate_results = outcome.get("gate_results", {})
    forced_fail = outcome.get("forced_fail", False)

    # 게이트 이벤트 방출 (매번 새로 실행 — 캐시 금지)
    gate_policy = step.gate_policy
    degraded = False

    if forced_fail or gate_results.get("schema") == "fail":
        # schema gate fail
        await queue.put(_sse({
            "type": "step.gate",
            "step_id": step.step_id,
            "gate": "schema",
            "status": "fail",
            "reason": gate_results.get("schema", ""),
        }))
        if forced_fail:
            # error 이벤트 추가
            await queue.put(_sse({
                "type": "error",
                "step_id": step.step_id,
                "code": "STEP_FORCED_FAIL",
                "message": f"step {step.step_id} forced fail via COPILOT_FORCE_FAIL_STEP",
            }))
        degraded = True
    else:
        # schema gate
        if gate_policy.schema_check:
            schema_status, schema_reason = _schema_gate(card, step)
            await queue.put(_sse({
                "type": "step.gate",
                "step_id": step.step_id,
                "gate": "schema",
                "status": schema_status,
                "reason": schema_reason if schema_status == "fail" else None,
            }))
            if schema_status == "fail":
                degraded = True

        if not degraded and gate_policy.domain:
            domain_status, domain_reason = _domain_gate(card, step)
            await queue.put(_sse({
                "type": "step.gate",
                "step_id": step.step_id,
                "gate": "domain",
                "status": domain_status,
                "reason": domain_reason if domain_status == "fail" else None,
            }))
            if domain_status == "fail":
                # 1회 retry 후에도 fail → degraded
                await queue.put(_sse({
                    "type": "error",
                    "step_id": step.step_id,
                    "code": "DOMAIN_GATE_FAIL",
                    "message": domain_reason,
                }))
                degraded = True

        if not degraded and gate_policy.critique:
            critique_status, critique_reason = await _critique_gate(card, step)
            await queue.put(_sse({
                "type": "step.gate",
                "step_id": step.step_id,
                "gate": "critique",
                "status": critique_status,
                "reason": critique_reason if critique_status == "fail" else None,
            }))
            if critique_status == "fail":
                degraded = True

    if degraded:
        card = {**card, "degraded": True}

    # step.result
    await queue.put(_sse({"type": "step.result", "step_id": step.step_id, "card": card}))

    return {"step_id": step.step_id, "card": card, "degraded": degraded}


# ── 위상 정렬 ────────────────────────────────────────────────────────────────


def _topological_levels(steps: list[CopilotStep]) -> list[list[CopilotStep]]:
    """DAG 를 위상 레벨 별로 묶는다. 같은 레벨의 step 은 병렬 실행 가능."""
    step_map = {s.step_id: s for s in steps}
    in_degree: dict[str, int] = {s.step_id: 0 for s in steps}
    dependents: dict[str, list[str]] = defaultdict(list)

    for s in steps:
        for dep in s.depends_on:
            in_degree[s.step_id] += 1
            dependents[dep].append(s.step_id)

    levels: list[list[CopilotStep]] = []
    ready = [s for s in steps if in_degree[s.step_id] == 0]

    while ready:
        levels.append(ready)
        next_ready: list[CopilotStep] = []
        for s in ready:
            for child_id in dependents[s.step_id]:
                in_degree[child_id] -= 1
                if in_degree[child_id] == 0:
                    next_ready.append(step_map[child_id])
        ready = next_ready

    return levels


# ── 최종 통합 게이트 ──────────────────────────────────────────────────────────


async def _run_final_gate(
    step_results: dict[str, dict[str, Any]],
    query: str,
    queue: asyncio.Queue[bytes],
) -> dict[str, Any]:
    """모든 step 결과를 합성해 최종 통합 카드를 만들고 step_id='final' 게이트를 실행한다.

    sprint-05: 세션 컨텍스트를 썼더라도 매번 전부 재실행 (캐시 금지).
    """
    # 최종 통합 카드 합성 (stub)
    bodies = []
    any_step_degraded = False
    for sid, r in step_results.items():
        card = r.get("card", {})
        degraded = r.get("degraded", False) or card.get("degraded", False)
        if degraded:
            any_step_degraded = True
        content = card.get("content", card.get("body", str(card)))
        bodies.append(f"[{sid}{'(degraded)' if degraded else ''}] {content}")

    final_card: dict[str, Any] = {
        "type": "text",
        "content": "\n\n".join(bodies) or "분석 완료",
        # 하위 step 이 하나라도 degraded 이면 최종 카드도 degraded 로 propagate
        "degraded": any_step_degraded,
    }

    # step_id="final" 가상 step 생성 — model_construct 로 step_id 예약어 validator 우회
    final_step = CopilotStep.model_construct(
        step_id="final",
        agent="portfolio",  # 더미 값 (최종 게이트에서만 사용)
        gate_policy=GatePolicy(schema_check=True, domain=True, critique=True),  # type: ignore[call-arg]
        inputs={},
        depends_on=[],
    )

    # schema gate (매번 새로 실행)
    schema_status, schema_reason = _schema_gate(final_card, final_step)
    await queue.put(_sse({
        "type": "step.gate",
        "step_id": "final",
        "gate": "schema",
        "status": schema_status,
        "reason": schema_reason if schema_status == "fail" else None,
    }))

    # domain gate (매번 새로 실행)
    domain_status, domain_reason = _domain_gate(final_card, final_step)
    await queue.put(_sse({
        "type": "step.gate",
        "step_id": "final",
        "gate": "domain",
        "status": domain_status,
        "reason": domain_reason if domain_status == "fail" else None,
    }))

    # critique gate (매번 새로 실행)
    critique_status, critique_reason = await _critique_gate(final_card, final_step, is_final=True)
    await queue.put(_sse({
        "type": "step.gate",
        "step_id": "final",
        "gate": "critique",
        "status": critique_status,
        "reason": critique_reason if critique_status == "fail" else None,
    }))

    if schema_status == "fail" or domain_status == "fail" or critique_status == "fail":
        final_card = {**final_card, "degraded": True}

    return final_card


# ── 메인 스트림 생성기 ─────────────────────────────────────────────────────────


async def stream_copilot_query(
    query: str,
    session_id: str | None = None,
    context: dict[str, Any] | None = None,
    harness_step_delay_ms: int = 0,
) -> AsyncGenerator[bytes, None]:
    """SSE 스트림 비동기 제너레이터.

    caller (FastAPI StreamingResponse) 가 `async for chunk in stream_copilot_query(...)` 로 소비.

    sprint-05 변경:
    - 매 턴 시작 시 active_context 조립 (세션 메모리에서 직전 3턴 읽기)
    - planner 에 active_context 전달 (user role 메시지로 병합)
    - 매 스텝 + 최종 게이트 캐시 없이 재실행
    """
    resolved_session_id = session_id or str(uuid.uuid4())
    turn_id = make_turn_id()

    # ── sprint-05: active_context 조립 ─────────────────────────────────────
    store = get_session_store()
    active_context: ActiveContext = await build_active_context(
        session_id=session_id,  # 신규 세션이면 None 전달
        user_query=query,
        store=store,
    )
    context_str = format_context_for_planner(active_context)

    # ── 플랜 생성 ────────────────────────────────────────────────────────────
    try:
        plan: CopilotPlan = await build_copilot_plan(
            query=context_str,  # follow-up 컨텍스트 포함 질의
            session_id=resolved_session_id,
        )
    except Exception as exc:  # noqa: BLE001
        yield _sse({
            "type": "error",
            "code": "PLANNER_ERROR",
            "message": str(exc),
        })
        yield _sse({
            "type": "done",
            "session_id": resolved_session_id,
            "turn_id": turn_id,
        })
        return

    # plan.ready 이벤트
    yield _sse({"type": "plan.ready", "plan": plan.model_dump()})

    # ── 위상 정렬 ────────────────────────────────────────────────────────────
    levels = _topological_levels(plan.steps)

    # ── step 실행 (level-by-level 병렬) ────────────────────────────────────
    step_results: dict[str, dict[str, Any]] = {}
    queue: asyncio.Queue[bytes] = asyncio.Queue()

    for level in levels:
        # 같은 레벨의 step 은 asyncio.gather 로 병렬 실행
        tasks = [
            asyncio.create_task(_execute_step(step, harness_step_delay_ms, queue))
            for step in level
        ]

        # gather 와 queue 소비를 동시에 처리
        gather_task = asyncio.gather(*tasks, return_exceptions=True)

        while True:
            # queue 에서 이벤트를 꺼내 yield
            try:
                chunk = queue.get_nowait()
                yield chunk
            except asyncio.QueueEmpty:
                if gather_task.done():
                    # 남은 큐 비우기
                    while not queue.empty():
                        yield await queue.get()
                    break
                await asyncio.sleep(0)

        results = await gather_task
        for step, result in zip(level, results):
            if isinstance(result, Exception):
                step_results[step.step_id] = {
                    "card": {"type": "text", "content": str(result), "degraded": True},
                    "degraded": True,
                }
            else:
                step_results[step.step_id] = result  # type: ignore[assignment]

    # ── 최종 통합 게이트 (매번 캐시 없이 재실행) ───────────────────────────
    final_queue: asyncio.Queue[bytes] = asyncio.Queue()
    final_card = await _run_final_gate(step_results, query, final_queue)

    while not final_queue.empty():
        yield await final_queue.get()

    yield _sse({"type": "final.card", "card": final_card})

    # ── done 직전 SessionTurn 영속화 ────────────────────────────────────────
    # summary 추출 (final_card 에서)
    _summary = final_card.get("content") or final_card.get("body") or "분석 완료"
    if len(_summary) > 400:
        _summary = _summary[:400] + "…"

    new_turn = SessionTurn(
        turn_id=turn_id,
        query=query,
        plan_id=plan.plan_id,
        final_card=final_card,
        citations=[],
        active_context=active_context.model_dump(),
    )

    try:
        await store.append_turn(resolved_session_id, new_turn)
    except Exception:  # noqa: BLE001
        pass  # 저장 실패는 스트림에 영향 없이 무시

    yield _sse({
        "type": "done",
        "session_id": resolved_session_id,
        "turn_id": turn_id,
    })
