from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.schemas.copilot import ActiveContext, PriorTurn, SessionTurn
from app.services.copilot.context import build_active_context, format_context_for_agent
from app.services.copilot.intent import classify_copilot_intent
from app.services.session.memory_store import InMemorySessionStore, make_turn_id


def _prior_turn(idx: int, query: str = "NVDA 분석해줘") -> SessionTurn:
    return SessionTurn(
        turn_id=f"turn-{idx}",
        query=query,
        final_card={
            "type": "text",
            "content": f"검증된 이전 답변 {idx}: NVDA 비중과 리스크를 설명했습니다.",
        },
    )


def _active_context() -> ActiveContext:
    return ActiveContext(
        prior_turns=[
            PriorTurn(
                turn_id="turn-1",
                query="NVDA와 TSLA 비교해줘",
                summary="NVDA 변동성과 TSLA 민감도를 검증된 비교 결과로 설명했습니다.",
            )
        ],
        user_query="<user_query>방금 내용을 쉽게 설명해줘</user_query>",
    )


async def _async_tuple(first: str, second: str) -> tuple[str, str]:
    return first, second


def test_client_resolution_result_exposes_structured_candidates() -> None:
    from app.services.copilot.orchestrator import _client_resolution_result

    resolution = SimpleNamespace(
        status="ambiguous",
        reason="name_match",
        candidates=(
            SimpleNamespace(
                user_id="pb-demo",
                client_id="client-007",
                label="VIP-7",
                display_name="Kim",
                display_label="Kim",
                match_type="name",
                matched_value="Kim",
                holdings_count=4,
                last_activity_at=None,
            ),
            SimpleNamespace(
                user_id="pb-demo",
                client_id="client-003",
                label="VIP-3",
                display_name="Kim",
                display_label="Kim",
                match_type="name",
                matched_value="Kim",
                holdings_count=1,
                last_activity_at=None,
            ),
        ),
    )

    result = _client_resolution_result(resolution)
    card = result["card"]

    assert card["client_resolution_status"] == "ambiguous"
    assert card["client_resolution_reason"] == "name_match"
    assert card["requires_client_selection"] is True
    assert [candidate["client_id"] for candidate in card["client_candidates"]] == [
        "client-007",
        "client-003",
    ]


def test_conversation_shortcut_allows_explanatory_follow_up_with_prior_context() -> None:
    decision = classify_copilot_intent(
        "방금 말한 비중을 고객에게 쉽게 설명해줘",
        active_context=_active_context(),
    )

    assert decision.route == "conversation"
    assert decision.reason == "explanatory_follow_up"


@pytest.mark.parametrize(
    "query",
    [
        "방금 내용 기준으로 리밸런싱 꼭 해야 해?",
        "방금 말한 NVDA랑 TSLA를 다시 비교해줘",
        "그 종목 최근 공시 요약",
        "오늘 뉴스 근거로 설명해줘",
        "현재 포트폴리오 비중 다시 계산해줘",
        "AAPL 목표 비중을 20%로 바꾸면?",
    ],
)
def test_conversation_shortcut_blocks_new_analysis_or_investment_judgement(query: str) -> None:
    decision = classify_copilot_intent(query, active_context=_active_context())

    assert decision.route == "analysis"
    assert decision.reason in {
        "new_analysis_keyword",
        "investment_judgement_keyword",
        "ticker_or_numeric_input",
        "client_or_portfolio_reference",
    }


def test_conversation_shortcut_blocks_explicit_client_portfolio_selection() -> None:
    decision = classify_copilot_intent(
        "client-902 \ud3ec\ud2b8\ud3f4\ub9ac\uc624 \uc694\uc57d",
        active_context=_active_context(),
    )

    assert decision.route == "analysis"
    assert decision.reason == "client_or_portfolio_reference"


def test_conversation_shortcut_blocks_client_existence_correction() -> None:
    decision = classify_copilot_intent(
        "방금 고객 B라고 한 건 틀렸는데?",
        active_context=_active_context(),
    )

    assert decision.route == "analysis"
    assert decision.reason == "correction_or_missing_context"


