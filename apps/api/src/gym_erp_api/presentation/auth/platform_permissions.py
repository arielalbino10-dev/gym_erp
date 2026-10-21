"""Dependencias FastAPI: permisos platform (RBAC server-side)."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Request

from gym_erp_api.modules.platform_admin.application.errors import PlatformPermissionDeniedError
from gym_erp_api.modules.platform_admin.domain.platform_permission import PlatformPermission
from gym_erp_api.presentation.auth.platform_context import (
    PlatformRequestContext,
    require_platform_admin_infrastructure,
    require_platform_request_context,
)
from gym_erp_api.presentation.http_security.errors import PlatformAccessDeniedError


def require_platform_permission(
    permission: PlatformPermission,
) -> Callable[..., object]:
    async def _dependency(request: Request) -> PlatformRequestContext:
        ctx = await require_platform_request_context(request)
        admin = require_platform_admin_infrastructure(request)
        try:
            await admin.platform_authorization_service.require_permission(
                user_id=ctx.resolved_session.user_id,
                permission=permission,
            )
        except PlatformPermissionDeniedError as exc:
            raise PlatformAccessDeniedError() from exc
        return ctx

    return _dependency
