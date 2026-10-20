"""Pruebas HTTP auth (ASGI, infra inyectada)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from gym_erp_api.core.config import Settings
from gym_erp_api.infrastructure.identity.identity_container import IdentityInfrastructure
from gym_erp_api.main import create_app
from gym_erp_api.modules.identity.application.dto.auth_results import CreatedSession
from gym_erp_api.modules.identity.application.errors import AuthenticationFailedError
from gym_erp_api.modules.identity.application.security.http_auth_contracts import (
    GYM_SESSION_COOKIE,
    PLATFORM_AUTH_CONTINUATION_COOKIE,
    PLATFORM_SESSION_COOKIE,
    CsrfPolicy,
)
from gym_erp_api.modules.identity.domain.auth_session import AuthSession
from gym_erp_api.modules.identity.domain.session_kind import SessionKind
from gym_erp_api.presentation.http_security.csrf import CsrfProtectionService
from gym_erp_api.presentation.http_security.rate_limit import HttpRateLimiter
from tests.support.in_memory_csrf_token_repository import InMemoryCsrfTokenRepository
from tests.support.in_memory_rate_limit_repository import InMemoryRateLimitRepository

_ORIGIN = "http://127.0.0.1:5173"
_CSRF = CsrfPolicy()
_MOMENT = datetime(2026, 12, 1, tzinfo=UTC)


def _settings() -> Settings:
    return Settings(app_env="test", mongodb_uri=None, allow_insecure_cookies=True)


def _session(kind: SessionKind) -> AuthSession:
    return AuthSession.create(
        user_id="00000000-0000-4000-8000-000000000001",
        session_kind=kind,
        token_hash="a" * 64,
        expires_at=_MOMENT.replace(year=_MOMENT.year + 1),
        idle_expires_at=_MOMENT.replace(year=_MOMENT.year + 1),
        credential_version=0,
        now=_MOMENT,
    )


def _auth_app(infra: IdentityInfrastructure | None = None):
    settings = _settings()
    app = create_app(settings=settings)
    rate_repo = InMemoryRateLimitRepository()
    csrf_repo = InMemoryCsrfTokenRepository()
    app.state.http_rate_limiter = HttpRateLimiter(repository=rate_repo, settings=settings)
    app.state.csrf_protection = CsrfProtectionService(repository=csrf_repo)
    app.state.identity_infrastructure = infra
    return app


@pytest.mark.asyncio
async def test_gym_login_wrong_password_generic():
    infra = MagicMock(spec=IdentityInfrastructure)
    infra.credential_verification = MagicMock()
    infra.credential_verification.verify = AsyncMock(side_effect=AuthenticationFailedError("x"))
    app = _auth_app(infra)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/gym/auth/login",
            json={"email": "a@b.test", "password": "wrong-password-12"},
            headers={"Origin": _ORIGIN},
        )
    assert response.status_code == 401
    assert "hash" not in response.text.lower()
    assert "mongodb" not in response.text.lower()


@pytest.mark.asyncio
async def test_gym_login_sets_cookie_not_json_token():
    session = _session(SessionKind.GYM)
    created = CreatedSession(session=session, opaque_token="opaque-gym-token-value")
    infra = MagicMock(spec=IdentityInfrastructure)
    infra.credential_verification = MagicMock()
    infra.credential_verification.verify = AsyncMock(return_value=MagicMock())
    infra.create_gym_session = MagicMock()
    infra.create_gym_session.execute = AsyncMock(return_value=created)
    app = _auth_app(infra)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/gym/auth/login",
            json={"email": "a@b.test", "password": "valid-password-12"},
            headers={"Origin": _ORIGIN},
        )
    assert response.status_code == 204
    assert "opaque-gym-token-value" not in response.text
    assert GYM_SESSION_COOKIE.name in response.headers.get("set-cookie", "")


@pytest.mark.asyncio
async def test_gym_login_not_blocked_by_unresolvable_session_cookie():
    session = _session(SessionKind.GYM)
    resolved = MagicMock()
    resolved.session_kind = SessionKind.GYM
    resolved.session = session
    resolved.user_id = session.user_id
    infra = MagicMock(spec=IdentityInfrastructure)
    infra.resolve_session = MagicMock()
    infra.resolve_session.execute = AsyncMock(side_effect=Exception("revoked"))
    infra.credential_verification = MagicMock()
    infra.credential_verification.verify = AsyncMock(return_value=MagicMock())
    infra.create_gym_session = MagicMock()
    infra.create_gym_session.execute = AsyncMock(
        return_value=CreatedSession(session=session, opaque_token="new-token")
    )
    app = _auth_app(infra)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/gym/auth/login",
            json={"email": "a@b.test", "password": "valid-password-12"},
            headers={"Origin": _ORIGIN},
            cookies={GYM_SESSION_COOKIE.name: "stale-opaque-token"},
        )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_gym_login_rejects_bad_origin():
    app = _auth_app(MagicMock(spec=IdentityInfrastructure))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/gym/auth/login",
            json={"email": "a@b.test", "password": "x" * 12},
            headers={"Origin": "http://evil.example"},
        )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_gym_logout_requires_csrf_when_session_valid():
    session = _session(SessionKind.GYM)
    resolved = MagicMock()
    resolved.session_kind = SessionKind.GYM
    resolved.session = session
    resolved.user_id = session.user_id
    infra = MagicMock(spec=IdentityInfrastructure)
    infra.resolve_session = MagicMock()
    infra.resolve_session.execute = AsyncMock(return_value=resolved)
    app = _auth_app(infra)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/gym/auth/logout",
            headers={"Origin": _ORIGIN},
            cookies={GYM_SESSION_COOKIE.name: "session-token"},
        )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_platform_login_sets_continuation_not_platform_session():
    bundle = MagicMock()
    bundle.opaque_token = "cont-token-value"
    bundle.expires_at = _MOMENT.replace(year=_MOMENT.year + 1)
    infra = MagicMock(spec=IdentityInfrastructure)
    infra.credential_verification = MagicMock()
    infra.credential_verification.verify = AsyncMock(return_value=MagicMock())
    infra.platform_session_eligibility = MagicMock()
    infra.platform_session_eligibility.require_eligible_operator = AsyncMock(return_value=None)
    infra.create_auth_continuation = MagicMock()
    infra.create_auth_continuation.execute = AsyncMock(return_value=bundle)
    app = _auth_app(infra)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/platform/auth/login",
            json={"email": "p@b.test", "password": "valid-password-12"},
            headers={"Origin": _ORIGIN},
        )
    assert response.status_code == 204
    raw = response.headers.get("set-cookie", "")
    assert PLATFORM_AUTH_CONTINUATION_COOKIE.name in raw
    if PLATFORM_SESSION_COOKIE.name in raw:
        assert "Max-Age=0" in raw
    assert "cont-token-value" not in response.text


@pytest.mark.asyncio
async def test_platform_login_rejects_non_eligible_operator():
    principal = MagicMock(user_id="00000000-0000-4000-8000-000000000099")
    infra = MagicMock(spec=IdentityInfrastructure)
    infra.credential_verification = MagicMock()
    infra.credential_verification.verify = AsyncMock(return_value=principal)
    infra.platform_session_eligibility = MagicMock()
    infra.platform_session_eligibility.require_eligible_operator = AsyncMock(
        side_effect=AuthenticationFailedError("Credenciales inválidas.")
    )
    infra.create_auth_continuation = MagicMock()
    infra.create_auth_continuation.execute = AsyncMock()
    app = _auth_app(infra)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/platform/auth/login",
            json={"email": "gym.only@example.test", "password": "valid-password-12"},
            headers={"Origin": _ORIGIN},
        )
    assert response.status_code == 401
    infra.create_auth_continuation.execute.assert_not_called()


@pytest.mark.asyncio
async def test_auth_endpoints_503_without_identity():
    app = _auth_app(None)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/gym/auth/login",
            json={"email": "a@b.test", "password": "valid-password-12"},
            headers={"Origin": _ORIGIN},
        )
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_health_unaffected(app_no_mongo):
    transport = ASGITransport(app=app_no_mongo)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health/live")
    assert response.status_code == 200
