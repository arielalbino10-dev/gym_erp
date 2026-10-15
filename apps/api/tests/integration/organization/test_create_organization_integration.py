"""CreateOrganizationHandler contra MongoDB de prueba (H1-D.3.3.4).

Requiere GYM_ERP_RUN_INTEGRATION=1, usuario gym_erp_integration y bases *_test.
No ejecutar hasta autorización explícita (este módulo se prepara sin correr integración).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from gym_erp_api.infrastructure.mongo.mongo_unit_of_work import MongoUnitOfWork
from gym_erp_api.infrastructure.mongo.scoped_repository import TenantScopedRepository
from gym_erp_api.modules.organization.application.errors import IdempotencyPayloadConflictError
from gym_erp_api.modules.organization.application.idempotency_constants import (
    CREATE_ORGANIZATION_OPERATION,
)
from gym_erp_api.modules.organization.application.ports.idempotency_store import (
    IdempotencyRecordStatus,
)
from gym_erp_api.modules.organization.application.use_cases.create_organization_handler import (
    CreateOrganizationHandler,
)
from gym_erp_api.modules.organization.domain.branch import Branch
from gym_erp_api.modules.organization.domain.enums import BranchStatus, TenantStatus
from gym_erp_api.modules.organization.infrastructure.mongo.branch_document_mapper import (
    branch_to_document,
)
from gym_erp_api.modules.organization.infrastructure.mongo.idempotency_document_mapper import (
    build_idempotency_document_id,
)
from gym_erp_api.modules.organization.infrastructure.mongo.operational_branch_repository import (
    OperationalBranchRepository,
)
from gym_erp_api.modules.organization.infrastructure.mongo.platform_idempotency_repository import (
    PlatformIdempotencyRepository,
)
from gym_erp_api.modules.organization.infrastructure.mongo.platform_tenant_repository import (
    PlatformTenantRepository,
)
from gym_erp_api.shared_kernel.identifiers import new_uuid
from gym_erp_api.shared_kernel.tenant_context import TenantContext
from tests.support.create_organization_integration import (
    AbortCreateOrganizationProbe,
    AbortOnTenantSaveRepository,
    SessionCapture,
    SessionRecordingBranchRepositoryFactory,
    SessionRecordingIdempotencyRepository,
    SessionRecordingTenantRepository,
    build_create_organization_handler,
    execute_create_organization_with_in_progress_retry,
    integration_create_command,
)
from tests.support.integration_environment import (
    EXPECTED_OPERATIONAL_DB_IN_URI,
    EXPECTED_PLATFORM_DB,
    verify_integration_mongodb_identity,
)
from tests.support.tenant_fixtures import MEMBERSHIP_A_ID, USER_A_ID

pytestmark = [
    pytest.mark.integration,
    pytest.mark.organization_create_organization,
    pytest.mark.asyncio(loop_scope="session"),
]


async def test_create_organization_success_persists_tenant_branch_and_idempotency(
    create_organization_handler: CreateOrganizationHandler,
    organization_platform_tenant_repository: PlatformTenantRepository,
    organization_platform_idempotency_repository: PlatformIdempotencyRepository,
    organization_platform_idempotency_collection,
    organization_operational_branches_collection,
    organization_platform_tenants_collection,
):
    key = f"org-int-{new_uuid()[:8]}-success"
    cmd = integration_create_command(
        idempotency_key=key,
        created_by_user_id=USER_A_ID,
        commercial_email="success@integration.test",
    )

    result = await create_organization_handler.execute(cmd)

    assert result.idempotency_replayed is False
    assert result.tenant_status == TenantStatus.ACTIVE
    assert result.branch_status == BranchStatus.ACTIVE

    tenant = await organization_platform_tenant_repository.get_by_id(result.tenant_id)
    assert tenant is not None
    assert tenant.status == TenantStatus.ACTIVE

    scoped = TenantContext(
        tenant_id=result.tenant_id,
        user_id=USER_A_ID,
        membership_id=MEMBERSHIP_A_ID,
        allowed_branch_ids=frozenset({result.branch_id}),
    )
    branch_repo = OperationalBranchRepository(
        TenantScopedRepository(
            organization_operational_branches_collection,
            scoped,
            branch_scoped=True,
        )
    )
    branch = await branch_repo.get_by_id(result.branch_id)
    assert branch is not None
    assert branch.tenant_id == result.tenant_id

    doc_id = build_idempotency_document_id(CREATE_ORGANIZATION_OPERATION, key)
    raw = await organization_platform_idempotency_collection.find_one({"_id": doc_id})
    assert raw is not None
    assert raw["status"] == IdempotencyRecordStatus.COMPLETED.value
    record = await organization_platform_idempotency_repository.find_by_operation_and_key(
        CREATE_ORGANIZATION_OPERATION,
        key,
    )
    assert record is not None
    assert record.result is not None
    assert record.result.tenant_id == result.tenant_id
    assert record.result.branch_id == result.branch_id

    assert organization_platform_tenants_collection.database.name == EXPECTED_PLATFORM_DB
    assert organization_operational_branches_collection.database.name == (
        EXPECTED_OPERATIONAL_DB_IN_URI
    )


async def test_create_organization_replay_returns_same_ids(
    create_organization_handler: CreateOrganizationHandler,
):
    key = f"org-int-{new_uuid()[:8]}-replay"
    cmd = integration_create_command(idempotency_key=key, display_name="Replay Gym")

    first = await create_organization_handler.execute(cmd)
    second = await create_organization_handler.execute(cmd)

    assert first.idempotency_replayed is False
    assert second.idempotency_replayed is True
    assert second.tenant_id == first.tenant_id
    assert second.branch_id == first.branch_id


async def test_create_organization_same_key_different_payload_conflicts(
    create_organization_handler: CreateOrganizationHandler,
    organization_platform_tenants_collection,
    organization_platform_idempotency_collection,
    organization_operational_branches_collection,
):
    key = f"org-int-{new_uuid()[:8]}-conflict"
    await create_organization_handler.execute(
        integration_create_command(idempotency_key=key, display_name="Original")
    )

    with pytest.raises(IdempotencyPayloadConflictError):
        await create_organization_handler.execute(
            integration_create_command(idempotency_key=key, display_name="Distinto")
        )

    assert await organization_platform_tenants_collection.count_documents({}) == 1
    assert await organization_platform_idempotency_collection.count_documents({}) == 1
    assert await organization_operational_branches_collection.count_documents({}) == 1


async def test_create_organization_abort_leaves_no_confirmed_documents(
    organization_mongo_databases,
    organization_platform_tenant_repository: PlatformTenantRepository,
    organization_platform_idempotency_repository: PlatformIdempotencyRepository,
    organization_operational_branches_collection,
    organization_platform_tenants_collection,
    organization_platform_idempotency_collection,
):
    capture = SessionCapture()
    abort_tenant_repo = AbortOnTenantSaveRepository(
        organization_platform_tenant_repository,
        capture,
    )
    handler = build_create_organization_handler(
        tenant_repository=abort_tenant_repo,
        idempotency_repository=organization_platform_idempotency_repository,
        operational_branches_collection=organization_operational_branches_collection,
        mongo_databases=organization_mongo_databases,
    )
    key = f"org-int-{new_uuid()[:8]}-abort"
    cmd = integration_create_command(idempotency_key=key)

    with pytest.raises(AbortCreateOrganizationProbe):
        await handler.execute(cmd)

    assert await organization_platform_tenants_collection.count_documents({}) == 0
    assert await organization_platform_idempotency_collection.count_documents({}) == 0
    assert await organization_operational_branches_collection.count_documents({}) == 0


async def test_create_organization_concurrent_same_key_no_duplicate_tenants(
    organization_mongo_databases,
    organization_platform_tenant_repository: PlatformTenantRepository,
    organization_platform_idempotency_repository: PlatformIdempotencyRepository,
    organization_operational_branches_collection,
    organization_platform_tenants_collection,
    organization_platform_idempotency_collection,
):
    key = f"org-int-{new_uuid()[:8]}-concurrent"
    cmd = integration_create_command(idempotency_key=key, legal_name="Concurrent Legal SA")
    barrier = asyncio.Barrier(2)

    def make_handler() -> CreateOrganizationHandler:
        return build_create_organization_handler(
            tenant_repository=organization_platform_tenant_repository,
            idempotency_repository=organization_platform_idempotency_repository,
            operational_branches_collection=organization_operational_branches_collection,
            mongo_databases=organization_mongo_databases,
        )

    async def run_once() -> object:
        await barrier.wait()
        handler = make_handler()
        return await execute_create_organization_with_in_progress_retry(handler, cmd)

    results = await asyncio.gather(run_once(), run_once())

    tenant_ids = {results[0].tenant_id, results[1].tenant_id}
    assert len(tenant_ids) == 1
    assert await organization_platform_tenants_collection.count_documents({}) == 1
    assert await organization_operational_branches_collection.count_documents({}) == 1
    assert await organization_platform_idempotency_collection.count_documents({}) == 1
    assert sum(1 for item in results if item.idempotency_replayed) == 1


async def test_create_organization_tenant_branch_isolation_after_provision(
    create_organization_handler: CreateOrganizationHandler,
    organization_operational_branches_collection,
):
    key = f"org-int-{new_uuid()[:8]}-iso"
    cmd = integration_create_command(idempotency_key=key)
    result = await create_organization_handler.execute(cmd)

    foreign_branch = Branch.create(
        tenant_id=new_uuid(),
        name="Foreign Branch",
        branch_id=new_uuid(),
        now=datetime(2026, 6, 1, tzinfo=UTC),
    )
    await organization_operational_branches_collection.insert_one(
        branch_to_document(foreign_branch)
    )

    ctx = TenantContext(
        tenant_id=result.tenant_id,
        user_id=USER_A_ID,
        membership_id=MEMBERSHIP_A_ID,
        allowed_branch_ids=frozenset({result.branch_id}),
    )
    scoped_repo = OperationalBranchRepository(
        TenantScopedRepository(
            organization_operational_branches_collection,
            ctx,
            branch_scoped=True,
        )
    )
    assert await scoped_repo.get_by_id(result.branch_id) is not None
    assert await scoped_repo.get_by_id(foreign_branch.branch_id) is None
    listed = await scoped_repo.list_branches()
    assert len(listed) == 1
    assert listed[0].branch_id == result.branch_id


async def test_create_organization_documents_are_utc_aware(
    create_organization_handler: CreateOrganizationHandler,
    organization_platform_tenant_repository: PlatformTenantRepository,
    organization_operational_branches_collection,
):
    key = f"org-int-{new_uuid()[:8]}-utc"
    cmd = integration_create_command(idempotency_key=key)
    result = await create_organization_handler.execute(cmd)

    tenant = await organization_platform_tenant_repository.get_by_id(result.tenant_id)
    assert tenant is not None
    assert tenant.created_at.tzinfo is not None
    assert result.created_at.tzinfo is not None

    ctx = TenantContext(
        tenant_id=result.tenant_id,
        user_id=USER_A_ID,
        membership_id=MEMBERSHIP_A_ID,
        allowed_branch_ids=frozenset({result.branch_id}),
    )
    branch_repo = OperationalBranchRepository(
        TenantScopedRepository(
            organization_operational_branches_collection,
            ctx,
            branch_scoped=True,
        )
    )
    branch = await branch_repo.get_by_id(result.branch_id)
    assert branch is not None
    assert branch.created_at.tzinfo is not None


async def test_create_organization_handler_passes_same_uow_session_to_repositories(
    organization_mongo_databases,
    organization_platform_tenant_repository: PlatformTenantRepository,
    organization_platform_idempotency_repository: PlatformIdempotencyRepository,
    organization_operational_branches_collection,
):
    capture = SessionCapture()
    recording_tenant = SessionRecordingTenantRepository(
        organization_platform_tenant_repository,
        capture,
    )
    recording_idempotency = SessionRecordingIdempotencyRepository(
        organization_platform_idempotency_repository,
        capture,
    )
    branch_factory = SessionRecordingBranchRepositoryFactory(
        organization_operational_branches_collection,
        capture,
    )
    handler = CreateOrganizationHandler(
        idempotency_store=recording_idempotency,
        tenant_repository=recording_tenant,
        branch_repository_factory=branch_factory,
        unit_of_work_factory=lambda: MongoUnitOfWork(organization_mongo_databases),
    )
    key = f"org-int-{new_uuid()[:8]}-session"
    await handler.execute(integration_create_command(idempotency_key=key))

    txn_sessions = capture.session_object_ids
    assert len(txn_sessions) >= 4
    assert len(set(txn_sessions)) == 1


async def test_create_organization_integration_environment_verified_before_writes(
    organization_integration_state,
    organization_mongo_client,
):
    assert organization_integration_state.security_verified is True
    assert organization_integration_state.platform_db == EXPECTED_PLATFORM_DB
    assert organization_integration_state.operational_db == EXPECTED_OPERATIONAL_DB_IN_URI
    await verify_integration_mongodb_identity(organization_mongo_client)
