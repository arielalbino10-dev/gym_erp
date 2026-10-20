"""Cabeceras de seguridad HTTP."""

from __future__ import annotations

from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from gym_erp_api.modules.identity.application.security.http_auth_contracts import (
    SecurityHeadersPolicy,
)

_policy = SecurityHeadersPolicy()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", _policy.content_type_options)
        response.headers.setdefault("X-Frame-Options", _policy.frame_options)
        response.headers.setdefault("Referrer-Policy", _policy.referrer_policy)
        response.headers.setdefault("Permissions-Policy", _policy.permissions_policy)
        path = request.url.path
        if (
            path.startswith("/api/v1/platform")
            or path.startswith("/api/v1/gym")
            or "/auth/" in path
        ):
            response.headers.setdefault("Cache-Control", _policy.auth_cache_control)
        return response
