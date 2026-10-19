"""Resultados internos de autenticación (sin contraseñas ni tokens en repr)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from gym_erp_api.modules.identity.domain.auth_session import AuthSession
from gym_erp_api.modules.identity.domain.session_kind import SessionKind


@dataclass(frozen=True, slots=True)
class VerifiedPrincipal:
    """Identidad autenticada tras verificación de credenciales."""

    user_id: str
    credential_version: int
    email_normalized: str
    verified_at: datetime


@dataclass(frozen=True, slots=True)
class CreatedSession:
    """Sesión recién emitida; el token opaco solo existe en memoria del llamador."""

    session: AuthSession
    opaque_token: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class ResolvedSession:
    """Sesión resuelta y validada para uso interno (sin permisos operativos)."""

    session: AuthSession
    user_id: str
    session_kind: SessionKind
    credential_version: int
    active_tenant_id: str | None
