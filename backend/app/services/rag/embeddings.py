"""Embedding provider 분기 모듈.

sprint-02: COPILOT_EMBED_PROVIDER 환경변수로 provider 선택.
  - fake  (기본값): sha256 기반 결정론적 1024차원 L2-정규화 벡터
  - openai: 미구현 (NotImplementedError)
  - voyage: 미구현 (NotImplementedError)

fake_embed 계약 (contract.md 고정):
  1. digest = hashlib.sha256(text.encode("utf-8")).digest()  # 32 bytes
  2. 4-byte slice → struct.unpack("<f", ...) → 8 float32. nan/inf → 0.0
  3. 8개 float 를 128회 repeat → slice 로 정확히 1024개
  4. L2 정규화: v / max(||v||_2, 1e-12)
  5. list[float] 반환
"""
from __future__ import annotations

import hashlib
import math
import os
import struct


def fake_embed(text: str) -> list[float]:
    """결정론적 fake 임베딩. 동일 text → 동일 1024차원 L2-정규화 벡터."""
    # 1. SHA-256 digest (32 bytes)
    digest = hashlib.sha256(text.encode("utf-8")).digest()

    # 2. 4-byte slice → little-endian float32 (8개). nan/inf → 0.0
    raw: list[float] = []
    for i in range(0, 32, 4):
        (val,) = struct.unpack("<f", digest[i : i + 4])
        if not math.isfinite(val):
            val = 0.0
        raw.append(val)

    # 3. 1024개가 될 때까지 repeat (128회) 후 정확히 slice
    repeated = (raw * 128)[:1024]

    # 4. L2 정규화
    norm = math.sqrt(sum(x * x for x in repeated))
    denom = max(norm, 1e-12)
    normalized = [x / denom for x in repeated]

    return normalized


def _embed_openai(text: str) -> list[float]:
    raise NotImplementedError(
        "openai embedding provider는 sprint-03 이후 구현 예정. "
        "COPILOT_EMBED_PROVIDER=fake 사용."
    )


def _embed_voyage(text: str) -> list[float]:
    raise NotImplementedError(
        "voyage embedding provider는 sprint-03 이후 구현 예정. "
        "COPILOT_EMBED_PROVIDER=fake 사용."
    )


def get_active_provider() -> str:
    """현재 활성 embedding provider 이름 반환. 기본값 'fake'."""
    return os.environ.get("COPILOT_EMBED_PROVIDER", "fake").lower()


def embed(text: str) -> list[float]:
    """활성 provider 로 텍스트를 임베딩한다."""
    provider = get_active_provider()
    if provider == "fake":
        return fake_embed(text)
    elif provider == "openai":
        return _embed_openai(text)
    elif provider == "voyage":
        return _embed_voyage(text)
    else:
        raise ValueError(
            f"알 수 없는 COPILOT_EMBED_PROVIDER: {provider!r}. "
            "fake | openai | voyage 중 하나여야 합니다."
        )
