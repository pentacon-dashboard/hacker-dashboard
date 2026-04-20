"""
Critique Gate — 별도 LLM 호출로 Analyzer 결론의 근거 진위 검증.

입력: analyzer_output.summary / highlights / evidence + 원본 input_data
출력: {"verdict": "pass"|"fail", "per_claim":[...], "reason": "..."}

실패 시 재시도 금지. gate 상태는 'pass' | 'fail: <reason>'.

보수적 정책:
- LLM 호출 자체가 실패하면 'pass: critique unavailable (<err>)' 로 기록하고 통과.
  (운영 중 외부 의존성 장애로 파이프라인이 통째로 막히는 것을 방지)
- verdict 누락이나 JSON 파싱 실패는 'fail: ...' 로 처리.
"""
from __future__ import annotations

import json
from typing import Any

from app.agents.llm import call_llm, extract_json
from app.agents.state import AgentState


def _build_user_content(state: AgentState) -> str:
    output = state.get("analyzer_output") or {}
    summary = output.get("summary")
    highlights = output.get("highlights") or []
    evidence = output.get("evidence") or []
    rows = state.get("input_data") or []

    return json.dumps(
        {
            "input_data": rows[:50],
            "analyzer_output": {
                "summary": summary,
                "highlights": highlights,
                "evidence": evidence,
                "metrics": output.get("metrics"),
            },
        },
        ensure_ascii=False,
    )


async def critique_gate(state: AgentState) -> AgentState:
    """
    별도 LLM 호출로 근거 검증. 실패해도 재시도 없음.
    """
    output = state.get("analyzer_output")
    if not isinstance(output, dict):
        return _mark(state, "fail: no analyzer_output to critique")

    try:
        raw = await call_llm(
            system_prompt_name="critique_system",
            user_content=_build_user_content(state),
            max_tokens=600,
        )
    except Exception as exc:  # noqa: BLE001 — 외부 경계
        # 운영 관용: 비치명적 경로로 통과시키되 이유는 명시
        return _mark(state, f"pass: critique unavailable ({type(exc).__name__})")

    try:
        parsed = extract_json(raw)
    except ValueError as exc:
        return _mark(state, f"fail: critique JSON parse error — {exc}")

    verdict = parsed.get("verdict")
    reason = parsed.get("reason", "")

    if verdict == "pass":
        return _mark(state, "pass", critique=parsed)
    if verdict == "fail":
        return _mark(state, f"fail: {reason or 'claims unsupported'}", critique=parsed)

    return _mark(state, f"fail: missing or invalid verdict — got {verdict!r}")


def _mark(state: AgentState, status: str, *, critique: dict[str, Any] | None = None) -> AgentState:
    gates = {**state["gates"], "critique_gate": status}
    patch: dict[str, Any] = {**state, "gates": gates}
    # critique 상세는 analyzer_output 내 _critique 에 첨부 (프런트 디버깅·데모용)
    if critique is not None:
        out = state.get("analyzer_output") or {}
        if isinstance(out, dict):
            patch["analyzer_output"] = {**out, "_critique": critique}
    return patch
