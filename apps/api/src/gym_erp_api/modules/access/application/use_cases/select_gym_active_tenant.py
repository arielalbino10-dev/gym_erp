"""Selección server-side de tenant gym en sesión opaca."""

from __future__ import annotations

from gym_erp_api.modules.access.application.dto.trusted_auth import TrustedGymAuthContext
from gym_erp_api.modules.access.application.errors import MembershipAccessDeniedError
from gym_erp_api.modules.access.application.services.tenant_context_factory import (
    TenantContextFactory,
)
from gym_erp_api.modules.identity.application.dto.auth_results import ResolvedSession
from gym_erp_api.modules.identity.application.ports.session_repository import SessionRepository
from gym_erp_api.modules.identity.domain.errors import SessionUpdateConflictError
from gym_erp_api.modules.identity.domain.session_kind import SessionKind
from gym_erp_api.modules.organization.domain.validators import require_uuid_v4


class SelectGymActiveTenantUseCase:
    def __init__(
        self,
        *,
        sessions: SessionRepository,
        tenant_context_factory: TenantContextFactory,
    ) -> None:
        self._sessions = sessions
        self._factory = tenant_context_factory

    async def execute(
        self,
        *,
        resolved: ResolvedSession,
        tenant_id: str,
    ) -> ResolvedSession:
        if resolved.session_kind is not SessionKind.GYM:
            raise MembershipAccessDeniedError("Sesión no es de gimnasio.")
        tid = require_uuid_v4(tenant_id, "tenant_id")
        auth = TrustedGymAuthContext(user_id=resolved.user_id, selected_tenant_id=tid)
        ctx = await self._factory.build_for_gym(auth)
        updated_session = resolved.session.with_gym_tenant_selection(
            active_tenant_id=tid,
            membership_authz_epoch=ctx.authz_epoch,
        )
        try:
            persisted = await self._sessions.update_gym_tenant_selection(
                updated_session,
                expected_last_seen_at=resolved.session.last_seen_at,
            )
        except SessionUpdateConflictError as exc:
            raise MembershipAccessDeniedError(
                "Conflicto al seleccionar tenant; reintente."
            ) from exc
        return ResolvedSession(
            session=persisted,
            user_id=resolved.user_id,
            session_kind=resolved.session_kind,
            credential_version=resolved.credential_version,
            active_tenant_id=persisted.active_tenant_id,
            gym_membership_authz_epoch=persisted.gym_membership_authz_epoch,
        )
