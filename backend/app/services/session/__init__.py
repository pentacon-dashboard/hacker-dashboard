"""세션 저장소 팩토리 — sprint-05.

환경변수 `COPILOT_SESSION_STORE` 로 구현체를 선택한다.

- memory (기본): InMemorySessionStore 싱글톤 (memory_store 모듈의 _store 공유)
- postgres: PostgresSessionStore (COPILOT_SESSION_STORE_URL 필요)
"""
from __future__ import annotations

import os

from app.services.session.memory_store import InMemorySessionStore
from app.services.session.memory_store import get_session_store as _memory_get_store
from app.services.session.postgres_store import PostgresSessionStore
from app.services.session.protocol import SessionStoreProtocol

__all__ = [
    "SessionStoreProtocol",
    "InMemorySessionStore",
    "PostgresSessionStore",
    "get_session_store",
]

# Postgres 싱글톤 캐시 (memory 는 memory_store 모듈 싱글톤에 위임)
_postgres_store: PostgresSessionStore | None = None

# 테스트에서 None 으로 리셋해 싱글톤 교체 가능
_memory_store: InMemorySessionStore | None = None


def get_session_store() -> InMemorySessionStore | PostgresSessionStore:
    """env: COPILOT_SESSION_STORE=memory|postgres (default: memory).

    반환 타입은 SessionStoreProtocol 을 만족하는 구현체.

    memory 모드: memory_store.get_session_store() 에 위임 → 동일 싱글톤 보장.
    postgres 모드: PostgresSessionStore 싱글톤 생성.
    """
    global _postgres_store, _memory_store

    mode = os.environ.get("COPILOT_SESSION_STORE", "memory").strip().lower()

    if mode == "postgres":
        if _postgres_store is None:
            _postgres_store = PostgresSessionStore()
        return _postgres_store

    # memory 모드: _memory_store 가 테스트에 의해 None 으로 리셋된 경우 재생성
    if _memory_store is None:
        _memory_store = _memory_get_store()
    return _memory_store
