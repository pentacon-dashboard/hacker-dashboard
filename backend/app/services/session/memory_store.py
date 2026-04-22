"""InMemorySessionStore — sprint-05: SessionStoreProtocol 구현체.

sprint-04 에서 이관 + Protocol 준수.
테스트 격리 및 로컬 개발용으로 유지 (삭제 금지).
TTL/max_turns 정책은 COPILOT_SESSION_MAX_TURNS / COPILOT_SESSION_TTL_DAYS 환경변수 기반.
"""
from __future__ import annotations

import datetime
import os
import uuid

from app.schemas.copilot import SessionTurn


class InMemorySessionStore:
    """In-memory 세션 저장소 (SessionStoreProtocol 만족).

    `_sessions` dict: session_id → list[SessionTurn]
    `_created_at` dict: session_id → datetime (TTL 계산용)
    `_updated_at` dict: session_id → datetime (TTL 계산용)
    """

    def __init__(self) -> None:
        self._sessions: dict[str, list[SessionTurn]] = {}
        self._created_at: dict[str, datetime.datetime] = {}
        self._updated_at: dict[str, datetime.datetime] = {}

    def _max_turns(self) -> int:
        return int(os.environ.get("COPILOT_SESSION_MAX_TURNS", "50"))

    def _ttl_days(self) -> int:
        return int(os.environ.get("COPILOT_SESSION_TTL_DAYS", "7"))

    def _is_expired(self, session_id: str) -> bool:
        ttl_days = self._ttl_days()
        if ttl_days == 0:
            return True
        updated = self._updated_at.get(session_id)
        if updated is None:
            return False
        now = datetime.datetime.now(datetime.UTC)
        return (now - updated).days >= ttl_days

    async def get_turns(self, session_id: str, limit: int = 5) -> list[SessionTurn]:
        """최근 `limit` 개 턴을 반환한다."""
        if self._is_expired(session_id):
            return []
        turns = self._sessions.get(session_id, [])
        return turns[-limit:]

    async def append_turn(self, session_id: str, turn: SessionTurn) -> None:
        """턴을 추가하고 max_turns 초과 시 가장 오래된 것부터 삭제한다."""
        if session_id not in self._sessions:
            self._sessions[session_id] = []
            self._created_at[session_id] = datetime.datetime.now(datetime.UTC)
        self._sessions[session_id].append(turn)
        self._updated_at[session_id] = datetime.datetime.now(datetime.UTC)
        # max_turns 초과 시 가장 오래된 턴 삭제
        max_t = self._max_turns()
        if len(self._sessions[session_id]) > max_t:
            self._sessions[session_id] = self._sessions[session_id][-max_t:]

    async def clear(self, session_id: str) -> None:
        """세션을 완전히 삭제한다."""
        self._sessions.pop(session_id, None)
        self._created_at.pop(session_id, None)
        self._updated_at.pop(session_id, None)

    async def new_session(self) -> str:
        """uuid4 hex 세션 ID 생성 + 빈 세션 초기화."""
        session_id = uuid.uuid4().hex
        self._sessions[session_id] = []
        now = datetime.datetime.now(datetime.UTC)
        self._created_at[session_id] = now
        self._updated_at[session_id] = now
        return session_id

    # ── 하위 호환 / 동기 래퍼 (sprint-04 테스트 호환) ─────────────────────────

    def save_turn(self, turn: SessionTurn) -> None:
        """동기 래퍼 — sprint-04 오케스트레이터 하위 호환."""
        session_id = getattr(turn, "session_id", None) or ""
        if session_id not in self._sessions:
            self._sessions[session_id] = []
            now = datetime.datetime.now(datetime.UTC)
            self._created_at[session_id] = now
            self._updated_at[session_id] = now
        self._sessions[session_id].append(turn)
        self._updated_at[session_id] = datetime.datetime.now(datetime.UTC)
        max_t = self._max_turns()
        if len(self._sessions[session_id]) > max_t:
            self._sessions[session_id] = self._sessions[session_id][-max_t:]

    def list_turns(self, session_id: str) -> list[SessionTurn]:
        """동기 래퍼 — sprint-04 테스트 하위 호환. get_turns 의 alias."""
        if self._is_expired(session_id):
            return []
        return list(self._sessions.get(session_id, []))

    def reset_all(self) -> None:
        """테스트 격리용 전체 초기화."""
        self._sessions.clear()
        self._created_at.clear()
        self._updated_at.clear()

    def exists(self, session_id: str) -> bool:
        """세션 존재 여부 확인 (TTL 반영)."""
        if session_id not in self._sessions:
            return False
        if self._is_expired(session_id):
            return False
        return True


def make_turn_id() -> str:
    return f"turn-{uuid.uuid4().hex[:8]}"


# ── 하위 호환 싱글톤 접근자 (sprint-04 테스트 직접 import 호환) ────────────────

_store: InMemorySessionStore | None = None


def get_session_store() -> InMemorySessionStore:
    """싱글톤 접근자 — sprint-04 하위 호환 (memory_store 직접 import 시 사용).

    sprint-05 이후는 `from app.services.session import get_session_store` 권장.
    """
    global _store
    if _store is None:
        _store = InMemorySessionStore()
    return _store
