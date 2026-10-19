"""Emite sesión opaca gym tras principal verificado."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from gym_erp_api.modules.identity.application.dto.auth_results import (
    CreatedSession,
    VerifiedPrincipal,
)
from gym_erp_api.modules.identity.application.errors import AuthenticationFailedError
from gym_erp_api.modules.identity.application.policies.session_timing_policy import (
    SessionTimingPolicy,
)
from gym_erp_api.modules.identity.application.ports.identity_repository import IdentityRepository
from gym_erp_api.modules.identity.application.ports.session_repository import SessionRepository
from gym_erp_api.modules.identity.application.services.identity_guard import require_active_identity
from gym_erp_api.modules.identity.domain.auth_session import AuthSession
from gym_erp_api.modules.identity.domain.session_kind import SessionKind
from gym_erp_api.modules.identity.domain.time_utils import utc_now_ms
from gym_erp_api.modules.identity.domain.validators import require_user_uuid_v4
from gym_erp_api.modules.identity.infrastructure.crypto.session_token_hash import (
    generate_opaque_session_token,
    hash_session_token,
)


class CreateGymSessionUseCase:
    """``active_tenant_id`` es hint de contexto futuro; no sustituye membresía (H2-C)."""

    def __init__(
        self,
        *,
        identities: IdentityRepository,
        sessions: SessionRepository,
        timing: SessionTimingPolicy | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._identities = identities
        self._sessions = sessions
        self._timing = timing or SessionTimingPolicy()
        self._clock = clock or utc_now_ms

    async def execute(
        self,
        *,
        principal: VerifiedPrincipal,
        active_tenant_id: str | None = None,
    ) -> CreatedSession:
        identity = await require_active_identity(self._identities, principal.user_id)
        if identity.credential_version != principal.credential_version:
            raise AuthenticationFailedError("Credenciales inválidas o cuenta no disponible.")
        tenant_id = (
            require_user_uuid_v4(active_tenant_id, "active_tenant_id") if active_tenant_id else None
        )
        now = self._clock()
        opaque = generate_opaque_session_token()
        token_hash = hash_session_token(opaque)
        expires = self._timing.absolute_expires_at(SessionKind.GYM, now)
        idle = self._timing.idle_expires_at(SessionKind.GYM, now, absolute_cap=expires)
        session = AuthSession.create(
            user_id=identity.user_id,
            session_kind=SessionKind.GYM,
            token_hash=token_hash,
            expires_at=expires,
            idle_expires_at=idle,
            credential_version=identity.credential_version,
            active_tenant_id=tenant_id,
            now=now,
        )
        await self._sessions.insert(session)
        return CreatedSession(session=session, opaque_token=opaque)