def test_conversation_shortcut_requires_prior_context() -> None:
    decision = classify_copilot_intent(
        "방금 답을 한 문장으로 요약해줘",
        active_context=ActiveContext(prior_turns=[], user_query="<user_query />"),
    )

    assert decision.route == "analysis"
    assert decision.reason == "no_prior_context"


@pytest.mark.asyncio
async def test_active_context_keeps_eight_recent_turns() -> None:
    store = InMemorySessionStore()
    for idx in range(10):
        await store.append_turn("s1", _prior_turn(idx, query=f"질문 {idx}"))

    context = await build_active_context(
        session_id="s1",
        user_query="방금 내용을 쉽게 설명해줘",
        store=store,
    )

    assert len(context.prior_turns) == 8
    assert [turn.turn_id for turn in context.prior_turns] == [f"turn-{idx}" for idx in range(2, 10)]


def test_agent_context_formatter_includes_prior_turn_summaries() -> None:
    context = ActiveContext(
        prior_turns=[
            PriorTurn(
                turn_id=make_turn_id(),
                query="포트폴리오 리스크 요약",
                summary="집중도와 변동성 근거를 검증했습니다.",
            )
        ],
        user_query="<user_query>고객용으로 바꿔줘</user_query>",
    )

    formatted = format_context_for_agent(context)

    assert "Conversation context" in formatted
    assert "포트폴리오 리스크 요약" in formatted
    assert "집중도와 변동성 근거를 검증했습니다." in formatted
    assert "Do not introduce new calculations" in formatted


@pytest.mark.asyncio
async def test_stream_uses_conversation_shortcut_and_saves_turn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import json

    from app.services.copilot.orchestrator import stream_copilot_query

    store = InMemorySessionStore()
    await store.append_turn("s1", _prior_turn(1))
    captured_prompt: dict[str, str] = {}

    async def fake_call_llm(**kwargs: str) -> str:
        captured_prompt["system_prompt_name"] = str(kwargs["system_prompt_name"])
        captured_prompt["user_content"] = str(kwargs["user_content"])
        return "이전 답변을 쉬운 고객용 문장으로 다시 정리했습니다."

    monkeypatch.setattr("app.agents.llm.call_llm", fake_call_llm, raising=False)
    monkeypatch.setattr(
        "app.services.copilot.orchestrator.get_session_store",
        lambda: store,
        raising=False,
    )

    events: list[dict] = []
    async for chunk in stream_copilot_query(
        "방금 내용을 고객용으로 쉽게 설명해줘", session_id="s1"
    ):
        for block in chunk.decode().split("\n\n"):
            for line in block.splitlines():
                if line.startswith("data:"):
                    events.append(json.loads(line[len("data:") :].strip()))

    plan = next(event["plan"] for event in events if event.get("type") == "plan.ready")
    final_card = next(event["card"] for event in events if event.get("type") == "final.card")

    assert plan["steps"][0]["inputs"]["mode"] == "conversation"
    assert final_card["content"] == "이전 답변을 쉬운 고객용 문장으로 다시 정리했습니다."
    assert captured_prompt["system_prompt_name"] == "copilot_conversation_system"
    assert "Conversation context" in captured_prompt["user_content"]
    assert "검증된 이전 답변 1" in captured_prompt["user_content"]
    assert len(await store.get_turns("s1", limit=10)) == 2


@pytest.mark.asyncio
async def test_portfolio_agent_degrades_when_requested_client_has_no_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.schemas.copilot import CopilotStep, GatePolicy
    from app.services.copilot.orchestrator import _run_agent_llm

    captured_client_ids: list[str] = []

    async def fake_fetch_portfolio_context(
        *,
        client_id: str,
        client_name: str | None = None,
    ) -> dict:
        captured_client_ids.append(client_id)
        return {
            "portfolio_context_unavailable": True,
            "reason": "client_portfolio_not_found",
            "client_context": {"client_id": client_id, "client_name": "고객 B"},
            "indicators": {},
            "holdings": [],
        }

    async def fail_call_llm(**_: str) -> str:
        pytest.fail("missing client portfolio should not call LLM")

    monkeypatch.setattr(
        "app.services.copilot.orchestrator._fetch_portfolio_context",
        fake_fetch_portfolio_context,
        raising=False,
    )
    async def fake_resolve_client(*_: object, **__: object) -> tuple[str, bool, str | None, None]:
        return "client-002", True, "고객 B", None

    monkeypatch.setattr(
        "app.services.copilot.orchestrator._resolve_client_for_copilot",
        fake_resolve_client,
        raising=False,
    )
    monkeypatch.setattr("app.agents.llm.call_llm", fail_call_llm, raising=False)

    step = CopilotStep(
        step_id="a",
        agent="portfolio",
        inputs={},
        depends_on=[],
        gate_policy=GatePolicy.model_validate({"schema": True, "domain": True, "critique": True}),
    )

    result = await _run_agent_llm(step, "고객 B 포트폴리오 요약")

    assert captured_client_ids == ["client-002"]
    assert result["card"]["degraded"] is True
    assert "고객 B" in result["card"]["content"]
    assert "포트폴리오 원장 데이터가 없습니다" in result["card"]["content"]


