"""Emite sesión platform solo con ticket MFA emitido por puerto dedicado."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

from gym_erp_api.modules.identity.application.dto.auth_results import (
    CreatedSession,
    VerifiedPrincipal,
)
from gym_erp_api.modules.identity.application.dto.platform_mfa import PlatformMfaVerificationTicket
from gym_erp_api.modules.identity.application.errors import (
    AuthenticationFailedError,
    PlatformMfaRequiredError,
)
from gym_erp_api.modules.identity.application.policies.session_timing_policy import (
    SessionTimingPolicy,
)
from gym_erp_api.modules.identity.application.ports.identity_repository import IdentityRepository
from gym_erp_api.modules.identity.application.ports.platform_session_emission_gate import (
    HardDisabledPlatformSessionEmission,
    PlatformSessionEmissionGate,
)
from gym_erp_api.modules.identity.application.ports.session_repository import SessionRepository
from gym_erp_api.modules.identity.application.services.identity_guard import require_active_identity
from gym_erp_api.modules.identity.domain.auth_session import AuthSession
from gym_erp_api.modules.identity.domain.session_kind import SessionKind
from gym_erp_api.modules.identity.domain.time_utils import utc_now_ms
from gym_erp_api.modules.identity.infrastructure.crypto.session_token_hash import (
    generate_opaque_session_token,
    hash_session_token,
)

_GENERIC_AUTH_FAILURE = "Credenciales inválidas o cuenta no disponible."
_PLATFORM_MFA_MAX_AGE = timedelta(minutes=5)


class CreatePlatformSessionUseCase:
    def __init__(
        self,
        *,
        identities: IdentityRepository,
        sessions: SessionRepository,
        timing: SessionTimingPolicy | None = None,
        clock: Callable[[], datetime] | None = None,
        emission_gate: PlatformSessionEmissionGate | None = None,
    ) -> None:
        self._identities = identities
        self._sessions = sessions
        self._timing = timing or SessionTimingPolicy()
        self._clock = clock or utc_now_ms
        self._emission_gate = emission_gate or HardDisabledPlatformSessionEmission()

    async def execute(
        self,
        *,
        principal: VerifiedPrincipal,
        mfa_ticket: PlatformMfaVerificationTicket | None,
    ) -> CreatedSession:
        self._emission_gate.assert_emission_allowed()
        if mfa_ticket is None:
            raise PlatformMfaRequiredError("MFA platform requerido antes de emitir sesión.")
        if mfa_ticket.user_id != principal.user_id:
            raise PlatformMfaRequiredError("MFA platform requerido antes de emitir sesión.")
        now = self._clock()
        if now - mfa_ticket.verified_at > _PLATFORM_MFA_MAX_AGE:
            raise PlatformMfaRequiredError("MFA platform requerido antes de emitir sesión.")

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
