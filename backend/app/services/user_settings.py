"""User Settings 서비스 — migration 006: DB 영속화.

in-memory dict 를 제거하고 Postgres user_settings 테이블로 전환한다.
uvicorn 재시작 후에도 설정이 유지된다 (심사 데모 영속화 요구사항).

변경 이유:
  - 기존 _settings_store dict 는 프로세스 수명과 같아 재시작 시 기본값으로 리셋됨.
  - DB 기반으로 전환해 GET → DB 조회, PATCH → DB UPDATE, 없으면 INSERT.
"""

from __future__ import annotations

import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UserSettings as UserSettingsRow
from app.schemas.user import (
    ConnectedAccount,
    DataSettings,
    NotificationSettings,
    ThemeSettings,
    UserSettings,
    UserSettingsPatch,
)


def _now_iso() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")


def _default_connected_accounts() -> list[dict[str, Any]]:
    return [
        {
            "provider": "google",
            "email": "demo@demo.com",
            "connected_at": "2026-01-01T00:00:00Z",
        }
    ]


def _default_row(user_id: str) -> UserSettingsRow:
    """DB INSERT 용 기본 ORM 행 생성."""
    return UserSettingsRow(
        user_id=user_id,
        name="Demo User",
        email="demo@demo.com",
        language="ko",
        timezone="Asia/Seoul",
        theme={"mode": "system", "accent": "violet"},
        notifications={
            "email_alerts": True,
            "push_alerts": False,
            "price_threshold_pct": 5.0,
            "daily_digest": True,
        },
        data={
            "refresh_interval_sec": 60,
            "auto_refresh": True,
            "auto_backup": False,
            "cache_size_mb": 256,
        },
        connected_accounts=_default_connected_accounts(),
        updated_at=datetime.datetime.now(datetime.UTC),
    )


def default_settings(user_id: str) -> UserSettings:
    """기본 UserSettings Pydantic 스키마 팩토리 (테스트 / 시드 용)."""
    return UserSettings(
        user_id=user_id,
        name="Demo User",
        email="demo@demo.com",
        language="ko",
        timezone="Asia/Seoul",
        theme=ThemeSettings(),
        notifications=NotificationSettings(),
        data=DataSettings(),
        connected_accounts=[
            ConnectedAccount(
                provider="google",
                email="demo@demo.com",
                connected_at="2026-01-01T00:00:00Z",
            )
        ],
        updated_at=_now_iso(),
    )


def _row_to_schema(row: UserSettingsRow) -> UserSettings:
    """ORM 행 → Pydantic 스키마 변환."""
    updated_at_str = (
        row.updated_at.isoformat().replace("+00:00", "Z") if row.updated_at else _now_iso()
    )
    connected = [ConnectedAccount.model_validate(a) for a in (row.connected_accounts or [])]
    return UserSettings(
        user_id=row.user_id,
        name=row.name,
        email=row.email,
        language=row.language,
        timezone=row.timezone,
        theme=ThemeSettings.model_validate(row.theme),
        notifications=NotificationSettings.model_validate(row.notifications),
        data=DataSettings.model_validate(row.data),
        connected_accounts=connected,
        updated_at=updated_at_str,
    )


async def get_settings(db: AsyncSession, user_id: str) -> UserSettings:
    """user_id 에 해당하는 설정을 DB 에서 조회한다. 없으면 기본 행을 INSERT 후 반환."""
    result = await db.execute(select(UserSettingsRow).where(UserSettingsRow.user_id == user_id))
    row = result.scalar_one_or_none()

    if row is None:
        row = _default_row(user_id)
        db.add(row)
        await db.commit()
        await db.refresh(row)

    return _row_to_schema(row)


async def patch_settings(db: AsyncSession, user_id: str, patch: UserSettingsPatch) -> UserSettings:
    """partial update — deep merge. JSONB 필드(theme/notifications/data)는 key 단위 병합.

    없으면 기본 행 INSERT 후 패치 적용.
    """
    result = await db.execute(select(UserSettingsRow).where(UserSettingsRow.user_id == user_id))
    row = result.scalar_one_or_none()

    if row is None:
        row = _default_row(user_id)
        db.add(row)
        # flush 해 row 가 세션에 등록되도록 (commit 은 아래서 한 번만)
        await db.flush()

    patch_dict = patch.model_dump(exclude_none=True)

    for key, value in patch_dict.items():
        if isinstance(value, dict):
            # JSONB deep merge: 기존 dict 와 병합
            current_val = getattr(row, key, {}) or {}
            merged = {**current_val, **value}
            setattr(row, key, merged)
        else:
            setattr(row, key, value)

    row.updated_at = datetime.datetime.now(datetime.UTC)

    await db.commit()
    await db.refresh(row)

    return _row_to_schema(row)


# ---------------------------------------------------------------------------
# 하위 호환: 기존 sync 시그니처는 제거. reset_store 는 테스트 격리용으로 유지
# (DB 기반이므로 실제 효과는 없음 — 테스트는 db_session fixture 트랜잭션 롤백으로 격리)
# ---------------------------------------------------------------------------


def reset_store() -> None:
    """테스트 격리용 stub — DB 기반으로 전환 후 no-op."""
