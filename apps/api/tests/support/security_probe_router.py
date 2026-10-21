"""Rutas de prueba para protecciones HTTP (solo tests, no producción)."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from gym_erp_api.modules.access.domain.gym_permission import GymPermission
from gym_erp_api.modules.identity.application.security.http_auth_contracts import (
    CsrfPolicy,
)
from gym_erp_api.presentation.auth.gym_context import (
    GymRequestContext,
    require_access_infrastructure,
    require_gym_tenant_context,
)
from gym_erp_api.presentation.auth.gym_permissions import require_gym_permission
from gym_erp_api.presentation.http_security.cookies import (
    clear_gym_session_cookie,
    clear_platform_session_cookie,
    set_platform_session_cookie,
)
from gym_erp_api.presentation.http_security.dependencies import (
    enforce_cookie_session_mutation_security,
    enforce_login_rate_limits,
    enforce_pre_authentication_mutation_security,
    get_app_settings,
    get_csrf_service,
    require_identity_infrastructure,
)

router = APIRouter(prefix="/internal/security-probe", tags=["security-probe"])
gym_auth_probe_router = APIRouter(
    prefix="/gym/internal/security-probe",
    tags=["security-probe-gym-auth"],
)
_csrf = CsrfPolicy()


@router.post("/origin")
async def probe_origin(request: Request) -> JSONResponse:
    await enforce_pre_authentication_mutation_security(request)
    return JSONResponse({"ok": True})


@router.post("/pre-auth-with-session-cookie")
async def probe_pre_auth_with_session_cookie(request: Request) -> JSONResponse:
    await enforce_pre_authentication_mutation_security(request)
    return JSONResponse({"ok": True})


@router.post("/csrf/{binding_key}")
async def probe_csrf(binding_key: str, request: Request) -> JSONResponse:
    await enforce_cookie_session_mutation_security(request, csrf_binding_key=binding_key)
    return JSONResponse({"ok": True})


@router.post("/csrf-issue/{binding_key}")
async def probe_csrf_issue(binding_key: str, request: Request) -> JSONResponse:
    csrf = get_csrf_service(request)
    settings = get_app_settings(request)
    if csrf is None:
        return JSONResponse(status_code=503, content={"detail": "unavailable"})
    issued = await csrf.issue(binding_key=binding_key, now=datetime.now(tz=UTC))
    response = JSONResponse({"ok": True})
    csrf.attach_token_to_response(
        response,
        token=issued.token,
        binding_key=binding_key,
        settings=settings,
    )
    return response


@router.post("/rate-limit/{account_key}")
async def probe_rate_limit(account_key: str, request: Request) -> JSONResponse:
    await enforce_login_rate_limits(request, account_key=account_key)
    return JSONResponse({"ok": True})


@router.get("/identity-infra")
async def probe_identity_infra(
    _infra=Depends(require_identity_infrastructure),
) -> JSONResponse:
    return JSONResponse({"ok": True})


@router.post("/cookie-platform")
async def probe_cookie_platform(request: Request) -> JSONResponse:
    settings = get_app_settings(request)
    now = datetime.now(tz=UTC)
    response = JSONResponse({"ok": True})
    set_platform_session_cookie(
        response,
        token="probe-platform-token-value",
        settings=settings,
        expires_at=now.replace(year=now.year + 1),
        now=now,
    )
    return response


@router.post("/cookie-gym-clear")
async def probe_cookie_clear(request: Request) -> JSONResponse:
    settings = get_app_settings(request)
    response = JSONResponse({"ok": True})
    clear_platform_session_cookie(response, settings=settings)
    clear_gym_session_cookie(response, settings=settings)
    return response


@router.post("/cookie-session-missing-csrf")
async def probe_cookie_session_missing_csrf(request: Request) -> JSONResponse:
    await enforce_cookie_session_mutation_security(request, csrf_binding_key="")
    return JSONResponse({"ok": True})


@gym_auth_probe_router.get("/gym-permission/{permission_value}")
async def probe_gym_permission_path(
    permission_value: str,
    request: Request,
    branch_id: str | None = Query(default=None),
) -> JSONResponse:
    """Solo tests: valida permiso sin exponer CRUD operational."""
    permission = GymPermission(permission_value)
    from gym_erp_api.presentation.http_security.errors import AccessInfrastructureUnavailableError

    try:
        gym_ctx = await require_gym_tenant_context(request)
        access = require_access_infrastructure(request)
    except AccessInfrastructureUnavailableError:
        return JSONResponse(status_code=503, content={"detail": "unavailable"})
    auth = access.gym_authorization_service.trusted_context_from_resolved(gym_ctx.tenant)
    access.gym_authorization_service.require_permission(
        auth=auth,
        permission=permission,
        branch_id=branch_id,
    )
    return JSONResponse(
        {
            "ok": True,
            "tenant_id": gym_ctx.tenant.context.tenant_id,
            "permission": permission.value,
        }
    )


@gym_auth_probe_router.get("/gym-permission-dep/branches.read")
async def probe_gym_permission_dep(
    gym_ctx: GymRequestContext = Depends(require_gym_permission(GymPermission.BRANCHES_READ)),
) -> JSONResponse:
    return JSONResponse({"ok": True, "tenant_id": gym_ctx.tenant.context.tenant_id})
