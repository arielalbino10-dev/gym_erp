"""Revoca todas las sesiones activas de un usuario (opcionalmente por kind)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from gym_erp_api.modules.identity.application.ports.session_repository import SessionRepository
from gym_erp_api.modules.identity.domain.session_kind import SessionKind
from gym_erp_api.modules.identity.domain.time_utils import utc_now_ms
from gym_erp_api.modules.identity.domain.validators import require_user_uuid_v4


class RevokeAllUserSessionsUseCase:
    def __init__(
        self,
        *,
        sessions: SessionRepository,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._sessions = sessions
        self._clock = clock or utc_now_ms

    async def execute(
        self,
        *,
        user_id: str,
        reason: str,
        session_kind: SessionKind | None = None,
    ) -> int:
        uid = require_user_uuid_v4(user_id)
        return await self._sessions.revoke_all_for_user(
            uid,
            session_kind=session_kind,
            reason=reason,
            revoked_at=self._clock(),
        )
