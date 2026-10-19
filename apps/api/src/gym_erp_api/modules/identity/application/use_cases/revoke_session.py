"""Revoca una sesión por id."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from gym_erp_api.modules.identity.application.errors import SessionRevocationFailedError
from gym_erp_api.modules.identity.application.ports.session_repository import SessionRepository
from gym_erp_api.modules.identity.domain.time_utils import utc_now_ms

_GENERIC_REVOCATION_FAILURE = "No se pudo revocar la sesión."


class RevokeSessionUseCase:
    def __init__(
        self,
        *,
        sessions: SessionRepository,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._sessions = sessions
        self._clock = clock or utc_now_ms

    async def execute(self, *, session_id: str, reason: str) -> None:
        stored = await self._sessions.get_by_id(session_id)
        if stored is None:
            raise SessionRevocationFailedError(_GENERIC_REVOCATION_FAILURE)
        if stored.is_revoked():
            return
        revoked = stored.revoke(reason=reason, now=self._clock())
        try:
            await self._sessions.save_revoked(revoked)
        except Exception as exc:
            raise SessionRevocationFailedError(_GENERIC_REVOCATION_FAILURE) from exc