@pytest.mark.parametrize(
    ("raw_client_id", "expected"),
    [
        ("C", "client-003"),
        ("client C", "client-003"),
        ("client-C", "client-003"),
        ("customer C", "client-003"),
        ("client 3", "client-003"),
        ("client-003", "client-003"),
        ("\uace0\uac1d C", "client-003"),
        ("C \uace0\uac1d", "client-003"),
    ],
)
def test_resolve_requested_client_normalizes_planner_client_labels(
    raw_client_id: str,
    expected: str,
) -> None:
    from app.schemas.copilot import CopilotStep, GatePolicy
    from app.services.copilot.orchestrator import _resolve_requested_client

    step = CopilotStep(
        step_id="a",
        agent="portfolio",
        inputs={"client_id": raw_client_id},
        depends_on=[],
        gate_policy=GatePolicy.model_validate({"schema": True, "domain": True, "critique": True}),
    )

    assert _resolve_requested_client(step, "client C portfolio summary") == (expected, True)


def test_client_portfolio_query_builds_deterministic_plan() -> None:
    from app.services.copilot.orchestrator import _build_client_portfolio_plan

    plan = _build_client_portfolio_plan("고객 C 포트폴리오 요약", session_id="s1")

    assert plan is not None
    assert len(plan.steps) == 1
    assert plan.steps[0].agent == "portfolio"
    assert plan.steps[0].inputs["client_id"] == "고객 C"
    english_plan = _build_client_portfolio_plan("client C portfolio summary", session_id="s1")
    assert english_plan is not None
    assert english_plan.steps[0].inputs["client_id"] == "client C"
    assert _build_client_portfolio_plan("TSLA 최근 1년 분석", session_id="s1") is None


@pytest.mark.asyncio
async def test_portfolio_agent_uses_normalized_planner_client_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.schemas.copilot import CopilotStep, GatePolicy
    from app.services.copilot.orchestrator import _run_agent_llm

    captured_client_ids: list[str] = []
    captured_prompt: dict[str, str] = {}

    async def fake_fetch_portfolio_context(
        *,
        client_id: str,
        client_name: str | None = None,
    ) -> dict:
        captured_client_ids.append(client_id)
        return {
            "client_context": {"client_id": client_id, "client_name": "Client C"},
            "indicators": {
                "total_value": "13718214.00",
                "pnl_pct": "-32.14",
                "n_holdings": 3,
                "asset_class_breakdown": {"stock_us": "1.0000"},
            },
            "holdings": [{"market": "yahoo", "code": "AAPL", "value_krw": "6810075.00"}],
        }

    async def fake_call_llm(**kwargs: str) -> str:
        captured_prompt["system_prompt_name"] = str(kwargs["system_prompt_name"])
        captured_prompt["user_content"] = str(kwargs["user_content"])
        return "Client C portfolio summary from verified context."

    monkeypatch.setattr(
        "app.services.copilot.orchestrator._fetch_portfolio_context",
        fake_fetch_portfolio_context,
        raising=False,
    )

    async def fake_resolve_client(*_: object, **__: object) -> tuple[str, bool, str | None, None]:
        return "client-003", True, "Client C", None

    monkeypatch.setattr(
        "app.services.copilot.orchestrator._resolve_client_for_copilot",
        fake_resolve_client,
        raising=False,
    )
    monkeypatch.setattr("app.agents.llm.call_llm", fake_call_llm, raising=False)

    step = CopilotStep(
        step_id="a",
        agent="portfolio",
        inputs={"client_id": "C"},
        depends_on=[],
        gate_policy=GatePolicy.model_validate({"schema": True, "domain": True, "critique": True}),
    )

    result = await _run_agent_llm(step, "client C portfolio summary")

    assert captured_client_ids == ["client-003"]
    assert result["card"]["degraded"] is False
    assert "Client C" in result["card"]["content"]
    assert "13,718,214원" in result["card"]["content"]
    assert "미국 주식 100.00%" in result["card"]["content"]
    assert captured_prompt["system_prompt_name"] == "portfolio_system"
    assert '"client_id": "client-003"' in captured_prompt["user_content"]


