"""User Settings 서비스 — sprint-08 B-6.

in-memory store 기반. persistence 전환은 non-goal.
"""
from __future__ import annotations

import datetime

from app.schemas.user import (
    ConnectedAccount,
    DataSettings,
    NotificationSettings,
    ThemeSettings,
    UserSettings,
    UserSettingsPatch,
)

# in-memory store: user_id → UserSettings
_settings_store: dict[str, UserSettings] = {}


def _now_iso() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")


def default_settings(user_id: str) -> UserSettings:
    """기본 UserSettings 팩토리."""
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


def get_settings(user_id: str) -> UserSettings:
    """user_id 에 해당하는 설정을 반환한다. 없으면 기본값을 생성 후 저장."""
    if user_id not in _settings_store:
        _settings_store[user_id] = default_settings(user_id)
    return _settings_store[user_id]


def patch_settings(user_id: str, patch: UserSettingsPatch) -> UserSettings:
    """partial update — deep merge. pydantic model_dump(exclude_none=True) 활용."""
    current = get_settings(user_id)
    current_dict = current.model_dump()

    patch_dict = patch.model_dump(exclude_none=True)

    # deep merge: 중첩 모델(theme / notifications / data) 필드별 병합
    for key, value in patch_dict.items():
        if isinstance(value, dict) and isinstance(current_dict.get(key), dict):
            current_dict[key] = {**current_dict[key], **value}
        else:
            current_dict[key] = value

    current_dict["updated_at"] = _now_iso()

    updated = UserSettings.model_validate(current_dict)
    _settings_store[user_id] = updated
    return updated


def reset_store() -> None:
    """테스트 격리용 전체 초기화."""
    _settings_store.clear()
