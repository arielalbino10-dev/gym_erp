"""Detección de cookies de sesión en peticiones."""

from __future__ import annotations

from starlette.requests import Request

from gym_erp_api.modules.identity.application.security.http_auth_contracts import (
    GYM_SESSION_COOKIE,
    PLATFORM_SESSION_COOKIE,
)

_AUTHENTICATED_SESSION_COOKIE_NAMES: frozenset[str] = frozenset(
    {
        PLATFORM_SESSION_COOKIE.name,
        GYM_SESSION_COOKIE.name,
    }
)


def request_carries_session_cookie(request: Request) -> bool:
    """Sesión gym/platform autenticada (excluye cookie de continuación MFA)."""
    return any(request.cookies.get(name) for name in _AUTHENTICATED_SESSION_COOKIE_NAMES)
