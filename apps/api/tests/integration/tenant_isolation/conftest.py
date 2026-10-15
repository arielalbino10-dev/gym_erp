"""Harness de colección efímera y repositorios para aislamiento multi-tenant."""

from __future__ import annotations

import os
from typing import Any

import pytest
import pytest_asyncio
from pymongo import AsyncMongoClient

from gym_erp_api.infrastructure.mongo.database import mongo_client_options
from gym_erp_api.infrastructure.mongo.scoped_repository import TenantScopedRepository
from tests.integration.conftest import IntegrationSessionState
from tests.support.integration_environment import (
    EXPECTED_OPERATIONAL_DB_IN_URI,
    assert_ephemeral_collection_safe_for_teardown,
    generate_ephemeral_collection_name,
    validate_integration_environment,
    verify_integration_mongodb_identity,
)
from tests.support.tenant_fixtures import (
    BRANCH_X_ID,
    BRANCH_Y_ID,
    make_context_tenant_a,
    make_context_tenant_b,
)


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def integration_mongo_client(
    integration_mongodb_uri: str,
    integration_session_state: IntegrationSessionState,
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

    integration_session_state.security_verified = True
    integration_session_state.operational_db = operational_db
    integration_session_state.teardown_enabled = True
    yield client
    await client.close()


@pytest_asyncio.fixture(autouse=True, loop_scope="session")
async def reset_isolation_collection_between_tests(isolation_collection: Any) -> Any:
    """Evita colisiones de _id/índices entre tests sobre la misma colección de sesión.

    Debe usar el mismo event loop que ``integration_mongo_client`` (session); PyMongo
    rechaza ``AsyncMongoClient`` usado desde otro loop.
    """
    await isolation_collection.delete_many({})
    yield
    await isolation_collection.delete_many({})


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def isolation_collection(
    integration_mongo_client: Any,
    integration_session_state: IntegrationSessionState,
) -> Any:
    if not integration_session_state.security_verified:
        pytest.fail("Controles de seguridad no verificados; no se crea colección.")

    name = generate_ephemeral_collection_name()
    integration_session_state.ephemeral_collection_name = name
    db = integration_mongo_client[EXPECTED_OPERATIONAL_DB_IN_URI]
    collection = db[name]
    await collection.create_index([("tenant_id", 1), ("email_normalized", 1)], unique=True)
    await collection.create_index(
        [("tenant_id", 1), ("branch_id", 1), ("member_code", 1)],
        unique=True,
        partialFilterExpression={"status": "active"},
        name="uniq_active_member_per_branch",
    )
    yield collection

    if not integration_session_state.teardown_enabled:
        return
    registered = integration_session_state.ephemeral_collection_name
    op_db = integration_session_state.operational_db
    if not registered or not op_db:
        return
    try:
        assert_ephemeral_collection_safe_for_teardown(
            name,
            expected_name=registered,
            operational_db=op_db,
        )
    except ValueError:
        return
    await collection.drop()


@pytest.fixture
def repo_titan(isolation_collection: Any) -> TenantScopedRepository:
    return TenantScopedRepository(isolation_collection, make_context_tenant_a())


@pytest.fixture
def repo_olympus(isolation_collection: Any) -> TenantScopedRepository:
    return TenantScopedRepository(isolation_collection, make_context_tenant_b())


@pytest.fixture
def repo_titan_branch_x(isolation_collection: Any) -> TenantScopedRepository:
    ctx = make_context_tenant_a(allowed_branch_ids=frozenset({BRANCH_X_ID}))
    return TenantScopedRepository(isolation_collection, ctx, branch_scoped=True)


@pytest_asyncio.fixture(loop_scope="session")
async def seeded_member_docs(isolation_collection: Any) -> dict[str, Any]:
    """Dos miembros (Titan / Olympus) con ids fijos para pruebas de aislamiento."""
    titan_id = "doc-titan-001"
    olympus_id = "doc-olympus-001"
    await isolation_collection.insert_many(
        [
            {
                "_id": titan_id,
                "tenant_id": make_context_tenant_a().tenant_id,
                "email_normalized": "titan.member@example.test",
                "display_name": "Titan Member",
                "status": "active",
                "branch_id": BRANCH_X_ID,
                "member_code": "T-001",
            },
            {
                "_id": olympus_id,
                "tenant_id": make_context_tenant_b().tenant_id,
                "email_normalized": "olympus.member@example.test",
                "display_name": "Olympus Member",
                "status": "active",
                "branch_id": BRANCH_Y_ID,
                "member_code": "O-001",
            },
        ]
    )
    return {"titan_id": titan_id, "olympus_id": olympus_id}
