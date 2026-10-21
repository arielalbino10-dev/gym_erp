"""Pruebas HTTP unitarias — RBAC administración platform (H3-A.3-A.1)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from gym_erp_api.core.config import Settings
from gym_erp_api.infrastructure.platform_admin.platform_admin_container import (
    PlatformAdminInfrastructure,
)
from gym_erp_api.main import create_app
from gym_erp_api.modules.identity.application.dto.auth_results import ResolvedSession
from gym_erp_api.modules.identity.application.errors import SessionResolutionFailedError
from gym_erp_api.modules.identity.application.security.http_auth_contracts import (
    GYM_SESSION_COOKIE,
    PLATFORM_SESSION_COOKIE,
)
from gym_erp_api.modules.identity.domain.auth_session import AuthSession
from gym_erp_api.modules.identity.domain.session_kind import SessionKind
from gym_erp_api.modules.platform_admin.application.services.platform_authorization_service import (
    PlatformAuthorizationService,
)
from gym_erp_api.modules.platform_admin.application.use_cases.apply_platform_role_assignment import (  # noqa: E501
    ApplyPlatformRoleAssignmentUseCase,
)
from gym_erp_api.modules.platform_admin.application.use_cases.record_platform_audit_event import (
    RecordPlatformAuditEventUseCase,
)
from gym_erp_api.modules.platform_admin.domain.platform_permission import PlatformPermission
from gym_erp_api.modules.platform_admin.domain.platform_role import PlatformRole
from gym_erp_api.modules.platform_admin.domain.platform_role_assignment import (
    PlatformRoleAssignment,
)
from gym_erp_api.presentation.http_security.csrf import CsrfProtectionService
from gym_erp_api.presentation.http_security.rate_limit import HttpRateLimiter
from tests.support.in_memory_csrf_token_repository import InMemoryCsrfTokenRepository
from tests.support.in_memory_platform_audit_repository import InMemoryPlatformAuditRepository
from tests.support.in_memory_platform_role_assignment_repository import (
    InMemoryPlatformRoleAssignmentRepository,
)
from tests.support.in_memory_rate_limit_repository import InMemoryRateLimitRepository

_MOMENT = datetime(2026, 11, 1, tzinfo=UTC)
_USER = "00000000-0000-4000-8000-000000000001"
_ACCESS = "/api/v1/platform/admin/access"
_HEALTH = "/api/v1/platform/admin/system/health-summary"


def _session_resolved(*, kind: SessionKind) -> ResolvedSession:
    session = AuthSession.create(
        user_id=_USER,
        session_kind=kind,
        token_hash="a" * 64,
        expires_at=_MOMENT.replace(year=_MOMENT.year + 1),
        idle_expires_at=_MOMENT.replace(year=_MOMENT.year + 1),
        credential_version=0,
        now=_MOMENT,
    )
    return ResolvedSession(
        user_id=_USER,
        session_kind=kind,
        session=session,
        credential_version=0,
        active_tenant_id=None,
        gym_membership_authz_epoch=None,
    )


def _platform_admin_infra(
    repo: InMemoryPlatformRoleAssignmentRepository,
) -> PlatformAdminInfrastructure:
    audit_repo = InMemoryPlatformAuditRepository()
    authz = PlatformAuthorizationService(assignments=repo)
    record_audit = RecordPlatformAuditEventUseCase(audit=audit_repo)
    apply_assignment = ApplyPlatformRoleAssignmentUseCase(
        assignments=repo,
        authorization=authz,
        audit=record_audit,
    )
    return PlatformAdminInfrastructure(
        platform_authorization_service=authz,
        platform_role_assignment_repository=repo,  # type: ignore[arg-type]
        record_platform_audit_event=record_audit,
        apply_platform_role_assignment=apply_assignment,
    )


def _platform_app(
    *,
    infra: MagicMock,
    admin: PlatformAdminInfrastructure | None,
    repo: InMemoryPlatformRoleAssignmentRepository | None = None,
):
    settings = Settings(app_env="test", mongodb_uri=None, allow_insecure_cookies=True)
    app = create_app(settings=settings)
    rate_repo = InMemoryRateLimitRepository()
    csrf_repo = InMemoryCsrfTokenRepository()
    app.state.http_rate_limiter = HttpRateLimiter(repository=rate_repo, settings=settings)
    app.state.csrf_protection = CsrfProtectionService(repository=csrf_repo)
    app.state.identity_infrastructure = infra
    app.state.platform_admin_infrastructure = admin
    return app, repo


@pytest.mark.asyncio
async def test_platform_admin_access_without_session_returns_401():
    infra = MagicMock()
    repo = InMemoryPlatformRoleAssignmentRepository()
    app, _ = _platform_app(infra=infra, admin=_platform_admin_infra(repo))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(_ACCESS)
    assert response.status_code == 401
    assert response.json()["detail"] == "No autenticado."


@pytest.mark.asyncio
async def test_gym_session_does_not_grant_platform_admin_access():
    infra = MagicMock()
    infra.resolve_session = MagicMock()
    infra.resolve_session.execute = AsyncMock(
        return_value=_session_resolved(kind=SessionKind.GYM),
    )
    infra.platform_session_eligibility = MagicMock()
    repo = InMemoryPlatformRoleAssignmentRepository()
    app, _ = _platform_app(infra=infra, admin=_platform_admin_infra(repo))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            _ACCESS,
            cookies={PLATFORM_SESSION_COOKIE.name: "gym-opaque-token"},
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_gym_cookie_alone_does_not_authenticate_platform_routes():
    infra = MagicMock()
    infra.resolve_session = MagicMock()
    infra.resolve_session.execute = AsyncMock(
        return_value=_session_resolved(kind=SessionKind.GYM),
    )
    repo = InMemoryPlatformRoleAssignmentRepository()
    app, _ = _platform_app(infra=infra, admin=_platform_admin_infra(repo))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            _ACCESS,
            cookies={GYM_SESSION_COOKIE.name: "gym-only-cookie"},
        )
    assert response.status_code == 401
    infra.resolve_session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_platform_session_without_permission_gets_403_on_health_summary():
    infra = MagicMock()
    infra.resolve_session = MagicMock()
    infra.resolve_session.execute = AsyncMock(
        return_value=_session_resolved(kind=SessionKind.PLATFORM),
    )
    infra.platform_session_eligibility = MagicMock()
    infra.platform_session_eligibility.require_eligible_operator = AsyncMock()
    repo = InMemoryPlatformRoleAssignmentRepository()
    app, _ = _platform_app(infra=infra, admin=_platform_admin_infra(repo))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            _HEALTH,
            cookies={PLATFORM_SESSION_COOKIE.name: "platform-opaque-token"},
        )
    assert response.status_code == 403
    body = response.text.lower()
    assert "password" not in body
    assert "token" not in body


@pytest.mark.asyncio
async def test_platform_session_with_system_read_permission_gets_health_summary():
    infra = MagicMock()
    infra.resolve_session = MagicMock()
    infra.resolve_session.execute = AsyncMock(
        return_value=_session_resolved(kind=SessionKind.PLATFORM),
    )
    infra.platform_session_eligibility = MagicMock()
    infra.platform_session_eligibility.require_eligible_operator = AsyncMock()
    repo = InMemoryPlatformRoleAssignmentRepository()
    await repo.upsert(
        assignment=PlatformRoleAssignment(
            user_id=_USER,
            roles=frozenset({PlatformRole.PLATFORM_ADMIN}),
            granted_permissions=frozenset({PlatformPermission.PLATFORM_SYSTEM_READ}),
        ),
    )
    app, _ = _platform_app(infra=infra, admin=_platform_admin_infra(repo))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            _HEALTH,
            cookies={PLATFORM_SESSION_COOKIE.name: "platform-opaque-token"},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["maturity"] == "provisional_stub"
    assert "metrics" not in payload


@pytest.mark.asyncio
async def test_platform_access_summary_lists_effective_permissions():
    infra = MagicMock()
    infra.resolve_session = MagicMock()
    infra.resolve_session.execute = AsyncMock(
        return_value=_session_resolved(kind=SessionKind.PLATFORM),
    )
    infra.platform_session_eligibility = MagicMock()
    infra.platform_session_eligibility.require_eligible_operator = AsyncMock()
    repo = InMemoryPlatformRoleAssignmentRepository()
    await repo.upsert(
        assignment=PlatformRoleAssignment(
            user_id=_USER,
            roles=frozenset({PlatformRole.PLATFORM_ADMIN}),
            granted_permissions=frozenset({PlatformPermission.PLATFORM_OPERATORS_READ}),
        ),
    )
    app, _ = _platform_app(infra=infra, admin=_platform_admin_infra(repo))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            _ACCESS,
            cookies={PLATFORM_SESSION_COOKIE.name: "platform-opaque-token"},
        )
    assert response.status_code == 200
    assert response.json()["permissions"] == ["platform.operators.read"]


@pytest.mark.asyncio
async def test_revoked_platform_permission_denied_on_next_request():
    infra = MagicMock()
    infra.resolve_session = MagicMock()
    infra.resolve_session.execute = AsyncMock(
        return_value=_session_resolved(kind=SessionKind.PLATFORM),
    )
    infra.platform_session_eligibility = MagicMock()
    infra.platform_session_eligibility.require_eligible_operator = AsyncMock()
    repo = InMemoryPlatformRoleAssignmentRepository()
    await repo.upsert(
        assignment=PlatformRoleAssignment(
            user_id=_USER,
            roles=frozenset({PlatformRole.PLATFORM_ADMIN}),
            granted_permissions=frozenset({PlatformPermission.PLATFORM_SYSTEM_READ}),
        ),
    )
    app, _ = _platform_app(infra=infra, admin=_platform_admin_infra(repo))
    cookies = {PLATFORM_SESSION_COOKIE.name: "platform-opaque-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        ok = await client.get(_HEALTH, cookies=cookies)
        assert ok.status_code == 200
        await repo.upsert(
            assignment=PlatformRoleAssignment(
                user_id=_USER,
                roles=frozenset({PlatformRole.PLATFORM_ADMIN}),
                granted_permissions=frozenset(),
            ),
        )
        denied = await client.get(_HEALTH, cookies=cookies)
    assert denied.status_code == 403


@pytest.mark.asyncio
async def test_gym_owner_role_assignment_does_not_imply_platform_access():
    infra = MagicMock()
    infra.resolve_session = MagicMock()
    infra.resolve_session.execute = AsyncMock(
        return_value=_session_resolved(kind=SessionKind.PLATFORM),
    )
    infra.platform_session_eligibility = MagicMock()
    infra.platform_session_eligibility.require_eligible_operator = AsyncMock()
    repo = InMemoryPlatformRoleAssignmentRepository()
    app, _ = _platform_app(infra=infra, admin=_platform_admin_infra(repo))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        access = await client.get(
            _ACCESS,
            cookies={PLATFORM_SESSION_COOKIE.name: "platform-opaque-token"},
        )
        health = await client.get(
            _HEALTH,
            cookies={PLATFORM_SESSION_COOKIE.name: "platform-opaque-token"},
        )
    assert access.status_code == 200
    assert access.json()["permissions"] == []
    assert health.status_code == 403


@pytest.mark.asyncio
async def test_invalid_platform_session_returns_401_without_leaking_internals():
    infra = MagicMock()
    infra.resolve_session = MagicMock()
    infra.resolve_session.execute = AsyncMock(
        side_effect=SessionResolutionFailedError("detalle interno no debe filtrarse"),
    )
    infra.platform_session_eligibility = MagicMock()
    repo = InMemoryPlatformRoleAssignmentRepository()
    app, _ = _platform_app(infra=infra, admin=_platform_admin_infra(repo))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            _ACCESS,
            cookies={PLATFORM_SESSION_COOKIE.name: "bad-token"},
        )
    assert response.status_code == 401
    assert "detalle interno" not in response.text
