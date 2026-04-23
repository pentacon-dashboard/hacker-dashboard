"""User / Settings 스키마 — sprint-08 B-6."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class NotificationSettings(BaseModel):
    email_alerts: bool = True
    push_alerts: bool = False
    price_threshold_pct: float = 5.0
    daily_digest: bool = True


class DataSettings(BaseModel):
    refresh_interval_sec: int = 60
    auto_refresh: bool = True
    auto_backup: bool = False
    cache_size_mb: int = 256


class ThemeSettings(BaseModel):
    mode: Literal["light", "dark", "system"] = "system"
    accent: Literal["violet", "cyan", "blue", "orange", "rose"] = "violet"


class ConnectedAccount(BaseModel):
    provider: Literal["google", "apple", "kakao", "github"]
    email: str | None = None
    connected_at: str | None = None


class UserSettings(BaseModel):
    user_id: str
    name: str
    email: str
    language: Literal["ko", "en"] = "ko"
    timezone: str = "Asia/Seoul"
    theme: ThemeSettings
    notifications: NotificationSettings
    data: DataSettings
    connected_accounts: list[ConnectedAccount]
    updated_at: str


class UserSettingsPatch(BaseModel):
    name: str | None = None
    language: Literal["ko", "en"] | None = None
    timezone: str | None = None
    theme: ThemeSettings | None = None
    notifications: NotificationSettings | None = None
    data: DataSettings | None = None


class UserMe(BaseModel):
    user_id: str
    name: str
    email: str
    avatar_url: str | None = None
