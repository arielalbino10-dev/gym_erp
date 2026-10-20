"""Rate limit MongoDB: concurrencia real en gym_platform_test."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from gym_erp_api.core.config import Settings
from gym_erp_api.infrastructure.mongo.mongo_rate_limit_repository import MongoRateLimitRepository
from gym_erp_api.main import create_app
from gym_erp_api.presentation.http_security.errors import RateLimitBackendError
from gym_erp_api.presentation.http_security.rate_limit import HttpRateLimiter, RateLimitBucket
from tests.support.security_probe_router import router as security_probe_router

pytestmark = [pytest.mark.integration, pytest.mark.http_security]


@pytest.mark.asyncio
async def test_mongo_rate_limit_concurrent_requests_respect_limit(
    http_rate_limit_integration_collection,
):
    repo = MongoRateLimitRepository(http_rate_limit_integration_collection)
    now = datetime.now(tz=UTC)
    limit = 8
    window = timedelta(minutes=1)
    bucket = RateLimitBucket.LOGIN_ACCOUNT.value
    scope = "integration-concurrent-account"

    async def hit():
        return await repo.check_and_increment(
            bucket=bucket,
            scope_key=scope,
            limit=limit,
            window=window,
            now=now,
        )

    results = await asyncio.gather(*[hit() for _ in range(24)])
    allowed = sum(1 for decision in results if decision.allowed)
    denied = [d for d in results if not d.allowed]
    assert allowed == limit
    assert len(denied) == 24 - limit
    assert all(d.retry_after_seconds >= 1 for d in denied)

    doc = await http_rate_limit_integration_collection.find_one({"_id": f"{bucket}:{scope}"})
    assert doc is not None
    assert int(doc["count"]) == limit


@pytest.mark.asyncio
async def test_mongo_rate_limit_window_rolls_over(
    http_rate_limit_integration_collection,
):
    repo = MongoRateLimitRepository(http_rate_limit_integration_collection)
    start = datetime.now(tz=UTC)
    limit = 3
    window = timedelta(seconds=1)
    bucket = "integration_window"
    scope = "scope-a"

    for _ in range(3):
        decision = await repo.check_and_increment(
            bucket=bucket,
            scope_key=scope,
            limit=limit,
            window=window,
            now=start,
        )
        assert decision.allowed

    blocked = await repo.check_and_increment(
        bucket=bucket,
        scope_key=scope,
        limit=limit,
        window=window,
        now=start,
    )
    assert not blocked.allowed

    await asyncio.sleep(1.1)
    after = datetime.now(tz=UTC)
    fresh = await repo.check_and_increment(
        bucket=bucket,
        scope_key=scope,
        limit=limit,
        window=window,
        now=after,
    )
    assert fresh.allowed
    doc = await http_rate_limit_integration_collection.find_one({"_id": f"{bucket}:{scope}"})
    assert doc is not None
    assert int(doc["count"]) == 1


@pytest.mark.asyncio
async def test_mongo_rate_limit_backend_failure_fail_closed(
    integration_mongodb_uri: str,
    http_rate_limit_integration_collection,
):
    from pymongo import AsyncMongoClient

    from gym_erp_api.infrastructure.mongo.database import mongo_client_options
    from tests.support.integration_environment import EXPECTED_PLATFORM_DB

    settings = Settings(app_env="test", mongodb_uri=None, rate_limit_fail_closed=True)
    client = AsyncMongoClient(integration_mongodb_uri, **mongo_client_options())
    collection = client[EXPECTED_PLATFORM_DB][http_rate_limit_integration_collection.name]
    repo = MongoRateLimitRepository(collection)
    limiter = HttpRateLimiter(repository=repo, settings=settings)
    await client.close()

    with pytest.raises(RateLimitBackendError):
        await limiter.enforce(
            bucket=RateLimitBucket.LOGIN_IP,
            scope_key="1.2.3.4",
            limit=5,
            window=timedelta(minutes=1),
            now=datetime.now(tz=UTC),
        )


@pytest.mark.asyncio
async def test_probe_rate_limit_returns_429_with_retry_after(
    integration_settings: Settings,
):
    settings = integration_settings.model_copy(update={"rate_limit_fail_closed": True})
    app = create_app(settings=settings)
    app.include_router(security_probe_router, prefix="/api/v1")
    origin = settings.cors_origin_list[0]
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            last = None
            for _ in range(12):
                last = await client.post(
                    "/api/v1/internal/security-probe/rate-limit/integration-account",
                    headers={"Origin": origin},
                )
    assert last is not None
    assert last.status_code == 429
    assert last.headers.get("Retry-After")
