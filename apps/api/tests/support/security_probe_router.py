"""Rutas de prueba para protecciones HTTP (solo tests, no producción)."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from gym_erp_api.modules.identity.application.security.http_auth_contracts import (
    CsrfPolicy,
)
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
    response.set_cookie(
        key=_csrf.cookie_name,
        value=issued.token,
        httponly=False,
        secure=not settings.allow_insecure_cookies,
        samesite="strict",
        path="/api/v1",
    )
    response.headers[_csrf.header_name] = issued.token
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
