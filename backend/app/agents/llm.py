"""
Anthropic client 래퍼.

- system prompt 를 cache_control ephemeral 블록으로 감싸 프롬프트 캐시 활용
- 모델 선택(기본 sonnet, 고난도 opus)을 한 곳에 집중
- 테스트에서 `set_client` 로 주입 가능 (DI 패턴)
- 직전 호출의 usage/cache 메트릭을 `_last_cache_metrics` 에 보관 → API meta 로 전파

실제 anthropic 호출은 `anthropic.AsyncAnthropic` 를 쓴다. respx 가 httpx 레벨에서
mock 하므로, 테스트에서 별도 stub 주입 없이도 응답 고정이 가능하다. 다만 API 키가
없을 때를 대비해 `get_client` 는 lazy 초기화 + 실패 시 명시적 에러를 낸다.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from anthropic import AsyncAnthropic

from app.core.config import settings

# 모델 고정값 (rules/backend.md 기준)
MODEL_SONNET = "claude-sonnet-4-6"
MODEL_OPUS = "claude-opus-4-7"

# 입력 행수가 이 값을 넘으면 복잡 입력으로 판단해 Opus 로 승급
COMPLEX_ROW_THRESHOLD = 300

_PROMPT_DIR = Path(__file__).parent / "prompts"

# DI 훅 — 테스트에서 대체 가능
_client_override: AsyncAnthropic | None = None

# 직전 LLM 호출의 사용량/캐시 메트릭. /analyze 응답 meta.cache 로 노출된다.
# 한 요청 안에서 여러 번 호출되면 누적되므로, API 레이어는 호출 직전 `reset_cache_metrics`
# 로 리셋한 뒤 마지막에 읽어간다.
_last_cache_metrics: dict[str, int] = {
    "cache_read_input_tokens": 0,
    "cache_creation_input_tokens": 0,
    "input_tokens": 0,
    "output_tokens": 0,
}


def load_prompt(name: str) -> str:
    """prompts/<name>.md 를 읽는다. 파일 단위 캐싱은 OS 페이지 캐시에 맡긴다."""
    path = _PROMPT_DIR / f"{name}.md"
    return path.read_text(encoding="utf-8")


def set_client(client: AsyncAnthropic | None) -> None:
    """테스트/의존성 주입용. None 을 넘기면 기본 클라이언트로 리셋."""
    global _client_override
    _client_override = client


def get_client() -> AsyncAnthropic:
    """기본 AsyncAnthropic 싱글턴. API 키 미설정 시에도 객체는 생성된다 (httpx 레벨 mock 호환)."""
    if _client_override is not None:
        return _client_override
    return AsyncAnthropic(api_key=settings.anthropic_api_key)


# 프롬프트를 (정적·캐시대상) / (동적·캐시제외) 두 블록으로 나누기 위한 구분자.
# 프롬프트 파일 어딘가에 `<!-- DYNAMIC -->` 마커가 있으면 그 이후는 cache_control 을
# 적용하지 않는 별도 블록으로 분리한다. Anthropic 은 순차적 블록 prefix 가 일치하면
# 캐시 히트를 인정하므로, 자주 바뀌는 지침을 뒤로 몰면 캐시 히트율이 오른다.
_DYNAMIC_MARKER = "<!-- DYNAMIC -->"


def _with_cache_control(system_text: str) -> list[dict[str, Any]]:
    """
    system 프롬프트를 cache_control 블록으로 래핑.

    `<!-- DYNAMIC -->` 마커가 있으면:
      block[0] = 정적 파트 (cache_control: ephemeral)    ← 장기 캐시 대상
      block[1] = 동적 파트 (cache_control 없음)          ← 매번 변경 가능
    마커가 없으면 전체를 단일 cached 블록으로 래핑 (기존 동작).
    """
    if _DYNAMIC_MARKER in system_text:
        static_part, dynamic_part = system_text.split(_DYNAMIC_MARKER, 1)
        static_part = static_part.rstrip()
        dynamic_part = dynamic_part.lstrip()
        blocks: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": static_part,
                "cache_control": {"type": "ephemeral"},
            }
        ]
        if dynamic_part:
            blocks.append({"type": "text", "text": dynamic_part})
        return blocks

    return [
        {
            "type": "text",
            "text": system_text,
            "cache_control": {"type": "ephemeral"},
        }
    ]


class LLMUnavailableError(RuntimeError):
    """LLM 호출이 비활성화되었을 때(키 없음, DI 미주입) 던진다."""


def _is_api_key_configured() -> bool:
    key = settings.anthropic_api_key
    return bool(key) and key not in {"", "your-key-here", "test-key", "sk-ant-xxx"}


def reset_cache_metrics() -> None:
    """/analyze 요청 시작 직전에 호출. 누적 메트릭을 0 으로 초기화."""
    for k in _last_cache_metrics:
        _last_cache_metrics[k] = 0


def get_cache_metrics() -> dict[str, int]:
    """현재 누적된 캐시/토큰 메트릭 스냅샷."""
    return dict(_last_cache_metrics)


def select_model(row_count: int) -> str:
    """행 수가 임계치를 넘으면 opus, 아니면 sonnet."""
    return MODEL_OPUS if row_count > COMPLEX_ROW_THRESHOLD else MODEL_SONNET


def _record_usage(resp: Any) -> None:
    """anthropic 응답의 usage 블록에서 토큰·캐시 메트릭을 누적한다."""
    usage = getattr(resp, "usage", None)
    if usage is None:
        return
    for key in (
        "cache_read_input_tokens",
        "cache_creation_input_tokens",
        "input_tokens",
        "output_tokens",
    ):
        value = _usage_get(usage, key)
        if value is not None:
            _last_cache_metrics[key] += int(value)


def _usage_get(usage: Any, key: str) -> int | None:
    """usage 가 dict / pydantic 모델 / 기타 객체 어느 형태든 안전하게 읽기."""
    if isinstance(usage, dict):
        v = usage.get(key)
    else:
        v = getattr(usage, key, None)
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


async def call_llm(
    *,
    system_prompt_name: str,
    user_content: str,
    model: str = MODEL_SONNET,
    max_tokens: int = 8192,
    temperature: float = 0.2,
) -> str:
    """
    LLM 1회 호출. system 프롬프트는 prompts/<name>.md 에서 로드.
    assistant 응답 텍스트(문자열)를 반환한다.

    API 키가 없고 DI 클라이언트도 주입되지 않았으면 LLMUnavailableError 를 던진다.
    상위 노드(router/analyzer/gates)는 이를 잡아 안전한 기본값으로 폴백한다.
    """
    if _client_override is None and not _is_api_key_configured():
        raise LLMUnavailableError(
            "anthropic API key not configured and no test client injected"
        )

    client = get_client()
    system_text = load_prompt(system_prompt_name)

    resp = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=_with_cache_control(system_text),
        messages=[{"role": "user", "content": user_content}],
    )

    # usage 가 있으면 기록 (fake client 에서도 usage 를 심어 테스트 가능)
    _record_usage(resp)

    # anthropic 응답: content 는 list[ContentBlock]. 텍스트 블록만 join.
    parts: list[str] = []
    for block in resp.content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "".join(parts).strip()


def extract_json(text: str) -> dict[str, Any]:
    """
    LLM 응답에서 첫 JSON 객체를 추출한다.
    - 코드펜스(```json ... ```) 제거
    - 중괄호 블록을 정규식으로 느슨하게 잡는다 (Claude 가 가끔 설명을 덧붙임)
    실패 시 ValueError 를 올린다 → schema gate 가 잡아서 1회 재시도.
    """
    cleaned = text.strip()

    # 코드펜스 제거 (닫는 펜스가 누락되어도 여는 펜스는 제거)
    if cleaned.startswith("```"):
        first_newline = cleaned.find("\n")
        if first_newline != -1:
            cleaned = cleaned[first_newline + 1 :]
        closing = cleaned.rfind("```")
        if closing != -1:
            cleaned = cleaned[:closing]
        cleaned = cleaned.strip()

    # 먼저 직접 파싱 시도
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # 첫 `{` 부터 짝맞는 `}` 까지 greedy 매칭
    start = cleaned.find("{")
    if start == -1:
        raise ValueError(f"no JSON object found in LLM output: {text[:200]!r}")

    depth = 0
    for i in range(start, len(cleaned)):
        ch = cleaned[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = cleaned[start : i + 1]
                try:
                    parsed = json.loads(candidate)
                    if isinstance(parsed, dict):
                        return parsed
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"malformed JSON in LLM output: {exc}; raw={candidate[:200]!r}"
                    ) from exc

    raise ValueError(f"unbalanced braces in LLM output: {text[:200]!r}")
