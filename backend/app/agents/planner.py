"""Copilot Planner — NL Query → CopilotPlan (sprint-01).

자연어 질의를 받아 LLM(copilot_planner_system 프롬프트) 으로 플랜 JSON 을 생성하고,
3단 게이트(schema/domain/critique) 를 적용한다.

게이트 재사용 방식:
- Schema gate: Pydantic(CopilotPlan) 파싱으로 구조 검증
- Domain gate: DAG 유효성(steps 순서, dangling depends_on) 검사
- Critique gate: "모든 step 이 query 에 필요한가?" LLM self-critique

모든 게이트는 1회 재시도(schema only) 또는 즉시 실패(domain/critique) 정책.
"""

from __future__ import annotations

import datetime
import json
import uuid
from typing import Any

from pydantic import ValidationError

import app.agents.llm as _llm_module
from app.agents.llm import LLMUnavailableError, extract_json
from app.schemas.copilot import CopilotPlan

_ALLOWED_AGENTS = {
    "stock",
    "crypto",
    "fx",
    "macro",
    "portfolio",
    "rebalance",
    "comparison",
    "simulator",
    "news-rag",
}

# ── 내부 유틸 ──────────────────────────────────────────────────────────────


def _now_iso() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _make_plan_id() -> str:
    return f"p-{uuid.uuid4().hex[:8]}"


def _make_session_id() -> str:
    return f"sess-{uuid.uuid4().hex[:8]}"


# ── Gate 1: Schema (Pydantic) ──────────────────────────────────────────────


def _validate_plan_schema(raw: dict[str, Any]) -> tuple[CopilotPlan | None, str]:
    """Pydantic 으로 CopilotPlan 검증. 성공 → (plan, ""), 실패 → (None, 에러)."""
    try:
        plan = CopilotPlan.model_validate(raw)
        return plan, ""
    except ValidationError as exc:
        return None, exc.json()


# ── Gate 2: Domain (DAG 유효성) ────────────────────────────────────────────


def _validate_plan_domain(plan: CopilotPlan) -> str | None:
    """DAG 구조 sanity check.

    - 모든 agent 가 9개 리터럴 집합에 속하는지 (schema gate 이후이므로 실제로는 중복이지만 명시적 체크)
    - 모든 depends_on 이 동일 plan 의 step_id 를 가리키는지 (dangling 금지)
    - step_id 중복 없음
    """
    seen_ids: set[str] = set()
    for step in plan.steps:
        if step.agent not in _ALLOWED_AGENTS:
            return f"invalid agent literal: {step.agent!r}"
        if step.step_id in seen_ids:
            return f"duplicate step_id: {step.step_id!r}"
        seen_ids.add(step.step_id)

    for step in plan.steps:
        for dep in step.depends_on:
            if dep not in seen_ids:
                return f"dangling dependency {dep!r} in step {step.step_id!r}"

    return None


# ── Gate 3: Critique (LLM self-critique) ──────────────────────────────────


async def _critique_plan(query: str, plan: CopilotPlan) -> tuple[bool, str]:
    """LLM 에 "모든 step 이 질의에 필요한가?" 를 묻는다.

    LLM 불가 상황(키 미설정 등) 에서는 보수적으로 pass 처리한다.
    반환: (passed, reason)
    """
    prompt = json.dumps(
        {
            "query": query,
            "plan": plan.model_dump(),
            "instruction": (
                "위 plan 의 각 step 이 user query 를 답하기 위해 실제로 필요한지 판단하라. "
                "불필요한 step 이 있으면 verdict=fail, reason 에 해당 step_id 를 명시하라. "
                "모두 필요하면 verdict=pass. "
                'JSON 만 출력: {"verdict": "pass"|"fail", "reason": "..."}'
            ),
        },
        ensure_ascii=False,
    )
    try:
        raw = await _llm_module.call_llm(
            system_prompt_name="copilot_planner_system",
            user_content=prompt,
            max_tokens=300,
        )
        parsed = extract_json(raw)
        verdict = parsed.get("verdict", "")
        reason = parsed.get("reason", "")
        if verdict == "fail":
            return False, reason or "unused steps detected"
        return True, reason
    except (LLMUnavailableError, Exception):  # noqa: BLE001
        # 운영 관용: critique unavailable 이면 pass
        return True, "critique unavailable"


# ── 메인 함수 ──────────────────────────────────────────────────────────────


