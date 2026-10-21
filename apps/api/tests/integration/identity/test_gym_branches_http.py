"""HTTP gym: crear y consultar sucursales operational (H3-B.1)."""

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
    AUTH_HTTP_ORIGIN,
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


async def _select_tenant(http, *, tenant_id: str, csrf_token: str) -> str:
    headers, _ = csrf_headers_and_cookies(
        token=csrf_token,
        cookie_name=GYM_CSRF_COOKIE.name,
    )
    select = await http.post(
        "/api/v1/gym/auth/select-tenant",
        json={"tenant_id": tenant_id},
        headers=headers,
    )
    assert select.status_code == 204
    return select.headers.get(_CSRF.header_name) or csrf_token


async def test_gym_branch_create_list_get_flow(
    integration_settings,
    auth_http_repos,
):
    settings = integration_settings_with_mfa(integration_settings)
    moment = datetime(2026, 12, 1, tzinfo=UTC)
    email = "http.gym.branch.flow@example.test"
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
        display_name="BranchFlowGym",
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
    ) as http:
        csrf = await _gym_login(http, email=email)
        csrf = await _select_tenant(http, tenant_id=tenant_id, csrf_token=csrf)
        headers, _ = csrf_headers_and_cookies(
            token=csrf,
            cookie_name=GYM_CSRF_COOKIE.name,
        )
        create = await http.post(
            "/api/v1/gym/branches/",
            json={"name": "Sucursal Centro"},
            headers=headers,
        )
        assert create.status_code == 201
        branch_id = create.json()["branch_id"]
        assert create.json()["name"] == "Sucursal Centro"

        listed = await http.get("/api/v1/gym/branches/")
        assert listed.status_code == 200
        ids = {row["branch_id"] for row in listed.json()["branches"]}
        assert branch_id in ids

        one = await http.get(f"/api/v1/gym/branches/{branch_id}")
        assert one.status_code == 200
        assert one.json()["branch_id"] == branch_id


async def test_gym_branch_create_requires_csrf(
    integration_settings,
    auth_http_repos,
):
    settings = integration_settings_with_mfa(integration_settings)
    moment = datetime(2026, 12, 2, tzinfo=UTC)
    email = "http.gym.branch.csrf@example.test"
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
        display_name="CsrfGym",
        moment=moment,
    )
    await seed_active_membership(
        auth_http_repos["memberships"],
        user_id=identity.user_id,
        tenant_id=tenant_id,
        moment=moment,
    )
    databases, infra, _, http_sec, access = _stack(settings, auth_http_repos)
    async with mounted_auth_http_client(
        settings=settings,
        identity_infrastructure=infra,
        databases=databases,
        http_security=http_sec,
        access_infrastructure=access,
    ) as http:
        csrf = await _gym_login(http, email=email)
        csrf = await _select_tenant(http, tenant_id=tenant_id, csrf_token=csrf)
        response = await http.post(
            "/api/v1/gym/branches/",
            json={"name": "Sin CSRF"},
            headers={"Origin": AUTH_HTTP_ORIGIN},
        )
        assert response.status_code == 403


async def test_gym_branch_admin_cannot_create(
    integration_settings,
    auth_http_repos,
):
    settings = integration_settings_with_mfa(integration_settings)
    moment = datetime(2026, 12, 3, tzinfo=UTC)
    email = "http.gym.branch.admin@example.test"
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
        display_name="AdminGym",
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
    ) as http:
        csrf = await _gym_login(http, email=email)
        csrf = await _select_tenant(http, tenant_id=tenant_id, csrf_token=csrf)
        headers, _ = csrf_headers_and_cookies(
            token=csrf,
            cookie_name=GYM_CSRF_COOKIE.name,
        )
        response = await http.post(
            "/api/v1/gym/branches/",
            json={"name": "No permitido"},
            headers=headers,
        )
        assert response.status_code == 403


async def test_gym_branch_get_cross_tenant_returns_404(
    integration_settings,
    auth_http_repos,
):
    settings = integration_settings_with_mfa(integration_settings)
    moment = datetime(2026, 12, 4, tzinfo=UTC)
    email = "http.gym.branch.xtenant@example.test"
    identity = await _seed_gym_user(
        mongo_identity_repository=auth_http_repos["identity"],
        mongo_credential_repository=auth_http_repos["credential"],
        email=email,
        password=_PASSWORD,
        moment=moment,
    )
    tenant_a = new_uuid()
    tenant_b = new_uuid()
    await seed_active_tenant(
        auth_http_repos["tenants"],
        tenant_id=tenant_a,
        display_name="TenantA",
        moment=moment,
    )
    await seed_active_tenant(
        auth_http_repos["tenants"],
        tenant_id=tenant_b,
        display_name="TenantB",
        moment=moment,
    )
    await seed_active_membership(
        auth_http_repos["memberships"],
        user_id=identity.user_id,
        tenant_id=tenant_a,
        moment=moment,
    )
    other_branch_id = new_uuid()
    from gym_erp_api.modules.organization.domain.branch import Branch
    from gym_erp_api.modules.organization.infrastructure.mongo.branch_document_mapper import (
        branch_to_document,
    )

    await auth_http_repos["operational_branches"].insert_one(
        branch_to_document(
            Branch.create(
                tenant_id=tenant_b,
                name="Ajena",
                branch_id=other_branch_id,
                now=moment,
            )
        )
    )
    databases, infra, _, http_sec, access = _stack(settings, auth_http_repos)
    async with mounted_auth_http_client(
        settings=settings,
        identity_infrastructure=infra,
        databases=databases,
        http_security=http_sec,
        access_infrastructure=access,
    ) as http:
        csrf = await _gym_login(http, email=email)
        csrf = await _select_tenant(http, tenant_id=tenant_a, csrf_token=csrf)
        response = await http.get(f"/api/v1/gym/branches/{other_branch_id}")
        assert response.status_code == 404
