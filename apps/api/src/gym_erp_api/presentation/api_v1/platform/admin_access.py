"""Endpoints RBAC platform (MVP H3-A.3 / incremento A)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from gym_erp_api.modules.platform_admin.domain.platform_permission import (
    PLATFORM_PERMISSION_CATALOG_VERSION,
    PlatformPermission,
)
from gym_erp_api.presentation.auth.platform_context import (
    PlatformRequestContext,
    require_platform_admin_infrastructure,
    require_platform_request_context,
)
from gym_erp_api.presentation.auth.platform_permissions import require_platform_permission

router = APIRouter(prefix="/admin", tags=["platform-admin"])


@router.get("/access")
async def platform_access_summary(request: Request) -> JSONResponse:
    """Resumen de permisos efectivos del operador (solo lectura)."""
    ctx = await require_platform_request_context(request)
    admin = require_platform_admin_infrastructure(request)
    perms = await admin.platform_authorization_service.effective_permissions(
        user_id=ctx.resolved_session.user_id,
    )
    return JSONResponse(
        status_code=200,
        content={
            "user_id": ctx.resolved_session.user_id,
            "catalog_version": PLATFORM_PERMISSION_CATALOG_VERSION,
            "permissions": sorted(p.value for p in perms),
        },
    )


@router.get("/system/health-summary")
async def platform_system_health_summary(
    _ctx: PlatformRequestContext = Depends(
        require_platform_permission(PlatformPermission.PLATFORM_SYSTEM_READ),
    ),
) -> JSONResponse:
    """Placeholder RBAC-only; no sustituye monitoreo operativo (incremento H)."""
    return JSONResponse(
        status_code=200,
        content={
            "maturity": "provisional_stub",
            "status": "reachable",
            "note": "Endpoint de humo RBAC; sin métricas ni diagnóstico de infraestructura.",
        },
    )
