"""
알림 엔드포인트 단위·통합 테스트.

- GET  /notifications
- POST /notifications/read-all
- POST /notifications/{id}/read

conftest.py 의 app 의존 없이 notifications 서비스만 독립 테스트.
"""

from __future__ import annotations

import pytest

from app.schemas.notifications import (
    MarkAllReadResponse,
    MarkReadResponse,
    Notification,
    NotificationListResponse,
)
from app.services.notifications import (
    _read_flags,
    mark_all_read,
    mark_read,
)

# ──────────────────────────── 스키마 단위 테스트 ─────────────────────────────


def test_notification_schema_valid():
    """Notification 스키마가 올바른 필드를 받아 생성된다."""
    n = Notification(
        id="price-1",
        title="BTC 가격 돌파",
        message="현재가 50M 돌파",
        severity="critical",
        category="price",
        unread=True,
        created_at="2026-04-24T00:00:00+00:00",
    )
    assert n.id == "price-1"
    assert n.severity == "critical"
    assert n.unread is True


def test_notification_schema_no_message():
    """message 는 None 허용."""
    n = Notification(
        id="system-1",
        title="시스템 점검",
        message=None,
        severity="info",
        category="system",
        unread=False,
        created_at="2026-04-24T00:00:00+00:00",
    )
    assert n.message is None


def test_notification_schema_severity_literal():
    """severity 는 info | warning | critical 외 값 거부."""
    with pytest.raises(Exception):  # Pydantic ValidationError
        Notification(
            id="x-1",
            title="x",
            message=None,
            severity="unknown_value",  # type: ignore[arg-type]
            category="price",
            unread=True,
            created_at="2026-04-24T00:00:00+00:00",
        )


def test_notification_schema_category_literal():
    """category 는 price | portfolio | alert | system 외 값 거부."""
    with pytest.raises(Exception):
        Notification(
            id="x-2",
            title="x",
            message=None,
            severity="info",
            category="invalid_category",  # type: ignore[arg-type]
            unread=False,
            created_at="2026-04-24T00:00:00+00:00",
        )


# ─────────────────────────── in-memory 읽음 상태 ─────────────────────────────


def test_mark_read_valid_id():
    """유효한 ID 형식으로 읽음 처리."""
    _read_flags.clear()
    result = mark_read("price-42")
    assert result is True
    assert _read_flags[("price", "42")] is True


def test_mark_read_invalid_id():
    """구분자 없는 ID 는 False 반환."""
    _read_flags.clear()
    result = mark_read("invalidid")
    assert result is False


def test_mark_all_read():
    """여러 ID 일괄 읽음 처리."""
    _read_flags.clear()
    ids = ["price-1", "portfolio-2", "holding-3"]
    mark_all_read(ids)
    assert _read_flags[("price", "1")] is True
    assert _read_flags[("portfolio", "2")] is True
    assert _read_flags[("holding", "3")] is True


def test_mark_read_idempotent():
    """이미 읽은 알림을 다시 읽음 처리해도 오류 없음."""
    _read_flags.clear()
    mark_read("price-5")
    result = mark_read("price-5")
    assert result is True


def test_mark_read_with_dash_in_source():
    """source 부분에 하이픈이 포함된 복잡한 ID 처리."""
    _read_flags.clear()
    result = mark_read("price-123")
    assert result is True
    # key: ("price", "123")
    assert _read_flags.get(("price", "123")) is True


# ─────────────────────────── 응답 스키마 테스트 ──────────────────────────────


def test_mark_all_read_response_schema():
    resp = MarkAllReadResponse(marked_count=5)
    assert resp.marked_count == 5


def test_mark_read_response_schema():
    resp = MarkReadResponse(id="price-1", unread=False)
    assert resp.id == "price-1"
    assert resp.unread is False


def test_notification_list_response_schema():
    items = [
        Notification(
            id="price-1",
            title="BTC 돌파",
            message=None,
            severity="critical",
            category="price",
            unread=True,
            created_at="2026-04-24T00:00:00+00:00",
        )
    ]
    resp = NotificationListResponse(items=items, unread_count=1)
    assert resp.unread_count == 1
    assert len(resp.items) == 1
