"""
Simulator Analyzer — sprint-03.

"AAPL 12개월 50% 오르면 포트 TWR은?" 류 what-if 시뮬레이터.
출력: SimulatorResultCard (type="simulator_result").

shocks 값은 **배율(multiplier)** 단위:
  - 1.5 = +50%
  - 0.8 = -20%
  - 0.01~1.99 범위만 허용 (domain gate)

3단 게이트 정책:
  schema : SimulatorResultCard Pydantic 검증
  domain : shock 값이 [0.01, 1.99] 범위 안
  critique: query 에 없는 심볼에 대한 결과 포함 금지
"""
from __future__ import annotations

from typing import Any

from app.agents.state import AgentState
from app.schemas.copilot import CopilotStep, SimulatorResultCard

# 도메인 게이트 경계 — plan.md 기준 ±99%
_MIN_SHOCK = 0.01   # -99%
_MAX_SHOCK = 1.99   # +99%


def _check_schema(card_dict: dict[str, Any]) -> tuple[bool, str]:
    try:
        SimulatorResultCard.model_validate(card_dict)
        return True, ""
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def _check_domain_shocks(shocks: dict[str, float]) -> tuple[str, str]:
    """shock 값이 [_MIN_SHOCK, _MAX_SHOCK] 범위 안인지 확인."""
    for sym, mult in shocks.items():
        try:
            m = float(mult)
        except (TypeError, ValueError):
            return "fail", f"shock for {sym} is not a number: {mult!r}"
        if not (_MIN_SHOCK <= m <= _MAX_SHOCK):
            return "fail", (
                f"shock for {sym}={m} is outside [{_MIN_SHOCK}, {_MAX_SHOCK}] "
                f"(±99% boundary)"
            )
    return "pass", ""


def _check_critique(card_dict: dict[str, Any], step: CopilotStep) -> tuple[str, str]:
    """결과 심볼이 입력 holdings 에 있는 것만 포함하는지 확인."""
    holdings = step.inputs.get("holdings", [])
    input_symbols = {h.get("symbol", "").upper() for h in holdings}
    shocks = step.inputs.get("shocks", {})
    input_symbols |= {s.upper() for s in shocks}

    result_symbols = {s["symbol"].upper() for s in card_dict.get("scenarios", [])}
    extra = result_symbols - input_symbols
    if extra:
        return "fail", f"result contains symbols not in input: {extra}"
    return "pass", ""


def _compute_card(step: CopilotStep) -> dict[str, Any]:
    """결정론적으로 시뮬레이션 결과를 계산 (LLM 없이)."""
    holdings: list[dict[str, Any]] = step.inputs.get("holdings", [])
    shocks: dict[str, float] = step.inputs.get("shocks", {})
    base_prices: dict[str, float] = step.inputs.get("base_prices", {})

    # 기준 포트폴리오 가치 계산
    base_value = 0.0
    shocked_value = 0.0
    scenarios = []
    sensitivity: dict[str, float] = {}

    for holding in holdings:
        sym = holding.get("symbol", "")
        qty = float(holding.get("quantity", 0))
        avg_price = float(holding.get("avg_price", holding.get("avg_cost", 0)))
        current_price = float(base_prices.get(sym, avg_price))

        holding_base = qty * current_price
        base_value += holding_base

        shock_mult = float(shocks.get(sym, 1.0))
        new_price = current_price * shock_mult
        holding_shocked = qty * new_price
        shocked_value += holding_shocked

        delta_pct = (shock_mult - 1.0) * 100.0
        scenarios.append({
            "symbol": sym,
            "shock": shock_mult,
            "new_value": round(holding_shocked, 4),
            "delta_pct": round(delta_pct, 4),
        })

        # sensitivity: +1pp shock → TWR change
        if base_value > 0:
            sensitivity[sym] = round((holding_base / base_value) * 1.0, 6)

    twr_change = (
        (shocked_value - base_value) / base_value * 100.0
        if base_value > 0
        else 0.0
    )

    return {
        "type": "simulator_result",
        "base_value": round(base_value, 4),
        "shocked_value": round(shocked_value, 4),
        "twr_change_pct": round(twr_change, 4),
        "scenarios": scenarios,
        "sensitivity": sensitivity,
    }


def run(step: CopilotStep) -> dict[str, Any]:
    """
    CopilotStep 을 받아 simulator_result 카드를 생성하고 3단 게이트 결과를 반환.

    반환 형식:
    {
        "card": dict,
        "gate_results": {
            "schema": "pass"|"fail",
            "domain": "pass"|"fail",
            "critique": "pass"|"fail",
        },
    }
    """
    gate_policy = step.gate_policy
    shocks: dict[str, float] = step.inputs.get("shocks", {})

    # ── Domain Gate (early: shock bounds check) ──────────────────────────────
    domain_status, domain_reason = _check_domain_shocks(shocks)
    if gate_policy.domain and domain_status == "fail":
        # 카드를 생성조차 하지 않고 실패 반환
        stub_card = {
            "type": "simulator_result",
            "base_value": 0.0,
            "shocked_value": 0.0,
            "twr_change_pct": 0.0,
            "scenarios": [],
            "sensitivity": {},
            "degraded": True,
        }
        return {
            "card": stub_card,
            "gate_results": {"schema": "skip", "domain": "fail", "critique": "skip"},
        }

    # ── 카드 생성 ────────────────────────────────────────────────────────────
    card_dict = _compute_card(step)

    # ── Schema Gate ──────────────────────────────────────────────────────────
    schema_ok, schema_err = _check_schema(card_dict)
    schema_status = "pass" if schema_ok else "fail"

    if gate_policy.schema_check and not schema_ok:
        return {
            "card": {**card_dict, "degraded": True},
            "gate_results": {"schema": "fail", "domain": "skip", "critique": "skip"},
        }

    # ── Critique Gate ────────────────────────────────────────────────────────
    critique_status, critique_reason = _check_critique(card_dict, step)
    if gate_policy.critique and critique_status == "fail":
        return {
            "card": {**card_dict, "degraded": True},
            "gate_results": {"schema": schema_status, "domain": domain_status, "critique": "fail"},
        }

    return {
        "card": card_dict,
        "gate_results": {
            "schema": schema_status,
            "domain": domain_status,
            "critique": critique_status,
        },
    }


async def run_async(state: AgentState) -> dict[str, Any]:
    """LangGraph 서브그래프 노드 진입점 (비동기)."""
    from app.schemas.copilot import CopilotStep

    copilot_plan = state.get("copilot_plan") or {}
    steps = copilot_plan.get("steps", [])
    sim_step = next((s for s in steps if s.get("agent") == "simulator"), None)
    if sim_step is None:
        return {**state}

    step = CopilotStep.model_validate(sim_step)
    outcome = run(step)

    step_results = dict(state.get("copilot_step_results") or {})
    step_results[step.step_id] = outcome["card"]
    return {**state, "copilot_step_results": step_results}
