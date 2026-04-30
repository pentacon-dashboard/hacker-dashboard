"""Copilot SSE orchestrator.

The transport remains JSON-over-SSE, but user-facing final cards must be
conversation-ready text. Internal step ids, gate labels, and fallback markers
must never leak into final answers.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from collections import defaultdict
from collections.abc import AsyncGenerator
from typing import Any, cast

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


def _sse(payload: dict[str, Any]) -> bytes:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode()


def _schema_gate(card: dict[str, Any], step: CopilotStep) -> tuple[str, str]:
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
    card_type = card.get("type", "")
    if card_type == "chart" and not card.get("series"):
        return "fail", "chart card has no series data"
    if card_type == "scorecard" and not card.get("rows"):
        return "fail", "scorecard card has no rows"
    return "pass", ""


async def _critique_gate(
    card: dict[str, Any], step: CopilotStep, *, is_final: bool = False
) -> tuple[str, str]:
    instruction = "위 copilot card 가 사용자 질의에 적합하고 사실에 기반한 내용인지 평가하라. "
    if is_final:
        instruction += "최종 통합 응답이므로 인용이 있다면 excerpt 와 일치하는지 확인하라. "
    instruction += 'JSON 만 출력: {"verdict": "pass"|"fail", "reason": "..."}'

    prompt = json.dumps(
        {
            "step_id": step.step_id,
            "card": card,
            "instruction": instruction,
            "critique": True,
            "final": is_final,
        },
        ensure_ascii=False,
    )

    try:
        raw = await _llm_module.call_llm(
            system_prompt_name="critique_system",
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


def _strip_code_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        first_nl = t.find("\n")
        if first_nl != -1:
            t = t[first_nl + 1 :]
        close = t.rfind("```")
        if close != -1:
            t = t[:close]
    return t.strip()


def _format_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:,.2f}".rstrip("0").rstrip(".")
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, str):
        return value
    if value is None:
        return "-"
    return json.dumps(value, ensure_ascii=False, default=str)


def _coerce_llm_answer_to_text(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith(("{", "[")):
        return _sanitize_debug_text(stripped)

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return _sanitize_debug_text(stripped)

    if isinstance(parsed, dict):
        for key in (
            "answer",
            "response",
            "narrative",
            "summary",
            "headline",
            "message",
            "analysis",
            "content",
            "body",
        ):
            value = parsed.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        lines: list[str] = []
        highlights = parsed.get("highlights")
        if isinstance(highlights, list):
            lines.extend(f"- {_format_value(item)}" for item in highlights[:5])
        if lines:
            return "\n".join(lines)

        for key, value in parsed.items():
            if key in {"type", "metrics", "signals", "evidence"}:
                continue
            if isinstance(value, (str, int, float, bool)) or value is None:
                lines.append(f"{key.replace('_', ' ')}: {_format_value(value)}")
        return "\n".join(lines).strip() or "분석 결과를 정리했습니다."

    if isinstance(parsed, list):
        return (
            "\n".join(f"- {_format_value(item)}" for item in parsed[:6])
            or "분석 결과를 정리했습니다."
        )

    return _format_value(parsed)


def _sanitize_debug_text(text: str) -> str:
    cleaned = text.strip()
    cleaned = cleaned.replace("sync fallback:", "", 1).strip()
    cleaned = cleaned.replace("(sync fallback)", "").strip()
    cleaned = cleaned.replace(
        "LLM 미설정 — OPENAI_API_KEY 를 설정해 주세요.", "AI 분석 설정이 아직 완료되지 않았습니다."
    )
    cleaned = cleaned.replace(
        "LLM 미설정 - OPENAI_API_KEY 를 설정해 주세요.", "AI 분석 설정이 아직 완료되지 않았습니다."
    )
    for prefix in (
        "포트폴리오 분석 결과:",
        "portfolio 분석 결과:",
        "stock 분석 결과:",
        "crypto 분석 결과:",
        "fx 분석 결과:",
        "macro 분석 결과:",
        "rebalance 분석 결과:",
    ):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix) :].strip()
    return cleaned or "분석 결과를 정리했습니다."


def _fallback_text(agent: str, user_query: str) -> str:
    if agent == "portfolio":
        return (
            "현재 포트폴리오 리스크는 수익률보다 집중도와 변동성 노출을 먼저 봐야 합니다. "
            "지금 응답은 실시간 AI 분석 경로가 제한되어 확정 지표 기반의 간단 요약으로 제공됩니다. "
            "보유 종목 수, 상위 종목 비중, 통화 노출, 최근 손익률을 함께 확인한 뒤 리밸런싱 여부를 판단하세요."
        )
    if agent == "rebalance":
        return (
            "리밸런싱은 단일 종목과 자산군 비중이 과도하게 높아졌는지부터 확인하는 것이 좋습니다."
        )
    return f"{user_query or '요청한 내용'}에 대한 분석을 정리했습니다."


_AGENT_PROMPT_MAP: dict[str, str] = {
    "stock": "stock_system",
    "crypto": "crypto_system",
    "fx": "fx_system",
    "macro": "macro_system",
    "portfolio": "portfolio_system",
    "rebalance": "rebalance_system",
    "mixed": "mixed_system",
}

if os.environ.get("COPILOT_ALL_AGENTS_LLM", "").lower() in ("1", "true", "yes"):
    _AGENT_PROMPT_MAP.update(
        {
            "comparison": "comparison_system",
            "simulator": "simulator_system",
            "news-rag": "news_rag_system",
        }
    )


def _run_step_sync(step: CopilotStep, user_query: str = "") -> dict[str, Any]:
    force_fail = os.environ.get("COPILOT_FORCE_FAIL_STEP", "")
    if force_fail and step.step_id == force_fail:
        return {
            "card": {
                "type": "text",
                "content": "요청한 분석 일부를 완료하지 못했습니다.",
                "degraded": True,
            },
            "gate_results": {"schema": "fail", "domain": "skip", "critique": "skip"},
            "forced_fail": True,
        }

    if step.agent == "comparison":
        from app.agents.analyzers.comparison import run as run_comparison

        return run_comparison(step)
    if step.agent == "simulator":
        from app.agents.analyzers.simulator import run as run_simulator

        return run_simulator(step)
    if step.agent == "news-rag":
        from app.agents.analyzers.news_rag import run as run_news_rag

        return run_news_rag(step)

    return {
        "card": {
            "type": "text",
            "content": _fallback_text(step.agent, user_query),
            "degraded": True,
        },
        "gate_results": {"schema": "pass", "domain": "pass", "critique": "skip"},
    }


async def _fetch_portfolio_context() -> dict[str, Any]:
    from sqlalchemy import select

    from app.db.models import Holding
    from app.db.session import AsyncSessionLocal
    from app.services.portfolio import compute_summary, get_period_snapshot, get_prev_snapshot

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Holding).where(Holding.user_id == "demo"))
        holdings_rows = list(result.scalars().all())
        prev_snap = await get_prev_snapshot(db, user_id="demo")
        period_snap = await get_period_snapshot(db, user_id="demo", period_days=30)
        summary = await compute_summary(
            holdings_rows,
            prev_snapshot=prev_snap,
            period_snapshot=period_snap,
            period_days=30,
        )

    return {
        "indicators": {
            "total_value": str(summary.total_value_krw),
            "pnl_pct": str(summary.total_pnl_pct),
            "daily_change_pct": str(summary.daily_change_pct),
            "period_change_pct": str(summary.period_change_pct),
            "n_holdings": summary.holdings_count,
            "asset_class_breakdown": {k: str(v) for k, v in summary.asset_class_breakdown.items()},
        },
        "holdings": [
            {
                "market": h.market,
                "code": h.code,
                "quantity": str(h.quantity),
                "avg_cost": str(h.avg_cost),
                "value_krw": str(h.value_krw),
                "pnl_pct": str(h.pnl_pct),
            }
            for h in summary.holdings
        ],
    }


async def _run_agent_llm(step: CopilotStep, user_query: str) -> dict[str, Any]:
    from app.agents.llm import LLMUnavailableError, call_llm

    agent = step.agent
    prompt_name = _AGENT_PROMPT_MAP.get(agent)
    if prompt_name is None:
        return _run_step_sync(step, user_query)

    try:
        if agent in {"portfolio", "rebalance"}:
            try:
                ctx = await _fetch_portfolio_context()
            except Exception as exc:  # noqa: BLE001
                ctx = {
                    "portfolio_context_unavailable": True,
                    "reason": type(exc).__name__,
                    "indicators": {},
                    "holdings": [],
                }
            user_content = (
                f"사용자 질문: {user_query}\n\n"
                f"포트폴리오 데이터:\n{json.dumps(ctx, ensure_ascii=False, indent=2)}"
            )
        else:
            user_content = (
                f"사용자 질문: {user_query}\n"
                f"Step 파라미터:\n{json.dumps(dict(step.inputs), ensure_ascii=False, indent=2)}"
            )

        raw = await call_llm(
            system_prompt_name=prompt_name,
            user_content=user_content,
            temperature=0.3,
            max_tokens=2048,
            expect_json=agent in {"portfolio", "rebalance"},
        )
        cleaned = _coerce_llm_answer_to_text(_strip_code_fence(raw)) or _fallback_text(
            agent, user_query
        )
        return {
            "card": {"type": "text", "content": cleaned, "degraded": False},
            "gate_results": {"schema": "pass", "domain": "pass", "critique": "pass"},
        }
    except LLMUnavailableError:
        return {
            "card": {
                "type": "text",
                "content": _fallback_text(agent, user_query),
                "degraded": True,
            },
            "gate_results": {"schema": "pass", "domain": "pass", "critique": "skip"},
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "card": {
                "type": "text",
                "content": f"{_fallback_text(agent, user_query)}",
                "degraded": True,
                "degraded_reason": str(exc)[:160],
            },
            "gate_results": {"schema": "pass", "domain": "pass", "critique": "skip"},
        }


async def _execute_step(
    step: CopilotStep,
    delay_ms: int,
    queue: asyncio.Queue[bytes],
    user_query: str = "",
) -> dict[str, Any]:
    if delay_ms > 0:
        await asyncio.sleep(delay_ms / 1000)

    start_events: list[bytes] = [
        _sse({"type": "step.start", "step_id": step.step_id}),
        _sse({"type": "step.token", "step_id": step.step_id, "text": f"{step.agent} 분석 중..."}),
    ]

    if step.agent in _AGENT_PROMPT_MAP:
        outcome = await _run_agent_llm(step, user_query)
    else:
        loop = asyncio.get_event_loop()
        outcome = await loop.run_in_executor(None, _run_step_sync, step, user_query)

    card = outcome["card"]
    gate_results = outcome.get("gate_results", {})
    forced_fail = outcome.get("forced_fail", False)
    gate_events: list[bytes] = []
    gate_policy = step.gate_policy
    degraded = bool(card.get("degraded"))

    if forced_fail or gate_results.get("schema") == "fail":
        gate_events.append(
            _sse(
                {
                    "type": "step.gate",
                    "step_id": step.step_id,
                    "gate": "schema",
                    "status": "fail",
                    "reason": gate_results.get("schema", ""),
                }
            )
        )
        if forced_fail:
            gate_events.append(
                _sse(
                    {
                        "type": "error",
                        "step_id": step.step_id,
                        "code": "STEP_FORCED_FAILURE",
                        "message": "step execution was forced to fail",
                    }
                )
            )
        degraded = True
    else:
        if gate_policy.schema_check:
            schema_status, schema_reason = _schema_gate(card, step)
            gate_events.append(
                _sse(
                    {
                        "type": "step.gate",
                        "step_id": step.step_id,
                        "gate": "schema",
                        "status": schema_status,
                        "reason": schema_reason if schema_status == "fail" else None,
                    }
                )
            )
            degraded = degraded or schema_status == "fail"

        if not degraded and gate_policy.domain:
            domain_status, domain_reason = _domain_gate(card, step)
            gate_events.append(
                _sse(
                    {
                        "type": "step.gate",
                        "step_id": step.step_id,
                        "gate": "domain",
                        "status": domain_status,
                        "reason": domain_reason if domain_status == "fail" else None,
                    }
                )
            )
            degraded = degraded or domain_status == "fail"

        if not degraded and gate_policy.critique and gate_results.get("critique") != "skip":
            critique_status, critique_reason = await _critique_gate(card, step)
            gate_events.append(
                _sse(
                    {
                        "type": "step.gate",
                        "step_id": step.step_id,
                        "gate": "critique",
                        "status": critique_status,
                        "reason": critique_reason if critique_status == "fail" else None,
                    }
                )
            )
            degraded = degraded or critique_status == "fail"

    if degraded:
        card = {**card, "degraded": True}
    gate_events.append(_sse({"type": "step.result", "step_id": step.step_id, "card": card}))

    return {
        "step_id": step.step_id,
        "card": card,
        "degraded": degraded,
        "_start_events": start_events,
        "_gate_events": gate_events,
    }


def _topological_levels(steps: list[CopilotStep]) -> list[list[CopilotStep]]:
    step_map = {s.step_id: s for s in steps}
    in_degree: dict[str, int] = {s.step_id: 0 for s in steps}
    dependents: dict[str, list[str]] = defaultdict(list)

    for step in steps:
        for dep in step.depends_on:
            in_degree[step.step_id] += 1
            dependents[dep].append(step.step_id)

    levels: list[list[CopilotStep]] = []
    ready = [s for s in steps if in_degree[s.step_id] == 0]
    while ready:
        levels.append(ready)
        next_ready: list[CopilotStep] = []
        for step in ready:
            for child_id in dependents[step.step_id]:
                in_degree[child_id] -= 1
                if in_degree[child_id] == 0:
                    next_ready.append(step_map[child_id])
        ready = next_ready
    return levels


def _card_to_final_text(card: dict[str, Any]) -> str:
    card_type = card.get("type", "text")
    if card_type == "text":
        return _sanitize_debug_text(str(card.get("content") or card.get("body") or ""))

    if card_type == "comparison_table":
        lines: list[str] = []
        summary = str(card.get("summary") or "").strip()
        if summary:
            lines.append(summary)
        rows_value = card.get("rows")
        rows = rows_value if isinstance(rows_value, list) else []
        for row_value in rows[:4]:
            if not isinstance(row_value, dict):
                continue
            row = cast("dict[str, Any]", row_value)
            symbol = row.get("symbol", "종목")
            metrics_value = row.get("metrics")
            metrics = (
                cast("dict[str, Any]", metrics_value) if isinstance(metrics_value, dict) else {}
            )
            metric_text = ", ".join(
                f"{name}: {_format_value(value)}" for name, value in list(metrics.items())[:4]
            )
            lines.append(f"- {symbol}: {metric_text}" if metric_text else f"- {symbol}")
        return "\n".join(lines) or "비교 분석 결과를 정리했습니다."

    if card_type == "simulator_result":
        lines = [
            f"시뮬레이션 기준 포트폴리오 가치는 {_format_value(card.get('base_value'))}에서 {_format_value(card.get('shocked_value'))}로 변합니다.",
            f"예상 수익률 변화는 {_format_value(card.get('twr_change_pct'))}%입니다.",
        ]
        scenarios_value = card.get("scenarios")
        scenarios = scenarios_value if isinstance(scenarios_value, list) else []
        for scenario_value in scenarios[:3]:
            if isinstance(scenario_value, dict):
                scenario = cast("dict[str, Any]", scenario_value)
                lines.append(
                    f"- {scenario.get('symbol', '종목')}: 변화율 {_format_value(scenario.get('delta_pct'))}%"
                )
        return "\n".join(lines)

    if card_type == "scorecard":
        rows_value = card.get("rows")
        rows = rows_value if isinstance(rows_value, list) else []
        lines = [str(card.get("title") or "주요 지표")]
        for row_value in rows[:5]:
            if isinstance(row_value, dict):
                row = cast("dict[str, Any]", row_value)
                lines.append(
                    f"- {row.get('label', '지표')}: {_format_value(row.get('value'))}{row.get('unit') or ''}"
                )
        return "\n".join(lines)

    if card_type == "chart":
        return f"{card.get('title') or '차트'} 흐름을 기준으로 분석했습니다."

    if card_type == "citation":
        title = str(card.get("title") or "인용 자료")
        excerpt = str(card.get("excerpt") or "").strip()
        return f"{title}\n{excerpt}" if excerpt else f"{title} 자료를 참고했습니다."

    return "분석 결과를 정리했습니다."


async def _run_final_gate(
    step_results: dict[str, dict[str, Any]],
    query: str,
    queue: asyncio.Queue[bytes],
) -> dict[str, Any]:
    """모든 step 결과를 합성해 최종 통합 카드를 만들고 step_id='final' 게이트를 실행한다.

    sprint-05: 세션 컨텍스트를 썼더라도 매번 전부 재실행 (캐시 금지).
    """
    # 최종 통합 카드 합성
    bodies = []
    any_step_degraded = False
    for _sid, r in step_results.items():
        card = r.get("card", {})
        degraded = r.get("degraded", False) or card.get("degraded", False)
        if degraded:
            any_step_degraded = True
        content = _card_to_final_text(card)
        if len(step_results) == 1:
            bodies.append(content)
        else:
            suffix = " (일부 제한)" if degraded else ""
            bodies.append(f"분석 결과{suffix}\n{content}")

    final_card: dict[str, Any] = {
        "type": "text",
        "content": "\n\n".join(bodies) or "분석 결과를 정리했습니다.",
        "degraded": any_step_degraded,
    }

    final_step = CopilotStep.model_construct(
        step_id="final",
        agent="portfolio",
        gate_policy=GatePolicy(schema_check=True, domain=True, critique=True),
        inputs={},
        depends_on=[],
    )

    schema_status, schema_reason = _schema_gate(final_card, final_step)
    await queue.put(
        _sse(
            {
                "type": "step.gate",
                "step_id": "final",
                "gate": "schema",
                "status": schema_status,
                "reason": schema_reason if schema_status == "fail" else None,
            }
        )
    )

    domain_status, domain_reason = _domain_gate(final_card, final_step)
    await queue.put(
        _sse(
            {
                "type": "step.gate",
                "step_id": "final",
                "gate": "domain",
                "status": domain_status,
                "reason": domain_reason if domain_status == "fail" else None,
            }
        )
    )

    critique_status, critique_reason = await _critique_gate(final_card, final_step, is_final=True)
    await queue.put(
        _sse(
            {
                "type": "step.gate",
                "step_id": "final",
                "gate": "critique",
                "status": critique_status,
                "reason": critique_reason if critique_status == "fail" else None,
            }
        )
    )

    if schema_status == "fail" or domain_status == "fail" or critique_status == "fail":
        final_card = {**final_card, "degraded": True}
    return final_card


async def stream_copilot_query(
    query: str,
    session_id: str | None = None,
    context: dict[str, Any] | None = None,
    harness_step_delay_ms: int = 0,
) -> AsyncGenerator[bytes, None]:
    resolved_session_id = session_id or str(uuid.uuid4())
    turn_id = make_turn_id()
    store = get_session_store()

    active_context: ActiveContext = await build_active_context(
        session_id=session_id,
        user_query=query,
        store=store,
    )
    context_str = format_context_for_planner(active_context)

    try:
        plan: CopilotPlan = await build_copilot_plan(
            query=context_str, session_id=resolved_session_id
        )
    except Exception as exc:  # noqa: BLE001
        yield _sse({"type": "error", "code": "PLANNER_ERROR", "message": str(exc)})
        yield _sse({"type": "done", "session_id": resolved_session_id, "turn_id": turn_id})
        return

    yield _sse({"type": "plan.ready", "plan": plan.model_dump()})

    step_results: dict[str, dict[str, Any]] = {}
    dummy_queue: asyncio.Queue[bytes] = asyncio.Queue()

    for level in _topological_levels(plan.steps):
        results = await asyncio.gather(
            *[_execute_step(step, harness_step_delay_ms, dummy_queue, query) for step in level],
            return_exceptions=True,
        )
        sorted_pairs = sorted(zip(level, results), key=lambda pair: pair[0].step_id)

        for _step, result in sorted_pairs:
            if not isinstance(result, Exception):
                result_dict: dict[str, Any] = result  # type: ignore[assignment]
                for event in result_dict.get("_start_events", []):
                    yield event

        for step, result in sorted_pairs:
            if isinstance(result, Exception):
                yield _sse(
                    {
                        "type": "error",
                        "step_id": step.step_id,
                        "code": "STEP_EXECUTION_ERROR",
                        "message": str(result)[:200],
                    }
                )
                step_results[step.step_id] = {
                    "card": {
                        "type": "text",
                        "content": "분석 중 일부 오류가 발생했습니다.",
                        "degraded": True,
                    },
                    "degraded": True,
                }
            else:
                result_dict = result  # type: ignore[assignment]
                for event in result_dict.get("_gate_events", []):
                    yield event
                step_results[step.step_id] = {
                    key: value
                    for key, value in result_dict.items()
                    if key not in ("_start_events", "_gate_events")
                }

    final_queue: asyncio.Queue[bytes] = asyncio.Queue()
    final_card = await _run_final_gate(step_results, query, final_queue)
    while not final_queue.empty():
        yield await final_queue.get()

    yield _sse({"type": "final.card", "card": final_card})

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
        pass

    yield _sse({"type": "done", "session_id": resolved_session_id, "turn_id": turn_id})
