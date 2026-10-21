"""Vista HTTP de sesión gym (sin TenantContext completo)."""

from __future__ import annotations

from gym_erp_api.infrastructure.access.access_container import AccessInfrastructure
from gym_erp_api.modules.access.application.dto.trusted_auth import TrustedGymAuthContext
from gym_erp_api.modules.access.application.errors import (
    MembershipAccessDeniedError,
    MembershipNotFoundError,
)
from gym_erp_api.modules.identity.application.dto.auth_results import ResolvedSession
from gym_erp_api.presentation.auth.schemas import SessionResponse


async def build_gym_session_response(
    *,
    resolved: ResolvedSession,
    access: AccessInfrastructure,
) -> SessionResponse:
    body = SessionResponse(
        user_id=resolved.user_id,
        session_kind=resolved.session_kind.value,
        active_tenant_id=resolved.active_tenant_id,
    )
    if resolved.active_tenant_id is None:
        return body
    auth = TrustedGymAuthContext(
        user_id=resolved.user_id,
        selected_tenant_id=resolved.active_tenant_id,
    )
    try:
        ctx = await access.tenant_context_factory.build_for_gym(auth)
    except (MembershipNotFoundError, MembershipAccessDeniedError):
        return SessionResponse(
            user_id=resolved.user_id,
            session_kind=resolved.session_kind.value,
            active_tenant_id=None,
        )
    session_epoch = resolved.gym_membership_authz_epoch
    if session_epoch is not None and session_epoch != ctx.authz_epoch:
        return SessionResponse(
            user_id=resolved.user_id,
            session_kind=resolved.session_kind.value,
            active_tenant_id=None,
        )
    tenant = await access.tenant_repository.get_by_id(resolved.active_tenant_id)
    display = tenant.display_name if tenant is not None else None
    return SessionResponse(
        user_id=resolved.user_id,
        session_kind=resolved.session_kind.value,
        active_tenant_id=resolved.active_tenant_id,
        membership_id=ctx.context.membership_id,
        gym_roles=sorted(ctx.gym_roles),
        tenant_display_name=display,
    )
