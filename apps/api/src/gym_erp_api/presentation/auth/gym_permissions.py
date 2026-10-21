"""Dependencias FastAPI: permiso gym + contexto tenant (H2-C.4)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Query, Request

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
) -> Callable[..., object]:
    """Factory Depends: reutiliza sesión, tenant y membresía vigentes."""

    async def _dependency(
        request: Request,
        branch_id: Annotated[str | None, Query()] = None,
    ) -> GymRequestContext:
        gym_ctx = await require_gym_tenant_context(request)
        access = require_access_infrastructure(request)
        auth = access.gym_authorization_service.trusted_context_from_resolved(gym_ctx.tenant)
        try:
            access.gym_authorization_service.require_permission(
                auth=auth,
                permission=permission,
                branch_id=branch_id,
            )
        except PermissionDeniedError as exc:
            raise GymAccessDeniedError() from exc
        return gym_ctx

    return _dependency
