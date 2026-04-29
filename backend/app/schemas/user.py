"""User / Settings 스키마 — sprint-08 B-6."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, StrictBool, StrictFloat, StrictInt

_NO_NUL_PATTERN = r"^[^\x00]+$"
StrictNumber = StrictFloat | StrictInt


class NotificationSettings(BaseModel):
    email_alerts: StrictBool = True
    push_alerts: StrictBool = False
    price_threshold_pct: StrictNumber = 5.0
    daily_digest: StrictBool = True


class DataSettings(BaseModel):
    refresh_interval_sec: StrictInt = 60
    auto_refresh: StrictBool = True
    auto_backup: StrictBool = False
    cache_size_mb: StrictInt = 256


class ThemeSettings(BaseModel):
    mode: Literal["light", "dark", "system"] = "system"
    accent: Literal["violet", "cyan", "blue", "orange", "rose"] = "violet"


class ConnectedAccount(BaseModel):
    provider: Literal["google", "apple", "kakao", "github"]
    email: str | None = Field(None, max_length=256, pattern=_NO_NUL_PATTERN)
    connected_at: str | None = None


class UserSettings(BaseModel):
    user_id: str = Field(..., max_length=64, pattern=_NO_NUL_PATTERN)
    name: str = Field(..., max_length=128, pattern=_NO_NUL_PATTERN)
    email: str = Field(..., max_length=256, pattern=_NO_NUL_PATTERN)
    language: Literal["ko", "en"] = "ko"
    timezone: str = Field("Asia/Seoul", max_length=64, pattern=_NO_NUL_PATTERN)
    theme: ThemeSettings
    notifications: NotificationSettings
    data: DataSettings
    connected_accounts: list[ConnectedAccount]
    updated_at: str


class UserSettingsPatch(BaseModel):
    name: str | None = Field(None, max_length=128, pattern=_NO_NUL_PATTERN)
    language: Literal["ko", "en"] | None = None
    timezone: str | None = Field(None, max_length=64, pattern=_NO_NUL_PATTERN)
    theme: ThemeSettings | None = None
    notifications: NotificationSettings | None = None
    data: DataSettings | None = None


class UserMe(BaseModel):
    user_id: str = Field(..., max_length=64, pattern=_NO_NUL_PATTERN)
    name: str = Field(..., max_length=128, pattern=_NO_NUL_PATTERN)
    email: str = Field(..., max_length=256, pattern=_NO_NUL_PATTERN)
    avatar_url: str | None = None
