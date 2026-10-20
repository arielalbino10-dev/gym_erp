"""Auth HTTP platform + MFA (H2-B.7.2)."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from gym_erp_api.modules.identity.application.errors import (
    AuthenticationFailedError,
    PlatformAuthContinuationError,
    PlatformMfaVerificationFailedError,
    SessionResolutionFailedError,
    SessionRevocationFailedError,
)
from gym_erp_api.modules.identity.application.security.http_auth_contracts import (
    PLATFORM_AUTH_CONTINUATION_COOKIE,
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
from gym_erp_api.presentation.auth.schemas import LoginRequest, MfaVerifyRequest, SessionResponse
from gym_erp_api.presentation.http_security.client_ip import client_ip
from gym_erp_api.presentation.http_security.cookies import (
    clear_platform_auth_continuation_cookie,
    clear_platform_session_cookie,
    set_platform_auth_continuation_cookie,
)
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

router = APIRouter(prefix="/auth", tags=["platform-auth"])


@router.post("/login")
async def platform_login(body: LoginRequest, request: Request) -> JSONResponse:
    await enforce_login_mutation_security(request, realm="platform")
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
        await infra.platform_session_eligibility.require_eligible_operator(
            user_id=principal.user_id,
        )
        bundle = await infra.create_auth_continuation.execute(principal=principal)
    except AuthenticationFailedError:
        response = JSONResponse(status_code=401, content={"detail": "Credenciales inválidas."})
        clear_platform_session_cookie(response, settings=settings)
        clear_platform_auth_continuation_cookie(response, settings=settings)
        return response
    except PlatformAuthContinuationError:
        response = JSONResponse(status_code=401, content={"detail": "Credenciales inválidas."})
        clear_platform_auth_continuation_cookie(response, settings=settings)
        return response

    response = JSONResponse(status_code=204, content=None)
    clear_platform_session_cookie(response, settings=settings)
    set_platform_auth_continuation_cookie(
        response,
        token=bundle.opaque_token,
        settings=settings,
        expires_at=bundle.expires_at,
        now=now,
    )
    return response


@router.post("/mfa/verify")
async def platform_mfa_verify(body: MfaVerifyRequest, request: Request) -> JSONResponse:
    await enforce_login_mutation_security(request, realm="platform")
    settings = get_app_settings(request)
    infra = require_infra(request)
    limiter = get_http_rate_limiter(request)
    now = utc_now()
    if limiter is None:
        raise IdentityInfrastructureUnavailableError()

    cont_token = request.cookies.get(PLATFORM_AUTH_CONTINUATION_COOKIE.name, "").strip()
    if not cont_token:
        return JSONResponse(status_code=401, content={"detail": "Credenciales inválidas."})

    ip = client_ip(request, settings)
    await limiter.enforce_mfa_verify_ip(ip=ip, now=now)
    try:
        ctx = await infra.resolve_auth_continuation.execute(opaque_token=cont_token)
    except PlatformAuthContinuationError:
        return JSONResponse(status_code=401, content={"detail": "Credenciales inválidas."})

    cont_key = ctx.continuation_id
    await limiter.enforce_mfa_continuation(continuation_key=cont_key, now=now)

    try:
        await infra.platform_session_eligibility.require_eligible_operator(user_id=ctx.user_id)
        await infra.complete_auth_continuation_mfa.execute(
            opaque_token=cont_token,
            totp_code=body.totp_code,
        )
        created = await infra.create_platform_session_from_continuation.execute(
            opaque_token=cont_token,
        )
    except AuthenticationFailedError:
        return JSONResponse(status_code=401, content={"detail": "Credenciales inválidas."})
    except (PlatformAuthContinuationError, PlatformMfaVerificationFailedError):
        return JSONResponse(status_code=401, content={"detail": "Credenciales inválidas."})

    response = JSONResponse(status_code=204, content=None)
    clear_platform_auth_continuation_cookie(response, settings=settings)
    await attach_session_cookies_and_csrf(
        response, request, created=created, settings=settings, now=now
    )
    return response


@router.get("/session")
async def platform_session(request: Request) -> JSONResponse:
    settings = get_app_settings(request)
    infra = require_infra(request)
    token = read_session_token_from_request(request, kind=SessionKind.PLATFORM)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "No autenticado."})
    try:
        resolved = await infra.resolve_session.execute(opaque_token=token, touch_activity=False)
    except SessionResolutionFailedError:
        response = JSONResponse(status_code=401, content={"detail": "No autenticado."})
        clear_platform_session_cookie(response, settings=settings)
        return response
    if resolved.session_kind is not SessionKind.PLATFORM:
        response = JSONResponse(status_code=401, content={"detail": "No autenticado."})
        clear_platform_session_cookie(response, settings=settings)
        return response
    try:
        await infra.platform_session_eligibility.require_eligible_operator(
            user_id=resolved.user_id,
        )
    except AuthenticationFailedError:
        await infra.revoke_session.execute(
            session_id=resolved.session.session_id,
            reason="operator_ineligible",
        )
        response = JSONResponse(status_code=401, content={"detail": "No autenticado."})
        clear_platform_session_cookie(response, settings=settings)
        return response
    await infra.resolve_session.execute(opaque_token=token, touch_activity=True)
    body = SessionResponse(user_id=resolved.user_id, session_kind=SessionKind.PLATFORM.value)
    response = JSONResponse(content=body.model_dump())
    csrf = get_csrf_service(request)
    if csrf is not None:
        binding = csrf_binding_for_session(
            session_kind=SessionKind.PLATFORM.value,
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
async def platform_logout(request: Request) -> JSONResponse:
    settings = get_app_settings(request)
    infra = require_infra(request)
    token = read_session_token_from_request(request, kind=SessionKind.PLATFORM)
    binding_key = ""
    resolved_ok = False
    if token:
        try:
            resolved = await infra.resolve_session.execute(
                opaque_token=token,
                touch_activity=False,
            )
            if resolved.session_kind is SessionKind.PLATFORM:
                resolved_ok = True
                binding_key = csrf_binding_for_session(
                    session_kind=SessionKind.PLATFORM.value,
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
    clear_platform_session_cookie(response, settings=settings)
    clear_platform_auth_continuation_cookie(response, settings=settings)
    csrf = get_csrf_service(request)
    plat_csrf_binding = csrf_binding_for_session(
        session_kind=SessionKind.PLATFORM.value,
        session_id="logout",
    )
    if csrf is not None:
        if binding_key:
            await csrf.revoke_binding(binding_key=binding_key)
        csrf.clear_csrf_cookie(response, binding_key=plat_csrf_binding, settings=settings)
    return response
