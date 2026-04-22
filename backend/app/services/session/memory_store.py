"""세션 저장소 stub — in-memory dict singleton.

sprint-04 범위: in-memory 구현으로 테스트 재현성 확보.
TODO(sprint-05): swap with Postgres-backed store at COPILOT_SESSION_STORE_URL
"""
from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SessionTurn:
    """단일 세션 턴 — done 이벤트 직전에 저장된다."""

    turn_id: str
    session_id: str
    query: str
    plan_id: str | None
    final_card: dict[str, Any] | None
    citations: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.datetime.now(datetime.UTC).isoformat())


class MemorySessionStore:
    """In-memory 세션 저장소.

    `sessions` dict: session_id → list[SessionTurn]
    """

    def __init__(self) -> None:
        self._sessions: dict[str, list[SessionTurn]] = {}

    def save_turn(self, turn: SessionTurn) -> None:
        if turn.session_id not in self._sessions:
            self._sessions[turn.session_id] = []
        self._sessions[turn.session_id].append(turn)

    def list_turns(self, session_id: str) -> list[SessionTurn]:
        return list(self._sessions.get(session_id, []))

    def clear(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def reset_all(self) -> None:
        """테스트 격리용 전체 초기화."""
        self._sessions.clear()


# 모듈 수준 싱글턴
_store: MemorySessionStore | None = None


def get_session_store() -> MemorySessionStore:
    """싱글턴 접근자."""
    global _store
    if _store is None:
        _store = MemorySessionStore()
    return _store


def make_turn_id() -> str:
    return f"turn-{uuid.uuid4().hex[:8]}"
