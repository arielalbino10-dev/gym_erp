from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from gym_erp_api.infrastructure.mongo.scoped_repository import TenantScopedRepository
from gym_erp_api.modules.organization.domain.branch import Branch
from gym_erp_api.modules.organization.domain.enums import BranchStatus
from gym_erp_api.modules.organization.domain.errors import (
    InvalidOrganizationFieldError,
    OrganizationEntityNotFoundError,
)
from gym_erp_api.modules.organization.infrastructure.mongo.operational_branch_repository import (
    OperationalBranchRepository,
)
from tests.support.tenant_fixtures import (
    BRANCH_X_ID,
    BRANCH_Y_ID,
    TENANT_A_ID,
    TENANT_B_ID,
    make_context_tenant_a,
    make_context_tenant_b,
)


@pytest.fixture
def mock_collection():
    collection = MagicMock()
    collection.find_one = AsyncMock(return_value=None)
    collection.insert_one = AsyncMock()
    collection.update_one = AsyncMock(return_value=MagicMock(matched_count=1))
    return collection


def _branch_repo(mock_collection, *, tenant_a: bool = True) -> OperationalBranchRepository:
    ctx = make_context_tenant_a() if tenant_a else make_context_tenant_b()
    scoped = TenantScopedRepository(mock_collection, ctx)
    return OperationalBranchRepository(scoped)


@pytest.mark.asyncio
async def test_insert_scoped_to_context_tenant(mock_collection):
    repo = _branch_repo(mock_collection)
    branch = Branch.create(
        tenant_id=TENANT_A_ID,
        name="Centro",
        branch_id=BRANCH_X_ID,
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )
    await repo.insert(branch)
    doc = mock_collection.insert_one.await_args[0][0]
    assert doc["tenant_id"] == TENANT_A_ID
    assert doc["branch_id"] == BRANCH_X_ID


@pytest.mark.asyncio
async def test_insert_rejects_cross_tenant_branch(mock_collection):
    repo = _branch_repo(mock_collection)
    branch = Branch.create(
        tenant_id=TENANT_B_ID,
        name="Other",
        branch_id=BRANCH_Y_ID,
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )
    with pytest.raises(InvalidOrganizationFieldError):
        await repo.insert(branch)
    mock_collection.insert_one.assert_not_called()


@pytest.mark.asyncio
async def test_get_by_id_applies_scoped_filter(mock_collection):
    moment = datetime(2026, 1, 1, tzinfo=UTC)
    doc = {
        "_id": BRANCH_X_ID,
        "branch_id": BRANCH_X_ID,
        "tenant_id": TENANT_A_ID,
        "name": "Centro",
        "status": "active",
        "timezone": "America/Mexico_City",
        "created_at": moment,
        "updated_at": moment,
    }
    mock_collection.find_one = AsyncMock(return_value=doc)
    repo = _branch_repo(mock_collection)
    branch = await repo.get_by_id(BRANCH_X_ID)
    assert branch is not None
    assert branch.branch_id == BRANCH_X_ID
    filter_arg = mock_collection.find_one.await_args[0][0]
    assert filter_arg["tenant_id"] == TENANT_A_ID
    assert filter_arg["branch_id"] == BRANCH_X_ID


@pytest.mark.asyncio
async def test_list_branches_tenant_b_context_differs(mock_collection):
    async def _async_iter(docs):
        for doc in docs:
            yield doc

    moment = datetime(2026, 2, 1, tzinfo=UTC)
    docs = [
        {
            "_id": BRANCH_Y_ID,
            "branch_id": BRANCH_Y_ID,
            "tenant_id": TENANT_B_ID,
            "name": "Olympus",
            "status": "active",
            "timezone": "America/Mexico_City",
            "created_at": moment,
            "updated_at": moment,
        }
    ]
    mock_collection.find = MagicMock(return_value=_async_iter(docs))
    repo = _branch_repo(mock_collection, tenant_a=False)
    branches = await repo.list_branches()
    assert len(branches) == 1
    filter_arg = mock_collection.find.call_args[0][0]
    assert filter_arg["tenant_id"] == TENANT_B_ID


@pytest.mark.asyncio
async def test_save_update_excludes_immutable_ids(mock_collection):
    repo = _branch_repo(mock_collection)
    branch = Branch.create(
        tenant_id=TENANT_A_ID,
        name="Centro",
        branch_id=BRANCH_X_ID,
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )
    await repo.save(branch)
    update_doc = mock_collection.update_one.await_args[0][1]["$set"]
    assert "tenant_id" not in update_doc
    assert "branch_id" not in update_doc
    assert update_doc["name"] == "Centro"


@pytest.mark.asyncio
async def test_save_not_found(mock_collection):
    mock_collection.update_one = AsyncMock(return_value=MagicMock(matched_count=0))
    repo = _branch_repo(mock_collection)
    branch = Branch.create(
        tenant_id=TENANT_A_ID,
        name="Centro",
        branch_id=BRANCH_X_ID,
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )
    with pytest.raises(OrganizationEntityNotFoundError):
        await repo.save(branch)


