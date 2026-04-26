"""
Golden 테스트 공용 fixture.

전략:
- **모듈 수준 DI** 를 쓴다: `app.agents.llm.set_client(FakeClient())` 로
  가짜 클라이언트를 주입해 `chat.completions.create` 를 원하는 응답으로 고정한다.
- OpenAI SDK 인터페이스(`chat.completions.create`) 를 흉내낸다.
- API 키 없이 100% 동작한다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from app.agents import llm as llm_module

_SAMPLES_DIR = Path(__file__).parent / "samples"


# ─────────────────────────── 가짜 OpenAI 클라이언트 ───────────────────────


@dataclass
class _Usage:
    """Fake usage 객체.

    Anthropic 스타일 필드명을 사용한다 (테스트 고정값과의 호환).
    llm._record_usage 가 Anthropic/OpenAI 양쪽 모두를 처리하므로 동작한다.
    """

    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class _Message:
    content: str
    role: str = "assistant"


@dataclass
class _Choice:
    message: _Message
    index: int = 0
    finish_reason: str = "stop"


@dataclass
class _Response:
    choices: list[_Choice]
    usage: _Usage | None = None


@dataclass
class _Completions:
    parent: FakeAnthropicClient

    async def create(self, **kwargs: Any) -> _Response:
        # OpenAI 스타일: messages 리스트에서 system 메시지 추출
        messages = kwargs.get("messages") or []
        system_text = ""
        for msg in messages:
            if isinstance(msg, dict) and msg.get("role") == "system":
                system_text = msg.get("content", "")
                break

        route = _detect_route(system_text)
        self.parent.calls.append({"route": route, "kwargs": kwargs})

        usage = self.parent.usage_per_route.get(route) or self.parent.default_usage

        if route in self.parent.responses:
            payload = self.parent.responses[route]
            if callable(payload):
                payload = payload(kwargs)
            text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
            return _Response(choices=[_Choice(message=_Message(content=text))], usage=usage)

        # fallback: 빈 JSON
        return _Response(choices=[_Choice(message=_Message(content="{}"))], usage=usage)


@dataclass
class _ChatNamespace:
    completions: _Completions


@dataclass
class FakeAnthropicClient:
    """
    openai.AsyncOpenAI 의 최소 surface 만 흉내낸다.
    `responses` 에 {'router': dict_or_str, 'analyzer': ..., 'critique': ...} 형태로 응답을 등록한다.
    `usage_per_route` 또는 `default_usage` 로 응답에 토큰/캐시 메트릭을 심을 수 있다.

    클래스 이름은 하위 호환을 위해 FakeAnthropicClient 를 유지한다.
    """

    responses: dict[str, Any] = field(default_factory=dict)
    calls: list[dict[str, Any]] = field(default_factory=list)
    usage_per_route: dict[str, _Usage] = field(default_factory=dict)
    default_usage: _Usage | None = None

    def __post_init__(self) -> None:
        self.chat = _ChatNamespace(completions=_Completions(parent=self))


def _detect_route(system_text: str) -> str:
    """system 프롬프트 첫 몇백 바이트에서 라우트를 결정."""
    head = system_text[:300]
    if "Meta Router" in head or ("asset_class" in head and "Router" in head):
        return "router"
    if "Critique Verifier" in head or ("verdict" in head and "per_claim" in head):
        return "critique"
    # 서브 analyzer 헤더 매칭. 새 analyzer 추가 시 여기 추가.
    if (
        "Stock Analyzer" in head
        or "Crypto Analyzer" in head
        or "FX Analyzer" in head
        or "Portfolio Analyzer" in head
        or "Macro Analyzer" in head
        or "Mixed (Multi-Asset) Analyzer" in head
        or "Rebalance Analyzer" in head
    ):
        return "analyzer"
    return "unknown"


# ─────────────────────────── pytest fixtures ────────────────────────────────


@pytest.fixture
def fake_client() -> FakeAnthropicClient:
    """응답이 비어있는 가짜 클라이언트. 테스트가 setup 에서 채운다."""
    client = FakeAnthropicClient()
    llm_module.set_client(client)  # type: ignore[arg-type]
    yield client
    llm_module.set_client(None)


@pytest.fixture
def golden_samples() -> dict[str, dict[str, Any]]:
    """samples/*.json 을 모두 로드해 {id: sample} 딕셔너리로 반환."""
    out: dict[str, dict[str, Any]] = {}
    for path in sorted(_SAMPLES_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        out[data["id"]] = data
    return out


@pytest.fixture
def prime_client_from_sample(fake_client: FakeAnthropicClient):
    """
    golden sample 하나를 받아 fake_client 의 responses 를 자동 세팅한다.
    반환값은 setup 함수 (sample -> None).
    """

    def _setup(sample: dict[str, Any]) -> None:
        fake_client.responses.clear()
        # Router 응답은 실제 파이프라인에서 heuristic 으로 결정되지만,
        # LLM fallback 경로를 위해 준비
        fake_client.responses["router"] = {
            "asset_class": sample["expected_asset_class"],
            "router_reason": f"mocked router for {sample['id']}",
            "confidence": 0.95,
            "detected_symbols": [],
        }
        if "mock_analyzer_output" in sample:
            fake_client.responses["analyzer"] = sample["mock_analyzer_output"]
        if "mock_critique" in sample:
            fake_client.responses["critique"] = sample["mock_critique"]

    return _setup
