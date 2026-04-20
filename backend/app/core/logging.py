"""
구조화 JSON 로깅 모듈.

- python-json-logger 가 설치된 경우 JSON 포맷 사용, 미설치 시 표준 텍스트 포맷으로 폴백
- request_id 는 X-Request-ID 헤더를 그대로 쓰거나 UUID 자동 생성
- 요청 컨텍스트(request_id, path)는 contextvars 로 전파 → 멀티 코루틴 충돌 없음
"""
from __future__ import annotations

import logging
import sys
import uuid
from contextvars import ContextVar

# 요청 컨텍스트 — 코루틴별 격리
_request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    return _request_id_var.get()


def set_request_id(rid: str) -> None:
    _request_id_var.set(rid)


def configure_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO

    try:
        from pythonjsonlogger.jsonlogger import JsonFormatter  # type: ignore[import-untyped]

        handler = logging.StreamHandler(sys.stdout)
        fmt = JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            rename_fields={"asctime": "ts", "levelname": "level", "name": "logger"},
        )
        handler.setFormatter(fmt)
        root = logging.getLogger()
        root.setLevel(level)
        root.handlers.clear()
        root.addHandler(handler)
    except ImportError:
        # python-json-logger 없으면 표준 텍스트 포맷
        logging.basicConfig(
            stream=sys.stdout,
            level=level,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )

    # uvicorn 기본 핸들러와 충돌 방지
    logging.getLogger("uvicorn.access").propagate = False


logger = logging.getLogger("hacker_dashboard")


def _compute_cache_hit_rate(cache_tokens: dict) -> float | None:
    """
    프롬프트 캐시 히트율. `read / (read + creation + input)`.
    총 토큰이 0 이면 (heuristic 결정 등 LLM 미호출) None 을 반환.
    """
    read = int(cache_tokens.get("read_tokens") or cache_tokens.get("cache_read_input_tokens") or 0)
    creation = int(
        cache_tokens.get("creation_tokens") or cache_tokens.get("cache_creation_input_tokens") or 0
    )
    input_t = int(cache_tokens.get("input_tokens") or 0)
    total = read + creation + input_t
    if total == 0:
        return None
    return round(read / total, 4)


def log_analyze_event(
    *,
    request_id: str,
    asset_class: str,
    duration_ms: int,
    cache_tokens: dict,
    cached: bool = False,
) -> None:
    """
    분석 완료 이벤트 구조화 로그.

    cache_tokens 에서 히트율을 유도해 함께 로깅한다 (docs/agents/cache-strategy.md).
    - cached=True 면 결과 캐시(HIT) → LLM 호출 자체가 없음 → prompt_cache_hit_rate=None
    - cached=False 면 LLM 호출 있었거나 heuristic 으로 바로 결정된 경우.
      prompt_cache_hit_rate 가 None 이면 LLM 호출 0 (heuristic only), 수치면 캐시 히트율.
    """
    prompt_cache_hit_rate = _compute_cache_hit_rate(cache_tokens)
    logger.info(
        "analyze",
        extra={
            "event": "analyze",
            "request_id": request_id,
            "asset_class": asset_class,
            "duration_ms": duration_ms,
            "cache_tokens": cache_tokens,
            "prompt_cache_hit_rate": prompt_cache_hit_rate,
            "x_cache": "HIT" if cached else "MISS",
        },
    )
