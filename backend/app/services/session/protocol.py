"""SessionStoreProtocol — sprint-05: 세션 저장소 공통 인터페이스.

모든 구현체(InMemorySessionStore, PostgresSessionStore)는 이 Protocol을 만족해야 한다.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.schemas.copilot import SessionTurn


@runtime_checkable
class SessionStoreProtocol(Protocol):
    """세션 저장소 공통 인터페이스 (Protocol — duck typing 지원)."""

    async def get_turns(self, session_id: str, limit: int = 5) -> list[SessionTurn]: ...

    async def append_turn(self, session_id: str, turn: SessionTurn) -> None: ...

    async def clear(self, session_id: str) -> None: ...

    async def new_session(self) -> str:
        """uuid4 hex 세션 ID 생성 + 빈 세션 초기화."""
        ...
