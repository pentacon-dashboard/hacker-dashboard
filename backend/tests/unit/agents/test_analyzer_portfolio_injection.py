"""
단위 테스트: BaseAnalyzer._call 의 portfolio_context 주입 불변성 검증.

검증 항목:
  1. portfolio_context=None 시 payload 에 해당 키 자체가 없어야 함
  2. portfolio_context 값이 있으면 payload 에 포함되어야 함
  3. BaseAnalyzer.run(state) 이 state["portfolio_context"] 를 _call 에 정확히 전달
  4. MixedAnalyzer.run 이 자식 state 전파 시 portfolio_context 를 포함

LLM 실제 호출 없이 _call 을 patch 하여 payload JSON 만 검증.
"""
from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from app.agents.analyzers.base import BaseAnalyzer
from app.agents.analyzers.mixed import MixedAnalyzer
from app.agents.state import AgentState


# ── 테스트용 최소 Analyzer 구현 ───────────────────────────────────────────────

class _DummyAnalyzer(BaseAnalyzer):
    """테스트용 최소 analyzer — LLM 호출 없이 payload 를 캡처한다."""

    asset_class = "stock"
    prompt_name = "stock_system"

    async def _call(self, *, rows, query, indicators=None, portfolio_context=None) -> str:
        # 호출 인자를 직렬화해 반환 — 테스트에서 캡처
        payload: dict[str, Any] = {
            "rows": rows[:50],
            "row_count": len(rows),
            "query": query,
        }
        if indicators:
            payload["indicators"] = indicators
        if portfolio_context:
            payload["portfolio_context"] = portfolio_context
        # 테스트가 검증할 수 있도록 인스턴스에 저장
        self._last_payload = payload  # type: ignore[attr-defined]
        return json.dumps({
            "asset_class": "stock",
            "headline": "test",
            "narrative": "test narrative",
            "summary": "test",
            "highlights": [],
            "metrics": {},
            "signals": [],
            "evidence": [],
            "confidence": 0.5,
        })


def _make_state(**kwargs: Any) -> AgentState:
    base: AgentState = {
        "input_data": [{"symbol": "AAPL", "close": 192.5}],
        "query": None,
        "asset_class_hint": "stock",
        "asset_class": "stock",
        "router_reason": "test",
        "analyzer_output": None,
        "gates": {"schema_gate": "pending", "domain_gate": "pending", "critique_gate": "pending"},
        "error": None,
        "snapshots": None,
        "portfolio_context": None,
    }
    base.update(kwargs)  # type: ignore[typeddict-item]
    return base


# ── 1. portfolio_context=None → payload 에 키 없음 ───────────────────────────

@pytest.mark.asyncio
async def test_call_without_portfolio_context_excludes_key() -> None:
    """portfolio_context=None 이면 payload 에 'portfolio_context' 키가 없어야 함."""
    analyzer = _DummyAnalyzer()
    await analyzer._call(
        rows=[{"close": 100.0}],
        query=None,
        indicators=None,
        portfolio_context=None,
    )
    assert "portfolio_context" not in analyzer._last_payload, (  # type: ignore[attr-defined]
        "portfolio_context=None 인데 payload 에 키가 포함되어 있음"
    )


# ── 2. portfolio_context 값이 있으면 payload 에 포함 ─────────────────────────

@pytest.mark.asyncio
async def test_call_with_portfolio_context_includes_key() -> None:
    """portfolio_context 가 dict 면 payload 에 포함되어야 함."""
    ctx = {
        "holdings": [{"market": "yahoo", "code": "AAPL", "quantity": "5", "avg_cost": "185"}],
        "total_value_krw": "1300000",
        "asset_class_breakdown": {"stock_us": 1.0},
        "matched_holding": {"market": "yahoo", "code": "AAPL", "quantity": "5", "avg_cost": "185"},
    }
    analyzer = _DummyAnalyzer()
    await analyzer._call(
        rows=[{"close": 100.0}],
        query=None,
        indicators=None,
        portfolio_context=ctx,
    )
    assert "portfolio_context" in analyzer._last_payload, (  # type: ignore[attr-defined]
        "portfolio_context 가 있는데 payload 에 키가 없음"
    )
    assert analyzer._last_payload["portfolio_context"] == ctx  # type: ignore[attr-defined]


# ── 3. BaseAnalyzer.run(state) → _call 에 portfolio_context 전달 ─────────────