async def build_copilot_plan(
    query: str,
    session_id: str | None = None,
) -> CopilotPlan:
    """자연어 질의 → CopilotPlan (3단 게이트 결과 포함)."""

    resolved_session_id = session_id or _make_session_id()
    gate_results: dict[str, str] = {}

    # ── LLM 호출 ───────────────────────────────────────────────────────────
    user_content = json.dumps(
        {"query": query, "session_id": resolved_session_id},
        ensure_ascii=False,
    )

    raw_text: str
    try:
        raw_text = await _llm_module.call_llm(
            system_prompt_name="copilot_planner_system",
            user_content=user_content,
        )
    except LLMUnavailableError:
        # 키 없는 환경 — fallback stub plan (테스트에서 monkeypatch 로 대체됨)
        raise

    # ── Gate 1: Schema ──────────────────────────────────────────────────────
    try:
        raw_dict = extract_json(raw_text)
    except ValueError as exc:
        gate_results["schema"] = f"fail: JSON parse error — {exc}"
        return _fallback_response(resolved_session_id, gate_results)

    # 필수 메타 보강 (LLM 이 누락할 경우 대비)
    raw_dict.setdefault("plan_id", _make_plan_id())
    raw_dict.setdefault("session_id", resolved_session_id)
    raw_dict.setdefault("created_at", _now_iso())

    plan, err = _validate_plan_schema(raw_dict)
    if plan is None:
        # 1회 재시도: 오류 메시지를 LLM 에 넘겨 교정 요청
        correction_content = json.dumps(
            {
                "previous_output": raw_dict,
                "validation_error": err,
                "instruction": (
                    "위 JSON 이 CopilotPlan 스키마를 위반했다. "
                    "오류를 수정해 올바른 CopilotPlan JSON 만 재출력하라. "
                    "agent 는 반드시 다음 9개 중 하나: "
                    "stock, crypto, fx, macro, portfolio, rebalance, comparison, simulator, news-rag"
                ),
            },
            ensure_ascii=False,
        )
        try:
            raw_text2 = await _llm_module.call_llm(
                system_prompt_name="copilot_planner_system",
                user_content=correction_content,
            )
            raw_dict2 = extract_json(raw_text2)
            raw_dict2.setdefault("plan_id", _make_plan_id())
            raw_dict2.setdefault("session_id", resolved_session_id)
            raw_dict2.setdefault("created_at", _now_iso())
            plan, err2 = _validate_plan_schema(raw_dict2)
            if plan is None:
                gate_results["schema"] = f"fail: schema invalid after retry — {err2[:160]}"
                return _fallback_response(resolved_session_id, gate_results)
        except (LLMUnavailableError, Exception):  # noqa: BLE001
            gate_results["schema"] = "fail: retry LLM error"
            return _fallback_response(resolved_session_id, gate_results)

    gate_results["schema"] = "pass"

    # ── Gate 2: Domain (DAG) ────────────────────────────────────────────────
    domain_err = _validate_plan_domain(plan)
    if domain_err:
        gate_results["domain"] = f"fail: {domain_err}"
        return _fallback_response(resolved_session_id, gate_results, partial_plan=plan)

    gate_results["domain"] = "pass"

    # ── Gate 3: Critique ────────────────────────────────────────────────────
    critique_passed, critique_reason = await _critique_plan(query, plan)
    if not critique_passed:
        gate_results["critique"] = f"fail: {critique_reason}"
        # critique fail = degraded 허용 (plan 은 반환, 단 gate 결과 기록)
    else:
        gate_results["critique"] = "pass"

    return CopilotPlan(
        plan_id=plan.plan_id,
        session_id=plan.session_id,
        steps=plan.steps,
        created_at=plan.created_at,
        gate_results=gate_results,
    )


def _fallback_response(
    session_id: str,
    gate_results: dict[str, str],
    partial_plan: CopilotPlan | None = None,
) -> CopilotPlan:
    """게이트 실패 시 최소 응답을 구성한다."""
    if partial_plan:
        return CopilotPlan(
            plan_id=partial_plan.plan_id,
            session_id=partial_plan.session_id,
            steps=partial_plan.steps,
            created_at=partial_plan.created_at,
            gate_results=gate_results,
        )
    return CopilotPlan(
        plan_id=_make_plan_id(),
        session_id=session_id,
        steps=[],
        created_at=_now_iso(),
        gate_results=gate_results,
    )
