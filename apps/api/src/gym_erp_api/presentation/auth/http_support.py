"""Utilidades compartidas HTTP auth."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import Request
from starlette.responses import Response

from gym_erp_api.core.config import Settings
from gym_erp_api.infrastructure.identity.identity_container import IdentityInfrastructure
from gym_erp_api.modules.identity.application.dto.auth_results import CreatedSession
from gym_erp_api.modules.identity.application.security.http_auth_contracts import (
    GYM_SESSION_COOKIE,
    PLATFORM_SESSION_COOKIE,
)
from gym_erp_api.modules.identity.domain.session_kind import SessionKind
from gym_erp_api.presentation.http_security.cookies import (
    set_gym_session_cookie,
    set_platform_session_cookie,
)
from gym_erp_api.presentation.http_security.csrf import (
    csrf_binding_for_session,
)
from gym_erp_api.presentation.http_security.dependencies import get_csrf_service


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


async def attach_session_cookies_and_csrf(
    response: Response,
    request: Request,
    *,
    created: CreatedSession,
    settings: Settings,
    now: datetime,
) -> None:
    kind = created.session.session_kind
    if kind is SessionKind.GYM:
        set_gym_session_cookie(
            response,
            token=created.opaque_token,
            settings=settings,
            expires_at=created.session.expires_at,
            now=now,
        )
    elif kind is SessionKind.PLATFORM:
        set_platform_session_cookie(
            response,
            token=created.opaque_token,
            settings=settings,
            expires_at=created.session.expires_at,
            now=now,
        )
    csrf = get_csrf_service(request)
    if csrf is None:
        return
    binding = csrf_binding_for_session(
        session_kind=kind.value,
        session_id=created.session.session_id,
    )
    issued = await csrf.issue(binding_key=binding, now=now)
    csrf.attach_token_to_response(
        response,
        token=issued.token,
        binding_key=binding,
        settings=settings,
    )


def read_session_token_from_request(request: Request, *, kind: SessionKind) -> str | None:
    if kind is SessionKind.GYM:
        name = GYM_SESSION_COOKIE.name
    else:
        name = PLATFORM_SESSION_COOKIE.name
    value = request.cookies.get(name, "").strip()
    return value or None


def require_infra(request: Request) -> IdentityInfrastructure:
    from gym_erp_api.presentation.http_security.dependencies import require_identity_infrastructure

    return require_identity_infrastructure(request)
