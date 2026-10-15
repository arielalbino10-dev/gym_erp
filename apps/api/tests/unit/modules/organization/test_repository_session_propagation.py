from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from pymongo.asynchronous.client_session import AsyncClientSession

from gym_erp_api.infrastructure.mongo.scoped_repository import TenantScopedRepository
from gym_erp_api.infrastructure.mongo.uow_errors import InvalidMongoSessionError
from gym_erp_api.modules.organization.domain.branch import Branch
from gym_erp_api.modules.organization.domain.tenant import Tenant
from gym_erp_api.modules.organization.infrastructure.mongo.operational_branch_repository import (
    OperationalBranchRepository,
)
from gym_erp_api.modules.organization.infrastructure.mongo.platform_tenant_repository import (
    PlatformTenantRepository,
)
from tests.support.tenant_fixtures import (
    BRANCH_X_ID,
    BRANCH_Y_ID,
    TENANT_A_ID,
    make_context_tenant_a,
)


@pytest.fixture
def mongo_client():
    return MagicMock()


@pytest.fixture
def shared_session(mongo_client):
    session = MagicMock(spec=AsyncClientSession)
    session.has_ended = False
    session.in_transaction = True
    session.client = mongo_client
    return session


def _bind_collection_client(collection: MagicMock, mongo_client: MagicMock) -> None:
    collection.database = MagicMock()
    collection.database.client = mongo_client


@pytest.mark.asyncio
async def test_platform_and_branch_repos_receive_same_session(shared_session, mongo_client):
    platform_collection = MagicMock()
    platform_collection.insert_one = AsyncMock()
    branch_collection = MagicMock()
    branch_collection.insert_one = AsyncMock()
    _bind_collection_client(platform_collection, mongo_client)
    _bind_collection_client(branch_collection, mongo_client)

    platform_repo = PlatformTenantRepository(platform_collection)
    scoped = TenantScopedRepository(branch_collection, make_context_tenant_a())
    branch_repo = OperationalBranchRepository(scoped)

    moment = datetime(2026, 1, 1, tzinfo=UTC)
    tenant = Tenant.create(
        legal_name="L",
        display_name="D",
        tenant_id=TENANT_A_ID,
        now=moment,
    )
    branch = Branch.create(
        tenant_id=TENANT_A_ID,
        name="Centro",
        branch_id=BRANCH_X_ID,
        now=moment,
    )

    await platform_repo.insert(tenant, session=shared_session)
    await branch_repo.insert(branch, session=shared_session)

    assert platform_collection.insert_one.await_args.kwargs["session"] is shared_session
    assert branch_collection.insert_one.await_args.kwargs["session"] is shared_session


@pytest.mark.asyncio
async def test_branch_get_by_id_keeps_tenant_filter_with_session(shared_session, mongo_client):
    branch_collection = MagicMock()
    branch_collection.find_one = AsyncMock(return_value=None)
    _bind_collection_client(branch_collection, mongo_client)
    scoped = TenantScopedRepository(branch_collection, make_context_tenant_a())
    repo = OperationalBranchRepository(scoped)

    await repo.get_by_id(BRANCH_X_ID, session=shared_session)

    filter_doc = branch_collection.find_one.await_args[0][0]
    assert filter_doc["tenant_id"] == TENANT_A_ID
    assert branch_collection.find_one.await_args.kwargs["session"] is shared_session


@pytest.mark.asyncio
async def test_branch_insert_respects_allowed_branch_ids_with_session(shared_session, mongo_client):
    branch_collection = MagicMock()
    branch_collection.insert_one = AsyncMock()
    _bind_collection_client(branch_collection, mongo_client)
    ctx = make_context_tenant_a(allowed_branch_ids=frozenset({BRANCH_X_ID}))
    scoped = TenantScopedRepository(branch_collection, ctx, branch_scoped=True)
    repo = OperationalBranchRepository(scoped)
    branch = Branch.create(
        tenant_id=TENANT_A_ID,
        name="Norte",
        branch_id=BRANCH_Y_ID,
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )

    from gym_erp_api.modules.organization.domain.errors import InvalidOrganizationFieldError

    with pytest.raises(InvalidOrganizationFieldError):
        await repo.insert(branch, session=shared_session)
    branch_collection.insert_one.assert_not_called()


@pytest.mark.asyncio
async def test_platform_repo_rejects_invalid_session():
    collection = MagicMock()
    collection.insert_one = AsyncMock()
    repo = PlatformTenantRepository(collection)
    tenant = Tenant.create(
        legal_name="L",
        display_name="D",
        tenant_id=TENANT_A_ID,
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )
    with pytest.raises(InvalidMongoSessionError):
        await repo.insert(tenant, session=object())


@pytest.mark.asyncio
async def test_scoped_repo_rejects_invalid_session():
    collection = MagicMock()
    scoped = TenantScopedRepository(collection, make_context_tenant_a())
    with pytest.raises(InvalidMongoSessionError):
        await scoped.find_one({}, session="not-a-session")
