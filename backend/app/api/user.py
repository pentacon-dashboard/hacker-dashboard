"""User API 라우터 — sprint-08 B-6.

GET  /users/me             → UserMe
GET  /users/me/settings    → UserSettings
PATCH /users/me/settings   → UserSettings

인증 없음: X-User-Id 헤더 기반 fake auth. 헤더 없으면 "demo-user" default.
"""
from __future__ import annotations

from fastapi import APIRouter, Header

from app.schemas.user import UserMe, UserSettings, UserSettingsPatch
from app.services import user_settings as svc

router = APIRouter(prefix="/users", tags=["users"])

_DEFAULT_USER_ID = "demo-user"
_DEFAULT_NAME = "Demo User"
_DEFAULT_EMAIL = "demo@demo.com"


def _resolve_user_id(x_user_id: str | None) -> str:
    return x_user_id if x_user_id else _DEFAULT_USER_ID


@router.get(
    "/me",
    response_model=UserMe,
    summary="현재 사용자 정보 조회",
    description=(
        "X-User-Id 헤더 기반 fake auth. "
        "헤더 없으면 user_id='demo-user' 로 fallback."
    ),
)
async def get_me(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> UserMe:
    user_id = _resolve_user_id(x_user_id)
    return UserMe(
        user_id=user_id,
        name=_DEFAULT_NAME,
        email=_DEFAULT_EMAIL,
        avatar_url=None,
    )


@router.get(
    "/me/settings",
    response_model=UserSettings,
    summary="사용자 설정 조회",
    description="현재 사용자의 설정을 반환한다. 없으면 기본값을 생성 후 반환.",
)
async def get_settings(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> UserSettings:
    user_id = _resolve_user_id(x_user_id)
    return svc.get_settings(user_id)


@router.patch(
    "/me/settings",
    response_model=UserSettings,
    summary="사용자 설정 부분 업데이트",
    description="partial update. 전달된 필드만 deep-merge 로 반영하고 updated_at 갱신.",
)
async def patch_settings(
    body: UserSettingsPatch,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> UserSettings:
    user_id = _resolve_user_id(x_user_id)
    return svc.patch_settings(user_id, body)
