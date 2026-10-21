"""Dependencias FastAPI: permiso gym + contexto tenant (H2-C.4)."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Request

from gym_erp_api.modules.access.application.errors import PermissionDeniedError
from gym_erp_api.modules.access.domain.gym_permission import GymPermission
from gym_erp_api.presentation.auth.gym_context import (
    GymRequestContext,
    require_access_infrastructure,
    require_gym_tenant_context,
)
from gym_erp_api.presentation.http_security.errors import GymAccessDeniedError


def require_gym_permission(
    permission: GymPermission,
    *,
    list_operation: bool = False,
) -> Callable[..., object]:
    """Factory Depends: reutiliza sesión, tenant y membresía vigentes."""

    async def _dependency(request: Request) -> GymRequestContext:
        gym_ctx = await require_gym_tenant_context(request)
        access = require_access_infrastructure(request)
        auth = access.gym_authorization_service.trusted_context_from_resolved(gym_ctx.tenant)
        try:
            access.gym_authorization_service.require_permission(
                auth=auth,
                permission=permission,
                list_operation=list_operation,
            )
        except PermissionDeniedError as exc:
            raise GymAccessDeniedError() from exc
        return gym_ctx

    return _dependency


def require_gym_branch_read() -> Callable[..., object]:
    """Lectura/listado de sucursales sin exigir branch_id en query (alcance vía Mongo)."""
    return require_gym_permission(GymPermission.BRANCHES_READ, list_operation=True)
