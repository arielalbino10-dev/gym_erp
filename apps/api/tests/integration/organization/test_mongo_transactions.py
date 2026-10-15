"""Transacciones MongoUnitOfWork platform + operational (H1-D.3.2.1).

Requiere GYM_ERP_RUN_INTEGRATION=1, URI de gym_erp_integration y bases *_test.
No ejecutar contra gym_platform / gym_operational operativas.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from gym_erp_api.infrastructure.mongo.mongo_databases import MongoDatabases
from gym_erp_api.infrastructure.mongo.mongo_unit_of_work import MongoUnitOfWork
from gym_erp_api.infrastructure.mongo.uow_errors import MongoUnitOfWorkInactiveError
from gym_erp_api.modules.organization.domain.branch import Branch
from gym_erp_api.modules.organization.domain.enums import TenantStatus
from gym_erp_api.modules.organization.domain.errors import InvalidOrganizationFieldError
from gym_erp_api.modules.organization.domain.tenant import Tenant
from gym_erp_api.modules.organization.infrastructure.mongo.branch_document_mapper import (
    branch_to_document,
)
from gym_erp_api.modules.organization.infrastructure.mongo.operational_branch_repository import (
    OperationalBranchRepository,
)
from gym_erp_api.modules.organization.infrastructure.mongo.platform_tenant_repository import (
    PlatformTenantRepository,
)
from gym_erp_api.shared_kernel.identifiers import new_uuid
from tests.support.tenant_fixtures import (
    BRANCH_X_ID,
    BRANCH_Y_ID,
    TENANT_A_ID,
    TENANT_B_ID,
    USER_A_ID,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.organization_transactions,
    pytest.mark.asyncio(loop_scope="session"),
]


class _AbortTransactionProbe(Exception):
    """Señal controlada para provocar abort sin simular fallos de red."""


def _active_tenant(*, tenant_id: str, moment: datetime) -> Tenant:
    return Tenant.create(
        legal_name="Txn Legal SA",
        display_name="Txn Gym",
        tenant_id=tenant_id,
        commercial_email=f"txn-{tenant_id[:8]}@integration.test",
        created_by_user_id=USER_A_ID,
        now=moment,
    ).transition_status(TenantStatus.ACTIVE, now=moment)


def _branch_for_tenant_a(*, moment: datetime, branch_id: str | None = None) -> Branch:
    return Branch.create(
        tenant_id=TENANT_A_ID,
        name="Txn Sucursal",
        branch_id=branch_id,
        code="txn-centro",
        created_by_user_id=USER_A_ID,
        now=moment,
    )


async def test_uow_commit_persists_tenant_and_branch_across_databases(
    organization_mongo_databases: MongoDatabases,
    organization_platform_tenant_repository: PlatformTenantRepository,
    organization_branch_repository: OperationalBranchRepository,
):
    moment = datetime(2026, 5, 1, 16, 0, tzinfo=UTC)
    tenant_id = new_uuid()
    tenant = _active_tenant(tenant_id=tenant_id, moment=moment)
    branch = _branch_for_tenant_a(moment=moment)

    platform_repo = organization_platform_tenant_repository
    branch_repo = organization_branch_repository

    async with MongoUnitOfWork(organization_mongo_databases) as uow:
        session = uow.session
        assert session.in_transaction is True
        await platform_repo.insert(tenant, session=session)
        await branch_repo.insert(branch, session=session)
        listed = await branch_repo.list_branches(session=session)
        assert len(listed) == 1
        assert listed[0].branch_id == branch.branch_id

    assert await platform_repo.exists_by_id(tenant_id) is True
    restored_tenant = await platform_repo.get_by_id(tenant_id)
    assert restored_tenant is not None
    assert restored_tenant.created_at.tzinfo is not None
    assert restored_tenant.created_at.astimezone(UTC) == moment

    restored_branch = await branch_repo.get_by_id(branch.branch_id)
    assert restored_branch is not None
    assert restored_branch.tenant_id == TENANT_A_ID
    assert restored_branch.created_at.tzinfo is not None
    assert restored_branch.created_at.astimezone(UTC) == moment


async def test_uow_same_session_object_used_for_platform_and_operational(
    organization_mongo_databases: MongoDatabases,
    organization_platform_tenant_repository: PlatformTenantRepository,
    organization_branch_repository: OperationalBranchRepository,
):
    moment = datetime(2026, 5, 2, 10, 0, tzinfo=UTC)
    tenant_id = new_uuid()
    tenant = _active_tenant(tenant_id=tenant_id, moment=moment)
    branch = _branch_for_tenant_a(moment=moment)
    session_ids: list[int] = []

    async with MongoUnitOfWork(organization_mongo_databases) as uow:
        session = uow.session
        session_ids.append(id(session))
        await organization_platform_tenant_repository.insert(tenant, session=session)
        session_ids.append(id(session))
        await organization_branch_repository.insert(branch, session=session)
        session_ids.append(id(session))
        assert session.in_transaction is True
        assert len(set(session_ids)) == 1

    with pytest.raises(MongoUnitOfWorkInactiveError):
        _ = uow.session

    assert await organization_platform_tenant_repository.exists_by_id(tenant_id) is True
    assert await organization_branch_repository.get_by_id(branch.branch_id) is not None


async def test_uow_abort_after_tenant_before_branch_leaves_nothing_persisted(
    organization_mongo_databases: MongoDatabases,
    organization_platform_tenant_repository: PlatformTenantRepository,
    organization_branch_repository: OperationalBranchRepository,
):
    moment = datetime(2026, 5, 3, 11, 0, tzinfo=UTC)
    tenant_id = new_uuid()
    tenant = _active_tenant(tenant_id=tenant_id, moment=moment)
    branch = _branch_for_tenant_a(moment=moment)

    with pytest.raises(_AbortTransactionProbe):
        async with MongoUnitOfWork(organization_mongo_databases) as uow:
            await organization_platform_tenant_repository.insert(tenant, session=uow.session)
            raise _AbortTransactionProbe("before branch insert")

    assert await organization_platform_tenant_repository.exists_by_id(tenant_id) is False
    assert await organization_branch_repository.get_by_id(branch.branch_id) is None


async def test_uow_abort_after_both_inserts_before_commit_leaves_nothing_persisted(
    organization_mongo_databases: MongoDatabases,
    organization_platform_tenant_repository: PlatformTenantRepository,
    organization_branch_repository: OperationalBranchRepository,
):
    moment = datetime(2026, 5, 4, 12, 0, tzinfo=UTC)
    tenant_id = new_uuid()
    tenant = _active_tenant(tenant_id=tenant_id, moment=moment)
    branch = _branch_for_tenant_a(moment=moment)

    with pytest.raises(_AbortTransactionProbe):
        async with MongoUnitOfWork(organization_mongo_databases) as uow:
            await organization_platform_tenant_repository.insert(tenant, session=uow.session)
            await organization_branch_repository.insert(branch, session=uow.session)
            raise _AbortTransactionProbe("before commit")

    assert await organization_platform_tenant_repository.exists_by_id(tenant_id) is False
    assert await organization_branch_repository.get_by_id(branch.branch_id) is None


async def test_branch_allowed_scope_enforced_inside_transaction(
    organization_mongo_databases: MongoDatabases,
    organization_branch_repository_branch_scoped: OperationalBranchRepository,
):
    moment = datetime(2026, 5, 5, 13, 0, tzinfo=UTC)
    allowed_branch = _branch_for_tenant_a(moment=moment, branch_id=BRANCH_X_ID)
    disallowed_branch = _branch_for_tenant_a(moment=moment, branch_id=BRANCH_Y_ID)
    repo = organization_branch_repository_branch_scoped

    async with MongoUnitOfWork(organization_mongo_databases) as uow:
        await repo.insert(allowed_branch, session=uow.session)
        with pytest.raises(InvalidOrganizationFieldError):
            await repo.insert(disallowed_branch, session=uow.session)
        assert await repo.get_by_id(BRANCH_Y_ID, session=uow.session) is None
        visible = await repo.get_by_id(BRANCH_X_ID, session=uow.session)
        assert visible is not None
        assert visible.branch_id == BRANCH_X_ID

    assert await repo.get_by_id(BRANCH_X_ID) is not None
    assert await repo.get_by_id(BRANCH_Y_ID) is None


async def test_branch_tenant_mismatch_rejected_with_session(
    organization_mongo_databases: MongoDatabases,
    organization_branch_repository: OperationalBranchRepository,
    organization_operational_branches_collection,
):
    moment = datetime(2026, 5, 6, 14, 0, tzinfo=UTC)
    cross_tenant = replace(
        _branch_for_tenant_a(moment=moment),
        tenant_id=TENANT_B_ID,
    )

    async with MongoUnitOfWork(organization_mongo_databases) as uow:
        with pytest.raises(InvalidOrganizationFieldError):
            await organization_branch_repository.insert(cross_tenant, session=uow.session)

    assert await organization_operational_branches_collection.count_documents({}) == 0


async def test_branch_reads_hide_other_tenant_documents_inside_transaction(
    organization_mongo_databases: MongoDatabases,
    organization_branch_repository: OperationalBranchRepository,
    organization_operational_branches_collection,
):
    moment = datetime(2026, 5, 7, 15, 0, tzinfo=UTC)
    tenant_b_branch = Branch.create(
        tenant_id=TENANT_B_ID,
        name="Olympus Seed",
        branch_id=BRANCH_Y_ID,
        now=moment,
    )
    await organization_operational_branches_collection.insert_one(
        branch_to_document(tenant_b_branch)
    )

    async with MongoUnitOfWork(organization_mongo_databases) as uow:
        assert (
            await organization_branch_repository.get_by_id(BRANCH_Y_ID, session=uow.session) is None
        )
        listed = await organization_branch_repository.list_branches(session=uow.session)
        assert listed == []
        assert all(item.tenant_id == TENANT_A_ID for item in listed)
