"""알림 스키마 — Pydantic v2."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Notification(BaseModel):
    """단일 알림 항목."""

    id: str = Field(..., description="알림 ID (예: price-3, portfolio-12)")
    title: str = Field(..., description="알림 제목")
    message: str | None = Field(None, description="알림 상세 메시지")
    severity: Literal["info", "warning", "critical"] = Field(
        ..., description="심각도 (info | warning | critical)"
    )
    category: Literal["price", "portfolio", "alert", "system"] = Field(..., description="알림 범주")
    unread: bool = Field(..., description="읽지 않음 여부")
    created_at: str = Field(..., description="ISO-8601 UTC 생성 시각")


class NotificationListResponse(BaseModel):
    """GET /notifications 응답."""

    items: list[Notification]
    unread_count: int = Field(..., description="미확인 알림 수")


class MarkReadResponse(BaseModel):
    """POST /notifications/{id}/read 응답."""

    id: str
    unread: bool = False


class MarkAllReadResponse(BaseModel):
    """POST /notifications/read-all 응답."""

    marked_count: int = Field(..., description="읽음 처리된 알림 수")
