"""Resuelve token opaco a sesión validada (sin permisos RBAC)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from gym_erp_api.modules.identity.application.dto.auth_results import ResolvedSession
from gym_erp_api.modules.identity.application.errors import SessionResolutionFailedError
from gym_erp_api.modules.identity.application.policies.session_timing_policy import (
    SessionTimingPolicy,
)
from gym_erp_api.modules.identity.application.ports.identity_repository import IdentityRepository
from gym_erp_api.modules.identity.application.ports.session_repository import SessionRepository
from gym_erp_api.modules.identity.application.services.identity_guard import (
    require_active_identity_for_session,
)
from gym_erp_api.modules.identity.domain.errors import (
    SessionExpiredError,
    SessionRevokedError,
    SessionUpdateConflictError,
)
from gym_erp_api.modules.identity.domain.time_utils import utc_now_ms
from gym_erp_api.modules.identity.infrastructure.crypto.session_token_hash import hash_session_token

_GENERIC_SESSION_FAILURE = "Sesión inválida o expirada."


class ResolveSessionUseCase:
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
        opaque_token: str,
        touch_activity: bool = True,
    ) -> ResolvedSession:
        if not isinstance(opaque_token, str) or not opaque_token.strip():
            raise SessionResolutionFailedError(_GENERIC_SESSION_FAILURE)
        try:
            token_hash = hash_session_token(opaque_token)
        except ValueError as exc:
            raise SessionResolutionFailedError(_GENERIC_SESSION_FAILURE) from exc

        stored = await self._sessions.get_by_token_hash(token_hash)
        if stored is None:
            raise SessionResolutionFailedError(_GENERIC_SESSION_FAILURE)

        now = self._clock()
        try:
            stored.assert_usable_at(now)
        except (SessionRevokedError, SessionExpiredError) as exc:
            raise SessionResolutionFailedError(_GENERIC_SESSION_FAILURE) from exc

        await require_active_identity_for_session(
            self._identities,
            stored.user_id,
            expected_credential_version=stored.credential_version,
        )

        session = stored
        if touch_activity and self._timing.should_touch(stored.last_seen_at, now):
            idle = self._timing.idle_expires_at(
                stored.session_kind,
                now,
                absolute_cap=stored.expires_at,
            )
            touched = stored.touch_activity(idle_expires_at=idle, now=now)
            try:
                session = await self._sessions.touch_activity(
                    touched,
                    expected_last_seen_at=stored.last_seen_at,
                )
            except SessionUpdateConflictError:
                refreshed = await self._sessions.get_by_id(stored.session_id)
                if refreshed is None:
                    raise SessionResolutionFailedError(_GENERIC_SESSION_FAILURE) from None
                try:
                    refreshed.assert_usable_at(now)
                except (SessionRevokedError, SessionExpiredError) as exc:
                    raise SessionResolutionFailedError(_GENERIC_SESSION_FAILURE) from exc
                session = refreshed

        return ResolvedSession(
            session=session,
            user_id=session.user_id,
            session_kind=session.session_kind,
            credential_version=session.credential_version,
            active_tenant_id=session.active_tenant_id,
        )
