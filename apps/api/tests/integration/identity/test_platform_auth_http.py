"""Flujo HTTP platform auth + MFA contra gym_platform_test."""

from __future__ import annotations

from datetime import UTC, datetime

import pyotp
import pytest

from gym_erp_api.modules.identity.application.security.http_auth_contracts import (
    GYM_CSRF_COOKIE,
    PLATFORM_AUTH_CONTINUATION_COOKIE,
    PLATFORM_CSRF_COOKIE,
    PLATFORM_SESSION_COOKIE,
    CsrfPolicy,
)
from gym_erp_api.modules.identity.domain.user_credential import UserCredential
from gym_erp_api.modules.identity.domain.user_identity import UserIdentity
from gym_erp_api.modules.identity.infrastructure.crypto.argon2_password_hasher import (
    Argon2PasswordHasher,
)
from tests.support.auth_http_integration import (
    AUTH_HTTP_ORIGIN,
    build_auth_http_identity_stack,
    csrf_headers_and_cookies,
    grant_platform_operator_eligibility,
    integration_settings_with_mfa,
    mounted_auth_http_client,
    revoke_platform_operator_eligibility,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.http_auth,
    pytest.mark.identity_persistence,
    pytest.mark.asyncio(loop_scope="session"),
]

_PASSWORD = "integration-platform-login-12"
_CSRF = CsrfPolicy()


async def _seed_platform_operator(
    *,
    auth_http_repos,
    infra,
    operator_eligibility_collection,
    email: str,
    moment: datetime,
    eligible: bool,
) -> tuple[UserIdentity, str]:
    identity = UserIdentity.create(email=email, now=moment).mark_email_verified(now=moment)
    await auth_http_repos["identity"].save(identity)
    hasher = Argon2PasswordHasher()
    await auth_http_repos["credential"].insert(
        UserCredential.create(
            user_id=identity.user_id,
            password_hash=hasher.hash(_PASSWORD),
            credential_version=0,
            now=moment,
        )
    )
    if eligible:
        await grant_platform_operator_eligibility(
            operator_eligibility_collection,
            user_id=identity.user_id,
            granted_at=moment,
        )

    bundle = await infra.begin_totp_enrollment.execute(
        user_id=identity.user_id,
        account_email=identity.email_normalized,
    )
    secret = bundle.plaintext_secret.decode("ascii")
    code = pyotp.TOTP(secret).at(moment)
    await infra.confirm_totp_enrollment.execute(user_id=identity.user_id, totp_code=code)
    return identity, secret


async def _seed_gym_user_simple(auth_http_repos, email: str, moment: datetime) -> None:
    identity = UserIdentity.create(email=email, now=moment).mark_email_verified(now=moment)
    await auth_http_repos["identity"].save(identity)
    hasher = Argon2PasswordHasher()
    await auth_http_repos["credential"].insert(
        UserCredential.create(
            user_id=identity.user_id,
            password_hash=hasher.hash(_PASSWORD),
            credential_version=0,
            now=moment,
        )
    )


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
        operational_branches_collection=auth_http_repos["operational_branches"],
    )


async def test_platform_mfa_http_full_flow(
    integration_settings,
    auth_http_repos,
):
    settings = integration_settings_with_mfa(integration_settings)
    moment = datetime.now(tz=UTC)
    email = "http.platform.mfa@example.test"
    databases, infra, elig, http_sec, access = _stack(settings, auth_http_repos)
    identity, secret = await _seed_platform_operator(
        auth_http_repos=auth_http_repos,
        infra=infra,
        operator_eligibility_collection=elig,
        email=email,
        moment=moment,
        eligible=True,
    )
    async with mounted_auth_http_client(
        settings=settings,
        identity_infrastructure=infra,
        databases=databases,
        http_security=http_sec,
        access_infrastructure=access,
    ) as http:
        assert (await http.get("/api/v1/platform/auth/session")).status_code == 401

        login = await http.post(
            "/api/v1/platform/auth/login",
            json={"email": email, "password": _PASSWORD},
            headers={"Origin": AUTH_HTTP_ORIGIN},
        )
        assert login.status_code == 204
        login_cookies = login.headers.get("set-cookie", "")
        assert PLATFORM_AUTH_CONTINUATION_COOKIE.name in login_cookies
        if PLATFORM_SESSION_COOKIE.name in login_cookies:
            assert "Max-Age=0" in login_cookies
        assert (await http.get("/api/v1/platform/auth/session")).status_code == 401

        totp_code = pyotp.TOTP(secret).at(moment)
        mfa = await http.post(
            "/api/v1/platform/auth/mfa/verify",
            json={"totp_code": totp_code},
            headers={"Origin": AUTH_HTTP_ORIGIN},
        )
        assert mfa.status_code == 204
        assert PLATFORM_SESSION_COOKIE.name in mfa.headers.get("set-cookie", "")

        session = await http.get("/api/v1/platform/auth/session")
        assert session.status_code == 200
        assert session.json()["user_id"] == identity.user_id
        csrf_token = session.headers.get(_CSRF.header_name)
        assert csrf_token

        replay = await http.post(
            "/api/v1/platform/auth/mfa/verify",
            json={"totp_code": totp_code},
            headers={"Origin": AUTH_HTTP_ORIGIN},
        )
        assert replay.status_code in (401, 403)

        headers, cookies = csrf_headers_and_cookies(
            token=csrf_token,
            cookie_name=PLATFORM_CSRF_COOKIE.name,
        )
        logout = await http.post(
            "/api/v1/platform/auth/logout",
            headers=headers,
            cookies=cookies,
        )
        assert logout.status_code == 204
        assert (await http.get("/api/v1/platform/auth/session")).status_code == 401


