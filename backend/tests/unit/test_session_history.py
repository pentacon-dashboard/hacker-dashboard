"""Unit tests — session history list_sessions + build_session_meta (sprint-08 B-7)."""
from __future__ import annotations

import datetime

import pytest

from app.schemas.copilot import SessionTurn
from app.services.session.memory_store import InMemorySessionStore, build_session_meta, make_turn_id


def _make_turn(query: str, created_at: str = "2026-04-23T10:00:00Z") -> SessionTurn:
    return SessionTurn(
        turn_id=make_turn_id(),
        query=query,
        created_at=created_at,
    )


class TestBuildSessionMeta:
    def test_empty_turns(self):
        now = datetime.datetime.now(datetime.UTC)
        meta = build_session_meta("s1", [], now)
        assert meta.session_id == "s1"
        assert meta.turn_count == 0
        assert meta.title == "(빈 세션)"
        assert meta.preview == ""

    def test_single_turn_short_query(self):
        turns = [_make_turn("AAPL 분석해줘", "2026-04-23T10:00:00Z")]
        now = datetime.datetime.now(datetime.UTC)
        meta = build_session_meta("s1", turns, now)
        assert meta.turn_count == 1
        assert meta.title == "AAPL 분석해줘"
        assert meta.preview == "AAPL 분석해줘"
        assert meta.last_turn_at == "2026-04-23T10:00:00Z"

    def test_title_truncated_at_80_chars(self):
        long_query = "A" * 90
        turns = [_make_turn(long_query)]
        now = datetime.datetime.now(datetime.UTC)
        meta = build_session_meta("s1", turns, now)
        assert len(meta.title) == 83  # 80 + "..."
        assert meta.title.endswith("...")

    def test_preview_truncated_at_120_chars(self):
        short_first = "첫 질문"
        long_last = "B" * 130
        turns = [
            _make_turn(short_first, "2026-04-23T09:00:00Z"),
            _make_turn(long_last, "2026-04-23T10:00:00Z"),
        ]
        now = datetime.datetime.now(datetime.UTC)
        meta = build_session_meta("s1", turns, now)
        assert meta.title == short_first
        assert len(meta.preview) == 123  # 120 + "..."
        assert meta.preview.endswith("...")

    def test_multi_turn_uses_last_created_at(self):
        turns = [
            _make_turn("q1", "2026-04-23T08:00:00Z"),
            _make_turn("q2", "2026-04-23T09:00:00Z"),
            _make_turn("q3", "2026-04-23T10:00:00Z"),
        ]
        now = datetime.datetime.now(datetime.UTC)
        meta = build_session_meta("s1", turns, now)
        assert meta.last_turn_at == "2026-04-23T10:00:00Z"
        assert meta.turn_count == 3


class TestListSessions:
    @pytest.fixture
    def store(self) -> InMemorySessionStore:
        return InMemorySessionStore()

    def test_empty_store(self, store: InMemorySessionStore):
        result = store.list_sessions()
        assert result == []

    def test_single_session(self, store: InMemorySessionStore):
        store._sessions["s1"] = [_make_turn("첫 질문")]
        store._updated_at["s1"] = datetime.datetime.now(datetime.UTC)
        result = store.list_sessions()
        assert len(result) == 1
        assert result[0].session_id == "s1"

    def test_multiple_sessions_sorted_recent_first(self, store: InMemorySessionStore):
        now = datetime.datetime.now(datetime.UTC)
        store._sessions["s-old"] = [_make_turn("구 세션")]
        store._updated_at["s-old"] = now - datetime.timedelta(hours=2)

        store._sessions["s-new"] = [_make_turn("신 세션")]
        store._updated_at["s-new"] = now - datetime.timedelta(hours=1)

        result = store.list_sessions()
        assert len(result) == 2
        assert result[0].session_id == "s-new"
        assert result[1].session_id == "s-old"

    def test_pagination_limit(self, store: InMemorySessionStore):
        base = datetime.datetime.now(datetime.UTC)
        for i in range(25):
            sid = f"s{i:02d}"
            store._sessions[sid] = [_make_turn(f"질문{i}")]
            store._updated_at[sid] = base + datetime.timedelta(minutes=i)

        result = store.list_sessions(limit=10, offset=0)
        assert len(result) == 10

    def test_pagination_offset(self, store: InMemorySessionStore):
        base = datetime.datetime.now(datetime.UTC)
        for i in range(25):
            sid = f"s{i:02d}"
            store._sessions[sid] = [_make_turn(f"질문{i}")]
            store._updated_at[sid] = base + datetime.timedelta(minutes=i)

        page1 = store.list_sessions(limit=10, offset=0)
        page2 = store.list_sessions(limit=10, offset=10)
        page3 = store.list_sessions(limit=10, offset=20)

        ids_p1 = {m.session_id for m in page1}
        ids_p2 = {m.session_id for m in page2}
        ids_p3 = {m.session_id for m in page3}

        assert len(ids_p1 & ids_p2) == 0
        assert len(ids_p1 & ids_p3) == 0
        assert len(page3) == 5  # 마지막 페이지는 5개
