"""Fixtures de integración para persistencia organization (colecciones efímeras dedicadas)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import pytest
import pytest_asyncio
from pymongo import AsyncMongoClient

from gym_erp_api.core.config import Settings
from gym_erp_api.infrastructure.mongo.database import mongo_client_options
from gym_erp_api.infrastructure.mongo.mongo_databases import MongoDatabases
from gym_erp_api.infrastructure.mongo.scoped_repository import TenantScopedRepository
from gym_erp_api.modules.organization.infrastructure.mongo.operational_branch_repository import (
    OperationalBranchRepository,
)
from gym_erp_api.modules.organization.infrastructure.mongo.platform_idempotency_repository import (
    PlatformIdempotencyRepository,
)
from gym_erp_api.modules.organization.infrastructure.mongo.platform_tenant_repository import (
    PlatformTenantRepository,
)
from tests.support.create_organization_integration import build_create_organization_handler
from tests.support.integration_environment import (
    EXPECTED_OPERATIONAL_DB_IN_URI,
    EXPECTED_PLATFORM_DB,
    ORG_OPERATIONAL_COLLECTION_PREFIX,
    ORG_PLATFORM_COLLECTION_PREFIX,
    ORG_PLATFORM_IDEMPOTENCY_COLLECTION_PREFIX,
    assert_organization_ephemeral_collection_safe_for_teardown,
    generate_org_operational_collection_name,
    generate_org_platform_collection_name,
    generate_org_platform_idempotency_collection_name,
    validate_integration_environment,
    verify_integration_mongodb_identity,
)
from tests.support.tenant_fixtures import make_context_tenant_a


async def _ensure_ephemeral_collection(db: Any, name: str) -> None:
    """Crea la colección fuera de transacciones de prueba (evita createCollection en txn)."""
    existing = await db.list_collection_names(filter={"name": name})
    if name not in existing:
        await db.create_collection(name)


@dataclass
class OrganizationIntegrationState:
    security_verified: bool = False
    platform_db: str | None = None
    operational_db: str | None = None
    platform_collection_name: str | None = None
    idempotency_collection_name: str | None = None
    operational_collection_name: str | None = None
    teardown_enabled: bool = False
    extra: dict = field(default_factory=dict)


@pytest.fixture(scope="session")
def organization_integration_state() -> OrganizationIntegrationState:
    return OrganizationIntegrationState()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def organization_mongo_client(
    integration_mongodb_uri: str,
    organization_integration_state: OrganizationIntegrationState,
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

    organization_integration_state.security_verified = True
    organization_integration_state.platform_db = platform_db
    organization_integration_state.operational_db = operational_db
    organization_integration_state.teardown_enabled = True
    yield client
    await client.close()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def organization_platform_tenants_collection(
    organization_mongo_client: Any,
    organization_integration_state: OrganizationIntegrationState,
) -> Any:
    if not organization_integration_state.security_verified:
        pytest.fail("Controles de seguridad no verificados; no se crea colección platform.")

    name = generate_org_platform_collection_name()
    organization_integration_state.platform_collection_name = name
    db = organization_mongo_client[EXPECTED_PLATFORM_DB]
    await _ensure_ephemeral_collection(db, name)
    collection = db[name]
    yield collection

    if not organization_integration_state.teardown_enabled:
        return
    registered = organization_integration_state.platform_collection_name
    if not registered:
        return
    try:
        assert_organization_ephemeral_collection_safe_for_teardown(
            collection.name,
            expected_name=registered,
            database_name=collection.database.name,
            collection_prefix=ORG_PLATFORM_COLLECTION_PREFIX,
            expected_database=EXPECTED_PLATFORM_DB,
        )
    except ValueError as exc:
        pytest.fail(f"Teardown platform rechazado: {exc}")
    await collection.drop()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def organization_platform_idempotency_collection(
    organization_mongo_client: Any,
    organization_integration_state: OrganizationIntegrationState,
) -> Any:
    if not organization_integration_state.security_verified:
        pytest.fail("Controles de seguridad no verificados; no se crea colección idempotency.")

    name = generate_org_platform_idempotency_collection_name()
    organization_integration_state.idempotency_collection_name = name
    db = organization_mongo_client[EXPECTED_PLATFORM_DB]
    await _ensure_ephemeral_collection(db, name)
    collection = db[name]
    yield collection

    if not organization_integration_state.teardown_enabled:
        return
    registered = organization_integration_state.idempotency_collection_name
    if not registered:
        return
    try:
        assert_organization_ephemeral_collection_safe_for_teardown(
            collection.name,
            expected_name=registered,
            database_name=collection.database.name,
            collection_prefix=ORG_PLATFORM_IDEMPOTENCY_COLLECTION_PREFIX,
            expected_database=EXPECTED_PLATFORM_DB,
        )
    except ValueError as exc:
        pytest.fail(f"Teardown idempotency rechazado: {exc}")
    await collection.drop()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def organization_operational_branches_collection(
    organization_mongo_client: Any,
    organization_integration_state: OrganizationIntegrationState,
) -> Any:
    if not organization_integration_state.security_verified:
        pytest.fail("Controles de seguridad no verificados; no se crea colección operational.")

    name = generate_org_operational_collection_name()
    organization_integration_state.operational_collection_name = name
    db = organization_mongo_client[EXPECTED_OPERATIONAL_DB_IN_URI]
    await _ensure_ephemeral_collection(db, name)
    collection = db[name]
    yield collection

    if not organization_integration_state.teardown_enabled:
        return
    registered = organization_integration_state.operational_collection_name
    if not registered:
        return
    try:
        assert_organization_ephemeral_collection_safe_for_teardown(
            collection.name,
            expected_name=registered,
            database_name=collection.database.name,
            collection_prefix=ORG_OPERATIONAL_COLLECTION_PREFIX,
            expected_database=EXPECTED_OPERATIONAL_DB_IN_URI,
        )
    except ValueError as exc:
        pytest.fail(f"Teardown operational rechazado: {exc}")
    await collection.drop()


@pytest_asyncio.fixture(autouse=True, loop_scope="session")
async def reset_organization_ephemeral_collections(
    organization_platform_tenants_collection: Any,
    organization_platform_idempotency_collection: Any,
    organization_operational_branches_collection: Any,
) -> Any:
    await organization_platform_tenants_collection.delete_many({})
    await organization_platform_idempotency_collection.delete_many({})
    await organization_operational_branches_collection.delete_many({})
    yield
    await organization_platform_tenants_collection.delete_many({})
    await organization_platform_idempotency_collection.delete_many({})
    await organization_operational_branches_collection.delete_many({})


@pytest.fixture(scope="session")
def organization_integration_settings(integration_settings: Settings) -> Settings:
    return integration_settings


@pytest.fixture(scope="session")
def organization_mongo_databases(
    organization_mongo_client: Any,
    organization_integration_settings: Settings,
) -> MongoDatabases:
    dbs = MongoDatabases(organization_mongo_client, organization_integration_settings)
    assert dbs.platform.name == EXPECTED_PLATFORM_DB
    assert dbs.operational.name == EXPECTED_OPERATIONAL_DB_IN_URI
    return dbs


@pytest.fixture
def organization_platform_tenant_repository(
    organization_platform_tenants_collection: Any,
) -> PlatformTenantRepository:
    return PlatformTenantRepository(organization_platform_tenants_collection)


@pytest.fixture
def organization_platform_idempotency_repository(
    organization_platform_idempotency_collection: Any,
) -> PlatformIdempotencyRepository:
    return PlatformIdempotencyRepository(organization_platform_idempotency_collection)


@pytest.fixture
def create_organization_handler(
    organization_platform_tenant_repository: PlatformTenantRepository,
    organization_platform_idempotency_repository: PlatformIdempotencyRepository,
    organization_platform_tenants_collection: Any,
    organization_operational_branches_collection: Any,
    organization_mongo_databases: MongoDatabases,
) -> Any:
    assert (
        organization_operational_branches_collection.database.name == EXPECTED_OPERATIONAL_DB_IN_URI
    )
    assert organization_platform_tenants_collection.database.name == EXPECTED_PLATFORM_DB
    return build_create_organization_handler(
        tenant_repository=organization_platform_tenant_repository,
        idempotency_repository=organization_platform_idempotency_repository,
        operational_branches_collection=organization_operational_branches_collection,
        mongo_databases=organization_mongo_databases,
    )


@pytest.fixture
def organization_branch_repository(
    organization_operational_branches_collection: Any,
) -> OperationalBranchRepository:
    """Repositorio scoped con contexto ficticio válido (Titan Gym)."""
    ctx = make_context_tenant_a()
    scoped = TenantScopedRepository(organization_operational_branches_collection, ctx)
    return OperationalBranchRepository(scoped)


@pytest.fixture
def organization_branch_repository_branch_scoped(
    organization_operational_branches_collection: Any,
) -> OperationalBranchRepository:
    """Repositorio operational con allowed_branch_ids acotado (BRANCH_X)."""
    from tests.support.tenant_fixtures import BRANCH_X_ID

    ctx = make_context_tenant_a(allowed_branch_ids=frozenset({BRANCH_X_ID}))
    scoped = TenantScopedRepository(
        organization_operational_branches_collection,
        ctx,
        branch_scoped=True,
    )
    return OperationalBranchRepository(scoped)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if "/integration/organization/" in item.nodeid.replace("\\", "/"):
            item.add_marker(pytest.mark.asyncio(loop_scope="session"))
