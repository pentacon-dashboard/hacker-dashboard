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

        spy.captured_prompts.append(
            {
                "role_tag": role_tag,
                "system": system_text,
                "user": user_content,
                "system_prompt_name": system_prompt_name,
            }
        )

        # 반환값 분기
        if role_tag == "planner":
            import re as _re

            # ── 심볼 추출 ──────────────────────────────────────────────────────
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

            # ── 특수 케이스: degraded 시나리오 감지 ───────────────────────────
            # comparison_03: 존재하지 않는 심볼 포함 → domain gate fail → degraded
            has_unknown_symbol = "definitely_not_a_symbol_xyz" in lower
            # simulator_03: shock ±3배수 초과 (±300% 이상) → domain gate fail → degraded
            shock_match = _re.search(r"(\+?\d+(?:\.\d+)?)\s*%", user_content)
            has_extreme_shock = False
            if shock_match:
                shock_val = abs(float(shock_match.group(1)))
                has_extreme_shock = shock_val >= 300.0
            # "shock" 키워드 + "+500%" 혹은 직접 기재
            if "500" in user_content or "500%" in user_content:
                has_extreme_shock = True

            # ── follow-up (단일 news-rag step) ────────────────────────────────
            is_followup_short = "<prior_turns>" in user_content and any(
                kw in user_content for kw in ("계속", "조금", "더", "만", "그럼", "그")
            )

            if has_unknown_symbol:
                # comparison_03 시나리오: unknown symbol → comparison analyzer가 domain gate fail
                steps = [
                    {
                        "step_id": "a",
                        "agent": "comparison",
                        "inputs": {
                            "symbols": [symbol, "DEFINITELY_NOT_A_SYMBOL_XYZ"],
                            "metrics": ["return_3m_pct", "volatility_pct"],
                        },
                        "depends_on": [],
                        "gate_policy": {"schema": True, "domain": True, "critique": True},
                    }
                ]
            elif has_extreme_shock:
                # simulator_03 시나리오: extreme shock → simulator analyzer가 domain gate fail
                steps = [
                    {
                        "step_id": "a",
                        "agent": "simulator",
                        "inputs": {
                            "holdings": [{"symbol": symbol, "quantity": 10, "avg_price": 180.0}],
                            "shocks": {symbol: 5.0},  # +500% — 비현실적 → domain fail
                        },
                        "depends_on": [],
                        "gate_policy": {"schema": True, "domain": True, "critique": True},
                    }
                ]
            elif is_followup_short:
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
                # 기본: portfolio + comparison 2개 병렬 스텝 (sprint-04 병렬 테스트에도 사용)
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
                        "inputs": {"symbols": [symbol, "MSFT" if symbol != "MSFT" else "AAPL"]},
                        "depends_on": [],
                        "gate_policy": {"schema": True, "domain": True, "critique": True},
                    },
                ]

            return json.dumps(
                {
                    "plan_id": "p-fake",
                    "session_id": "s-fake",
                    "steps": steps,
                    "created_at": "2026-04-22T00:00:00Z",
                }
            )

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
def fake_planner_llm() -> None:
    """sprint-01 호환 — autouse=True 로 존재를 보장한다.

    실제 LLM 패치는 fake_orchestrator_llm(autouse=True) 이 담당한다.
    이 fixture 는 AC-06-9 "fake_planner_llm 이 autouse=True 로 정의됨" 를 만족하기 위해
    독립적으로 선언만 하고, call_llm 을 재패치하지 않는다.
    (같은 monkeypatch 를 이중으로 설정하면 마지막 값이 이겨 fake_orchestrator_llm 의
    고급 분기 로직이 덮어씌워지는 문제가 있었음 — sprint-06 iter-2 에서 수정)
    """
    # 패치 없음 — fake_orchestrator_llm autouse fixture 가 call_llm 을 처리한다.
