"""Integración HTTP: dependencia require_gym_permission vía probe (H2-C.4)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from gym_erp_api.modules.access.domain.enums import BranchScopeMode, GymRole
from gym_erp_api.modules.identity.application.security.http_auth_contracts import (
    GYM_CSRF_COOKIE,
    CsrfPolicy,
)
from gym_erp_api.shared_kernel.identifiers import new_uuid
from tests.integration.identity.test_gym_auth_http import (
    _PASSWORD,
    _seed_gym_user,
)
from tests.integration.identity.test_gym_tenant_auth_http import _gym_login, _stack
from tests.support.auth_http_integration import (
    csrf_headers_and_cookies,
    integration_settings_with_mfa,
    mounted_auth_http_client,
)
from tests.support.gym_access_http_seed import seed_active_membership, seed_active_tenant
from tests.support.tenant_fixtures import BRANCH_X_ID

pytestmark = [
    pytest.mark.integration,
    pytest.mark.identity_persistence,
    pytest.mark.asyncio(loop_scope="session"),
]

_CSRF = CsrfPolicy()


async def _login_select_tenant(http, *, email: str, tenant_id: str, csrf_from_login: str) -> None:
    headers, _ = csrf_headers_and_cookies(
        token=csrf_from_login,
        cookie_name=GYM_CSRF_COOKIE.name,
    )
    select = await http.post(
        "/api/v1/gym/auth/select-tenant",
        json={"tenant_id": tenant_id},
        headers=headers,
    )
    assert select.status_code == 204


async def test_probe_branches_read_owner_all_branches(
    integration_settings,
    auth_http_repos,
):
    settings = integration_settings_with_mfa(integration_settings)
    moment = datetime(2026, 11, 10, tzinfo=UTC)
    email = "http.gym.perm.owner@example.test"
    identity = await _seed_gym_user(
        mongo_identity_repository=auth_http_repos["identity"],
        mongo_credential_repository=auth_http_repos["credential"],
        email=email,
        password=_PASSWORD,
        moment=moment,
    )
    tenant_id = new_uuid()
    await seed_active_tenant(
        auth_http_repos["tenants"],
        tenant_id=tenant_id,
        display_name="PermGym",
        moment=moment,
    )
    await seed_active_membership(
        auth_http_repos["memberships"],
        user_id=identity.user_id,
        tenant_id=tenant_id,
        moment=moment,
        gym_roles=frozenset({GymRole.GYM_OWNER}),
    )
    databases, infra, _, http_sec, access = _stack(settings, auth_http_repos)
    async with mounted_auth_http_client(
        settings=settings,
        identity_infrastructure=infra,
        databases=databases,
        http_security=http_sec,
        access_infrastructure=access,
        include_security_probe=True,
    ) as http:
        csrf = await _gym_login(http, email=email)
        await _login_select_tenant(http, email=email, tenant_id=tenant_id, csrf_from_login=csrf)
        probe = await http.get(
            "/api/v1/gym/internal/security-probe/gym-permission/branches.read",
        )
        assert probe.status_code == 200
        assert probe.json()["tenant_id"] == tenant_id


async def test_probe_branch_admin_needs_branch_id(
    integration_settings,
    auth_http_repos,
):
    settings = integration_settings_with_mfa(integration_settings)
    moment = datetime(2026, 11, 11, tzinfo=UTC)
    email = "http.gym.perm.branch@example.test"
    identity = await _seed_gym_user(
        mongo_identity_repository=auth_http_repos["identity"],
        mongo_credential_repository=auth_http_repos["credential"],
        email=email,
        password=_PASSWORD,
        moment=moment,
    )
    tenant_id = new_uuid()
    await seed_active_tenant(
        auth_http_repos["tenants"],
        tenant_id=tenant_id,
        display_name="BranchGym",
        moment=moment,
    )
    await seed_active_membership(
        auth_http_repos["memberships"],
        user_id=identity.user_id,
        tenant_id=tenant_id,
        moment=moment,
        gym_roles=frozenset({GymRole.BRANCH_ADMIN}),
        branch_scope_mode=BranchScopeMode.EXPLICIT_BRANCHES,
        allowed_branch_ids=frozenset({BRANCH_X_ID}),
    )

    databases, infra, _, http_sec, access = _stack(settings, auth_http_repos)
    async with mounted_auth_http_client(
        settings=settings,
        identity_infrastructure=infra,
        databases=databases,
        http_security=http_sec,
        access_infrastructure=access,
        include_security_probe=True,
    ) as http:
        csrf = await _gym_login(http, email=email)
        await _login_select_tenant(http, email=email, tenant_id=tenant_id, csrf_from_login=csrf)
        denied = await http.get(
            "/api/v1/gym/internal/security-probe/gym-permission/branches.read",
        )
        assert denied.status_code == 403
        allowed = await http.get(
            "/api/v1/gym/internal/security-probe/gym-permission/branches.read",
            params={"branch_id": BRANCH_X_ID},
        )
        assert allowed.status_code == 200


async def test_probe_branch_admin_denied_create(
    integration_settings,
    auth_http_repos,
):
    settings = integration_settings_with_mfa(integration_settings)
    moment = datetime(2026, 11, 12, tzinfo=UTC)
    email = "http.gym.perm.nocreate@example.test"
    identity = await _seed_gym_user(
        mongo_identity_repository=auth_http_repos["identity"],
        mongo_credential_repository=auth_http_repos["credential"],
        email=email,
        password=_PASSWORD,
        moment=moment,
    )
    tenant_id = new_uuid()
    await seed_active_tenant(
        auth_http_repos["tenants"],
        tenant_id=tenant_id,
        display_name="NoCreate",
        moment=moment,
    )
    await seed_active_membership(
        auth_http_repos["memberships"],
        user_id=identity.user_id,
        tenant_id=tenant_id,
        moment=moment,
        gym_roles=frozenset({GymRole.BRANCH_ADMIN}),
        branch_scope_mode=BranchScopeMode.EXPLICIT_BRANCHES,
        allowed_branch_ids=frozenset({BRANCH_X_ID}),
    )
    databases, infra, _, http_sec, access = _stack(settings, auth_http_repos)
    async with mounted_auth_http_client(
        settings=settings,
        identity_infrastructure=infra,
        databases=databases,
        http_security=http_sec,
        access_infrastructure=access,
        include_security_probe=True,
    ) as http:
        csrf = await _gym_login(http, email=email)
        await _login_select_tenant(http, email=email, tenant_id=tenant_id, csrf_from_login=csrf)
        response = await http.get(
            "/api/v1/gym/internal/security-probe/gym-permission/branches.create",
            params={"branch_id": BRANCH_X_ID},
        )
        assert response.status_code == 403
