"""Sesión platform confiable para consola administrativa."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from gym_erp_api.infrastructure.platform_admin.platform_admin_container import (
    PlatformAdminInfrastructure,
)
from gym_erp_api.modules.identity.application.dto.auth_results import ResolvedSession
from gym_erp_api.modules.identity.application.errors import SessionResolutionFailedError
from gym_erp_api.modules.identity.domain.session_kind import SessionKind
from gym_erp_api.presentation.auth.http_support import (
    read_session_token_from_request,
    require_infra,
)
from gym_erp_api.presentation.http_security.errors import (
    IdentityInfrastructureUnavailableError,
    PlatformNotAuthenticatedError,
)


@dataclass(frozen=True, slots=True)
class PlatformRequestContext:
    resolved_session: ResolvedSession


def require_platform_admin_infrastructure(request: Request) -> PlatformAdminInfrastructure:
    infra = getattr(request.app.state, "platform_admin_infrastructure", None)
    if infra is None:
        raise IdentityInfrastructureUnavailableError()
    return infra


async def require_resolved_platform_session(request: Request) -> ResolvedSession:
    infra = require_infra(request)
    token = read_session_token_from_request(request, kind=SessionKind.PLATFORM)
    if not token:
        raise PlatformNotAuthenticatedError()
    try:
        resolved = await infra.resolve_session.execute(opaque_token=token, touch_activity=True)
    except SessionResolutionFailedError as exc:
        raise PlatformNotAuthenticatedError() from exc
    if resolved.session_kind is not SessionKind.PLATFORM:
        raise PlatformNotAuthenticatedError()
    await infra.platform_session_eligibility.require_eligible_operator(user_id=resolved.user_id)
    return resolved


async def require_platform_request_context(request: Request) -> PlatformRequestContext:
    resolved = await require_resolved_platform_session(request)
    return PlatformRequestContext(resolved_session=resolved)
