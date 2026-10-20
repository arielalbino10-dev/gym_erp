"""Origin/CSRF en login y logout (cookies de sesión obsoletas vs activas)."""

from __future__ import annotations

from typing import Literal

from fastapi import Request

from gym_erp_api.infrastructure.identity.identity_container import IdentityInfrastructure
from gym_erp_api.modules.identity.application.security.http_auth_contracts import OriginPolicy
from gym_erp_api.modules.identity.domain.session_kind import SessionKind
from gym_erp_api.presentation.auth.http_support import read_session_token_from_request
from gym_erp_api.presentation.http_security.dependencies import (
    enforce_cookie_session_mutation_security,
    get_app_settings,
    require_https_in_production,
    require_identity_infrastructure,
)
from gym_erp_api.presentation.http_security.errors import CsrfContextRequiredError
from gym_erp_api.presentation.http_security.origin import validate_origin_for_mutation

_origin_policy = OriginPolicy()


def _validate_mutation_origin(request: Request) -> None:
    require_https_in_production(request)
    if request.method.upper() not in _origin_policy.require_for_methods:
        return
    settings = get_app_settings(request)
    validate_origin_for_mutation(
        settings,
        origin_header=request.headers.get("origin"),
        referer_header=request.headers.get("referer"),
    )


async def _has_live_session(
    request: Request,
    *,
    infra: IdentityInfrastructure,
    kind: SessionKind,
) -> bool:
    token = read_session_token_from_request(request, kind=kind)
    if not token:
        return False
    try:
        resolved = await infra.resolve_session.execute(opaque_token=token, touch_activity=False)
    except Exception:
        return False
    return resolved.session_kind is kind


async def enforce_login_mutation_security(
    request: Request,
    *,
    realm: Literal["gym", "platform"],
) -> None:
    """Origin; exige CSRF solo si la cookie de sesión del realm sigue siendo válida."""
    _validate_mutation_origin(request)
    kind = SessionKind.GYM if realm == "gym" else SessionKind.PLATFORM
    infra = require_identity_infrastructure(request)
    if await _has_live_session(request, infra=infra, kind=kind):
        raise CsrfContextRequiredError()


async def enforce_logout_mutation_security(
    request: Request,
    *,
    csrf_binding_key: str | None,
) -> None:
    """Origin; CSRF solo cuando hay sesión viva revocable (binding conocido)."""
    _validate_mutation_origin(request)
    if csrf_binding_key and csrf_binding_key.strip():
        await enforce_cookie_session_mutation_security(
            request,
            csrf_binding_key=csrf_binding_key.strip(),
        )
