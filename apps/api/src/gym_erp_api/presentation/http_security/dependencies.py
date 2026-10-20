"""Dependencias FastAPI reutilizables (auth HTTP futuro)."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import Request

from gym_erp_api.core.config import Settings, get_settings
from gym_erp_api.infrastructure.identity.identity_container import IdentityInfrastructure
from gym_erp_api.modules.identity.application.security.http_auth_contracts import (
    MutationSecurityProfile,
    OriginPolicy,
)
from gym_erp_api.presentation.http_security.client_ip import client_ip, trusted_proxy_set
from gym_erp_api.presentation.http_security.csrf import CsrfProtectionService
from gym_erp_api.presentation.http_security.errors import (
    CsrfContextRequiredError,
    HttpsRequiredError,
    IdentityInfrastructureUnavailableError,
)
from gym_erp_api.presentation.http_security.origin import validate_origin_for_mutation
from gym_erp_api.presentation.http_security.rate_limit import HttpRateLimiter
from gym_erp_api.presentation.http_security.session_cookies import request_carries_session_cookie

_origin_policy = OriginPolicy()


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


def get_app_settings(request: Request) -> Settings:
    return getattr(request.app.state, "settings", None) or get_settings()


def require_https_in_production(request: Request) -> None:
    settings = get_app_settings(request)
    if not settings.https_required:
        return
    if request.url.scheme != "https":
        peer = request.client.host if request.client else ""
        forwarded = request.headers.get("X-Forwarded-Proto", "").lower().split(",")[0].strip()
        if peer in trusted_proxy_set(settings) and forwarded == "https":
            return
        raise HttpsRequiredError()


def require_identity_infrastructure(request: Request) -> IdentityInfrastructure:
    infra = getattr(request.app.state, "identity_infrastructure", None)
    if infra is None:
        raise IdentityInfrastructureUnavailableError()
    return infra


def get_http_rate_limiter(request: Request) -> HttpRateLimiter | None:
    return getattr(request.app.state, "http_rate_limiter", None)


def get_csrf_service(request: Request) -> CsrfProtectionService | None:
    return getattr(request.app.state, "csrf_protection", None)


async def enforce_mutation_security(
    request: Request,
    *,
    profile: MutationSecurityProfile,
    csrf_binding_key: str | None = None,
) -> None:
    """Origin + CSRF según perfil explícito (sin bypass global)."""
    require_https_in_production(request)
    if request.method.upper() not in _origin_policy.require_for_methods:
        return
    settings = get_app_settings(request)
    validate_origin_for_mutation(
        settings,
        origin_header=request.headers.get("origin"),
        referer_header=request.headers.get("referer"),
    )
    has_session_cookie = request_carries_session_cookie(request)

    if profile is MutationSecurityProfile.COOKIE_SESSION:
        if not (csrf_binding_key and csrf_binding_key.strip()):
            raise CsrfContextRequiredError()
        csrf = get_csrf_service(request)
        if csrf is None:
            raise IdentityInfrastructureUnavailableError()
        await csrf.verify_request(
            request,
            binding_key=csrf_binding_key.strip(),
            now=_utc_now(),
        )
        return

    if has_session_cookie:
        raise CsrfContextRequiredError()


async def enforce_public_mutation_security(request: Request) -> None:
    await enforce_mutation_security(request, profile=MutationSecurityProfile.PUBLIC)


async def enforce_pre_authentication_mutation_security(request: Request) -> None:
    await enforce_mutation_security(request, profile=MutationSecurityProfile.PRE_AUTHENTICATION)


async def enforce_cookie_session_mutation_security(
    request: Request,
    *,
    csrf_binding_key: str,
) -> None:
    await enforce_mutation_security(
        request,
        profile=MutationSecurityProfile.COOKIE_SESSION,
        csrf_binding_key=csrf_binding_key,
    )


async def enforce_login_rate_limits(
    request: Request,
    *,
    account_key: str,
) -> None:
    limiter = get_http_rate_limiter(request)
    if limiter is None:
        if get_app_settings(request).rate_limit_fail_closed:
            raise IdentityInfrastructureUnavailableError()
        return
    settings = get_app_settings(request)
    now = _utc_now()
    ip = client_ip(request, settings)
    await limiter.enforce_login_ip(ip=ip, now=now)
    await limiter.enforce_login_account(account_key=account_key, now=now)
