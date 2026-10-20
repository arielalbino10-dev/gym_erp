"""Fixtures integración access (gym_platform_test, colección efímera)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import pytest
import pytest_asyncio
from pymongo import AsyncMongoClient

from gym_erp_api.infrastructure.mongo.database import mongo_client_options
from gym_erp_api.modules.access.infrastructure.mongo.access_index_specs import (
    ensure_access_platform_indexes,
)
from gym_erp_api.modules.access.infrastructure.mongo.mongo_tenant_membership_repository import (
    MongoTenantMembershipRepository,
)
from tests.support.integration_environment import (
    ACCESS_TENANT_MEMBERSHIPS_PREFIX,
    EXPECTED_PLATFORM_DB,
    assert_organization_ephemeral_collection_safe_for_teardown,
    generate_access_tenant_memberships_collection_name,
    validate_integration_environment,
    verify_integration_mongodb_identity,
)


async def _ensure_ephemeral_collection(db: Any, name: str) -> None:
    existing = await db.list_collection_names(filter={"name": name})
    if name not in existing:
        await db.create_collection(name)


@dataclass
class AccessIntegrationState:
    security_verified: bool = False
    platform_db: str | None = None
    memberships_collection_name: str | None = None
    teardown_enabled: bool = False
    extra: dict = field(default_factory=dict)


@pytest.fixture(scope="session")
def access_integration_state() -> AccessIntegrationState:
    return AccessIntegrationState()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def access_mongo_client(
    integration_mongodb_uri: str,
    access_integration_state: AccessIntegrationState,
) -> Any:
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

    access_integration_state.security_verified = True
    access_integration_state.platform_db = platform_db
    access_integration_state.teardown_enabled = True
    yield client
    await client.close()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def access_memberships_collection(
    access_mongo_client: Any,
    access_integration_state: AccessIntegrationState,
) -> Any:
    if not access_integration_state.security_verified:
        pytest.fail("Validación de seguridad MongoDB no completada.")
    platform_db = access_integration_state.platform_db or EXPECTED_PLATFORM_DB
    name = generate_access_tenant_memberships_collection_name()
    access_integration_state.memberships_collection_name = name
    db = access_mongo_client[platform_db]
    await _ensure_ephemeral_collection(db, name)
    collection = db[name]
    await ensure_access_platform_indexes(memberships=collection)
    yield collection
    if access_integration_state.teardown_enabled:
        registered = access_integration_state.memberships_collection_name
        assert registered is not None
        assert_organization_ephemeral_collection_safe_for_teardown(
            registered,
            expected_name=name,
            database_name=platform_db,
            collection_prefix=ACCESS_TENANT_MEMBERSHIPS_PREFIX,
            expected_database=EXPECTED_PLATFORM_DB,
        )
        await db.drop_collection(name)


@pytest_asyncio.fixture(loop_scope="session")
async def mongo_membership_repository(
    access_memberships_collection: Any,
) -> MongoTenantMembershipRepository:
    return MongoTenantMembershipRepository(access_memberships_collection)
