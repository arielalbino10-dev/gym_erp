"""Emite sesión platform solo tras consumo atómico de autorización MFA."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from gym_erp_api.modules.identity.application.dto.auth_results import (
    CreatedSession,
    VerifiedPrincipal,
)
from gym_erp_api.modules.identity.application.errors import (
    AuthenticationFailedError,
    PlatformMfaRequiredError,
    PlatformSessionEmissionDisabledError,
)
from gym_erp_api.modules.identity.application.policies.session_timing_policy import (
    SessionTimingPolicy,
)
from gym_erp_api.modules.identity.application.ports import (
    IdentityRepository,
    PlatformMfaSessionAuthorizationRepository,
    SessionRepository,
)
from gym_erp_api.modules.identity.application.services.identity_guard import require_active_identity
from gym_erp_api.modules.identity.domain.auth_session import AuthSession
from gym_erp_api.modules.identity.domain.session_kind import SessionKind
from gym_erp_api.modules.identity.domain.time_utils import utc_now_ms
from gym_erp_api.modules.identity.domain.validators import require_user_uuid_v4
from gym_erp_api.modules.identity.infrastructure.crypto.session_token_hash import (
    generate_opaque_session_token,
    hash_session_token,
)

_GENERIC_AUTH_FAILURE = "Credenciales inválidas o cuenta no disponible."


class CreatePlatformSessionUseCase:
    def __init__(
        self,
        *,
        identities: IdentityRepository,
        sessions: SessionRepository,
        authorizations: PlatformMfaSessionAuthorizationRepository | None = None,
        timing: SessionTimingPolicy | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._identities = identities
        self._sessions = sessions
        self._authorizations = authorizations
        self._timing = timing or SessionTimingPolicy()
        self._clock = clock or utc_now_ms

    async def execute(
        self,
        *,
        principal: VerifiedPrincipal,
        authorization_id: str,
    ) -> CreatedSession:
        if self._authorizations is None:
            raise PlatformSessionEmissionDisabledError(
                "Emisión platform requiere repositorio de autorizaciones MFA (H2-B.5)."
            )
        aid = require_user_uuid_v4(authorization_id, "authorization_id")
        now = self._clock()
        consumed = await self._authorizations.consume_for_session(
            aid,
            user_id=principal.user_id,
            credential_version=principal.credential_version,
            now=now,
        )
        if not consumed:
            raise PlatformMfaRequiredError("Autorización MFA inválida, expirada o ya utilizada.")

        identity = await require_active_identity(self._identities, principal.user_id)
        if identity.credential_version != principal.credential_version:
            raise AuthenticationFailedError(_GENERIC_AUTH_FAILURE)

        opaque = generate_opaque_session_token()
        token_hash = hash_session_token(opaque)
        expires = self._timing.absolute_expires_at(SessionKind.PLATFORM, now)
        idle = self._timing.idle_expires_at(SessionKind.PLATFORM, now, absolute_cap=expires)
        session = AuthSession.create(
            user_id=identity.user_id,
            session_kind=SessionKind.PLATFORM,
            token_hash=token_hash,
            expires_at=expires,
            idle_expires_at=idle,
            credential_version=identity.credential_version,
            active_tenant_id=None,
            now=now,
        )
        await self._sessions.insert(session)
        return CreatedSession(session=session, opaque_token=opaque)
