"""Pruebas unitarias H2-C.3: membresías, selección y contexto gym."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from gym_erp_api.infrastructure.access.access_container import AccessInfrastructure
from gym_erp_api.main import create_app
from gym_erp_api.modules.access.application.errors import MembershipAccessDeniedError
from gym_erp_api.modules.access.application.services.tenant_context_factory import (
    ResolvedTenantContext,
)
from gym_erp_api.modules.access.application.use_cases.list_gym_memberships import (
    GymMembershipSummary,
)
from gym_erp_api.modules.identity.application.dto.auth_results import ResolvedSession
from gym_erp_api.modules.identity.application.errors import SessionResolutionFailedError
from gym_erp_api.modules.identity.application.security.http_auth_contracts import (
    GYM_SESSION_COOKIE,
)
from gym_erp_api.modules.identity.domain.auth_session import AuthSession
from gym_erp_api.modules.identity.domain.session_kind import SessionKind
from gym_erp_api.presentation.http_security.csrf import CsrfProtectionService
from gym_erp_api.presentation.http_security.rate_limit import HttpRateLimiter
from gym_erp_api.shared_kernel.tenant_context import TenantContext
from tests.support.in_memory_csrf_token_repository import InMemoryCsrfTokenRepository
from tests.support.in_memory_rate_limit_repository import InMemoryRateLimitRepository

_MOMENT = datetime(2026, 11, 1, tzinfo=UTC)
_USER = "00000000-0000-4000-8000-000000000001"
_TENANT = "550e8400-e29b-41d4-a716-446655440001"


def _resolved(*, active_tenant_id: str | None = None, epoch: int | None = None) -> ResolvedSession:
    session = AuthSession.create(
        user_id=_USER,
        session_kind=SessionKind.GYM,
        token_hash="a" * 64,
        expires_at=_MOMENT.replace(year=_MOMENT.year + 1),
        idle_expires_at=_MOMENT.replace(year=_MOMENT.year + 1),
        credential_version=0,
        now=_MOMENT,
    )
    if active_tenant_id is not None:
        session = session.with_gym_tenant_selection(
            active_tenant_id=active_tenant_id,
            membership_authz_epoch=epoch if epoch is not None else 0,
        )
    return ResolvedSession(
        user_id=_USER,
        session_kind=SessionKind.GYM,
        session=session,
        credential_version=0,
        active_tenant_id=session.active_tenant_id,
        gym_membership_authz_epoch=session.gym_membership_authz_epoch,
    )


def _access_app(*, infra: MagicMock, access: AccessInfrastructure | None):
    from gym_erp_api.core.config import Settings

    settings = Settings(app_env="test", mongodb_uri=None, allow_insecure_cookies=True)
    app = create_app(settings=settings)
    rate_repo = InMemoryRateLimitRepository()
    csrf_repo = InMemoryCsrfTokenRepository()
    app.state.http_rate_limiter = HttpRateLimiter(repository=rate_repo, settings=settings)
    app.state.csrf_protection = CsrfProtectionService(repository=csrf_repo)
    app.state.identity_infrastructure = infra
    app.state.access_infrastructure = access
    return app


@pytest.mark.asyncio
async def test_gym_memberships_requires_session():
    infra = MagicMock()
    access = MagicMock(spec=AccessInfrastructure)
    app = _access_app(infra=infra, access=access)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/gym/auth/memberships")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_gym_memberships_without_access_infra_503():
    infra = MagicMock()
    infra.resolve_session = MagicMock()
    infra.resolve_session.execute = AsyncMock(return_value=_resolved())
    app = _access_app(infra=infra, access=None)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/v1/gym/auth/memberships",
            cookies={GYM_SESSION_COOKIE.name: "opaque-token-value"},
        )
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_gym_memberships_lists_active_only():
    infra = MagicMock()
    infra.resolve_session = MagicMock()
    infra.resolve_session.execute = AsyncMock(return_value=_resolved())
    access = MagicMock(spec=AccessInfrastructure)
    access.list_gym_memberships = MagicMock()
    access.list_gym_memberships.execute = AsyncMock(
        return_value=[
            GymMembershipSummary(
                tenant_id=_TENANT,
                membership_id="880e8400-e29b-41d4-a716-446655440020",
                display_name="MedeGym",
                gym_roles=frozenset({"gym_owner"}),
            )
        ]
    )
    app = _access_app(infra=infra, access=access)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/v1/gym/auth/memberships",
            cookies={GYM_SESSION_COOKIE.name: "opaque-token-value"},
        )
    assert response.status_code == 200
    assert response.json()["memberships"][0]["display_name"] == "MedeGym"


@pytest.mark.asyncio
async def test_gym_select_tenant_denied_maps_403():
    infra = MagicMock()
    infra.resolve_session = MagicMock()
    infra.resolve_session.execute = AsyncMock(return_value=_resolved())
    access = MagicMock(spec=AccessInfrastructure)
    access.select_gym_active_tenant = MagicMock()
    access.select_gym_active_tenant.execute = AsyncMock(
        side_effect=MembershipAccessDeniedError("x")
    )
    app = _access_app(infra=infra, access=access)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/gym/auth/select-tenant",
            json={"tenant_id": _TENANT},
            cookies={GYM_SESSION_COOKIE.name: "opaque-token-value"},
            headers={"Origin": "http://127.0.0.1:5173"},
        )
    assert response.status_code in {403, 401}


@pytest.mark.asyncio
async def test_require_gym_tenant_context_epoch_mismatch():
    from gym_erp_api.presentation.auth.gym_context import require_gym_tenant_context

    infra = MagicMock()
    resolved = _resolved(active_tenant_id=_TENANT, epoch=1)
    infra.resolve_session = MagicMock()
    infra.resolve_session.execute = AsyncMock(return_value=resolved)
    access = MagicMock(spec=AccessInfrastructure)
    ctx = ResolvedTenantContext(
        context=TenantContext(
            tenant_id=_TENANT,
            user_id=_USER,
            membership_id="880e8400-e29b-41d4-a716-446655440020",
            allowed_branch_ids=None,
        ),
        authz_epoch=2,
        gym_roles=frozenset({"gym_owner"}),
    )
    access.tenant_context_factory = MagicMock()
    access.tenant_context_factory.build_for_gym = AsyncMock(return_value=ctx)

    request = MagicMock()
    request.app.state.access_infrastructure = access
    request.app.state.identity_infrastructure = infra
    request.cookies = {GYM_SESSION_COOKIE.name: "token"}

    from gym_erp_api.presentation.http_security.errors import GymAccessDeniedError

    with pytest.raises(GymAccessDeniedError):
        await require_gym_tenant_context(request)


@pytest.mark.asyncio
async def test_gym_session_invalid_token_401():
    infra = MagicMock()
    infra.resolve_session = MagicMock()
    infra.resolve_session.execute = AsyncMock(side_effect=SessionResolutionFailedError("x"))
    access = MagicMock(spec=AccessInfrastructure)
    app = _access_app(infra=infra, access=access)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/v1/gym/auth/session",
            cookies={GYM_SESSION_COOKIE.name: "bad"},
        )
    assert response.status_code == 401