@pytest.mark.asyncio
async def test_get_by_id_hidden_when_branch_outside_allowed_scope(mock_collection):
    moment = datetime(2026, 1, 1, tzinfo=UTC)
    doc = {
        "_id": BRANCH_Y_ID,
        "branch_id": BRANCH_Y_ID,
        "tenant_id": TENANT_A_ID,
        "name": "Norte",
        "status": "active",
        "timezone": "America/Mexico_City",
        "created_at": moment,
        "updated_at": moment,
    }
    mock_collection.find_one = AsyncMock(return_value=doc)
    ctx = make_context_tenant_a(allowed_branch_ids=frozenset({BRANCH_X_ID}))
    scoped = TenantScopedRepository(mock_collection, ctx, branch_scoped=True)
    repo = OperationalBranchRepository(scoped)
    assert await repo.get_by_id(BRANCH_Y_ID) is None
    mock_collection.find_one.assert_not_called()


@pytest.mark.asyncio
async def test_insert_rejects_branch_outside_allowed_scope(mock_collection):
    ctx = make_context_tenant_a(allowed_branch_ids=frozenset({BRANCH_X_ID}))
    scoped = TenantScopedRepository(mock_collection, ctx, branch_scoped=True)
    repo = OperationalBranchRepository(scoped)
    branch = Branch.create(
        tenant_id=TENANT_A_ID,
        name="Norte",
        branch_id=BRANCH_Y_ID,
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )
    with pytest.raises(InvalidOrganizationFieldError):
        await repo.insert(branch)


def _branch_repo_branch_scoped(mock_collection) -> OperationalBranchRepository:
    ctx = make_context_tenant_a(allowed_branch_ids=frozenset({BRANCH_X_ID}))
    scoped = TenantScopedRepository(mock_collection, ctx, branch_scoped=True)
    return OperationalBranchRepository(scoped)


@pytest.mark.asyncio
async def test_get_by_id_branch_scoped_in_scope(mock_collection):
    moment = datetime(2026, 1, 1, tzinfo=UTC)
    doc = {
        "_id": BRANCH_X_ID,
        "branch_id": BRANCH_X_ID,
        "tenant_id": TENANT_A_ID,
        "name": "Centro",
        "status": "active",
        "timezone": "America/Mexico_City",
        "created_at": moment,
        "updated_at": moment,
    }
    mock_collection.find_one = AsyncMock(return_value=doc)
    repo = _branch_repo_branch_scoped(mock_collection)
    branch = await repo.get_by_id(BRANCH_X_ID)
    assert branch is not None
    filter_arg = mock_collection.find_one.await_args[0][0]
    assert filter_arg == {"tenant_id": TENANT_A_ID, "branch_id": BRANCH_X_ID}


@pytest.mark.asyncio
async def test_get_by_id_branch_scoped_out_of_scope_returns_none_without_query(mock_collection):
    mock_collection.find_one = AsyncMock(return_value=None)
    repo = _branch_repo_branch_scoped(mock_collection)
    assert await repo.get_by_id(BRANCH_Y_ID) is None
    mock_collection.find_one.assert_not_called()


@pytest.mark.asyncio
async def test_get_by_id_branch_scoped_with_session_same_filter(mock_collection):
    from unittest.mock import MagicMock

    from pymongo.asynchronous.client_session import AsyncClientSession

    mock_collection.find_one = AsyncMock(return_value=None)
    mock_collection.database = MagicMock()
    mock_client = MagicMock()
    mock_collection.database.client = mock_client
    session = MagicMock(spec=AsyncClientSession)
    session.has_ended = False
    session.in_transaction = True
    session.client = mock_client
    repo = _branch_repo_branch_scoped(mock_collection)
    await repo.get_by_id(BRANCH_X_ID, session=session)
    assert mock_collection.find_one.await_args.kwargs["session"] is session
    assert mock_collection.find_one.await_args[0][0]["tenant_id"] == TENANT_A_ID


@pytest.mark.asyncio
async def test_save_branch_scoped_uses_trusted_mutation_filter(mock_collection):
    repo = _branch_repo_branch_scoped(mock_collection)
    branch = Branch.create(
        tenant_id=TENANT_A_ID,
        name="Centro",
        branch_id=BRANCH_X_ID,
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )
    await repo.save(branch)
    filter_arg = mock_collection.update_one.await_args[0][0]
    assert filter_arg == {"tenant_id": TENANT_A_ID, "branch_id": BRANCH_X_ID}


@pytest.mark.asyncio
async def test_list_branches_branch_scoped_does_not_duplicate_branch_id_clause(mock_collection):
    async def _empty():
        if False:
            yield {}

    mock_collection.find = MagicMock(return_value=_empty())
    repo = _branch_repo_branch_scoped(mock_collection)
    await repo.list_branches()
    filter_arg = mock_collection.find.call_args[0][0]
    assert filter_arg["tenant_id"] == TENANT_A_ID
    assert filter_arg["branch_id"] == {"$in": [BRANCH_X_ID]}
    assert "status" not in filter_arg


@pytest.mark.asyncio
async def test_list_branches_with_status_filter(mock_collection):
    async def _empty():
        if False:
            yield {}

    mock_collection.find = MagicMock(return_value=_empty())
    repo = _branch_repo(mock_collection)
    await repo.list_branches(status=BranchStatus.INACTIVE)
    filter_arg = mock_collection.find.call_args[0][0]
    assert filter_arg["status"] == "inactive"
    assert filter_arg["tenant_id"] == TENANT_A_ID
