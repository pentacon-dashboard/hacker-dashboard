"""harness/conftest.py — sprint-01~06 전체 하네스에 공통 적용되는 autouse fixture.

AC-06-9: fake_orchestrator_llm / fake_planner_llm 이 autouse=True 로 선언되어
ANTHROPIC_API_KEY 없이 모든 harness contract 가 실행된다.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import pytest


# ───────────────────────── Spy dataclass ────────────────────────────────────


@dataclass
class _FakeOrchestratorLLM:
    """planner + sub-agent + critique LLM 호출을 결정론적 fake 로 대체하는 스파이.

    captured_prompts — 매 LLM 호출마다 아래 형태로 append:
      { "role_tag": "planner"|"critique"|"unknown", "system": str, "user": str }
    """

    captured_prompts: list[dict[str, Any]] = field(default_factory=list)


# ───────────────────────── fake_orchestrator_llm ────────────────────────────


@pytest.fixture(autouse=True, scope="function")
def fake_orchestrator_llm(monkeypatch: pytest.MonkeyPatch) -> _FakeOrchestratorLLM:
    """planner + sub-agent + 최종 통합 LLM 호출을 결정론적 fake 로 대체.

    대체 대상: app.agents.llm.call_llm (planner/critique/final 공용 진입).
    autouse=True 이므로 harness/ 디렉토리 내 모든 테스트에 자동 적용.
    """
    spy = _FakeOrchestratorLLM()

    async def _fake(
        *,
        system_prompt_name: str,
        user_content: str,
        model: str | None = None,
        max_tokens: int = 4096,
        **_: Any,
    ) -> str:
        lower = user_content.lower()

        # role_tag 판별
        if "copilot_planner" in system_prompt_name:
            role_tag = "planner"
        elif "critique" in system_prompt_name:
            role_tag = "critique"
        elif any(m in lower for m in ("plan_id", "session_id")) and "steps" in lower:
            role_tag = "planner"
        elif any(m in lower for m in ("critique", "verdict", "final")):
            role_tag = "critique"
        else:
            role_tag = "unknown"

        # system prompt 텍스트 로드
        try:
            from app.agents.llm import load_prompt  # type: ignore[import]
            system_text = load_prompt(system_prompt_name)
        except Exception:  # noqa: BLE001
            system_text = system_prompt_name

        spy.captured_prompts.append({
            "role_tag": role_tag,
            "system": system_text,
            "user": user_content,
            "system_prompt_name": system_prompt_name,
        })

        # 반환값 분기
        if role_tag == "planner":
            import re as _re
            symbol = "AAPL"
            if "aapl" in lower:
                symbol = "AAPL"
            elif "msft" in lower:
                symbol = "MSFT"
            elif "nvda" in lower or "nvidia" in lower:
                symbol = "NVDA"
            elif "tsla" in lower:
                symbol = "TSLA"

            prior_match = _re.search(
                r"<prior_turns>.*?query:.*?([A-Z]{2,5}).*?</prior_turns>",
                user_content,
                _re.DOTALL,
            )
            if prior_match:
                symbol = prior_match.group(1)

            is_followup_short = (
                "<prior_turns>" in user_content
                and any(kw in user_content for kw in ("계속", "조금", "더", "만", "그럼", "그"))
            )
            if is_followup_short:
                steps = [
                    {
                        "step_id": "a",
                        "agent": "news-rag",
                        "inputs": {"symbol": symbol},
                        "depends_on": [],
                        "gate_policy": {"schema": True, "domain": True, "critique": True},
                    }
                ]
            else:
                steps = [
                    {
                        "step_id": "a",
                        "agent": "portfolio",
                        "inputs": {"symbol": symbol},
                        "depends_on": [],
                        "gate_policy": {"schema": True, "domain": True, "critique": True},
                    },
                    {
                        "step_id": "b",
                        "agent": "comparison",
                        "inputs": {"symbol": symbol},
                        "depends_on": [],
                        "gate_policy": {"schema": True, "domain": True, "critique": True},
                    },
                ]

            return json.dumps({
                "plan_id": "p-fake",
                "session_id": "s-fake",
                "steps": steps,
                "created_at": "2026-04-22T00:00:00Z",
            })

        if role_tag == "critique":
            return json.dumps({"verdict": "pass", "ok": True, "text": "fake critique pass"})

        # 일반 step token/result
        return json.dumps({"type": "text", "body": "fake card"})

    monkeypatch.setattr("app.agents.llm.call_llm", _fake, raising=False)

    # 세션 저장소 초기화 (테스트 격리)
    try:
        from app.services.session import get_session_store  # type: ignore[import]
        store = get_session_store()
        if hasattr(store, "reset_all"):
            store.reset_all()
    except Exception:  # noqa: BLE001
        pass

    return spy


# ───────────────────────── fake_planner_llm ─────────────────────────────────


@pytest.fixture(autouse=True, scope="function")
def fake_planner_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    """sprint-01 호환 — `/copilot/plan` 엔드포인트 호출용 planner fake.

    fake_orchestrator_llm 과 동일한 패치 대상이므로 둘 다 autouse 여도 충돌 없음
    (동일 monkeypatch 키를 마지막으로 설정된 값이 이김).
    autouse=True 로 harness 전 테스트 함수에서 Anthropic 실 호출 차단.
    """
    _FAKE_PLAN: dict[str, Any] = {
        "plan_id": "p-fake-plan",
        "session_id": "sess-fake-plan",
        "created_at": "2026-04-22T00:00:00Z",
        "steps": [
            {
                "step_id": "s1",
                "agent": "portfolio",
                "inputs": {"symbol": "AAPL"},
                "depends_on": [],
                "gate_policy": {"schema": True, "domain": True, "critique": True},
            }
        ],
    }

    async def _fake_plan_llm(
        *,
        system_prompt_name: str,
        user_content: str,
        **_: Any,
    ) -> str:
        lower = user_content.lower()
        if "comparison" in lower or "비교" in lower:
            plan = dict(_FAKE_PLAN)
            plan["steps"] = [
                {
                    "step_id": "c1",
                    "agent": "comparison",
                    "inputs": {"symbols": ["AAPL", "MSFT"]},
                    "depends_on": [],
                    "gate_policy": {"schema": True, "domain": True, "critique": True},
                }
            ]
            return json.dumps(plan)
        return json.dumps(_FAKE_PLAN)

    monkeypatch.setattr("app.agents.llm.call_llm", _fake_plan_llm, raising=False)
