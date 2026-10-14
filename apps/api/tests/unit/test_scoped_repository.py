from unittest.mock import AsyncMock, MagicMock

import pytest

from gym_erp_api.infrastructure.mongo.scoped_repository import TenantScopedRepository
from gym_erp_api.shared_kernel.exceptions import ForbiddenMongoOperatorError, TenantScopeError
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
    collection.update_one = AsyncMock()
    collection.update_many = AsyncMock()
    collection.delete_one = AsyncMock()
    collection.delete_many = AsyncMock()
    collection.insert_one = AsyncMock()
    collection.count_documents = AsyncMock(return_value=0)
    collection.aggregate = AsyncMock(return_value=MagicMock())
    return collection


@pytest.mark.asyncio
async def test_find_one_merges_tenant_id(mock_collection):
    ctx = make_context_tenant_a()
    repo = TenantScopedRepository(mock_collection, ctx)
    await repo.find_one({"status": "active"})
    filter_arg = mock_collection.find_one.await_args[0][0]
    assert filter_arg["tenant_id"] == TENANT_A_ID
    assert filter_arg["status"] == "active"


@pytest.mark.asyncio
async def test_find_one_tenant_b_differs_from_a(mock_collection):
    ctx_b = make_context_tenant_b()
    repo = TenantScopedRepository(mock_collection, ctx_b)
    await repo.find_one({})
    filter_arg = mock_collection.find_one.await_args[0][0]
    assert filter_arg["tenant_id"] == TENANT_B_ID


@pytest.mark.asyncio
async def test_update_many_uses_scoped_filter(mock_collection):
    ctx = make_context_tenant_a()
    repo = TenantScopedRepository(mock_collection, ctx)
    await repo.update_many({"status": "old"}, {"$set": {"status": "new"}})
    filter_arg = mock_collection.update_many.await_args[0][0]
    assert filter_arg["tenant_id"] == TENANT_A_ID


@pytest.mark.asyncio
async def test_delete_many_scoped(mock_collection):
    ctx = make_context_tenant_a()
    repo = TenantScopedRepository(mock_collection, ctx)
    await repo.delete_many({"status": "archived"})
    filter_arg = mock_collection.delete_many.await_args[0][0]
    assert filter_arg["tenant_id"] == TENANT_A_ID


@pytest.mark.asyncio
async def test_insert_one_sets_tenant_id(mock_collection):
    ctx = make_context_tenant_a()
    repo = TenantScopedRepository(mock_collection, ctx)
    await repo.insert_one({"name": "item"})
    doc = mock_collection.insert_one.await_args[0][0]
    assert doc["tenant_id"] == TENANT_A_ID


@pytest.mark.asyncio
async def test_update_rejects_malicious_tenant_in_set(mock_collection):
    ctx = make_context_tenant_a()
    repo = TenantScopedRepository(mock_collection, ctx)
    with pytest.raises(TenantScopeError):
        await repo.update_one({}, {"$set": {"tenant_id": TENANT_B_ID}})


@pytest.mark.asyncio
async def test_update_rejects_branch_id_change_tenant_scoped(mock_collection):
    ctx = make_context_tenant_a()
    repo = TenantScopedRepository(mock_collection, ctx)
    with pytest.raises(TenantScopeError):
        await repo.update_one(
            {"status": "active"},
            {"$set": {"branch_id": BRANCH_Y_ID}},
        )
    mock_collection.update_one.assert_not_called()


@pytest.mark.asyncio
async def test_update_rejects_branch_id_change_branch_scoped(mock_collection):
    ctx = make_context_tenant_a(allowed_branch_ids=frozenset({BRANCH_X_ID}))
    repo = TenantScopedRepository(mock_collection, ctx, branch_scoped=True)
    with pytest.raises(TenantScopeError):
        await repo.update_one(
            {"status": "active"},
            {"$set": {"branch_id": BRANCH_Y_ID}},
        )
    mock_collection.update_one.assert_not_called()


@pytest.mark.asyncio
async def test_update_rejects_pipeline(mock_collection):
    ctx = make_context_tenant_a()
    repo = TenantScopedRepository(mock_collection, ctx)
    with pytest.raises(ForbiddenMongoOperatorError):
        await repo.update_one(
            {"status": "old"},
            [{"$set": {"status": "x"}}],  # type: ignore[arg-type]
        )


@pytest.mark.asyncio
async def test_branch_scoped_repository_restricts_branches(mock_collection):
    ctx = make_context_tenant_a(allowed_branch_ids=frozenset({BRANCH_X_ID}))
    repo = TenantScopedRepository(mock_collection, ctx, branch_scoped=True)
    await repo.find_one({})
    filter_arg = mock_collection.find_one.await_args[0][0]
    assert filter_arg["branch_id"] == {"$in": [BRANCH_X_ID]}


@pytest.mark.asyncio
async def test_aggregate_prepends_match(mock_collection):
    ctx = make_context_tenant_a()
    repo = TenantScopedRepository(mock_collection, ctx)
    await repo.aggregate([{"$sort": {"created_at": -1}}])
    pipeline = mock_collection.aggregate.await_args[0][0]
    assert pipeline[0]["$match"]["tenant_id"] == TENANT_A_ID


@pytest.mark.asyncio
async def test_rejects_tenant_id_in_user_filter(mock_collection):
    ctx = make_context_tenant_a()
    repo = TenantScopedRepository(mock_collection, ctx)
    with pytest.raises(TenantScopeError):
        await repo.find_one({"tenant_id": TENANT_B_ID})


@pytest.mark.asyncio
async def test_delete_many_rejects_empty_business_filter(mock_collection):
    ctx = make_context_tenant_a()
    repo = TenantScopedRepository(mock_collection, ctx)
    with pytest.raises(TenantScopeError):
        await repo.delete_many({})


@pytest.mark.asyncio
async def test_update_one_rejects_empty_business_filter(mock_collection):
    ctx = make_context_tenant_a()
    repo = TenantScopedRepository(mock_collection, ctx)
    with pytest.raises(TenantScopeError):
        await repo.update_one({}, {"$set": {"status": "x"}})


@pytest.mark.asyncio
async def test_update_rejects_array_filters(mock_collection):
    ctx = make_context_tenant_a()
    repo = TenantScopedRepository(mock_collection, ctx)
    with pytest.raises(ForbiddenMongoOperatorError):
        await repo.update_one(
            {"member_id": "990e8400-e29b-41d4-a716-446655440040"},
            {"$set": {"items.0.qty": 1}},
            array_filters=[{"elem.qty": 1}],
        )


@pytest.mark.asyncio
async def test_aggregate_rejects_allow_disk_use(mock_collection):
    ctx = make_context_tenant_a()
    repo = TenantScopedRepository(mock_collection, ctx)
    with pytest.raises(ForbiddenMongoOperatorError):
        await repo.aggregate([{"$limit": 1}], allowDiskUse=True)


@pytest.mark.asyncio
async def test_find_rejects_unknown_kwargs(mock_collection):
    ctx = make_context_tenant_a()
    repo = TenantScopedRepository(mock_collection, ctx)
    with pytest.raises(ForbiddenMongoOperatorError):
        repo.find({}, unknown_option=True)
