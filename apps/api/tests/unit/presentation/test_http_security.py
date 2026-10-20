import asyncio
import base64
import os
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from gym_erp_api.core.config import Settings
from gym_erp_api.infrastructure.http.http_security_container import (
    build_http_security_infrastructure,
)
from gym_erp_api.infrastructure.mongo.mongo_databases import MongoDatabases
from gym_erp_api.main import create_app
from gym_erp_api.modules.identity.application.errors import AuthenticationFailedError
from gym_erp_api.modules.identity.application.security.http_auth_contracts import (
    GYM_CSRF_COOKIE,
    GYM_SESSION_COOKIE,
    PLATFORM_AUTH_CONTINUATION_COOKIE,
    PLATFORM_CSRF_COOKIE,
    PLATFORM_SESSION_COOKIE,
    CsrfPolicy,
)
from gym_erp_api.presentation.http_security.cookies import (
    clear_platform_session_cookie,
    set_platform_session_cookie,
)
from gym_erp_api.presentation.http_security.csrf import CsrfProtectionService
from gym_erp_api.presentation.http_security.errors import InvalidOriginError
from gym_erp_api.presentation.http_security.origin import (
    normalize_origin,
    validate_origin_for_mutation,
)
from gym_erp_api.presentation.http_security.rate_limit import HttpRateLimiter, RateLimitBucket
from tests.support.in_memory_csrf_token_repository import InMemoryCsrfTokenRepository
from tests.support.in_memory_rate_limit_repository import InMemoryRateLimitRepository
from tests.support.security_probe_router import router as security_probe_router

_CSRF = CsrfPolicy()
_DEFAULT_ORIGIN = "http://127.0.0.1:5173"


def _settings(**kwargs) -> Settings:
    defaults = dict(app_env="test", mongodb_uri=None, allow_insecure_cookies=True)
    defaults.update(kwargs)
    return Settings(**defaults)


def test_normalize_origin_exact():
    assert normalize_origin("http://127.0.0.1:5173") == "http://127.0.0.1:5173"
    assert normalize_origin("http://localhost:5173") == "http://localhost:5173"


def test_rejects_partial_origin_match():
    settings = _settings(cors_origins="http://127.0.0.1:5173")
    with pytest.raises(InvalidOriginError):
        validate_origin_for_mutation(
            settings,
            origin_header="http://127.0.0.1:5174",
            referer_header=None,
        )


def test_missing_origin_and_referer_rejected():
    settings = _settings()
    with pytest.raises(InvalidOriginError):
        validate_origin_for_mutation(settings, origin_header=None, referer_header=None)


def test_referer_used_when_origin_missing():
    settings = _settings(cors_origins="http://localhost:5173")
    validate_origin_for_mutation(
        settings,
        origin_header=None,
        referer_header="http://localhost:5173/some/path",
    )


def test_platform_cookie_path_and_flags():
    settings = _settings(app_env="test", allow_insecure_cookies=False)
    from starlette.responses import Response

    response = Response()
    now = datetime(2026, 1, 1, tzinfo=UTC)
    set_platform_session_cookie(
        response,
        token="opaque-token-value",
        settings=settings,
        expires_at=now + timedelta(hours=1),
        now=now,
    )
    raw = response.headers.get("set-cookie", "")
    assert PLATFORM_SESSION_COOKIE.name in raw
    assert "HttpOnly" in raw
    assert "Secure" in raw
    assert f"Path={PLATFORM_SESSION_COOKIE.path}" in raw
    clear_platform_session_cookie(response, settings=settings)


@pytest.mark.asyncio
async def test_rate_limit_by_ip_and_account():
    repo = InMemoryRateLimitRepository()
    limiter = HttpRateLimiter(repository=repo, settings=_settings(rate_limit_fail_closed=True))
    now = datetime(2026, 1, 1, tzinfo=UTC)
    for _ in range(10):
        await limiter.enforce_login_account(account_key="acct", now=now)
    from gym_erp_api.presentation.http_security.errors import RateLimitExceededError

    with pytest.raises(RateLimitExceededError):
        await limiter.enforce_login_account(account_key="acct", now=now)


@pytest.mark.asyncio
async def test_rate_limit_concurrent_increments():
    repo = InMemoryRateLimitRepository()
    now = datetime(2026, 1, 1, tzinfo=UTC)

    async def hit():
        return await repo.check_and_increment(
            bucket=RateLimitBucket.LOGIN_IP.value,
            scope_key="1.2.3.4",
            limit=5,
            window=timedelta(minutes=1),
            now=now,
        )

    results = await asyncio.gather(*[hit() for _ in range(8)])
    allowed = sum(1 for r in results if r.allowed)
    assert allowed == 5


@pytest.mark.asyncio
async def test_rate_limit_backend_fail_closed():
    repo = InMemoryRateLimitRepository()
    repo.fail_next = True
    limiter = HttpRateLimiter(repository=repo, settings=_settings(rate_limit_fail_closed=True))
    from gym_erp_api.presentation.http_security.errors import RateLimitBackendError

    with pytest.raises(RateLimitBackendError):
        await limiter.enforce(
            bucket=RateLimitBucket.LOGIN_IP,
            scope_key="9.9.9.9",
            limit=10,
            window=timedelta(minutes=1),
            now=datetime.now(tz=UTC),
        )