@pytest.mark.asyncio
async def test_portfolio_deterministic_summary_skips_subjective_critique(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import asyncio

    from app.schemas.copilot import CopilotStep, GatePolicy
    from app.services.copilot.orchestrator import _execute_step

    async def fake_fetch_portfolio_context(
        *,
        client_id: str,
        client_name: str | None = None,
    ) -> dict:
        return {
            "client_context": {"client_id": client_id, "client_name": "Client C"},
            "indicators": {
                "total_value": "13718214.00",
                "pnl_pct": "-32.14",
                "n_holdings": 3,
                "asset_class_breakdown": {"stock_us": "1.0000"},
            },
            "holdings": [{"market": "yahoo", "code": "TSLA", "value_krw": "3693249.00", "pnl_pct": "127.09"}],
        }

    async def fake_call_llm(**_: str) -> str:
        return "LLM text should be replaced by deterministic portfolio text."

    async def fail_critique(*_: object, **__: object) -> tuple[str, str]:
        pytest.fail("deterministic portfolio summary should not call subjective critique")

    monkeypatch.setattr(
        "app.services.copilot.orchestrator._fetch_portfolio_context",
        fake_fetch_portfolio_context,
        raising=False,
    )

    async def fake_resolve_client(*_: object, **__: object) -> tuple[str, bool, str | None, None]:
        return "client-003", True, "Client C", None

    monkeypatch.setattr(
        "app.services.copilot.orchestrator._resolve_client_for_copilot",
        fake_resolve_client,
        raising=False,
    )
    monkeypatch.setattr("app.agents.llm.call_llm", fake_call_llm, raising=False)
    monkeypatch.setattr(
        "app.services.copilot.orchestrator._critique_gate",
        fail_critique,
        raising=False,
    )

    step = CopilotStep(
        step_id="a",
        agent="portfolio",
        inputs={"client_id": "C"},
        depends_on=[],
        gate_policy=GatePolicy.model_validate({"schema": True, "domain": True, "critique": True}),
    )

    result = await _execute_step(step, 0, asyncio.Queue(), "client C portfolio summary")

    assert result["degraded"] is False
    assert "13,718,214원" in result["card"]["content"]


@pytest.mark.asyncio
async def test_final_gate_preserves_client_resolution_safety_card(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import asyncio

    from app.services.copilot.orchestrator import _run_final_gate

    async def fail_synthesizer(*_: object, **__: object) -> str:
        pytest.fail("client resolution safety states must not call final LLM synthesizer")

    async def fail_critique(*_: object, **__: object) -> tuple[str, str]:
        pytest.fail("client resolution safety states must not call subjective critique")

    monkeypatch.setattr(
        "app.services.copilot.orchestrator._run_final_synthesizer_llm",
        fail_synthesizer,
        raising=False,
    )
    monkeypatch.setattr(
        "app.services.copilot.orchestrator._critique_gate",
        fail_critique,
        raising=False,
    )

    step_results = {
        "a": {
            "step_id": "a",
            "card": {
                "type": "text",
                "content": "일치하는 고객이 여러 명입니다. 고객을 선택해 주세요.",
                "degraded": True,
                "degraded_reason": "ambiguous",
                "client_resolution_status": "ambiguous",
                "client_resolution_reason": "name_match",
                "requires_client_selection": True,
                "client_candidates": [
                    {"client_id": "client-007", "display_label": "Kim"},
                    {"client_id": "client-003", "display_label": "Kim"},
                ],
            },
            "degraded": True,
            "gate_results": {"schema": "pass", "domain": "fail", "critique": "skip"},
        }
    }

    card = await _run_final_gate(step_results, "Kim portfolio summary", asyncio.Queue())

    assert card["content"] == "일치하는 고객이 여러 명입니다. 고객을 선택해 주세요."
    assert card["degraded"] is True
    assert card["client_resolution_status"] == "ambiguous"
    assert card["requires_client_selection"] is True
    assert [candidate["client_id"] for candidate in card["client_candidates"]] == [
        "client-007",
        "client-003",
    ]


@pytest.mark.asyncio
async def test_final_gate_uses_llm_synthesizer(monkeypatch: pytest.MonkeyPatch) -> None:
    import asyncio

    from app.services.copilot.orchestrator import _run_final_gate

    captured: dict[str, str] = {}

    async def fake_call_llm(**kwargs: str) -> str:
        captured["system_prompt_name"] = str(kwargs["system_prompt_name"])
        captured["user_content"] = str(kwargs["user_content"])
        return "LLM이 최종 답변을 자연스럽게 정리했습니다."

    monkeypatch.setattr("app.agents.llm.call_llm", fake_call_llm, raising=False)
    monkeypatch.setattr(
        "app.services.copilot.orchestrator._critique_gate",
        lambda *args, **kwargs: _async_tuple("pass", "fake critique pass"),
        raising=False,
    )

    step_results = {
        "a": {
            "step_id": "a",
            "card": {"type": "text", "content": "고객 A 총 평가금액은 100원입니다."},
            "degraded": False,
            "gate_results": {"schema": "pass", "domain": "pass", "critique": "pass"},
        }
    }

    card = await _run_final_gate(step_results, "고객 A 요약", asyncio.Queue())

    assert card["content"] == "LLM이 최종 답변을 자연스럽게 정리했습니다."
    assert card["degraded"] is False
    assert captured["system_prompt_name"] == "copilot_synthesizer_system"
    assert "고객 A 총 평가금액은 100원입니다." in captured["user_content"]


@pytest.mark.asyncio
async def test_final_gate_keeps_degraded_status_from_steps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import asyncio

    from app.services.copilot.orchestrator import _run_final_gate

    async def fake_call_llm(**_: str) -> str:
        return "제한된 근거를 바탕으로 요약했습니다."

    monkeypatch.setattr("app.agents.llm.call_llm", fake_call_llm, raising=False)
    monkeypatch.setattr(
        "app.services.copilot.orchestrator._critique_gate",
        lambda *args, **kwargs: _async_tuple("pass", "fake critique pass"),
        raising=False,
    )

    step_results = {
        "a": {
            "step_id": "a",
            "card": {
                "type": "text",
                "content": "고객 B(client-002)의 포트폴리오 원장 데이터가 없습니다.",
                "degraded": True,
            },
            "degraded": True,
            "gate_results": {"schema": "pass", "domain": "fail", "critique": "skip"},
        }
    }

    card = await _run_final_gate(step_results, "고객 B 포트폴리오 요약", asyncio.Queue())

    assert card["content"] == "제한된 근거를 바탕으로 요약했습니다."
    assert card["degraded"] is True


@pytest.mark.asyncio
async def test_final_gate_falls_back_when_synthesizer_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import asyncio

    from app.agents.llm import LLMUnavailableError
    from app.services.copilot.orchestrator import _run_final_gate

    async def fake_call_llm(**_: str) -> str:
        raise LLMUnavailableError("no key")

    monkeypatch.setattr("app.agents.llm.call_llm", fake_call_llm, raising=False)
    monkeypatch.setattr(
        "app.services.copilot.orchestrator._critique_gate",
        lambda *args, **kwargs: _async_tuple("pass", "fake critique pass"),
        raising=False,
    )

    step_results = {
        "a": {
            "step_id": "a",
            "card": {"type": "text", "content": "기존 로컬 합성 문장입니다."},
            "degraded": False,
            "gate_results": {"schema": "pass", "domain": "pass", "critique": "pass"},
        }
    }

    card = await _run_final_gate(step_results, "요약", asyncio.Queue())

    assert "기존 로컬 합성 문장입니다." in card["content"]
    assert card["degraded"] is True
