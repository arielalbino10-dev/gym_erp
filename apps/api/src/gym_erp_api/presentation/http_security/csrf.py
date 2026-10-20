"""CSRF: double-submit + registro server-side."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from starlette.requests import Request

from gym_erp_api.infrastructure.mongo.mongo_csrf_token_repository import MongoCsrfTokenRepository
from gym_erp_api.modules.identity.application.security.http_auth_contracts import CsrfPolicy
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
        token = generate_opaque_session_token(nbytes=32)
        token_hash = hash_csrf_token(token)
        await self._repository.store(
            token_hash=token_hash,
            binding_key=binding_key,
            expires_at=now + _CSRF_TTL,
        )
        return IssuedCsrfToken(token=token, binding_key=binding_key)

    async def verify_request(
        self,
        request: Request,
        *,
        binding_key: str,
        now: datetime,
    ) -> None:
        header = request.headers.get(_policy.header_name, "").strip()
        cookie = request.cookies.get(_policy.cookie_name, "").strip()
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
        ok = await self._repository.consume_if_valid(
            token_hash=token_hash,
            binding_key=binding_key,
            now=now,
        )
        if not ok:
            raise CsrfValidationError("CSRF inválido o expirado.")
