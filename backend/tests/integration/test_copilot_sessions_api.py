"""Integration tests — GET /copilot/sessions (sprint-08 B-7)."""
from __future__ import annotations

import datetime

import pytest
from httpx import AsyncClient

from app.schemas.copilot import SessionTurn
from app.services.session import get_session_store
from app.services.session.memory_store import make_turn_id


def _add_session(session_id: str, queries: list[str], updated_at: datetime.datetime | None = None) -> None:
    """헬퍼: in-memory store 에 세션과 턴을 직접 추가."""
    store = get_session_store()
    store._sessions[session_id] = [
        SessionTurn(
            turn_id=make_turn_id(),
            query=q,
            created_at=f"2026-04-23T10:0{i}:00Z",
        )
        for i, q in enumerate(queries)
    ]
    store._updated_at[session_id] = updated_at or datetime.datetime.now(datetime.UTC)


@pytest.fixture(autouse=True)
def reset_store():
    """각 테스트 전후 세션 저장소 초기화."""
    store = get_session_store()
    store.reset_all()
    yield
    store.reset_all()


class TestListSessions:
    @pytest.mark.asyncio
    async def test_empty_returns_list(self, client: AsyncClient):
        resp = await client.get("/copilot/sessions")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_single_session_returned(self, client: AsyncClient):
        _add_session("s1", ["AAPL 분석해줘"])
        resp = await client.get("/copilot/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["session_id"] == "s1"
        assert data[0]["title"] == "AAPL 분석해줘"
        assert data[0]["turn_count"] == 1

    @pytest.mark.asyncio
    async def test_sessions_sorted_recent_first(self, client: AsyncClient):
        now = datetime.datetime.now(datetime.UTC)
        _add_session("s-old", ["구 세션"], now - datetime.timedelta(hours=2))
        _add_session("s-new", ["신 세션"], now - datetime.timedelta(hours=1))

        resp = await client.get("/copilot/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["session_id"] == "s-new"
        assert data[1]["session_id"] == "s-old"

    @pytest.mark.asyncio
    async def test_limit_param(self, client: AsyncClient):
        base = datetime.datetime.now(datetime.UTC)
        for i in range(15):
            _add_session(f"s{i:02d}", [f"질문{i}"], base + datetime.timedelta(minutes=i))

        resp = await client.get("/copilot/sessions?limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 5

    @pytest.mark.asyncio
    async def test_offset_param(self, client: AsyncClient):
        base = datetime.datetime.now(datetime.UTC)
        for i in range(15):
            _add_session(f"s{i:02d}", [f"질문{i}"], base + datetime.timedelta(minutes=i))

        page1 = await client.get("/copilot/sessions?limit=5&offset=0")
        page2 = await client.get("/copilot/sessions?limit=5&offset=5")

        ids1 = {m["session_id"] for m in page1.json()}
        ids2 = {m["session_id"] for m in page2.json()}
        assert len(ids1 & ids2) == 0

    @pytest.mark.asyncio
    async def test_session_meta_has_required_fields(self, client: AsyncClient):
        _add_session("s1", ["테스트 질문"])
        resp = await client.get("/copilot/sessions")
        item = resp.json()[0]
        assert "session_id" in item
        assert "title" in item
        assert "last_turn_at" in item
        assert "turn_count" in item
        assert "preview" in item
        assert "tags" in item