def _attach_probe_security(app, settings: Settings) -> None:
    rate_repo = InMemoryRateLimitRepository()
    csrf_repo = InMemoryCsrfTokenRepository()
    app.state.http_rate_limiter = HttpRateLimiter(repository=rate_repo, settings=settings)
    app.state.csrf_protection = CsrfProtectionService(repository=csrf_repo)


def _probe_app(settings: Settings, *, with_security: bool = False):
    app = create_app(settings=settings)
    if with_security:
        _attach_probe_security(app, settings)
    app.include_router(security_probe_router, prefix="/api/v1")
    return app


@pytest.mark.asyncio
async def test_probe_origin_authorized():
    app = _probe_app(_settings())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/internal/security-probe/origin",
            headers={"Origin": _DEFAULT_ORIGIN},
        )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_probe_origin_missing():
    app = _probe_app(_settings())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/internal/security-probe/origin")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_probe_origin_forbidden():
    app = _probe_app(_settings())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/internal/security-probe/origin",
            headers={"Origin": "http://evil.example"},
        )
    assert response.status_code == 403
    assert "mongodb" not in response.text.lower()


@pytest.mark.asyncio
async def test_probe_csrf_valid_flow():
    settings = _settings()
    app = _probe_app(settings, with_security=True)
    transport = ASGITransport(app=app)
    binding = "continuation:test-binding"
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        issued = await client.post(
            f"/api/v1/internal/security-probe/csrf-issue/{binding}",
            headers={"Origin": _DEFAULT_ORIGIN},
        )
        assert issued.status_code == 200
        token = issued.headers.get(_CSRF.header_name)
        assert token
        ok = await client.post(
            f"/api/v1/internal/security-probe/csrf/{binding}",
            headers={
                "Origin": _DEFAULT_ORIGIN,
                _CSRF.header_name: token,
            },
            cookies={_CSRF.cookie_name: token},
        )
        assert ok.status_code == 200


@pytest.mark.asyncio
async def test_pre_auth_allows_continuation_cookie_without_csrf():
    settings = _settings()
    app = _probe_app(settings, with_security=True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/internal/security-probe/pre-auth-with-session-cookie",
            headers={"Origin": _DEFAULT_ORIGIN},
            cookies={PLATFORM_AUTH_CONTINUATION_COOKIE.name: "opaque-continuation-token"},
        )
    assert response.status_code == 200


async def test_pre_auth_rejects_session_cookie_without_csrf_profile():
    settings = _settings()
    app = _probe_app(settings, with_security=True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/internal/security-probe/pre-auth-with-session-cookie",
            headers={"Origin": _DEFAULT_ORIGIN},
            cookies={PLATFORM_SESSION_COOKIE.name: "opaque-session-token"},
        )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cookie_session_profile_requires_binding_key():
    settings = _settings()
    app = _probe_app(settings, with_security=True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/internal/security-probe/cookie-session-missing-csrf",
            headers={"Origin": _DEFAULT_ORIGIN},
            cookies={PLATFORM_SESSION_COOKIE.name: "opaque-session-token"},
        )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_csrf_token_reusable_for_same_binding():
    settings = _settings()
    app = _probe_app(settings, with_security=True)
    transport = ASGITransport(app=app)
    binding = "session:binding-a"
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        issued = await client.post(
            f"/api/v1/internal/security-probe/csrf-issue/{binding}",
            headers={"Origin": _DEFAULT_ORIGIN},
        )
        token = issued.headers.get(_CSRF.header_name)
        first = await client.post(
            f"/api/v1/internal/security-probe/csrf/{binding}",
            headers={"Origin": _DEFAULT_ORIGIN, _CSRF.header_name: token},
            cookies={_CSRF.cookie_name: token},
        )
        assert first.status_code == 200
        second = await client.post(
            f"/api/v1/internal/security-probe/csrf/{binding}",
            headers={"Origin": _DEFAULT_ORIGIN, _CSRF.header_name: token},
            cookies={_CSRF.cookie_name: token},
        )
        assert second.status_code == 200


