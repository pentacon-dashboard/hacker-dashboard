"""
llm.py 와 Analyzer base 의 동작 보조 테스트.
- JSON 추출기 (코드펜스, 잉여 텍스트)
- API 키 미설정 시 LLMUnavailableError
- Analyzer 가 파싱 실패를 _parse_error 로 전달
"""

from __future__ import annotations

from typing import Any

import pytest

from app.agents import llm as llm_module
from app.agents.analyzers import get_analyzer
from app.agents.llm import LLMUnavailableError, call_llm, extract_json


def test_extract_json_plain() -> None:
    assert extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_code_fence() -> None:
    text = '```json\n{"x": 2, "y": "hello"}\n```'
    assert extract_json(text) == {"x": 2, "y": "hello"}


def test_extract_json_with_prose() -> None:
    text = 'Here is the output:\n\n{"k": [1,2,3]}\n\nHope this helps.'
    assert extract_json(text) == {"k": [1, 2, 3]}


def test_extract_json_malformed_raises() -> None:
    with pytest.raises(ValueError):
        extract_json("no json at all")


def test_extract_json_empty_raises() -> None:
    with pytest.raises(ValueError):
        extract_json("")


@pytest.mark.asyncio
async def test_call_llm_raises_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """API 키가 없고 DI 클라이언트도 없으면 LLMUnavailableError."""
    llm_module.set_client(None)
    monkeypatch.setattr(llm_module.settings, "openai_api_key", "")
    with pytest.raises(LLMUnavailableError):
        await call_llm(system_prompt_name="router_system", user_content="test")


@pytest.mark.asyncio
async def test_analyzer_returns_parse_error_on_bad_json(fake_client) -> None:
    """LLM 이 JSON 이 아닌 텍스트를 주면 analyzer 는 _parse_error 로 포장."""

    def _bad_response(_kwargs: dict[str, Any]) -> str:
        return "이건 JSON 이 아닙니다. 그냥 텍스트입니다."

    fake_client.responses["analyzer"] = _bad_response

    analyzer = get_analyzer("stock")
    state: dict[str, Any] = {
        "input_data": [{"symbol": "AAPL", "close": 100}],
        "query": None,
        "asset_class_hint": None,
        "asset_class": "stock",
        "router_reason": "",
        "analyzer_output": None,
        "gates": {"schema_gate": "pending", "domain_gate": "pending", "critique_gate": "pending"},
        "error": None,
    }
    out = await analyzer.run(state)  # type: ignore[arg-type]
    assert "_parse_error" in out
    assert out["asset_class"] == "stock"


@pytest.mark.asyncio
async def test_analyzer_injects_asset_class_if_missing(fake_client) -> None:
    """LLM 응답에 asset_class 가 없어도 Analyzer 가 자산군을 주입한다."""
    fake_client.responses["analyzer"] = {
        "summary": "no asset_class field",
        "highlights": [],
        "metrics": {},
        "evidence": [],
    }
    analyzer = get_analyzer("crypto")
    state: dict[str, Any] = {
        "input_data": [{"symbol": "KRW-BTC", "close": 100}],
        "query": None,
        "asset_class_hint": None,
        "asset_class": "crypto",
        "router_reason": "",
        "analyzer_output": None,
        "gates": {"schema_gate": "pending", "domain_gate": "pending", "critique_gate": "pending"},
        "error": None,
    }
    out = await analyzer.run(state)  # type: ignore[arg-type]
    assert out["asset_class"] == "crypto"


def test_get_analyzer_unknown_falls_back_to_stock() -> None:
    analyzer = get_analyzer("nonexistent_class")  # 등록 안 된 타입
    assert analyzer.asset_class == "stock"


@pytest.mark.asyncio
async def test_critique_gate_swallows_llm_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """critique 호출이 실패해도 파이프라인은 관용 모드로 통과."""
    from app.agents.gates.critique import critique_gate

    llm_module.set_client(None)
    monkeypatch.setattr(llm_module.settings, "openai_api_key", "")
    state: dict[str, Any] = {
        "input_data": [{"close": 100}],
        "query": None,
        "asset_class_hint": None,
        "asset_class": "stock",
        "router_reason": "",
        "analyzer_output": {
            "asset_class": "stock",
            "summary": "s",
            "highlights": [],
            "metrics": {},
            "evidence": [],
        },
        "gates": {"schema_gate": "pass", "domain_gate": "pass", "critique_gate": "pending"},
        "error": None,
    }
    result = await critique_gate(state)  # type: ignore[arg-type]
    assert result["gates"]["critique_gate"].startswith("pass")
    assert "unavailable" in result["gates"]["critique_gate"]
