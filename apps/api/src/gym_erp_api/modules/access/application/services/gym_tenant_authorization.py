"""Autorización gym: epoch de sesión vs membresía (H2-C.3)."""

from __future__ import annotations

from gym_erp_api.modules.access.application.dto.trusted_auth import TrustedGymAuthContext
from gym_erp_api.modules.access.application.errors import (
    MembershipAccessDeniedError,
    TenantNotSelectedError,
)
from gym_erp_api.modules.access.application.services.tenant_context_factory import (
    ResolvedTenantContext,
    TenantContextFactory,
)
from gym_erp_api.modules.identity.application.dto.auth_results import ResolvedSession


async def resolve_gym_tenant_context(
    *,
    resolved: ResolvedSession,
    factory: TenantContextFactory,
) -> ResolvedTenantContext:
    if resolved.active_tenant_id is None:
        raise TenantNotSelectedError("No hay tenant gym seleccionado en la sesión.")
    auth = TrustedGymAuthContext(
        user_id=resolved.user_id,
        selected_tenant_id=resolved.active_tenant_id,
    )
    ctx = await factory.build_for_gym(auth)
    session_epoch = resolved.gym_membership_authz_epoch
    if session_epoch is not None and session_epoch != ctx.authz_epoch:
        raise MembershipAccessDeniedError(
            "La autorización gym cambió; seleccione el gimnasio de nuevo."
        )
    return ctx