@pytest.mark.asyncio
async def test_csrf_gym_and_platform_cookies_isolated():
    settings = _settings()
    app = _probe_app(settings, with_security=True)
    transport = ASGITransport(app=app)
    gym_binding = "session:gym:11111111-1111-4111-8111-111111111111"
    plat_binding = "session:platform:22222222-2222-4222-8222-222222222222"
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        gym_issue = await client.post(
            f"/api/v1/internal/security-probe/csrf-issue/{gym_binding}",
            headers={"Origin": _DEFAULT_ORIGIN},
        )
        gym_token = gym_issue.headers.get(_CSRF.header_name)
        plat_issue = await client.post(
            f"/api/v1/internal/security-probe/csrf-issue/{plat_binding}",
            headers={"Origin": _DEFAULT_ORIGIN},
        )
        plat_token = plat_issue.headers.get(_CSRF.header_name)
        gym_ok = await client.post(
            f"/api/v1/internal/security-probe/csrf/{gym_binding}",
            headers={"Origin": _DEFAULT_ORIGIN, _CSRF.header_name: gym_token},
            cookies={GYM_CSRF_COOKIE.name: gym_token, PLATFORM_CSRF_COOKIE.name: plat_token},
        )
        assert gym_ok.status_code == 200
        plat_ok = await client.post(
            f"/api/v1/internal/security-probe/csrf/{plat_binding}",
            headers={"Origin": _DEFAULT_ORIGIN, _CSRF.header_name: plat_token},
            cookies={GYM_CSRF_COOKIE.name: gym_token, PLATFORM_CSRF_COOKIE.name: plat_token},
        )
        assert plat_ok.status_code == 200
        cross = await client.post(
            f"/api/v1/internal/security-probe/csrf/{gym_binding}",
            headers={"Origin": _DEFAULT_ORIGIN, _CSRF.header_name: plat_token},
            cookies={GYM_CSRF_COOKIE.name: plat_token, PLATFORM_CSRF_COOKIE.name: gym_token},
        )
        assert cross.status_code == 403


@pytest.mark.asyncio
async def test_csrf_token_not_valid_for_other_binding():
    settings = _settings()
    app = _probe_app(settings, with_security=True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        issued = await client.post(
            "/api/v1/internal/security-probe/csrf-issue/session:one",
            headers={"Origin": _DEFAULT_ORIGIN},
        )
        token = issued.headers.get(_CSRF.header_name)
        wrong = await client.post(
            "/api/v1/internal/security-probe/csrf/session:two",
            headers={"Origin": _DEFAULT_ORIGIN, _CSRF.header_name: token},
            cookies={_CSRF.cookie_name: token},
        )
        assert wrong.status_code == 403


@pytest.mark.asyncio
async def test_probe_csrf_missing():
    settings = _settings()
    app = _probe_app(settings, with_security=True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/internal/security-probe/csrf/binding-key",
            headers={"Origin": _DEFAULT_ORIGIN},
        )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_probe_rate_limit_429():
    settings = _settings()
    app = _probe_app(settings, with_security=True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        last = None
        for _ in range(11):
            last = await client.post(
                "/api/v1/internal/security-probe/rate-limit/same-account",
                headers={"Origin": _DEFAULT_ORIGIN},
            )
    assert last is not None
    assert last.status_code == 429
    assert last.headers.get("Retry-After")


@pytest.mark.asyncio
async def test_probe_cookie_platform_and_clear():
    settings = _settings(app_env="test", allow_insecure_cookies=False)
    app = _probe_app(settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        set_resp = await client.post(
            "/api/v1/internal/security-probe/cookie-platform",
            headers={"Origin": _DEFAULT_ORIGIN},
        )
        assert "gym_erp_platform_session" in set_resp.headers.get("set-cookie", "")
        clear_resp = await client.post(
            "/api/v1/internal/security-probe/cookie-gym-clear",
            headers={"Origin": _DEFAULT_ORIGIN},
        )
        cleared = clear_resp.headers.get_list("set-cookie")
        assert any("Max-Age=0" in c or '=""' in c for c in cleared)


@pytest.mark.asyncio
async def test_probe_identity_infra_503_without_mongo():
    app = _probe_app(_settings())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/internal/security-probe/identity-infra")
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_auth_error_handler_generic():
    app = _probe_app(_settings())

    @app.get("/throw-auth")
    async def _throw():
        raise AuthenticationFailedError("secret detail")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/throw-auth")
    assert response.status_code == 401
    assert "secret" not in response.text.lower()


@pytest.mark.asyncio
async def test_health_unaffected(app_no_mongo):
    transport = ASGITransport(app=app_no_mongo)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        live = await client.get("/api/v1/health/live")
    assert live.status_code == 200


def test_gym_cookie_path():
    assert GYM_SESSION_COOKIE.path == "/api/v1/gym"


def test_cookie_paths_cover_future_auth_routes():
    platform_prefix = "/api/v1/platform"
    gym_prefix = "/api/v1/gym"
    auth_prefix = "/api/v1/platform/auth"
    assert PLATFORM_SESSION_COOKIE.path == platform_prefix
    assert GYM_SESSION_COOKIE.path == gym_prefix
    assert PLATFORM_AUTH_CONTINUATION_COOKIE.path == auth_prefix
    assert auth_prefix.startswith(platform_prefix)


def test_build_http_security_container():
    settings = _settings(
        platform_mfa_encryption_key=SecretStr(base64.b64encode(os.urandom(32)).decode()),
    )
    client = MagicMock()
    platform_db = MagicMock()
    client.__getitem__.return_value = platform_db
    platform_db.__getitem__.side_effect = lambda n: MagicMock(name=n)
    infra = build_http_security_infrastructure(MongoDatabases(client, settings), settings)
    assert infra.rate_limiter is not None
    assert infra.csrf_protection is not None
