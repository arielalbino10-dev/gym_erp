"""Verificación interna email + contraseña (sin HTTP)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from gym_erp_api.modules.identity.application.dto.auth_results import VerifiedPrincipal
from gym_erp_api.modules.identity.application.errors import AuthenticationFailedError
from gym_erp_api.modules.identity.application.ports.credential_repository import (
    CredentialRepository,
)
from gym_erp_api.modules.identity.application.ports.identity_repository import IdentityRepository
from gym_erp_api.modules.identity.application.ports.password_hasher import PasswordHasher
from gym_erp_api.modules.identity.domain.enums import UserIdentityStatus
from gym_erp_api.modules.identity.domain.errors import InvalidIdentityFieldError
from gym_erp_api.modules.identity.domain.time_utils import utc_now_ms
from gym_erp_api.modules.identity.domain.validators import normalize_identity_email
from gym_erp_api.modules.identity.infrastructure.crypto.argon2_password_hasher import (
    InvalidStoredPasswordHashError,
)
from gym_erp_api.modules.identity.infrastructure.crypto.timing_safe_verification import (
    dummy_credential_hash_for_timing,
    verify_password_async,
)

_GENERIC_AUTH_FAILURE = "Credenciales inválidas o cuenta no disponible."
_MAX_PASSWORD_LEN = 256


class CredentialVerificationService:
    def __init__(
        self,
        *,
        identities: IdentityRepository,
        credentials: CredentialRepository,
        password_hasher: PasswordHasher,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._identities = identities
        self._credentials = credentials
        self._hasher = password_hasher
        self._clock = clock or utc_now_ms

    async def verify(self, *, email: str, password: str) -> VerifiedPrincipal:
        if not isinstance(email, str) or not isinstance(password, str):
            raise AuthenticationFailedError(_GENERIC_AUTH_FAILURE)
        if not password or len(password) > _MAX_PASSWORD_LEN:
            raise AuthenticationFailedError(_GENERIC_AUTH_FAILURE)
        try:
            _, normalized = normalize_identity_email(email)
        except InvalidIdentityFieldError as exc:
            raise AuthenticationFailedError(_GENERIC_AUTH_FAILURE) from exc

        identity = await self._identities.get_by_email_normalized(normalized)
        credential = await self._credentials.get_by_user_id(identity.user_id) if identity else None
        if credential is not None:
            stored_hash = credential.password_hash
        else:
            stored_hash = dummy_credential_hash_for_timing()
        try:
            password_ok = await verify_password_async(self._hasher, password, stored_hash)
        except InvalidStoredPasswordHashError as exc:
            raise AuthenticationFailedError(_GENERIC_AUTH_FAILURE) from exc

        if identity is None or credential is None or not password_ok:
            raise AuthenticationFailedError(_GENERIC_AUTH_FAILURE)

        if identity.status is not UserIdentityStatus.ACTIVE:
            raise AuthenticationFailedError(_GENERIC_AUTH_FAILURE)

        return VerifiedPrincipal(
            user_id=identity.user_id,
            credential_version=identity.credential_version,
            email_normalized=identity.email_normalized,
            verified_at=self._clock(),
        )
