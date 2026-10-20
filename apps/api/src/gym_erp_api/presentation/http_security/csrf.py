"""CSRF: double-submit + registro server-side (reutilizable por binding)."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from starlette.requests import Request
from starlette.responses import Response

from gym_erp_api.core.config import Settings
from gym_erp_api.infrastructure.mongo.mongo_csrf_token_repository import MongoCsrfTokenRepository
from gym_erp_api.modules.identity.application.security.http_auth_contracts import (
    GYM_CSRF_COOKIE,
    PLATFORM_CSRF_COOKIE,
    CsrfCookiePolicy,
    CsrfPolicy,
)
from gym_erp_api.modules.identity.infrastructure.crypto.session_token_hash import (
    generate_opaque_session_token,
)
from gym_erp_api.presentation.http_security.errors import CsrfValidationError

_CSRF_TTL = timedelta(hours=12)
_policy = CsrfPolicy()


def hash_csrf_token(token: str) -> str:
    if not token.strip():
        raise CsrfValidationError("CSRF inválido.")
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def csrf_binding_for_session(*, session_kind: str, session_id: str) -> str:
    return f"session:{session_kind}:{session_id}"


def csrf_cookie_policy_for_binding(binding_key: str) -> CsrfCookiePolicy:
    if binding_key.startswith("session:gym:"):
        return GYM_CSRF_COOKIE
    if binding_key.startswith("session:platform:"):
        return PLATFORM_CSRF_COOKIE
    return CsrfCookiePolicy(name=_policy.cookie_name, path="/api/v1")


@dataclass(frozen=True, slots=True)
class IssuedCsrfToken:
    token: str = field(repr=False)
    binding_key: str


class CsrfProtectionService:
    def __init__(self, *, repository: MongoCsrfTokenRepository) -> None:
        self._repository = repository

    async def issue(self, *, binding_key: str, now: datetime) -> IssuedCsrfToken:
        if not binding_key.strip():
            raise CsrfValidationError("CSRF binding inválido.")
        await self._repository.revoke_binding(binding_key=binding_key)
        token = generate_opaque_session_token(nbytes=32)
        token_hash = hash_csrf_token(token)
        await self._repository.store(
            token_hash=token_hash,
            binding_key=binding_key,
            expires_at=now + _CSRF_TTL,
        )
        return IssuedCsrfToken(token=token, binding_key=binding_key)

    async def revoke_binding(self, *, binding_key: str) -> None:
        await self._repository.revoke_binding(binding_key=binding_key)

    def attach_token_to_response(
        self,
        response: Response,
        *,
        token: str,
        binding_key: str,
        settings: Settings,
    ) -> None:
        cookie_policy = csrf_cookie_policy_for_binding(binding_key)
        env = settings.app_env.strip().lower()
        secure = not (env in {"development", "test"} and settings.allow_insecure_cookies)
        response.set_cookie(
            key=cookie_policy.name,
            value=token,
            httponly=False,
            secure=secure,
            samesite="strict",
            path=cookie_policy.path,
            max_age=int(_CSRF_TTL.total_seconds()),
        )
        response.headers[_policy.header_name] = token

    def clear_csrf_cookie(
        self,
        response: Response,
        *,
        binding_key: str,
        settings: Settings,
    ) -> None:
        cookie_policy = csrf_cookie_policy_for_binding(binding_key)
        env = settings.app_env.strip().lower()
        secure = not (env in {"development", "test"} and settings.allow_insecure_cookies)
        response.delete_cookie(
            key=cookie_policy.name,
            path=cookie_policy.path,
            httponly=False,
            secure=secure,
            samesite="strict",
        )

    async def verify_request(
        self,
        request: Request,
        *,
        binding_key: str,
        now: datetime,
    ) -> None:
        cookie_policy = csrf_cookie_policy_for_binding(binding_key)
        header = request.headers.get(_policy.header_name, "").strip()
        cookie = request.cookies.get(cookie_policy.name, "").strip()
        if not header or not cookie:
            raise CsrfValidationError("CSRF ausente.")
        try:
            header_bytes = header.encode("utf-8")
            cookie_bytes = cookie.encode("utf-8")
        except UnicodeError as exc:
            raise CsrfValidationError("CSRF inválido.") from exc
        if len(header_bytes) != len(cookie_bytes) or not secrets.compare_digest(
            header_bytes, cookie_bytes
        ):
            raise CsrfValidationError("CSRF mismatch.")
        token_hash = hash_csrf_token(header)
        ok = await self._repository.validate_if_valid(
            token_hash=token_hash,
            binding_key=binding_key,
            now=now,
        )
        if not ok:
            raise CsrfValidationError("CSRF inválido o expirado.")
