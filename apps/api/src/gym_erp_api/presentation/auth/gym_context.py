"""Resolución de sesión gym y TenantContext confiable (H2-C.3)."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from gym_erp_api.infrastructure.access.access_container import AccessInfrastructure
from gym_erp_api.modules.access.application.errors import (
    AccessApplicationError,
    TenantNotSelectedError,
)
from gym_erp_api.modules.access.application.services.gym_tenant_authorization import (
    resolve_gym_tenant_context,
)
from gym_erp_api.modules.access.application.services.tenant_context_factory import (
    ResolvedTenantContext,
)
from gym_erp_api.modules.identity.application.dto.auth_results import ResolvedSession
from gym_erp_api.modules.identity.application.errors import SessionResolutionFailedError
from gym_erp_api.modules.identity.domain.session_kind import SessionKind
from gym_erp_api.presentation.auth.http_support import (
    read_session_token_from_request,
    require_infra,
)
from gym_erp_api.presentation.http_security.errors import (
    AccessInfrastructureUnavailableError,
    GymAccessDeniedError,
    GymNotAuthenticatedError,
    GymTenantNotSelectedError,
)


@dataclass(frozen=True, slots=True)
class GymRequestContext:
    resolved_session: ResolvedSession
    tenant: ResolvedTenantContext


def require_access_infrastructure(request: Request) -> AccessInfrastructure:
    access = getattr(request.app.state, "access_infrastructure", None)
    if access is None:
        raise AccessInfrastructureUnavailableError()
    return access


async def require_resolved_gym_session(request: Request) -> ResolvedSession:
    infra = require_infra(request)
    token = read_session_token_from_request(request, kind=SessionKind.GYM)
    if not token:
        raise GymNotAuthenticatedError()
    try:
        resolved = await infra.resolve_session.execute(opaque_token=token, touch_activity=True)
    except SessionResolutionFailedError as exc:
        raise GymNotAuthenticatedError() from exc
    if resolved.session_kind is not SessionKind.GYM:
        raise GymNotAuthenticatedError()
    return resolved


async def require_gym_tenant_context(request: Request) -> GymRequestContext:
    access = require_access_infrastructure(request)
    resolved = await require_resolved_gym_session(request)
    try:
        tenant = await resolve_gym_tenant_context(
            resolved=resolved,
            factory=access.tenant_context_factory,
        )
    except TenantNotSelectedError as exc:
        raise GymTenantNotSelectedError() from exc
    except AccessApplicationError as exc:
        raise GymAccessDeniedError() from exc
    return GymRequestContext(resolved_session=resolved, tenant=tenant)
