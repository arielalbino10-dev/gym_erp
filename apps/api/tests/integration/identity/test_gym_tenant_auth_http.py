"""Flujo HTTP gym: membresías, selección de tenant y sesión (H2-C.3)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from gym_erp_api.modules.identity.application.security.http_auth_contracts import (
    GYM_CSRF_COOKIE,
    GYM_SESSION_COOKIE,
    CsrfPolicy,
)
from gym_erp_api.modules.organization.domain.enums import TenantStatus
from gym_erp_api.shared_kernel.identifiers import new_uuid
from tests.integration.identity.test_gym_auth_http import (
    _PASSWORD,
    _seed_gym_user,
)
from tests.support.auth_http_integration import (
    AUTH_HTTP_ORIGIN,
    build_auth_http_identity_stack,
    csrf_headers_and_cookies,
    integration_settings_with_mfa,
    mounted_auth_http_client,
)
from tests.support.gym_access_http_seed import seed_active_membership, seed_active_tenant

pytestmark = [
    pytest.mark.integration,
    pytest.mark.identity_persistence,
    pytest.mark.asyncio(loop_scope="session"),
]

_CSRF = CsrfPolicy()
MEDE_GYM = "MedeGym"
AARON_GYM = "AaronGym"


def _stack(settings, auth_http_repos):
    return build_auth_http_identity_stack(
        settings=settings,
        mongo_identity_repository=auth_http_repos["identity"],
        mongo_credential_repository=auth_http_repos["credential"],
        mongo_auth_session_repository=auth_http_repos["session"],
        mongo_platform_totp_enrollment_repository=auth_http_repos["totp"],
        mongo_platform_mfa_challenge_repository=auth_http_repos["challenge"],
        mongo_platform_mfa_step_repository=auth_http_repos["step"],
        mongo_platform_mfa_session_authorization_repository=auth_http_repos["authz"],
        access_memberships_collection=auth_http_repos["memberships"],
        access_tenants_collection=auth_http_repos["tenants"],
    )


async def _gym_login(http, *, email: str) -> str:
    login = await http.post(
        "/api/v1/gym/auth/login",
        json={"email": email, "password": _PASSWORD},
        headers={"Origin": AUTH_HTTP_ORIGIN},
    )
    assert login.status_code == 204
    assert GYM_SESSION_COOKIE.name in login.headers.get("set-cookie", "")
    session_resp = await http.get("/api/v1/gym/auth/session")
    assert session_resp.status_code == 200
    csrf_token = session_resp.headers.get(_CSRF.header_name)
    assert csrf_token
    return csrf_token


async def test_gym_login_memberships_select_tenant_session_flow(
    integration_settings,
    auth_http_repos,
):
    settings = integration_settings_with_mfa(integration_settings)
    moment = datetime(2026, 10, 1, tzinfo=UTC)
    email = "http.gym.tenant.flow@example.test"
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
        display_name=MEDE_GYM,
        moment=moment,
    )
    membership = await seed_active_membership(
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
        csrf_token = await _gym_login(http, email=email)
        memberships = await http.get("/api/v1/gym/auth/memberships")
        assert memberships.status_code == 200
        body = memberships.json()["memberships"]
        assert len(body) == 1
        assert body[0]["tenant_id"] == tenant_id
        assert body[0]["membership_id"] == membership.membership_id
        assert body[0]["display_name"] == MEDE_GYM

        headers, _cookies = csrf_headers_and_cookies(
            token=csrf_token,
            cookie_name=GYM_CSRF_COOKIE.name,
        )
        select = await http.post(
            "/api/v1/gym/auth/select-tenant",
            json={"tenant_id": tenant_id},
            headers=headers,
        )
        assert select.status_code == 204
        new_csrf = select.headers.get(_CSRF.header_name)
        assert new_csrf
        assert new_csrf != csrf_token

        session_resp = await http.get("/api/v1/gym/auth/session")
        assert session_resp.status_code == 200
        session_body = session_resp.json()
        assert session_body["active_tenant_id"] == tenant_id
        assert session_body["membership_id"] == membership.membership_id
        assert session_body["tenant_display_name"] == MEDE_GYM


async def test_gym_select_tenant_without_membership_forbidden(
    integration_settings,
    auth_http_repos,
):
    settings = integration_settings_with_mfa(integration_settings)
    moment = datetime(2026, 10, 2, tzinfo=UTC)
    email = "http.gym.cross@example.test"
    identity = await _seed_gym_user(
        mongo_identity_repository=auth_http_repos["identity"],
        mongo_credential_repository=auth_http_repos["credential"],
        email=email,
        password=_PASSWORD,
        moment=moment,
    )
    mede_id = new_uuid()
    aaron_id = new_uuid()
    await seed_active_tenant(
        auth_http_repos["tenants"],
        tenant_id=mede_id,
        display_name=MEDE_GYM,
        moment=moment,
    )
    await seed_active_tenant(
        auth_http_repos["tenants"],
        tenant_id=aaron_id,
        display_name=AARON_GYM,
        moment=moment,
    )
    await seed_active_membership(
        auth_http_repos["memberships"],
        user_id=identity.user_id,
        tenant_id=mede_id,
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
        csrf_token = await _gym_login(http, email=email)
        headers, cookies = csrf_headers_and_cookies(
            token=csrf_token,
            cookie_name=GYM_CSRF_COOKIE.name,
        )
        denied = await http.post(
            "/api/v1/gym/auth/select-tenant",
            json={"tenant_id": aaron_id},
            headers=headers,
        )
        assert denied.status_code == 403


async def test_gym_select_tenant_requires_csrf(
    integration_settings,
    auth_http_repos,
):
    settings = integration_settings_with_mfa(integration_settings)
    moment = datetime(2026, 10, 3, tzinfo=UTC)
    email = "http.gym.csrf@example.test"
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
        display_name=MEDE_GYM,
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
        await _gym_login(http, email=email)
        response = await http.post(
            "/api/v1/gym/auth/select-tenant",
            json={"tenant_id": tenant_id},
            headers={"Origin": AUTH_HTTP_ORIGIN},
        )
        assert response.status_code == 403


async def test_gym_session_clears_stale_authz_epoch(
    integration_settings,
    auth_http_repos,
):
    settings = integration_settings_with_mfa(integration_settings)
    moment = datetime(2026, 10, 4, tzinfo=UTC)
    email = "http.gym.epoch@example.test"
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
        display_name=MEDE_GYM,
        moment=moment,
    )
    membership = await seed_active_membership(
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
        csrf_token = await _gym_login(http, email=email)
        headers, cookies = csrf_headers_and_cookies(
            token=csrf_token,
            cookie_name=GYM_CSRF_COOKIE.name,
        )
        assert (
            await http.post(
                "/api/v1/gym/auth/select-tenant",
                json={"tenant_id": tenant_id},
                headers=headers,
            )
        ).status_code == 204

        from gym_erp_api.modules.access.domain.enums import GymRole

        updated = membership.with_roles(
            frozenset({GymRole.GYM_ADMIN, GymRole.GYM_OWNER}),
            now=moment.replace(hour=12),
        )
        await access.membership_repository.save(
            updated,
            expected_authz_epoch=membership.authz_epoch,
        )

        session_resp = await http.get("/api/v1/gym/auth/session")
        assert session_resp.status_code == 200
        assert session_resp.json()["active_tenant_id"] is None


async def test_gym_select_tenant_suspended_tenant_forbidden(
    integration_settings,
    auth_http_repos,
):
    settings = integration_settings_with_mfa(integration_settings)
    moment = datetime(2026, 10, 5, tzinfo=UTC)
    email = "http.gym.suspended@example.test"
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
        display_name=MEDE_GYM,
        moment=moment,
        status=TenantStatus.SUSPENDED,
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
        csrf_token = await _gym_login(http, email=email)
        headers, cookies = csrf_headers_and_cookies(
            token=csrf_token,
            cookie_name=GYM_CSRF_COOKIE.name,
        )
        denied = await http.post(
            "/api/v1/gym/auth/select-tenant",
            json={"tenant_id": tenant_id},
            headers=headers,
        )
        assert denied.status_code == 403
