"""PostgresSessionStore — sprint-05: Postgres 기반 세션 저장소.

COPILOT_SESSION_STORE=postgres 환경에서 사용된다.
실 DB 연결 없이 import 만 해도 작동하도록 설계 (연결 실패 시 런타임 오류).
테스트 환경에서는 COPILOT_SESSION_STORE=memory 로 동작하므로 인스턴스화 skip 허용.
"""

from __future__ import annotations

import datetime
import json
import os
import uuid
from typing import Any

from app.schemas.copilot import SessionMeta, SessionTurn


class PostgresSessionStore:
    """Postgres `copilot_sessions` / `copilot_turns` 테이블 기반 세션 저장소.

    실 DB 연결은 COPILOT_SESSION_STORE_URL 환경변수로 주입.
    연결 없이 사용 시 RuntimeError 를 발생시킨다.
    """

    def __init__(self) -> None:
        self._pool: Any | None = None
        self._dsn: str = os.environ.get("COPILOT_SESSION_STORE_URL", "")

    async def _get_pool(self) -> Any:
        """연결 풀 지연 초기화 — asyncpg 사용."""
        if self._pool is not None:
            return self._pool
        if not self._dsn:
            raise RuntimeError(
                "COPILOT_SESSION_STORE_URL 이 설정되지 않았습니다. "
                "Postgres 세션 저장소를 사용하려면 환경변수를 설정하세요."
            )
        try:
            import asyncpg  # noqa: PLC0415

            self._pool = await asyncpg.create_pool(self._dsn)
        except ImportError as exc:
            raise RuntimeError("asyncpg 가 설치되어 있지 않습니다.") from exc
        return self._pool

    def _max_turns(self) -> int:
        return int(os.environ.get("COPILOT_SESSION_MAX_TURNS", "50"))

    def _ttl_days(self) -> int:
        return int(os.environ.get("COPILOT_SESSION_TTL_DAYS", "7"))

    async def get_turns(self, session_id: str, limit: int = 5) -> list[SessionTurn]:
        """최근 `limit` 개 턴을 반환한다."""
        try:
            pool = await self._get_pool()
            # TTL 체크 — updated_at 기준
            ttl_days = self._ttl_days()
            ttl_check = ""
            if ttl_days == 0:
                return []
            if ttl_days > 0:
                ttl_check = f"AND s.updated_at > NOW() - INTERVAL '{ttl_days} days'"

            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    f"""
                    SELECT t.id, t.query, t.plan_id, t.final_card, t.citations,
                           t.active_context, t.created_at
                    FROM copilot_turns t
                    JOIN copilot_sessions s ON s.id = t.session_id
                    WHERE t.session_id = $1 {ttl_check}
                    ORDER BY t.turn_idx DESC
                    LIMIT $2
                    """,
                    session_id,
                    limit,
                )
                turns = []
                for row in reversed(rows):
                    turns.append(
                        SessionTurn(
                            turn_id=str(row["id"]),
                            query=row["query"],
                            plan_id=row["plan_id"],
                            final_card=json.loads(row["final_card"]) if row["final_card"] else None,
                            citations=json.loads(row["citations"]) if row["citations"] else [],
                            created_at=row["created_at"].isoformat() if row["created_at"] else "",
                            active_context=(
                                json.loads(row["active_context"]) if row["active_context"] else None
                            ),
                        )
                    )
                return turns
        except Exception:  # noqa: BLE001
            return []

    async def append_turn(self, session_id: str, turn: SessionTurn) -> None:
        """턴을 추가하고 max_turns 초과 시 가장 오래된 것부터 삭제한다."""
        try:
            pool = await self._get_pool()
            now = datetime.datetime.now(datetime.UTC)
            async with pool.acquire() as conn:
                # 세션 upsert
                await conn.execute(
                    """
                    INSERT INTO copilot_sessions (id, created_at, updated_at)
                    VALUES ($1, $2, $2)
                    ON CONFLICT (id) DO UPDATE SET updated_at = $2
                    """,
                    session_id,
                    now,
                )
                # 현재 turn_idx 계산
                row = await conn.fetchrow(
                    "SELECT COUNT(*) as cnt FROM copilot_turns WHERE session_id = $1",
                    session_id,
                )
                turn_idx = int(row["cnt"])
                # 턴 삽입
                await conn.execute(
                    """
                    INSERT INTO copilot_turns
                      (id, session_id, turn_idx, query, plan_id, final_card,
                       citations, active_context, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
                    uuid.uuid4(),
                    session_id,
                    turn_idx,
                    turn.query,
                    turn.plan_id,
                    json.dumps(turn.final_card) if turn.final_card else None,
                    json.dumps(turn.citations) if turn.citations else None,
                    json.dumps(turn.active_context) if turn.active_context else None,
                    now,
                )
                # max_turns 초과 시 오래된 것 삭제
                max_t = self._max_turns()
                await conn.execute(
                    """
                    DELETE FROM copilot_turns
                    WHERE session_id = $1
                      AND id NOT IN (
                        SELECT id FROM copilot_turns
                        WHERE session_id = $1
                        ORDER BY turn_idx DESC
                        LIMIT $2
                      )
                    """,
                    session_id,
                    max_t,
                )
        except Exception:  # noqa: BLE001
            pass  # 저장 실패는 조용히 무시 (로깅은 상위에서)

    async def clear(self, session_id: str) -> None:
        """세션과 모든 턴을 삭제한다."""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                await conn.execute("DELETE FROM copilot_turns WHERE session_id = $1", session_id)
                await conn.execute("DELETE FROM copilot_sessions WHERE id = $1", session_id)
        except Exception:  # noqa: BLE001
            pass

    async def exists(self, session_id: str) -> bool:
        """Return whether a non-expired session exists."""
        try:
            pool = await self._get_pool()
            ttl_days = self._ttl_days()
            if ttl_days == 0:
                return False
            ttl_check = ""
            if ttl_days > 0:
                ttl_check = f"AND updated_at > NOW() - INTERVAL '{ttl_days} days'"
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    f"SELECT 1 FROM copilot_sessions WHERE id = $1 {ttl_check} LIMIT 1",
                    session_id,
                )
                return row is not None
        except Exception:  # noqa: BLE001
            return False

    async def list_sessions(
        self,
        limit: int = 20,
        offset: int = 0,
        user_id: str | None = None,
    ) -> list[SessionMeta]:
        """Return recent session metadata for the Copilot sidebar."""
        del user_id  # Session ownership is not modeled yet.
        try:
            pool = await self._get_pool()
            ttl_days = self._ttl_days()
            if ttl_days == 0:
                return []
            ttl_check = ""
            if ttl_days > 0:
                ttl_check = f"WHERE s.updated_at > NOW() - INTERVAL '{ttl_days} days'"

            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    f"""
                    SELECT
                      s.id,
                      s.updated_at,
                      first_turn.query AS first_query,
                      last_turn.query AS last_query,
                      last_turn.created_at AS last_turn_at,
                      COALESCE(turn_counts.turn_count, 0) AS turn_count
                    FROM copilot_sessions s
                    LEFT JOIN LATERAL (
                      SELECT query
                      FROM copilot_turns
                      WHERE session_id = s.id
                      ORDER BY turn_idx ASC
                      LIMIT 1
                    ) first_turn ON TRUE
                    LEFT JOIN LATERAL (
                      SELECT query, created_at
                      FROM copilot_turns
                      WHERE session_id = s.id
                      ORDER BY turn_idx DESC
                      LIMIT 1
                    ) last_turn ON TRUE
                    LEFT JOIN LATERAL (
                      SELECT COUNT(*)::int AS turn_count
                      FROM copilot_turns
                      WHERE session_id = s.id
                    ) turn_counts ON TRUE
                    {ttl_check}
                    ORDER BY s.updated_at DESC
                    LIMIT $1 OFFSET $2
                    """,
                    limit,
                    offset,
                )

            sessions: list[SessionMeta] = []
            for row in rows:
                first_query = row["first_query"] or "(빈 세션)"
                last_query = row["last_query"] or ""
                title = first_query[:80] + ("..." if len(first_query) > 80 else "")
                preview = last_query[:120] + ("..." if len(last_query) > 120 else "")
                last_turn_at = row["last_turn_at"] or row["updated_at"]
                sessions.append(
                    SessionMeta(
                        session_id=str(row["id"]),
                        title=title,
                        last_turn_at=last_turn_at.isoformat().replace("+00:00", "Z"),
                        turn_count=int(row["turn_count"] or 0),
                        preview=preview,
                    )
                )
            return sessions
        except Exception:  # noqa: BLE001
            return []

    async def new_session(self) -> str:
        """uuid4 hex 세션 ID 생성 + DB 행 삽입."""
        session_id = uuid.uuid4().hex
        try:
            pool = await self._get_pool()
            now = datetime.datetime.now(datetime.UTC)
            async with pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO copilot_sessions (id, created_at, updated_at) VALUES ($1, $2, $2)",
                    session_id,
                    now,
                )
        except Exception:  # noqa: BLE001
            pass
        return session_id
