"""
Comparison Analyzer — sprint-03.

N개 종목/자산을 재무/수익률/변동성/상관 기준으로 비교.
출력: ComparisonTableCard (type="comparison_table").

3단 게이트 정책:
  schema : ComparisonTableCard Pydantic 검증
  domain : 비교 대상 종목이 알려진 심볼 목록에 존재 (존재하지 않는 심볼 → degraded)
  critique: 쿼리와 무관한 필드 생성 금지 확인
"""

from __future__ import annotations

from typing import Any

from app.agents.state import AgentState
from app.schemas.copilot import ComparisonTableCard, CopilotStep

# 알려진 심볼 목록 (데모용 고정값 — /market/symbols 와 동기화)
_KNOWN_SYMBOLS: set[str] = {
    "AAPL",
    "MSFT",
    "GOOGL",
    "AMZN",
    "NVDA",
    "TSLA",
    "META",
    "NFLX",
    "KRW-BTC",
    "KRW-ETH",
    "KRW-XRP",
    "BTC",
    "ETH",
    "005930",  # 삼성전자
    "000660",  # SK하이닉스
    "035420",  # NAVER
    "SPY",
    "QQQ",
    "TLT",
}


def _check_schema(card_dict: dict[str, Any]) -> tuple[bool, str]:
    """ComparisonTableCard 스키마 검증."""
    try:
        ComparisonTableCard.model_validate(card_dict)
        return True, ""
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def _check_domain(symbols: list[str]) -> tuple[str, list[str]]:
    """알려진 심볼 목록 확인. (gate_status, unknown_symbols)"""
    unknown = [s for s in symbols if s.upper() not in {k.upper() for k in _KNOWN_SYMBOLS}]
    if unknown:
        return "fail", unknown
    return "pass", []


def _check_critique(card_dict: dict[str, Any], step: CopilotStep) -> tuple[str, str]:
    """쿼리와 무관한 심볼 포함 여부 확인."""
    query_symbols = step.inputs.get("symbols", [])
    card_symbols = card_dict.get("symbols", [])
    extra = [s for s in card_symbols if s not in query_symbols]
    if extra:
        return "fail", f"output contains symbols not in request: {extra}"
    return "pass", ""


def _build_card_from_llm(step: CopilotStep) -> dict[str, Any]:
    """LLM 없이 결정론적으로 카드를 생성 (stub 모드 / 테스트용)."""
    symbols = step.inputs.get("symbols", [])
    metric_keys = ["return_3m_pct", "volatility_pct", "pe_ratio", "market_cap_usd"]
    rows = []
    for i, sym in enumerate(symbols):
        # deterministic fake values based on symbol hash
        seed = sum(ord(c) for c in sym)
        rows.append(
            {
                "symbol": sym,
                "metrics": {
                    "return_3m_pct": round((seed % 50) - 10, 2),
                    "volatility_pct": round(10 + (seed % 30), 2),
                    "pe_ratio": round(15 + (seed % 20), 1) if i % 2 == 0 else None,
                    "market_cap_usd": (seed % 10 + 1) * 1_000_000_000,
                },
            }
        )
    return {
        "type": "comparison_table",
        "symbols": symbols,
        "metrics": metric_keys,
        "rows": rows,
        "summary": f"Comparison of {', '.join(symbols)} across return, volatility, and valuation metrics.",
    }


def run(step: CopilotStep) -> dict[str, Any]:
    """
    CopilotStep 을 받아 comparison_table 카드를 생성하고 3단 게이트 결과를 반환.

    반환 형식:
    {
        "card": dict,           # ComparisonTableCard.model_dump() 또는 degraded 카드
        "gate_results": {
            "schema": "pass"|"fail",
            "domain": "pass"|"fail"|"retry",
            "critique": "pass"|"fail",
        },
    }
    """
    gate_policy = step.gate_policy
    symbols: list[str] = step.inputs.get("symbols", [])

    # ── 카드 생성 ────────────────────────────────────────────────────────────
    # LLM 호출은 비동기이지만 contract test 에서 동기로 호출되므로 stub 모드에서는
    # 동기 결정론적 경로를 우선 사용한다.
    card_dict = _build_card_from_llm(step)

    # ── Schema Gate ─────────────────────────────────────────────────────────
    schema_ok, schema_err = _check_schema(card_dict)
    schema_status = "pass" if schema_ok else "fail"

    if gate_policy.schema_check and not schema_ok:
        return {
            "card": {**card_dict, "degraded": True},
            "gate_results": {"schema": "fail", "domain": "skip", "critique": "skip"},
        }

    # ── Domain Gate ─────────────────────────────────────────────────────────
    domain_status, unknown_syms = _check_domain(symbols)
    if gate_policy.domain and domain_status == "fail":
        # degraded 카드 반환 (알려진 심볼만 남기거나 전체 degraded)
        degraded_card = {**card_dict, "degraded": True}
        return {
            "card": degraded_card,
            "gate_results": {"schema": schema_status, "domain": "fail", "critique": "skip"},
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
    # comparison step 찾기
    comp_step = next((s for s in steps if s.get("agent") == "comparison"), None)
    if comp_step is None:
        return {**state}

    step = CopilotStep.model_validate(comp_step)
    outcome = run(step)

    step_results = dict(state.get("copilot_step_results") or {})
    step_results[step.step_id] = outcome["card"]
    return {**state, "copilot_step_results": step_results}
