"""Auth HTTP gym (H2-B.7.2)."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from gym_erp_api.modules.identity.application.errors import (
    AuthenticationFailedError,
    SessionResolutionFailedError,
    SessionRevocationFailedError,
)
from gym_erp_api.modules.identity.domain.session_kind import SessionKind
from gym_erp_api.presentation.auth.account_rate_limit import login_account_rate_limit_key
from gym_erp_api.presentation.auth.http_support import (
    attach_session_cookies_and_csrf,
    read_session_token_from_request,
    require_infra,
    utc_now,
)
from gym_erp_api.presentation.auth.login_security import (
    enforce_login_mutation_security,
    enforce_logout_mutation_security,
)
from gym_erp_api.presentation.auth.schemas import LoginRequest, SessionResponse
from gym_erp_api.presentation.http_security.client_ip import client_ip
from gym_erp_api.presentation.http_security.cookies import clear_gym_session_cookie
from gym_erp_api.presentation.http_security.csrf import csrf_binding_for_session
from gym_erp_api.presentation.http_security.dependencies import (
    get_app_settings,
    get_csrf_service,
    get_http_rate_limiter,
)
from gym_erp_api.presentation.http_security.errors import (
    CsrfValidationError,
    IdentityInfrastructureUnavailableError,
)

router = APIRouter(prefix="/auth", tags=["gym-auth"])


@router.post("/login")
async def gym_login(body: LoginRequest, request: Request) -> JSONResponse:
    await enforce_login_mutation_security(request, realm="gym")
    settings = get_app_settings(request)
    infra = require_infra(request)
    limiter = get_http_rate_limiter(request)
    now = utc_now()
    if limiter is None:
        raise IdentityInfrastructureUnavailableError()
    ip = client_ip(request, settings)
    account_key = login_account_rate_limit_key(body.email)
    await limiter.enforce_login_ip(ip=ip, now=now)
    await limiter.enforce_login_account(account_key=account_key, now=now)

    try:
        principal = await infra.credential_verification.verify(
            email=body.email,
            password=body.password,
        )
        created = await infra.create_gym_session.execute(principal=principal)
    except AuthenticationFailedError:
        response = JSONResponse(status_code=401, content={"detail": "Credenciales inválidas."})
        clear_gym_session_cookie(response, settings=settings)
        return response

    response = JSONResponse(status_code=204, content=None)
    await attach_session_cookies_and_csrf(
        response, request, created=created, settings=settings, now=now
    )
    return response


@router.get("/session")
async def gym_session(request: Request) -> JSONResponse:
    settings = get_app_settings(request)
    infra = require_infra(request)
    token = read_session_token_from_request(request, kind=SessionKind.GYM)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "No autenticado."})
    try:
        resolved = await infra.resolve_session.execute(opaque_token=token, touch_activity=True)
    except Exception:
        return JSONResponse(status_code=401, content={"detail": "No autenticado."})
    if resolved.session_kind is not SessionKind.GYM:
        return JSONResponse(status_code=401, content={"detail": "No autenticado."})
    body = SessionResponse(user_id=resolved.user_id, session_kind=SessionKind.GYM.value)
    response = JSONResponse(content=body.model_dump())
    csrf = get_csrf_service(request)
    if csrf is not None:
        binding = csrf_binding_for_session(
            session_kind=SessionKind.GYM.value,
            session_id=resolved.session.session_id,
        )
        issued = await csrf.issue(binding_key=binding, now=utc_now())
        csrf.attach_token_to_response(
            response,
            token=issued.token,
            binding_key=binding,
            settings=settings,
        )
    return response


@router.post("/logout")
async def gym_logout(request: Request) -> JSONResponse:
    settings = get_app_settings(request)
    infra = require_infra(request)
    token = read_session_token_from_request(request, kind=SessionKind.GYM)
    binding_key = ""
    resolved_ok = False
    if token:
        try:
            resolved = await infra.resolve_session.execute(
                opaque_token=token,
                touch_activity=False,
            )
            if resolved.session_kind is SessionKind.GYM:
                resolved_ok = True
                binding_key = csrf_binding_for_session(
                    session_kind=SessionKind.GYM.value,
                    session_id=resolved.session.session_id,
                )
                await enforce_logout_mutation_security(
                    request,
                    csrf_binding_key=binding_key,
                )
                await infra.revoke_session.execute(
                    session_id=resolved.session.session_id,
                    reason="logout",
                )
        except CsrfValidationError:
            raise
        except SessionRevocationFailedError:
            raise
        except SessionResolutionFailedError:
            resolved_ok = False
        except Exception:
            raise
    if not resolved_ok:
        await enforce_logout_mutation_security(request, csrf_binding_key=None)

    response = JSONResponse(status_code=204, content=None)
    clear_gym_session_cookie(response, settings=settings)
    csrf = get_csrf_service(request)
    gym_csrf_binding = csrf_binding_for_session(
        session_kind=SessionKind.GYM.value,
        session_id="logout",
    )
    if csrf is not None:
        if binding_key:
            await csrf.revoke_binding(binding_key=binding_key)
        csrf.clear_csrf_cookie(response, binding_key=gym_csrf_binding, settings=settings)
    return response
