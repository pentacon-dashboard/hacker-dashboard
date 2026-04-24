"""
OpenAI client 래퍼.

- 모델 선택(기본 gpt-4o-mini, 고난도 gpt-4o)을 한 곳에 집중
- 테스트에서 `set_client` 로 주입 가능 (DI 패턴)
- 직전 호출의 usage/cache 메트릭을 `_last_cache_metrics` 에 보관 → API meta 로 전파
- OpenAI 는 자동 프롬프트 캐싱(cached_tokens)을 지원하므로 별도 cache_control 불필요

실제 OpenAI 호출은 `openai.AsyncOpenAI` 를 쓴다. 테스트에서는 `set_client` 로
FakeClient 를 주입해 LLM 없이 동작한다.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

from app.core.config import settings

# 모델 고정값 — 가성비(cost-efficient) 전략으로 기본·고난도 모두 gpt-4o-mini 사용.
# 고난도 구간을 분리하고 싶으면 MODEL_HIGH 를 "gpt-4o" 로 변경.
MODEL_DEFAULT = "gpt-4o-mini"
MODEL_HIGH = "gpt-4o-mini"

# deprecated aliases — 기존 import 경로 호환 유지
MODEL_SONNET = MODEL_DEFAULT
MODEL_OPUS = MODEL_HIGH

# 입력 행수가 이 값을 넘으면 복잡 입력으로 판단해 고난도 모델로 승급.
# 현재 MODEL_DEFAULT == MODEL_HIGH 라 승급 효과 없음 (비용 고정).
COMPLEX_ROW_THRESHOLD = 300

_PROMPT_DIR = Path(__file__).parent / "prompts"

# DI 훅 — 테스트에서 대체 가능
_client_override: AsyncOpenAI | None = None

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


def set_client(client: AsyncOpenAI | None) -> None:
    """테스트/의존성 주입용. None 을 넘기면 기본 클라이언트로 리셋."""
    global _client_override
    _client_override = client


def get_client() -> AsyncOpenAI:
    """기본 AsyncOpenAI 싱글턴. API 키 미설정 시에도 객체는 생성된다 (DI mock 호환)."""
    if _client_override is not None:
        return _client_override
    return AsyncOpenAI(api_key=settings.openai_api_key)


class LLMUnavailableError(RuntimeError):
    """LLM 호출이 비활성화되었을 때(키 없음, DI 미주입) 던진다."""


def _is_api_key_configured() -> bool:
    key = settings.openai_api_key
    return bool(key) and key not in {"", "your-key-here", "test-key", "sk-xxx"}


def reset_cache_metrics() -> None:
    """/analyze 요청 시작 직전에 호출. 누적 메트릭을 0 으로 초기화."""
    for k in _last_cache_metrics:
        _last_cache_metrics[k] = 0


def get_cache_metrics() -> dict[str, int]:
    """현재 누적된 캐시/토큰 메트릭 스냅샷."""
    return dict(_last_cache_metrics)


def select_model(row_count: int) -> str:
    """행 수가 임계치를 넘으면 고난도 모델, 아니면 기본 모델."""
    return MODEL_HIGH if row_count > COMPLEX_ROW_THRESHOLD else MODEL_DEFAULT


def _record_usage(resp: Any) -> None:
    """응답의 usage 블록에서 토큰·캐시 메트릭을 누적한다.

    OpenAI 스타일(prompt_tokens, completion_tokens, prompt_tokens_details.cached_tokens)과
    Anthropic 스타일(input_tokens, output_tokens, cache_read_input_tokens …) 모두 처리한다.
    테스트용 fake 클라이언트가 Anthropic 스타일 필드를 사용하는 경우에도 올바르게 누적된다.
    """
    usage = getattr(resp, "usage", None)
    if usage is None:
        return

    # ── Anthropic 스타일 직접 매핑 (테스트 fake 클라이언트 우선) ────────────────
    cache_read = _usage_get(usage, "cache_read_input_tokens")
    if cache_read is not None:
        _last_cache_metrics["cache_read_input_tokens"] += cache_read
        cache_creation = _usage_get(usage, "cache_creation_input_tokens") or 0
        _last_cache_metrics["cache_creation_input_tokens"] += cache_creation
        _last_cache_metrics["input_tokens"] += _usage_get(usage, "input_tokens") or 0
        _last_cache_metrics["output_tokens"] += _usage_get(usage, "output_tokens") or 0
        return

    # ── OpenAI 스타일 ────────────────────────────────────────────────────────────
    # prompt_tokens, completion_tokens, prompt_tokens_details.cached_tokens
    prompt_tokens = _usage_get(usage, "prompt_tokens") or 0
    completion_tokens = _usage_get(usage, "completion_tokens") or 0

    # cached_tokens 는 prompt_tokens_details 하위에 있다
    cached_tokens = 0
    details = getattr(usage, "prompt_tokens_details", None)
    if details is not None:
        cached_tokens = _usage_get(details, "cached_tokens") or 0
    elif isinstance(usage, dict):
        details_dict = usage.get("prompt_tokens_details") or {}
        cached_tokens = int(details_dict.get("cached_tokens", 0))

    _last_cache_metrics["input_tokens"] += prompt_tokens
    _last_cache_metrics["output_tokens"] += completion_tokens
    # OpenAI 자동 캐싱: cached 토큰은 cache_read_input_tokens 에 매핑
    _last_cache_metrics["cache_read_input_tokens"] += cached_tokens


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
    model: str = MODEL_DEFAULT,
    max_tokens: int = 8192,
    temperature: float = 0.2,
    expect_json: bool = False,
) -> str:
    """
    LLM 1회 호출. system 프롬프트는 prompts/<name>.md 에서 로드.
    assistant 응답 텍스트(문자열)를 반환한다.

    API 키가 없고 DI 클라이언트도 주입되지 않았으면 LLMUnavailableError 를 던진다.
    상위 노드(router/analyzer/gates)는 이를 잡아 안전한 기본값으로 폴백한다.
    """
    if _client_override is None and not _is_api_key_configured():
        raise LLMUnavailableError(
            "openai API key not configured and no test client injected"
        )

    client = get_client()
    system_text = load_prompt(system_prompt_name)

    response_format: dict[str, str] | None = (
        {"type": "json_object"} if expect_json else None
    )

    resp = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_text},
            {"role": "user", "content": user_content},
        ],
        response_format=response_format,  # type: ignore[arg-type]
        temperature=temperature,
        max_tokens=max_tokens,
    )

    # usage 가 있으면 기록 (fake client 에서도 usage 를 심어 테스트 가능)
    _record_usage(resp)

    return resp.choices[0].message.content or ""


def extract_json(text: str) -> dict[str, Any]:
    """
    LLM 응답에서 첫 JSON 객체를 추출한다.
    - 코드펜스(```json ... ```) 제거
    - 중괄호 블록을 정규식으로 느슨하게 잡는다 (LLM 이 가끔 설명을 덧붙임)
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
