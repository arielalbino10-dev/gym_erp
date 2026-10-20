"""Detección de cookies de sesión en peticiones."""

from __future__ import annotations

from starlette.requests import Request

from gym_erp_api.modules.identity.application.security.http_auth_contracts import (
    SESSION_COOKIE_NAMES,
)


def request_carries_session_cookie(request: Request) -> bool:
    return any(request.cookies.get(name) for name in SESSION_COOKIE_NAMES)
