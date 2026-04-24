"""
Schema Gate — Pydantic 으로 Analyzer 출력 구조를 검증.

실패 시 1회 재시도: 원본 raw 응답 + Pydantic 에러 메시지를 LLM 에 넘겨
"다음 스키마를 만족하도록 수정해서 재출력해라" 지시한다.
재시도 후에도 실패면 gate = "fail: <reason>" 으로 기록.
"""
from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from app.agents.llm import call_llm, extract_json
from app.agents.state import AgentState


class Evidence(BaseModel):
    claim: str
    rows: list[int] = Field(default_factory=list)


class Signal(BaseModel):
    kind: str
    strength: str
    rationale: str

    @field_validator("strength")
    @classmethod
    def _valid_strength(cls, v: str) -> str:
        if v not in {"low", "medium", "high"}:
            raise ValueError(f"invalid signal strength: {v}")
        return v


class AnalyzerOutput(BaseModel):
    """모든 자산군 Analyzer 가 최소 만족해야 하는 공통 스키마.

    하위 호환: `summary` 또는 `headline` 중 하나 이상이 있으면 통과.
    Week-1 출력(summary 만 있음)도 그대로 유효.
    """

    asset_class: str
    summary: str | None = Field(default=None)
    headline: str | None = Field(default=None)
    narrative: str | None = Field(default=None)
    highlights: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    signals: list[Signal] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    @field_validator("asset_class")
    @classmethod
    def _valid_class(cls, v: str) -> str:
        if v not in {"stock", "crypto", "fx", "macro", "mixed", "portfolio"}:
            raise ValueError(f"unknown asset_class: {v}")
        return v

    @model_validator(mode="after")
    def _require_text(self) -> AnalyzerOutput:
        if not (self.summary or self.headline):
            raise ValueError("either 'summary' or 'headline' must be present")
        return self


def _validate(output: dict[str, Any]) -> tuple[bool, str]:
    """AnalyzerOutput 검증. 통과 시 (True, ''), 실패 시 (False, 에러메시지)."""
    try:
        AnalyzerOutput.model_validate(output)
        return True, ""
    except ValidationError as exc:
        return False, exc.json()


async def _retry_with_correction(
    *,
    prompt_name: str,
    original_rows: list[dict[str, Any]],
    raw_or_parsed: Any,
    error_detail: str,
) -> dict[str, Any] | None:
    """
    LLM 에 교정 지시 메시지를 던져 다시 생성.
    실패 시 None.
    """
    correction = json.dumps(
        {
            "previous_output": raw_or_parsed,
            "validation_error": error_detail,
            "instruction": (
                "위 출력이 스키마 검증에 실패했다. "
                "동일한 입력 데이터에 대해 AnalyzerOutput 스키마("
                "asset_class, headline, narrative, summary(optional), highlights, metrics, signals, evidence, confidence)"
                "를 엄격히 준수하는 JSON 으로 다시 출력하라. "
                "headline 또는 summary 중 최소 하나는 반드시 포함. 추가 설명 금지."
            ),
            "rows_sample": original_rows[:20],
        },
        ensure_ascii=False,
    )
    try:
        raw = await call_llm(
            system_prompt_name=prompt_name,
            user_content=correction,
            max_tokens=1200,
        )
        return extract_json(raw)
    except (ValueError, Exception):  # noqa: BLE001
        return None


async def schema_gate(state: AgentState) -> AgentState:
    """
    분석 결과 → 스키마 검증 → 실패 시 1회 재시도.
    state.gates.schema_gate 에 'pass' | 'fail: <reason>' 기록.
    """
    output = state.get("analyzer_output")

    if not isinstance(output, dict):
        return _mark(state, "fail: analyzer_output is not a dict")

    # analyzer 가 JSON 파싱에서 이미 터졌다면 _parse_error 가 실린다
    if "_parse_error" in output:
        return _mark(state, f"fail: analyzer JSON parse error — {output['_parse_error']}")

    ok, err = _validate(output)
    if ok:
        return _mark(state, "pass")

    # 교정 재시도 1회
    prompt_name = _prompt_for(output.get("asset_class") or state.get("asset_class") or "stock")
    corrected = await _retry_with_correction(
        prompt_name=prompt_name,
        original_rows=state.get("input_data") or [],
        raw_or_parsed=output,
        error_detail=err,
    )
    if corrected is None:
        return _mark(state, f"fail: schema invalid and retry failed — {_short(err)}")

    corrected.setdefault("asset_class", state.get("asset_class", "stock"))
    ok2, err2 = _validate(corrected)
    if not ok2:
        return _mark(state, f"fail: schema invalid after retry — {_short(err2)}")

    # 교정본을 상태에 덮어쓰고 pass 로 마킹
    patched = _mark(state, "pass")
    return {**patched, "analyzer_output": corrected}


def _mark(state: AgentState, status: str) -> AgentState:
    return {**state, "gates": {**state["gates"], "schema_gate": status}}


def _prompt_for(asset_class: str) -> str:
    return {
        "stock": "stock_system",
        "crypto": "crypto_system",
        "fx": "fx_system",
        "macro": "macro_system",
        "mixed": "mixed_system",
        "portfolio": "portfolio_system",
    }.get(asset_class, "stock_system")


def _short(msg: str, limit: int = 160) -> str:
    return msg if len(msg) <= limit else msg[:limit] + "..."
