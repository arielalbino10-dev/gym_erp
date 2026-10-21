"""Puerto de persistencia de sesiones opacas (hash de token)."""

from datetime import datetime
from typing import Protocol

from gym_erp_api.modules.identity.domain.auth_session import AuthSession
from gym_erp_api.modules.identity.domain.session_kind import SessionKind


class SessionRepository(Protocol):
    async def insert(self, session: AuthSession) -> None:
        """Persiste una sesión nueva."""

    async def get_by_id(self, session_id: str) -> AuthSession | None:
        """Busca sesión por session_id."""

    async def get_by_token_hash(self, token_hash: str) -> AuthSession | None:
        """Busca sesión por hash SHA-256 del token opaco."""

    async def save_revoked(self, session: AuthSession) -> None:
        """Persiste revocación (expected: sesión no revocada previamente)."""

    async def revoke_all_for_user(
        self,
        user_id: str,
        *,
        session_kind: SessionKind | None = None,
        reason: str,
        revoked_at: datetime,
    ) -> int:
        """Revoca todas las sesiones activas del usuario; devuelve cantidad afectada."""

    async def touch_activity(
        self,
        session: AuthSession,
        *,
        expected_last_seen_at: datetime,
    ) -> AuthSession:
        """Actualiza last_seen_at e idle_expires_at con concurrencia optimista."""

    async def update_gym_tenant_selection(
        self,
        session: AuthSession,
        *,
        expected_last_seen_at: datetime,
    ) -> AuthSession:
        """Persiste active_tenant_id y gym_membership_authz_epoch (sesión gym, OCC)."""
