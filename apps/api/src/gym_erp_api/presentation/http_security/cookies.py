"""Helpers de cookies de sesión (sin emitir en rutas públicas aún)."""

from __future__ import annotations

from datetime import datetime

from starlette.responses import Response

from gym_erp_api.core.config import Settings
from gym_erp_api.modules.identity.application.security.http_auth_contracts import (
    GYM_SESSION_COOKIE,
    PLATFORM_AUTH_CONTINUATION_COOKIE,
    PLATFORM_SESSION_COOKIE,
    SessionCookiePolicy,
)


def _cookie_secure(settings: Settings, policy: SessionCookiePolicy) -> bool:
    env = settings.app_env.strip().lower()
    if env in {"development", "test"} and settings.allow_insecure_cookies:
        return False
    return policy.secure


def set_session_cookie(
    response: Response,
    *,
    policy: SessionCookiePolicy,
    token: str,
    settings: Settings,
    max_age_seconds: int,
) -> None:
    response.set_cookie(
        key=policy.name,
        value=token,
        max_age=max_age_seconds,
        path=policy.path,
        httponly=policy.http_only,
        secure=_cookie_secure(settings, policy),
        samesite=policy.same_site,
    )


def delete_session_cookie(
    response: Response,
    *,
    policy: SessionCookiePolicy,
    settings: Settings,
) -> None:
    response.delete_cookie(
        key=policy.name,
        path=policy.path,
        httponly=policy.http_only,
        secure=_cookie_secure(settings, policy),
        samesite=policy.same_site,
    )


def set_platform_session_cookie(
    response: Response,
    *,
    token: str,
    settings: Settings,
    expires_at: datetime,
    now: datetime,
) -> None:
    max_age = max(0, int((expires_at - now).total_seconds()))
    set_session_cookie(
        response,
        policy=PLATFORM_SESSION_COOKIE,
        token=token,
        settings=settings,
        max_age_seconds=max_age,
    )


def set_gym_session_cookie(
    response: Response,
    *,
    token: str,
    settings: Settings,
    expires_at: datetime,
    now: datetime,
) -> None:
    max_age = max(0, int((expires_at - now).total_seconds()))
    set_session_cookie(
        response,
        policy=GYM_SESSION_COOKIE,
        token=token,
        settings=settings,
        max_age_seconds=max_age,
    )


def clear_platform_session_cookie(response: Response, *, settings: Settings) -> None:
    delete_session_cookie(response, policy=PLATFORM_SESSION_COOKIE, settings=settings)


def clear_gym_session_cookie(response: Response, *, settings: Settings) -> None:
    delete_session_cookie(response, policy=GYM_SESSION_COOKIE, settings=settings)


def set_platform_auth_continuation_cookie(
    response: Response,
    *,
    token: str,
    settings: Settings,
    expires_at: datetime,
    now: datetime,
) -> None:
    max_age = max(0, int((expires_at - now).total_seconds()))
    set_session_cookie(
        response,
        policy=PLATFORM_AUTH_CONTINUATION_COOKIE,
        token=token,
        settings=settings,
        max_age_seconds=max_age,
    )


def clear_platform_auth_continuation_cookie(response: Response, *, settings: Settings) -> None:
    delete_session_cookie(response, policy=PLATFORM_AUTH_CONTINUATION_COOKIE, settings=settings)