async def test_platform_login_blocked_without_eligibility(
    integration_settings,
    auth_http_repos,
):
    settings = integration_settings_with_mfa(integration_settings)
    moment = datetime.now(tz=UTC)
    email = "http.gym.only.platform@example.test"
    databases, infra, elig, http_sec, access = _stack(settings, auth_http_repos)
    await _seed_platform_operator(
        auth_http_repos=auth_http_repos,
        infra=infra,
        operator_eligibility_collection=elig,
        email=email,
        moment=moment,
        eligible=False,
    )
    async with mounted_auth_http_client(
        settings=settings,
        identity_infrastructure=infra,
        databases=databases,
        http_security=http_sec,
        access_infrastructure=access,
    ) as http:
        login = await http.post(
            "/api/v1/platform/auth/login",
            json={"email": email, "password": _PASSWORD},
            headers={"Origin": AUTH_HTTP_ORIGIN},
        )
        assert login.status_code == 401
        set_cookie = login.headers.get("set-cookie", "")
        if PLATFORM_AUTH_CONTINUATION_COOKIE.name in set_cookie:
            assert "Max-Age=0" in set_cookie


async def test_gym_and_platform_sessions_csrf_isolated(
    integration_settings,
    auth_http_repos,
):
    settings = integration_settings_with_mfa(integration_settings)
    moment = datetime.now(tz=UTC)
    gym_email = "http.dual.gym@example.test"
    plat_email = "http.dual.platform@example.test"
    databases, infra, elig, http_sec, access = _stack(settings, auth_http_repos)
    await _seed_gym_user_simple(auth_http_repos, gym_email, moment)
    _, plat_secret = await _seed_platform_operator(
        auth_http_repos=auth_http_repos,
        infra=infra,
        operator_eligibility_collection=elig,
        email=plat_email,
        moment=moment,
        eligible=True,
    )
    async with mounted_auth_http_client(
        settings=settings,
        identity_infrastructure=infra,
        databases=databases,
        http_security=http_sec,
        access_infrastructure=access,
    ) as http:
        await http.post(
            "/api/v1/gym/auth/login",
            json={"email": gym_email, "password": _PASSWORD},
            headers={"Origin": AUTH_HTTP_ORIGIN},
        )
        gym_sess = await http.get("/api/v1/gym/auth/session")
        gym_csrf = gym_sess.headers.get(_CSRF.header_name)
        assert gym_csrf

        await http.post(
            "/api/v1/platform/auth/login",
            json={"email": plat_email, "password": _PASSWORD},
            headers={"Origin": AUTH_HTTP_ORIGIN},
        )
        await http.post(
            "/api/v1/platform/auth/mfa/verify",
            json={"totp_code": pyotp.TOTP(plat_secret).at(moment)},
            headers={"Origin": AUTH_HTTP_ORIGIN},
        )
        plat_sess = await http.get("/api/v1/platform/auth/session")
        plat_csrf = plat_sess.headers.get(_CSRF.header_name)
        assert plat_csrf

        gym_headers, gym_cookies = csrf_headers_and_cookies(
            token=gym_csrf,
            cookie_name=GYM_CSRF_COOKIE.name,
        )
        gym_logout = await http.post(
            "/api/v1/gym/auth/logout",
            headers=gym_headers,
            cookies=gym_cookies,
        )
        assert gym_logout.status_code == 204
        assert (await http.get("/api/v1/gym/auth/session")).status_code == 401
        assert (await http.get("/api/v1/platform/auth/session")).status_code == 200

        plat_sess_refresh = await http.get("/api/v1/platform/auth/session")
        plat_csrf = plat_sess_refresh.headers.get(_CSRF.header_name, plat_csrf)
        plat_headers, plat_cookies = csrf_headers_and_cookies(
            token=plat_csrf,
            cookie_name=PLATFORM_CSRF_COOKIE.name,
        )
        plat_logout = await http.post(
            "/api/v1/platform/auth/logout",
            headers=plat_headers,
            cookies=plat_cookies,
        )
        assert plat_logout.status_code == 204


async def test_platform_session_denied_after_eligibility_revoked(
    integration_settings,
    auth_http_repos,
):
    settings = integration_settings_with_mfa(integration_settings)
    moment = datetime.now(tz=UTC)
    email = "http.platform.revoke.elig@example.test"
    databases, infra, elig, http_sec, access = _stack(settings, auth_http_repos)
    identity, secret = await _seed_platform_operator(
        auth_http_repos=auth_http_repos,
        infra=infra,
        operator_eligibility_collection=elig,
        email=email,
        moment=moment,
        eligible=True,
    )
    async with mounted_auth_http_client(
        settings=settings,
        identity_infrastructure=infra,
        databases=databases,
        http_security=http_sec,
        access_infrastructure=access,
    ) as http:
        await http.post(
            "/api/v1/platform/auth/login",
            json={"email": email, "password": _PASSWORD},
            headers={"Origin": AUTH_HTTP_ORIGIN},
        )
        await http.post(
            "/api/v1/platform/auth/mfa/verify",
            json={"totp_code": pyotp.TOTP(secret).at(moment)},
            headers={"Origin": AUTH_HTTP_ORIGIN},
        )
        assert (await http.get("/api/v1/platform/auth/session")).status_code == 200
        await revoke_platform_operator_eligibility(elig, user_id=identity.user_id)
        assert (await http.get("/api/v1/platform/auth/session")).status_code == 401
