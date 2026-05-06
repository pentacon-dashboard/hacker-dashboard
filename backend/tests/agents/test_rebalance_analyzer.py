"""
RebalanceAnalyzer 단위 테스트.

검증 항목:
  1. actions=[] + drift ≈ 0 → LLM 미호출 + "이미 목표 비중" 지름길
  2. actions=[] + drift 큰 경우 → "실행 가능 액션 없음" 응답 + warnings 1개
  3. 정상 케이스: fake client 로 LLM 응답 고정 → schema/domain/critique 모두 pass
  4. Domain gate fail: narrative 가 너무 짧으면 fail
  5. Domain gate fail: 금지어 포함 시 fail
  6. Critique gate warn: narrative 에 actions 에 없는 종목 언급 시 warn
  7. 영어 산문 잔존 시 결정적 한국어 해석으로 대체
  8. LLM unavailable 시 schema_gate=fail, analysis=None
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import pytest

from app.agents import llm as llm_module
from app.agents.analyzers.rebalance import RebalanceAnalyzer
from app.schemas.rebalance import (
    RebalanceAction,
    RebalanceConstraints,
    TargetAllocation,
)

# ───────────────────────────── Fake OpenAI client ─────────────────────────────


@dataclass
class _FakeMessage:
    content: str
    role: str = "assistant"


@dataclass
class _FakeChoice:
    message: _FakeMessage
    index: int = 0
    finish_reason: str = "stop"


@dataclass
class _Response:
    choices: list[_FakeChoice]
    usage: Any = None


@dataclass
class _Completions:
    parent: FakeClient

    async def create(self, **kwargs: Any) -> _Response:
        self.parent.calls.append(kwargs)
        payload = self.parent.next_response
        if payload is None:
            text = "{}"
        elif isinstance(payload, str):
            text = payload
        else:
            text = json.dumps(payload, ensure_ascii=False)
        return _Response(choices=[_FakeChoice(message=_FakeMessage(content=text))])


@dataclass
class _ChatNamespace:
    completions: _Completions


@dataclass
class FakeClient:
    next_response: Any = None
    calls: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.chat = _ChatNamespace(completions=_Completions(parent=self))


@pytest.fixture
def fake_llm():
    client = FakeClient()
    llm_module.set_client(client)  # type: ignore[arg-type]
    yield client
    llm_module.set_client(None)


# ───────────────────────────── Helpers ─────────────────────────────


def _target() -> TargetAllocation:
    return TargetAllocation(stock_kr=0.2, stock_us=0.4, crypto=0.3, cash=0.1, fx=0.0)


def _constraints() -> RebalanceConstraints:
    return RebalanceConstraints(
        max_single_weight=0.5,
        min_trade_krw=Decimal("100000"),
        allow_fractional=True,
    )


def _make_action(
    *,
    action: str = "sell",
    market: str = "upbit",
    code: str = "KRW-BTC",
    asset_class: str = "crypto",
    quantity: str = "0.02",
    value: str | None = "1700000",
    reason: str = "test reason",
) -> RebalanceAction:
    return RebalanceAction(
        action=action,
        market=market,
        code=code,
        asset_class=asset_class,
        quantity=Decimal(quantity),
        estimated_value_krw=Decimal(value) if value is not None else None,
        reason=reason,
    )


# ───────────────────────────── 1. Empty actions shortcut (balanced) ────────────


@pytest.mark.asyncio
async def test_empty_actions_balanced_shortcut(fake_llm: FakeClient) -> None:
    """actions=[] + drift<1% → LLM 호출 없이 '이미 목표 비중' 응답."""
    analyzer = RebalanceAnalyzer()
    drift = {"stock_kr": 0.002, "stock_us": -0.003, "crypto": 0.001, "cash": 0.0, "fx": 0.0}
    analysis, gates = await analyzer.analyze(
        actions=[],
        drift=drift,
        current_allocation={"stock_kr": 0.2, "stock_us": 0.4, "crypto": 0.3, "cash": 0.1, "fx": 0},
        target_allocation=_target(),
        constraints=_constraints(),
    )
    assert len(fake_llm.calls) == 0, "shortcut 이지만 LLM 호출됨"
    assert analysis is not None
    assert gates == {"schema_gate": "pass", "domain_gate": "pass", "critique_gate": "pass"}
    assert "이미 목표" in analysis.headline or "도달" in analysis.headline
    assert analysis.warnings == []
    assert analysis.confidence >= 0.9


# ───────────────────────────── 2. Empty actions + large drift (constraint) ─────


@pytest.mark.asyncio
async def test_empty_actions_with_large_drift(fake_llm: FakeClient) -> None:
    """actions=[] 이지만 drift 가 큼 → '실행 가능 액션 없음' 응답 + warnings."""
    analyzer = RebalanceAnalyzer()
    drift = {"stock_kr": 0.2, "stock_us": -0.3, "crypto": 0.1, "cash": 0.0, "fx": 0.0}
    analysis, gates = await analyzer.analyze(
        actions=[],
        drift=drift,
        current_allocation={"stock_kr": 0.4, "stock_us": 0.1, "crypto": 0.4, "cash": 0.1, "fx": 0},
        target_allocation=_target(),
        constraints=_constraints(),
    )
    assert len(fake_llm.calls) == 0
    assert analysis is not None
    assert len(analysis.warnings) >= 1
    assert gates["schema_gate"] == "pass"
    assert gates["domain_gate"] == "pass"


# ───────────────────────────── 3. Normal case — all gates pass ─────────────────


@pytest.mark.asyncio
async def test_normal_case_all_gates_pass(fake_llm: FakeClient) -> None:
    """fake LLM 응답 → schema/domain/critique 모두 pass."""
    fake_llm.next_response = {
        "headline": "코인 비중 74% → 30% 축소 권장",
        "narrative": (
            "crypto 비중이 목표 대비 44%p 초과되어 집중 리스크가 큽니다. "
            "KRW-BTC 약 170만원을 매도하고 stock_us 보강을 위해 AAPL 3주를 매수합니다."
        ),
        "warnings": ["max_single_weight 제약 확인"],
        "confidence": 0.82,
    }
    analyzer = RebalanceAnalyzer()
    actions = [
        _make_action(action="sell", code="KRW-BTC", asset_class="crypto"),
        _make_action(
            action="buy",
            market="yahoo",
            code="AAPL",
            asset_class="stock_us",
            quantity="3",
            value="850000",
            reason="stock_us 부족분 매수",
        ),
    ]
    analysis, gates = await analyzer.analyze(
        actions=actions,
        drift={"crypto": 0.44, "stock_us": -0.21, "stock_kr": -0.13, "cash": -0.1, "fx": 0},
        current_allocation={
            "crypto": 0.74,
            "stock_us": 0.19,
            "stock_kr": 0.07,
            "cash": 0.0,
            "fx": 0,
        },
        target_allocation=_target(),
        constraints=_constraints(),
    )
    assert len(fake_llm.calls) == 1
    assert analysis is not None
    assert gates["schema_gate"] == "pass"
    assert gates["domain_gate"] == "pass"
    assert gates["critique_gate"] == "pass"
    assert "KRW-BTC" in analysis.narrative
    assert "AAPL" in analysis.narrative
    assert "crypto" not in analysis.narrative
    assert "stock_us" not in analysis.narrative
    assert "44퍼센트포인트" in analysis.narrative
    assert analysis.warnings == ["단일 종목 최대 비중 제약 확인"]


# ───────────────────────────── 4. Domain gate fail — narrative too short ───────


@pytest.mark.asyncio
async def test_domain_gate_fail_narrative_too_short(fake_llm: FakeClient) -> None:
    fake_llm.next_response = {
        "headline": "리밸런싱",
        "narrative": "짧음.",  # < 20 chars
        "warnings": [],
        "confidence": 0.5,
    }
    analyzer = RebalanceAnalyzer()
    actions = [_make_action()]
    analysis, gates = await analyzer.analyze(
        actions=actions,
        drift={"crypto": 0.1},
        current_allocation={"crypto": 0.4},
        target_allocation=_target(),
        constraints=_constraints(),
    )
    assert gates["schema_gate"] == "pass"
    assert gates["domain_gate"].startswith("fail"), f"expected fail, got {gates['domain_gate']}"
    assert "narrative too short" in gates["domain_gate"]


# ───────────────────────────── 5. Domain gate fail — forbidden term ────────────


@pytest.mark.asyncio
async def test_domain_gate_fail_forbidden_term(fake_llm: FakeClient) -> None:
    fake_llm.next_response = {
        "headline": "코인 축소",
        "narrative": "KRW-BTC 매도하면 수익이 반드시 오른다. 확실히 오른다 투자 조언.",
        "warnings": [],
        "confidence": 0.7,
    }
    analyzer = RebalanceAnalyzer()
    actions = [_make_action()]
    analysis, gates = await analyzer.analyze(
        actions=actions,
        drift={"crypto": 0.1},
        current_allocation={"crypto": 0.4},
        target_allocation=_target(),
        constraints=_constraints(),
    )
    assert gates["domain_gate"].startswith("fail"), f"expected fail, got {gates['domain_gate']}"
    assert "forbidden term" in gates["domain_gate"]


# ───────────────────────────── 6. Critique gate warn — unknown code ────────────


@pytest.mark.asyncio
async def test_critique_gate_warn_unknown_code(fake_llm: FakeClient) -> None:
    fake_llm.next_response = {
        "headline": "코인 축소",
        "narrative": (
            "crypto 비중이 과도해 KRW-BTC 를 매도합니다. "
            "NVDA 와 TSLA 를 추가 매수하는 것도 좋은 대안입니다."
        ),
        "warnings": [],
        "confidence": 0.7,
    }
    analyzer = RebalanceAnalyzer()
    # actions 에는 KRW-BTC 만 있음 → NVDA, TSLA 는 unknown
    actions = [_make_action(code="KRW-BTC")]
    analysis, gates = await analyzer.analyze(
        actions=actions,
        drift={"crypto": 0.1},
        current_allocation={"crypto": 0.4},
        target_allocation=_target(),
        constraints=_constraints(),
    )
    assert gates["schema_gate"] == "pass"
    assert gates["domain_gate"] == "pass"
    assert gates["critique_gate"].startswith("warn:"), (
        f"expected warn, got {gates['critique_gate']}"
    )
    assert "NVDA" in gates["critique_gate"] or "TSLA" in gates["critique_gate"]


# ───────────────────────────── 7. Schema gate fail — invalid JSON ──────────────


@pytest.mark.asyncio
async def test_schema_gate_fail_invalid_json(fake_llm: FakeClient) -> None:
    fake_llm.next_response = "this is not json at all"
    analyzer = RebalanceAnalyzer()
    actions = [_make_action()]
    analysis, gates = await analyzer.analyze(
        actions=actions,
        drift={"crypto": 0.1},
        current_allocation={"crypto": 0.4},
        target_allocation=_target(),
        constraints=_constraints(),
    )
    assert analysis is None
    assert gates["schema_gate"].startswith("fail")
    # downstream gates remain pending
    assert gates["domain_gate"] == "pending"
    assert gates["critique_gate"] == "pending"


# ───────────────────────────── 8. Korean fallback for English prose ───────────


@pytest.mark.asyncio
async def test_english_prose_falls_back_to_korean(fake_llm: FakeClient) -> None:
    """영어 산문이 남으면 결정적 한국어 해석으로 대체한다."""
    fake_llm.next_response = {
        "headline": "Recommend reducing crypto exposure",
        "narrative": "Reduce KRW-BTC and buy AAPL because allocation drift is high.",
        "warnings": ["Check trade costs"],
        "confidence": 0.86,
    }
    analyzer = RebalanceAnalyzer()
    actions = [
        _make_action(action="sell", code="KRW-BTC", asset_class="crypto"),
        _make_action(
            action="buy",
            market="yahoo",
            code="AAPL",
            asset_class="stock_us",
            quantity="3",
            value="850000",
            reason="미국 주식 부족분 매수",
        ),
    ]
    analysis, gates = await analyzer.analyze(
        actions=actions,
        drift={"crypto": 0.44, "stock_us": -0.21, "stock_kr": -0.13, "cash": -0.1, "fx": 0},
        current_allocation={
            "crypto": 0.74,
            "stock_us": 0.19,
            "stock_kr": 0.07,
            "cash": 0.0,
            "fx": 0,
        },
        target_allocation=_target(),
        constraints=_constraints(),
    )

    assert analysis is not None
    assert gates["schema_gate"] == "pass"
    assert gates["domain_gate"].startswith("warn: korean_fallback")
    combined = f"{analysis.headline} {analysis.narrative} {' '.join(analysis.warnings)}"
    assert "Recommend" not in combined
    assert "Reduce" not in combined
    assert "allocation" not in combined
    assert "암호화폐" in combined
    assert "KRW-BTC" in combined
    assert "AAPL" in combined


# ───────────────────────────── 9. LLM unavailable ──────────────────────────────


@pytest.mark.asyncio
async def test_llm_unavailable() -> None:
    """DI 미주입 + API key 미설정 → schema_gate=fail llm_unavailable."""
    llm_module.set_client(None)
    # API 키가 실제로 있을 수 있으니 명시적으로 LLMUnavailableError 를 유도하기 위해
    # settings 을 건드리는 대신 분기 자체를 검증하려면 fake_llm 미사용 조건에서 실제 호출이
    # 발생해야 한다. 대신 call_llm 의 is_api_key_configured 분기를 건너뛰는 방법:
    # ANTHROPIC_API_KEY 가 비어있거나 'test-key' 여야 한다.
    # 안전하게 settings 를 패치.
    from app.core import config as config_module

    original_key = config_module.settings.openai_api_key
    try:
        config_module.settings.openai_api_key = ""
        analyzer = RebalanceAnalyzer()
        actions = [_make_action()]
        analysis, gates = await analyzer.analyze(
            actions=actions,
            drift={"crypto": 0.1},
            current_allocation={"crypto": 0.4},
            target_allocation=_target(),
            constraints=_constraints(),
        )
        assert analysis is None
        assert gates["schema_gate"].startswith("fail")
        assert "llm_unavailable" in gates["schema_gate"]
    finally:
        config_module.settings.openai_api_key = original_key


# ───────────────────────────── 10. Payload construction ────────────────────────


@pytest.mark.asyncio
async def test_payload_includes_all_required_fields(fake_llm: FakeClient) -> None:
    """user_content 에 actions/drift/current/target/constraints 5 필드 모두 포함."""
    fake_llm.next_response = {
        "headline": "부분 리밸런싱 조정",
        "narrative": "crypto 비중이 과도해 KRW-BTC 를 매도해 drift 를 해소합니다.",
        "warnings": [],
        "confidence": 0.8,
    }
    analyzer = RebalanceAnalyzer()
    actions = [_make_action()]
    await analyzer.analyze(
        actions=actions,
        drift={"crypto": 0.1},
        current_allocation={"crypto": 0.4},
        target_allocation=_target(),
        constraints=_constraints(),
    )
    assert len(fake_llm.calls) == 1
    # OpenAI 스타일: messages[0]=system, messages[1]=user
    user_msg = next(m for m in fake_llm.calls[0]["messages"] if m.get("role") == "user")
    payload = json.loads(user_msg["content"])
    assert "actions" in payload and len(payload["actions"]) == 1
    assert "drift" in payload
    assert "current_allocation" in payload
    assert "target_allocation" in payload
    assert "constraints" in payload
    # actions 필드는 JSON 모드 직렬화이므로 Decimal 이 문자열
    assert payload["actions"][0]["code"] == "KRW-BTC"


# ───────────────────────────── 11. target_allocation as dict ───────────────────


@pytest.mark.asyncio
async def test_target_allocation_accepts_plain_dict(fake_llm: FakeClient) -> None:
    """target_allocation 이 TargetAllocation 이 아닌 plain dict 여도 동작."""
    fake_llm.next_response = {
        "headline": "리밸런싱 조정",
        "narrative": "KRW-BTC 매도해 비중을 조정합니다. 서술이 충분히 깁니다.",
        "warnings": [],
        "confidence": 0.7,
    }
    analyzer = RebalanceAnalyzer()
    actions = [_make_action()]
    analysis, gates = await analyzer.analyze(
        actions=actions,
        drift={"crypto": 0.1},
        current_allocation={"crypto": 0.4},
        target_allocation={"stock_kr": 0.2, "stock_us": 0.4, "crypto": 0.3, "cash": 0.1, "fx": 0.0},
        constraints=_constraints(),
    )
    assert analysis is not None
    assert gates["schema_gate"] == "pass"
