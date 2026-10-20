"""Flujos HTTP gym auth contra gym_platform_test (colecciones efímeras)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from gym_erp_api.modules.identity.application.security.http_auth_contracts import (
    GYM_CSRF_COOKIE,
    GYM_SESSION_COOKIE,
    CsrfPolicy,
)
from gym_erp_api.modules.identity.domain.enums import UserIdentityStatus
from gym_erp_api.modules.identity.domain.user_credential import UserCredential
from gym_erp_api.modules.identity.domain.user_identity import UserIdentity
from gym_erp_api.modules.identity.infrastructure.crypto.argon2_password_hasher import (
    Argon2PasswordHasher,
)
from tests.support.auth_http_integration import (
    AUTH_HTTP_ORIGIN,
    build_auth_http_identity_stack,
    csrf_headers_and_cookies,
    integration_settings_with_mfa,
    mounted_auth_http_client,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.identity_persistence,
    pytest.mark.asyncio(loop_scope="session"),
]

_PASSWORD = "integration-gym-login-12"
_CSRF = CsrfPolicy()


async def _seed_gym_user(
    *,
    mongo_identity_repository,
    mongo_credential_repository,
    email: str,
    password: str,
    moment: datetime,
    disabled: bool = False,
) -> UserIdentity:
    identity = UserIdentity.create(email=email, now=moment).mark_email_verified(now=moment)
    if disabled:
        identity = identity.transition_status(UserIdentityStatus.DISABLED, now=moment)
    await mongo_identity_repository.save(identity)
    hasher = Argon2PasswordHasher()
    await mongo_credential_repository.insert(
        UserCredential.create(
            user_id=identity.user_id,
            password_hash=hasher.hash(password),
            credential_version=0,
            now=moment,
        )
    )
    return identity


async def test_gym_login_session_logout_http(
    integration_settings,
    auth_http_repos,
):
    settings = integration_settings_with_mfa(integration_settings)
    moment = datetime(2026, 9, 1, tzinfo=UTC)
    email = "http.gym.auth@example.test"
    identity = await _seed_gym_user(
        mongo_identity_repository=auth_http_repos["identity"],
        mongo_credential_repository=auth_http_repos["credential"],
        email=email,
        password=_PASSWORD,
        moment=moment,
    )
    databases, infra, _elig, http_sec = build_auth_http_identity_stack(
        settings=settings,
        mongo_identity_repository=auth_http_repos["identity"],
        mongo_credential_repository=auth_http_repos["credential"],
        mongo_auth_session_repository=auth_http_repos["session"],
        mongo_platform_totp_enrollment_repository=auth_http_repos["totp"],
        mongo_platform_mfa_challenge_repository=auth_http_repos["challenge"],
        mongo_platform_mfa_step_repository=auth_http_repos["step"],
        mongo_platform_mfa_session_authorization_repository=auth_http_repos["authz"],
    )
    async with mounted_auth_http_client(
        settings=settings,
        identity_infrastructure=infra,
        databases=databases,
        http_security=http_sec,
    ) as http:
        login = await http.post(
            "/api/v1/gym/auth/login",
            json={"email": email, "password": _PASSWORD},
            headers={"Origin": AUTH_HTTP_ORIGIN},
        )
        assert login.status_code == 204
        assert GYM_SESSION_COOKIE.name in login.headers.get("set-cookie", "")
        csrf_token = login.headers.get(_CSRF.header_name)
        assert csrf_token
        session_resp = await http.get("/api/v1/gym/auth/session")
        assert session_resp.status_code == 200
        assert session_resp.json()["user_id"] == identity.user_id
        csrf_token = session_resp.headers.get(_CSRF.header_name, csrf_token)
        headers, cookies = csrf_headers_and_cookies(
            token=csrf_token,
            cookie_name=GYM_CSRF_COOKIE.name,
        )
        logout = await http.post(
            "/api/v1/gym/auth/logout",
            headers=headers,
            cookies=cookies,
        )
        assert logout.status_code == 204
        assert (await http.get("/api/v1/gym/auth/session")).status_code == 401


async def test_gym_login_wrong_password(integration_settings, auth_http_repos):
    settings = integration_settings_with_mfa(integration_settings)
    moment = datetime(2026, 9, 2, tzinfo=UTC)
    email = "http.gym.badpass@example.test"
    await _seed_gym_user(
        mongo_identity_repository=auth_http_repos["identity"],
        mongo_credential_repository=auth_http_repos["credential"],
        email=email,
        password=_PASSWORD,
        moment=moment,
    )
    databases, infra, _, http_sec = build_auth_http_identity_stack(
        settings=settings,
        mongo_identity_repository=auth_http_repos["identity"],
        mongo_credential_repository=auth_http_repos["credential"],
        mongo_auth_session_repository=auth_http_repos["session"],
        mongo_platform_totp_enrollment_repository=auth_http_repos["totp"],
        mongo_platform_mfa_challenge_repository=auth_http_repos["challenge"],
        mongo_platform_mfa_step_repository=auth_http_repos["step"],
        mongo_platform_mfa_session_authorization_repository=auth_http_repos["authz"],
    )
    async with mounted_auth_http_client(
        settings=settings,
        identity_infrastructure=infra,
        databases=databases,
        http_security=http_sec,
    ) as http:
        response = await http.post(
            "/api/v1/gym/auth/login",
            json={"email": email, "password": "wrong-password-99"},
            headers={"Origin": AUTH_HTTP_ORIGIN},
        )
        assert response.status_code == 401
        assert "hash" not in response.text.lower()


async def test_gym_login_disabled_account(
    integration_settings,
    auth_http_repos,
):
    settings = integration_settings_with_mfa(integration_settings)
    moment = datetime(2026, 9, 3, tzinfo=UTC)
    email = "http.gym.disabled@example.test"
    await _seed_gym_user(
        mongo_identity_repository=auth_http_repos["identity"],
        mongo_credential_repository=auth_http_repos["credential"],
        email=email,
        password=_PASSWORD,
        moment=moment,
        disabled=True,
    )
    databases, infra, _, http_sec = build_auth_http_identity_stack(
        settings=settings,
        mongo_identity_repository=auth_http_repos["identity"],
        mongo_credential_repository=auth_http_repos["credential"],
        mongo_auth_session_repository=auth_http_repos["session"],
        mongo_platform_totp_enrollment_repository=auth_http_repos["totp"],
        mongo_platform_mfa_challenge_repository=auth_http_repos["challenge"],
        mongo_platform_mfa_step_repository=auth_http_repos["step"],
        mongo_platform_mfa_session_authorization_repository=auth_http_repos["authz"],
    )
    async with mounted_auth_http_client(
        settings=settings,
        identity_infrastructure=infra,
        databases=databases,
        http_security=http_sec,
    ) as http:
        response = await http.post(
            "/api/v1/gym/auth/login",
            json={"email": email, "password": _PASSWORD},
            headers={"Origin": AUTH_HTTP_ORIGIN},
        )
        assert response.status_code == 401


async def test_gym_logout_requires_csrf(
    integration_settings,
    auth_http_repos,
):
    settings = integration_settings_with_mfa(integration_settings)
    moment = datetime(2026, 9, 4, tzinfo=UTC)
    email = "http.gym.nocsrf@example.test"
    await _seed_gym_user(
        mongo_identity_repository=auth_http_repos["identity"],
        mongo_credential_repository=auth_http_repos["credential"],
        email=email,
        password=_PASSWORD,
        moment=moment,
    )
    databases, infra, _, http_sec = build_auth_http_identity_stack(
        settings=settings,
        mongo_identity_repository=auth_http_repos["identity"],
        mongo_credential_repository=auth_http_repos["credential"],
        mongo_auth_session_repository=auth_http_repos["session"],
        mongo_platform_totp_enrollment_repository=auth_http_repos["totp"],
        mongo_platform_mfa_challenge_repository=auth_http_repos["challenge"],
        mongo_platform_mfa_step_repository=auth_http_repos["step"],
        mongo_platform_mfa_session_authorization_repository=auth_http_repos["authz"],
    )
    async with mounted_auth_http_client(
        settings=settings,
        identity_infrastructure=infra,
        databases=databases,
        http_security=http_sec,
    ) as http:
        await http.post(
            "/api/v1/gym/auth/login",
            json={"email": email, "password": _PASSWORD},
            headers={"Origin": AUTH_HTTP_ORIGIN},
        )
        logout = await http.post(
            "/api/v1/gym/auth/logout",
            headers={"Origin": AUTH_HTTP_ORIGIN},
        )
        assert logout.status_code == 403
        assert (await http.get("/api/v1/gym/auth/session")).status_code == 200


async def test_gym_login_503_without_identity_infra(integration_settings):
    settings = integration_settings_with_mfa(integration_settings)
    async with mounted_auth_http_client(
        settings=settings,
        identity_infrastructure=None,
    ) as http:
        response = await http.post(
            "/api/v1/gym/auth/login",
            json={"email": "x@example.test", "password": "any-password-12"},
            headers={"Origin": AUTH_HTTP_ORIGIN},
        )
    assert response.status_code == 503


async def test_gym_login_rate_limit_by_account(
    integration_settings,
    auth_http_repos,
):
    settings = integration_settings_with_mfa(integration_settings)
    moment = datetime(2026, 9, 5, tzinfo=UTC)
    email = "http.gym.ratelimit@example.test"
    await _seed_gym_user(
        mongo_identity_repository=auth_http_repos["identity"],
        mongo_credential_repository=auth_http_repos["credential"],
        email=email,
        password=_PASSWORD,
        moment=moment,
    )
    databases, infra, _, http_sec = build_auth_http_identity_stack(
        settings=settings,
        mongo_identity_repository=auth_http_repos["identity"],
        mongo_credential_repository=auth_http_repos["credential"],
        mongo_auth_session_repository=auth_http_repos["session"],
        mongo_platform_totp_enrollment_repository=auth_http_repos["totp"],
        mongo_platform_mfa_challenge_repository=auth_http_repos["challenge"],
        mongo_platform_mfa_step_repository=auth_http_repos["step"],
        mongo_platform_mfa_session_authorization_repository=auth_http_repos["authz"],
    )
    async with mounted_auth_http_client(
        settings=settings,
        identity_infrastructure=infra,
        databases=databases,
        http_security=http_sec,
    ) as http:
        last_status = 401
        for _ in range(11):
            response = await http.post(
                "/api/v1/gym/auth/login",
                json={"email": email, "password": "wrong-password-99"},
                headers={"Origin": AUTH_HTTP_ORIGIN},
            )
            last_status = response.status_code
        assert last_status == 429


async def test_gym_login_succeeds_with_revoked_session_cookie(
    integration_settings,
    auth_http_repos,
):
    settings = integration_settings_with_mfa(integration_settings)
    moment = datetime(2026, 9, 6, tzinfo=UTC)
    email = "http.gym.stale.cookie@example.test"
    await _seed_gym_user(
        mongo_identity_repository=auth_http_repos["identity"],
        mongo_credential_repository=auth_http_repos["credential"],
        email=email,
        password=_PASSWORD,
        moment=moment,
    )
    databases, infra, _, http_sec = build_auth_http_identity_stack(
        settings=settings,
        mongo_identity_repository=auth_http_repos["identity"],
        mongo_credential_repository=auth_http_repos["credential"],
        mongo_auth_session_repository=auth_http_repos["session"],
        mongo_platform_totp_enrollment_repository=auth_http_repos["totp"],
        mongo_platform_mfa_challenge_repository=auth_http_repos["challenge"],
        mongo_platform_mfa_step_repository=auth_http_repos["step"],
        mongo_platform_mfa_session_authorization_repository=auth_http_repos["authz"],
    )
    async with mounted_auth_http_client(
        settings=settings,
        identity_infrastructure=infra,
        databases=databases,
        http_security=http_sec,
    ) as http:
        login = await http.post(
            "/api/v1/gym/auth/login",
            json={"email": email, "password": _PASSWORD},
            headers={"Origin": AUTH_HTTP_ORIGIN},
        )
        assert login.status_code == 204
        session_resp = await http.get("/api/v1/gym/auth/session")
        user_id = session_resp.json()["user_id"]
        await infra.revoke_all_user_sessions.execute(user_id=user_id, reason="test-revoke")
        relogin = await http.post(
            "/api/v1/gym/auth/login",
            json={"email": email, "password": _PASSWORD},
            headers={"Origin": AUTH_HTTP_ORIGIN},
        )
        assert relogin.status_code == 204
        assert (await http.get("/api/v1/gym/auth/session")).status_code == 200


async def test_gym_logout_idempotent_when_session_already_revoked(
    integration_settings,
    auth_http_repos,
):
    settings = integration_settings_with_mfa(integration_settings)
    moment = datetime(2026, 9, 7, tzinfo=UTC)
    email = "http.gym.logout.stale@example.test"
    await _seed_gym_user(
        mongo_identity_repository=auth_http_repos["identity"],
        mongo_credential_repository=auth_http_repos["credential"],
        email=email,
        password=_PASSWORD,
        moment=moment,
    )
    databases, infra, _, http_sec = build_auth_http_identity_stack(
        settings=settings,
        mongo_identity_repository=auth_http_repos["identity"],
        mongo_credential_repository=auth_http_repos["credential"],
        mongo_auth_session_repository=auth_http_repos["session"],
        mongo_platform_totp_enrollment_repository=auth_http_repos["totp"],
        mongo_platform_mfa_challenge_repository=auth_http_repos["challenge"],
        mongo_platform_mfa_step_repository=auth_http_repos["step"],
        mongo_platform_mfa_session_authorization_repository=auth_http_repos["authz"],
    )
    async with mounted_auth_http_client(
        settings=settings,
        identity_infrastructure=infra,
        databases=databases,
        http_security=http_sec,
    ) as http:
        login = await http.post(
            "/api/v1/gym/auth/login",
            json={"email": email, "password": _PASSWORD},
            headers={"Origin": AUTH_HTTP_ORIGIN},
        )
        assert login.status_code == 204
        csrf_token = login.headers.get(_CSRF.header_name)
        headers, cookies = csrf_headers_and_cookies(
            token=csrf_token,
            cookie_name=GYM_CSRF_COOKIE.name,
        )
        first = await http.post(
            "/api/v1/gym/auth/logout",
            headers=headers,
            cookies=cookies,
        )
        assert first.status_code == 204
        second = await http.post(
            "/api/v1/gym/auth/logout",
            headers={"Origin": AUTH_HTTP_ORIGIN},
        )
        assert second.status_code == 204
        assert (await http.get("/api/v1/gym/auth/session")).status_code == 401
