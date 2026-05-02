from __future__ import annotations

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
    }


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
    async for chunk in stream_copilot_query("방금 내용을 고객용으로 쉽게 설명해줘", session_id="s1"):
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
