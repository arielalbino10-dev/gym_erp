"""Fixtures integración HTTP security (colecciones efímeras en gym_platform_test)."""

from __future__ import annotations

import os
from dataclasses import dataclass

import pytest
import pytest_asyncio
from pymongo import AsyncMongoClient

from gym_erp_api.infrastructure.mongo.database import mongo_client_options
from tests.support.integration_environment import (
    EXPECTED_PLATFORM_DB,
    HTTP_SECURITY_RATE_LIMIT_PREFIX,
    assert_organization_ephemeral_collection_safe_for_teardown,
    generate_http_security_rate_limit_collection_name,
    validate_integration_environment,
    verify_integration_mongodb_identity,
)


@dataclass
class HttpSecurityIntegrationState:
    security_verified: bool = False
    rate_limit_collection_name: str | None = None
    teardown_enabled: bool = False


@pytest.fixture(scope="session")
def http_security_integration_state() -> HttpSecurityIntegrationState:
    return HttpSecurityIntegrationState()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def http_security_mongo_client(
    integration_mongodb_uri: str,
    http_security_integration_state: HttpSecurityIntegrationState,
):
    platform_db = os.environ.get("MONGODB_PLATFORM_DB", "").strip().lower()
    operational_db = os.environ.get("MONGODB_OPERATIONAL_DB", "").strip().lower()
    try:
        validate_integration_environment(
            uri=integration_mongodb_uri,
            platform_db=platform_db,
            operational_db=operational_db,
        )
    except ValueError as exc:
        pytest.fail(f"Entorno de integración rechazado: {exc}")

    client = AsyncMongoClient(integration_mongodb_uri, **mongo_client_options())
    try:
        await verify_integration_mongodb_identity(client)
    except Exception as exc:
        await client.close()
        pytest.fail(f"Identidad MongoDB de integración rechazada: {exc}")

    http_security_integration_state.security_verified = True
    http_security_integration_state.teardown_enabled = True
    yield client
    await client.close()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def http_rate_limit_integration_collection(
    http_security_mongo_client,
    http_security_integration_state: HttpSecurityIntegrationState,
):
    if not http_security_integration_state.security_verified:
        pytest.fail("Controles de seguridad no verificados.")

    name = generate_http_security_rate_limit_collection_name()
    http_security_integration_state.rate_limit_collection_name = name
    db = http_security_mongo_client[EXPECTED_PLATFORM_DB]
    existing = await db.list_collection_names(filter={"name": name})
    if name not in existing:
        await db.create_collection(name)
    collection = db[name]
    await collection.create_index("expires_at", expireAfterSeconds=0, name="ttl_rate_limit")
    yield collection
    if not http_security_integration_state.teardown_enabled:
        return
    registered = http_security_integration_state.rate_limit_collection_name
    if not registered:
        return
    assert_organization_ephemeral_collection_safe_for_teardown(
        collection.name,
        expected_name=registered,
        database_name=collection.database.name,
        collection_prefix=HTTP_SECURITY_RATE_LIMIT_PREFIX,
        expected_database=EXPECTED_PLATFORM_DB,
    )
    await collection.drop()


@pytest_asyncio.fixture(autouse=True, loop_scope="session")
async def reset_http_rate_limit_collection(http_rate_limit_integration_collection):
    await http_rate_limit_integration_collection.delete_many({})
    yield
    await http_rate_limit_integration_collection.delete_many({})


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if "/integration/http_security/" in item.nodeid.replace("\\", "/"):
            item.add_marker(pytest.mark.asyncio(loop_scope="session"))
