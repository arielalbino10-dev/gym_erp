"""Comprobaciones de identidad para sesiones (sin TenantContext)."""

from __future__ import annotations

from gym_erp_api.modules.identity.application.errors import (
    AuthenticationFailedError,
    SessionResolutionFailedError,
)
from gym_erp_api.modules.identity.application.ports.identity_repository import IdentityRepository
from gym_erp_api.modules.identity.domain.enums import UserIdentityStatus
from gym_erp_api.modules.identity.domain.user_identity import UserIdentity

_GENERIC_AUTH_FAILURE = "Credenciales inválidas o cuenta no disponible."
_GENERIC_SESSION_FAILURE = "Sesión inválida o expirada."


async def require_active_identity(
    identities: IdentityRepository,
    user_id: str,
) -> UserIdentity:
    identity = await identities.get_by_id(user_id)
    if identity is None or identity.status is not UserIdentityStatus.ACTIVE:
        raise AuthenticationFailedError(_GENERIC_AUTH_FAILURE)
    return identity


async def require_active_identity_for_session(
    identities: IdentityRepository,
    user_id: str,
    *,
    expected_credential_version: int,
) -> UserIdentity:
    identity = await identities.get_by_id(user_id)
    if identity is None or identity.status is not UserIdentityStatus.ACTIVE:
        raise SessionResolutionFailedError(_GENERIC_SESSION_FAILURE)
    if identity.credential_version != expected_credential_version:
        raise SessionResolutionFailedError(_GENERIC_SESSION_FAILURE)
    return identity