@pytest.mark.asyncio
async def test_run_passes_portfolio_context_to_call() -> None:
    """run(state) 이 state['portfolio_context'] 를 _call 의 portfolio_context 인자로 전달."""
    ctx = {
        "holdings": [],
        "total_value_krw": "0",
        "asset_class_breakdown": {},
        "matched_holding": None,
    }
    state = _make_state(portfolio_context=ctx)

    captured_portfolio_context: list[Any] = []

    original_call = _DummyAnalyzer._call

    async def spy_call(self, *, rows, query, indicators=None, portfolio_context=None):
        captured_portfolio_context.append(portfolio_context)
        # 실제 구현도 실행 (반환값이 필요)
        return await original_call(
            self, rows=rows, query=query, indicators=indicators, portfolio_context=portfolio_context
        )

    analyzer = _DummyAnalyzer()

    with patch.object(_DummyAnalyzer, "_call", spy_call):
        await analyzer.run(state)

    assert len(captured_portfolio_context) == 1
    assert captured_portfolio_context[0] == ctx, (
        f"_call 에 전달된 portfolio_context 가 state 값과 다름: {captured_portfolio_context[0]}"
    )


@pytest.mark.asyncio
async def test_run_passes_none_portfolio_context_when_absent() -> None:
    """state 에 portfolio_context 가 없거나 None 이면 _call 에도 None 전달."""
    state = _make_state(portfolio_context=None)

    captured: list[Any] = []

    original_call = _DummyAnalyzer._call

    async def spy_call(self, *, rows, query, indicators=None, portfolio_context=None):
        captured.append(portfolio_context)
        return await original_call(
            self, rows=rows, query=query, indicators=indicators, portfolio_context=portfolio_context
        )

    analyzer = _DummyAnalyzer()

    with patch.object(_DummyAnalyzer, "_call", spy_call):
        await analyzer.run(state)

    assert captured[0] is None, f"portfolio_context=None 인데 _call 에 {captured[0]} 전달됨"


# ── 4. MixedAnalyzer.run 이 자식 state 에 portfolio_context 포함 ────────────

@pytest.mark.asyncio
async def test_mixed_analyzer_propagates_portfolio_context() -> None:
    """
    MixedAnalyzer.run 이 버킷별 서브 state 를 구성할 때
    portfolio_context 를 포함해야 한다.
    """
    ctx = {
        "holdings": [{"market": "yahoo", "code": "AAPL", "quantity": "5", "avg_cost": "185"}],
        "total_value_krw": "1300000",
        "asset_class_breakdown": {"stock_us": 1.0},
        "matched_holding": None,
    }

    state = _make_state(
        input_data=[
            {"symbol": "AAPL", "close": 192.5},  # stock 버킷
            {"symbol": "KRW-BTC", "close": 120000000},  # crypto 버킷
        ],
        asset_class="mixed",
        portfolio_context=ctx,
    )

    captured_sub_states: list[dict[str, Any]] = []

    async def fake_sub_run(self, sub_state: dict[str, Any]) -> dict[str, Any]:
        captured_sub_states.append(sub_state)
        return {
            "asset_class": sub_state.get("asset_class", "stock"),
            "headline": "sub test",
            "narrative": "sub narrative",
            "summary": "sub",
            "highlights": [],
            "metrics": {},
            "signals": [],
            "evidence": [],
            "confidence": 0.5,
        }

    # BaseAnalyzer.run 을 patch 해서 서브 analyzer 호출을 가로챔
    with patch.object(BaseAnalyzer, "run", fake_sub_run):
        analyzer = MixedAnalyzer()
        result = await analyzer.run(state)

    # 적어도 하나의 서브 state 가 캡처되어야 함
    assert len(captured_sub_states) >= 1, "서브 analyzer 가 전혀 호출되지 않음"

    # 모든 서브 state 에 portfolio_context 가 전파되어야 함
    for sub_state in captured_sub_states:
        assert "portfolio_context" in sub_state, (
            f"서브 state 에 portfolio_context 없음: keys={list(sub_state.keys())}"
        )
        assert sub_state["portfolio_context"] == ctx, (
            f"서브 state portfolio_context 값 불일치: {sub_state['portfolio_context']}"
        )

    # 최종 결과는 merged output
    assert result.get("asset_class") == "mixed"
