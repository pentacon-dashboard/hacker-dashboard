from __future__ import annotations

import json
from typing import Any

import pytest

from app.agents.gates.critique import critique_gate


@pytest.mark.asyncio
async def test_critique_gate_normalizes_supported_claims_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_call_llm(**_: Any) -> str:
        return json.dumps(
            {
                "verdict": "fail",
                "per_claim": [
                    {"claim": "other 비중 0.728", "status": "supported"},
                    {"claim": "KRW 노출 0.999", "status": "supported"},
                ],
                "reason": "all claims supported",
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr("app.agents.gates.critique.call_llm", fake_call_llm)

    state = {
        "input_data": [{"symbol": "AAPL", "quantity": 1}],
        "analyzer_output": {
            "summary": "AAPL 보유",
            "highlights": ["AAPL 1주"],
            "evidence": [{"claim": "AAPL 1주", "rows": [0]}],
            "metrics": {"n_holdings": 1},
        },
        "gates": {"schema_gate": "pass", "domain_gate": "pass", "critique_gate": "pending"},
    }

    result = await critique_gate(state)  # type: ignore[arg-type]

    assert result["gates"]["critique_gate"] == "pass"
    assert result["analyzer_output"]["_critique"]["verdict"] == "pass"
    assert result["analyzer_output"]["_critique"]["reason"] == "all claims supported"


@pytest.mark.asyncio
async def test_critique_gate_repairs_rounded_currency_metric_claim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_call_llm(**_: Any) -> str:
        return json.dumps(
            {
                "verdict": "fail",
                "per_claim": [{"claim": "비원화 노출 0.1%", "status": "hallucinated"}],
                "reason": "비원화 노출 0.1%는 입력 데이터에서 확인할 수 없는 수치입니다.",
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr("app.agents.gates.critique.call_llm", fake_call_llm)

    state = {
        "input_data": [{"symbol": "AAPL", "currency": "USD"}],
        "analyzer_output": {
            "summary": "비원화 노출 0.1%",
            "highlights": ["비원화 노출 0.1%"],
            "evidence": [{"claim": "비원화 노출 0.1%", "rows": [0]}],
            "metrics": {"currency_exposure": {"USD": 0.000614, "KRW": 0.999386}},
        },
        "gates": {"schema_gate": "pass", "domain_gate": "pass", "critique_gate": "pending"},
    }

    result = await critique_gate(state)  # type: ignore[arg-type]

    assert result["gates"]["critique_gate"] == "pass"
    assert result["analyzer_output"]["_critique"]["verdict"] == "pass"
    assert result["analyzer_output"]["_critique"]["per_claim"][0]["status"] == "supported"


@pytest.mark.asyncio
async def test_critique_gate_keeps_unsupported_claims_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_call_llm(**_: Any) -> str:
        return json.dumps(
            {
                "verdict": "fail",
                "per_claim": [{"claim": "없는 수익률", "status": "unsupported"}],
                "reason": "claim not supported by evidence",
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr("app.agents.gates.critique.call_llm", fake_call_llm)

    state = {
        "input_data": [{"symbol": "AAPL", "quantity": 1}],
        "analyzer_output": {
            "summary": "AAPL 보유",
            "highlights": ["없는 수익률"],
            "evidence": [{"claim": "AAPL 1주", "rows": [0]}],
            "metrics": {"n_holdings": 1},
        },
        "gates": {"schema_gate": "pass", "domain_gate": "pass", "critique_gate": "pending"},
    }

    result = await critique_gate(state)  # type: ignore[arg-type]

    assert result["gates"]["critique_gate"] == "fail: claim not supported by evidence"
    assert result["analyzer_output"]["_critique"]["verdict"] == "fail"
