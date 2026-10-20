"""Fixtures de integración identity (solo gym_platform_test, colecciones efímeras)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import pytest
import pytest_asyncio
from pymongo import AsyncMongoClient

from gym_erp_api.infrastructure.mongo.database import mongo_client_options
from gym_erp_api.modules.identity.infrastructure.mongo.mongo_auth_session_repository import (
    MongoAuthSessionRepository,
)
from gym_erp_api.modules.identity.infrastructure.mongo.mongo_credential_repository import (
    MongoCredentialRepository,
)
from gym_erp_api.modules.identity.infrastructure.mongo.mongo_identity_repository import (
    MongoIdentityRepository,
)
from gym_erp_api.modules.identity.infrastructure.mongo.mongo_platform_mfa_repositories import (
    MongoPlatformMfaChallengeRepository,
    MongoPlatformMfaSessionAuthorizationRepository,
    MongoPlatformMfaStepConsumptionRepository,
    MongoPlatformTotpEnrollmentRepository,
)
from gym_erp_api.modules.identity.infrastructure.mongo.platform_index_specs import (
    ensure_identity_platform_indexes,
)
from gym_erp_api.modules.identity.infrastructure.mongo.platform_mfa_index_specs import (
    ensure_platform_mfa_indexes,
)
from tests.support.integration_environment import (
    EXPECTED_PLATFORM_DB,
    IDENTITY_AUTH_SESSIONS_PREFIX,
    IDENTITY_MFA_AUTHZ_PREFIX,
    IDENTITY_MFA_CHALLENGES_PREFIX,
    IDENTITY_MFA_STEPS_PREFIX,
    IDENTITY_MFA_TOTP_PREFIX,
    IDENTITY_USER_CREDENTIALS_PREFIX,
    IDENTITY_USER_IDENTITIES_PREFIX,
    assert_organization_ephemeral_collection_safe_for_teardown,
    generate_identity_auth_sessions_collection_name,
    generate_identity_mfa_authz_collection_name,
    generate_identity_mfa_challenges_collection_name,
    generate_identity_mfa_steps_collection_name,
    generate_identity_mfa_totp_collection_name,
    generate_identity_user_credentials_collection_name,
    generate_identity_user_identities_collection_name,
    validate_integration_environment,
    verify_integration_mongodb_identity,
)


async def _ensure_ephemeral_collection(db: Any, name: str) -> None:
    existing = await db.list_collection_names(filter={"name": name})
    if name not in existing:
        await db.create_collection(name)


@dataclass
class IdentityIntegrationState:
    security_verified: bool = False
    identities_collection_name: str | None = None
    credentials_collection_name: str | None = None
    sessions_collection_name: str | None = None
    mfa_totp_collection_name: str | None = None
    mfa_challenges_collection_name: str | None = None
    mfa_steps_collection_name: str | None = None
    mfa_authz_collection_name: str | None = None
    teardown_enabled: bool = False
    extra: dict = field(default_factory=dict)


@pytest.fixture(scope="session")
def identity_integration_state() -> IdentityIntegrationState:
    return IdentityIntegrationState()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def identity_mongo_client(
    integration_mongodb_uri: str,
    identity_integration_state: IdentityIntegrationState,
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

    identity_integration_state.security_verified = True
    identity_integration_state.teardown_enabled = True
    yield client
    await client.close()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def identity_user_identities_collection(
    identity_mongo_client: Any,
    identity_integration_state: IdentityIntegrationState,
) -> Any:
    if not identity_integration_state.security_verified:
        pytest.fail("Controles de seguridad no verificados.")

    name = generate_identity_user_identities_collection_name()
    identity_integration_state.identities_collection_name = name
    db = identity_mongo_client[EXPECTED_PLATFORM_DB]
    await _ensure_ephemeral_collection(db, name)
    collection = db[name]
    yield collection
    if not identity_integration_state.teardown_enabled:
        return
    registered = identity_integration_state.identities_collection_name
    if not registered:
        return
    assert_organization_ephemeral_collection_safe_for_teardown(
        collection.name,
        expected_name=registered,
        database_name=collection.database.name,
        collection_prefix=IDENTITY_USER_IDENTITIES_PREFIX,
        expected_database=EXPECTED_PLATFORM_DB,
    )
    await collection.drop()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def identity_user_credentials_collection(
    identity_mongo_client: Any,
    identity_integration_state: IdentityIntegrationState,
) -> Any:
    if not identity_integration_state.security_verified:
        pytest.fail("Controles de seguridad no verificados.")

    name = generate_identity_user_credentials_collection_name()
    identity_integration_state.credentials_collection_name = name
    db = identity_mongo_client[EXPECTED_PLATFORM_DB]
    await _ensure_ephemeral_collection(db, name)
    collection = db[name]
    yield collection
    if not identity_integration_state.teardown_enabled:
        return
    registered = identity_integration_state.credentials_collection_name
    if not registered:
        return
    assert_organization_ephemeral_collection_safe_for_teardown(
        collection.name,
        expected_name=registered,
        database_name=collection.database.name,
        collection_prefix=IDENTITY_USER_CREDENTIALS_PREFIX,
        expected_database=EXPECTED_PLATFORM_DB,
    )
    await collection.drop()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def identity_auth_sessions_collection(
    identity_mongo_client: Any,
    identity_integration_state: IdentityIntegrationState,
) -> Any:
    if not identity_integration_state.security_verified:
        pytest.fail("Controles de seguridad no verificados.")

    name = generate_identity_auth_sessions_collection_name()
    identity_integration_state.sessions_collection_name = name
    db = identity_mongo_client[EXPECTED_PLATFORM_DB]
    await _ensure_ephemeral_collection(db, name)
    collection = db[name]
    yield collection
    if not identity_integration_state.teardown_enabled:
        return
    registered = identity_integration_state.sessions_collection_name
    if not registered:
        return
    assert_organization_ephemeral_collection_safe_for_teardown(
        collection.name,
        expected_name=registered,
        database_name=collection.database.name,
        collection_prefix=IDENTITY_AUTH_SESSIONS_PREFIX,
        expected_database=EXPECTED_PLATFORM_DB,
    )
    await collection.drop()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def identity_mfa_totp_collection(
    identity_mongo_client: Any,
    identity_integration_state: IdentityIntegrationState,
) -> Any:
    if not identity_integration_state.security_verified:
        pytest.fail("Controles de seguridad no verificados.")
    name = generate_identity_mfa_totp_collection_name()
    identity_integration_state.mfa_totp_collection_name = name
    db = identity_mongo_client[EXPECTED_PLATFORM_DB]
    await _ensure_ephemeral_collection(db, name)
    collection = db[name]
    yield collection
    if not identity_integration_state.teardown_enabled:
        return
    registered = identity_integration_state.mfa_totp_collection_name
    if not registered:
        return
    assert_organization_ephemeral_collection_safe_for_teardown(
        collection.name,
        expected_name=registered,
        database_name=collection.database.name,
        collection_prefix=IDENTITY_MFA_TOTP_PREFIX,
        expected_database=EXPECTED_PLATFORM_DB,
    )
    await collection.drop()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def identity_mfa_challenges_collection(
    identity_mongo_client: Any,
    identity_integration_state: IdentityIntegrationState,
) -> Any:
    if not identity_integration_state.security_verified:
        pytest.fail("Controles de seguridad no verificados.")
    name = generate_identity_mfa_challenges_collection_name()
    identity_integration_state.mfa_challenges_collection_name = name
    db = identity_mongo_client[EXPECTED_PLATFORM_DB]
    await _ensure_ephemeral_collection(db, name)
    collection = db[name]
    yield collection
    if not identity_integration_state.teardown_enabled:
        return
    registered = identity_integration_state.mfa_challenges_collection_name
    if not registered:
        return
    assert_organization_ephemeral_collection_safe_for_teardown(
        collection.name,
        expected_name=registered,
        database_name=collection.database.name,
        collection_prefix=IDENTITY_MFA_CHALLENGES_PREFIX,
        expected_database=EXPECTED_PLATFORM_DB,
    )
    await collection.drop()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def identity_mfa_steps_collection(
    identity_mongo_client: Any,
    identity_integration_state: IdentityIntegrationState,
) -> Any:
    if not identity_integration_state.security_verified:
        pytest.fail("Controles de seguridad no verificados.")
    name = generate_identity_mfa_steps_collection_name()
    identity_integration_state.mfa_steps_collection_name = name
    db = identity_mongo_client[EXPECTED_PLATFORM_DB]
    await _ensure_ephemeral_collection(db, name)
    collection = db[name]
    yield collection
    if not identity_integration_state.teardown_enabled:
        return
    registered = identity_integration_state.mfa_steps_collection_name
    if not registered:
        return
    assert_organization_ephemeral_collection_safe_for_teardown(
        collection.name,
        expected_name=registered,
        database_name=collection.database.name,
        collection_prefix=IDENTITY_MFA_STEPS_PREFIX,
        expected_database=EXPECTED_PLATFORM_DB,
    )
    await collection.drop()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def identity_mfa_authz_collection(
    identity_mongo_client: Any,
    identity_integration_state: IdentityIntegrationState,
) -> Any:
    if not identity_integration_state.security_verified:
        pytest.fail("Controles de seguridad no verificados.")
    name = generate_identity_mfa_authz_collection_name()
    identity_integration_state.mfa_authz_collection_name = name
    db = identity_mongo_client[EXPECTED_PLATFORM_DB]
    await _ensure_ephemeral_collection(db, name)
    collection = db[name]
    yield collection
    if not identity_integration_state.teardown_enabled:
        return
    registered = identity_integration_state.mfa_authz_collection_name
    if not registered:
        return
    assert_organization_ephemeral_collection_safe_for_teardown(
        collection.name,
        expected_name=registered,
        database_name=collection.database.name,
        collection_prefix=IDENTITY_MFA_AUTHZ_PREFIX,
        expected_database=EXPECTED_PLATFORM_DB,
    )
    await collection.drop()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def identity_platform_indexes(
    identity_user_identities_collection: Any,
    identity_user_credentials_collection: Any,
    identity_auth_sessions_collection: Any,
) -> None:
    await ensure_identity_platform_indexes(
        identities=identity_user_identities_collection,
        credentials=identity_user_credentials_collection,
        sessions=identity_auth_sessions_collection,
    )


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def identity_mfa_indexes(
    identity_mfa_totp_collection: Any,
    identity_mfa_challenges_collection: Any,
    identity_mfa_steps_collection: Any,
    identity_mfa_authz_collection: Any,
) -> None:
    await ensure_platform_mfa_indexes(
        totp=identity_mfa_totp_collection,
        challenges=identity_mfa_challenges_collection,
        steps=identity_mfa_steps_collection,
        authorizations=identity_mfa_authz_collection,
    )


@pytest_asyncio.fixture(autouse=True, loop_scope="session")
async def reset_identity_ephemeral_collections(
    identity_user_identities_collection: Any,
    identity_user_credentials_collection: Any,
    identity_auth_sessions_collection: Any,
    identity_platform_indexes: None,
    identity_mfa_totp_collection: Any,
    identity_mfa_challenges_collection: Any,
    identity_mfa_steps_collection: Any,
    identity_mfa_authz_collection: Any,
    identity_mfa_indexes: None,
) -> Any:
    await identity_user_identities_collection.delete_many({})
    await identity_user_credentials_collection.delete_many({})
    await identity_auth_sessions_collection.delete_many({})
    await identity_mfa_totp_collection.delete_many({})
    await identity_mfa_challenges_collection.delete_many({})
    await identity_mfa_steps_collection.delete_many({})
    await identity_mfa_authz_collection.delete_many({})
    yield
    await identity_user_identities_collection.delete_many({})
    await identity_user_credentials_collection.delete_many({})
    await identity_auth_sessions_collection.delete_many({})
    await identity_mfa_totp_collection.delete_many({})
    await identity_mfa_challenges_collection.delete_many({})
    await identity_mfa_steps_collection.delete_many({})
    await identity_mfa_authz_collection.delete_many({})


@pytest.fixture
def auth_http_repos(
    mongo_identity_repository,
    mongo_credential_repository,
    mongo_auth_session_repository,
    mongo_platform_totp_enrollment_repository,
    mongo_platform_mfa_challenge_repository,
    mongo_platform_mfa_step_repository,
    mongo_platform_mfa_session_authorization_repository,
):
    return {
        "identity": mongo_identity_repository,
        "credential": mongo_credential_repository,
        "session": mongo_auth_session_repository,
        "totp": mongo_platform_totp_enrollment_repository,
        "challenge": mongo_platform_mfa_challenge_repository,
        "step": mongo_platform_mfa_step_repository,
        "authz": mongo_platform_mfa_session_authorization_repository,
    }


@pytest.fixture
def mongo_identity_repository(
    identity_user_identities_collection: Any,
) -> MongoIdentityRepository:
    return MongoIdentityRepository(identity_user_identities_collection)


@pytest.fixture
def mongo_credential_repository(
    identity_user_credentials_collection: Any,
) -> MongoCredentialRepository:
    return MongoCredentialRepository(identity_user_credentials_collection)


@pytest.fixture
def mongo_auth_session_repository(
    identity_auth_sessions_collection: Any,
) -> MongoAuthSessionRepository:
    return MongoAuthSessionRepository(identity_auth_sessions_collection)


@pytest.fixture
def mongo_platform_totp_enrollment_repository(
    identity_mfa_totp_collection: Any,
) -> MongoPlatformTotpEnrollmentRepository:
    return MongoPlatformTotpEnrollmentRepository(identity_mfa_totp_collection)


@pytest.fixture
def mongo_platform_mfa_challenge_repository(
    identity_mfa_challenges_collection: Any,
) -> MongoPlatformMfaChallengeRepository:
    return MongoPlatformMfaChallengeRepository(identity_mfa_challenges_collection)


@pytest.fixture
def mongo_platform_mfa_step_repository(
    identity_mfa_steps_collection: Any,
) -> MongoPlatformMfaStepConsumptionRepository:
    return MongoPlatformMfaStepConsumptionRepository(identity_mfa_steps_collection)


@pytest.fixture
def mongo_platform_mfa_session_authorization_repository(
    identity_mfa_authz_collection: Any,
) -> MongoPlatformMfaSessionAuthorizationRepository:
    return MongoPlatformMfaSessionAuthorizationRepository(identity_mfa_authz_collection)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if "/integration/identity/" in item.nodeid.replace("\\", "/"):
            item.add_marker(pytest.mark.asyncio(loop_scope="session"))
            # No usar @pytest.mark.asyncio en funciones: anula loop_scope=session y rompe
            # AsyncMongoClient (session) con el loop por prueba.
