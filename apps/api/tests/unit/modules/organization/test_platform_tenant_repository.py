from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from gym_erp_api.modules.organization.domain.errors import OrganizationEntityNotFoundError
from gym_erp_api.modules.organization.domain.tenant import Tenant
from gym_erp_api.modules.organization.infrastructure.mongo.platform_tenant_repository import (
    PlatformTenantRepository,
)
from tests.support.tenant_fixtures import TENANT_A_ID


@pytest.fixture
def tenant_collection():
    collection = MagicMock()
    collection.insert_one = AsyncMock()
    collection.find_one = AsyncMock(return_value=None)
    collection.count_documents = AsyncMock(return_value=0)
    collection.update_one = AsyncMock()
    return collection


@pytest.mark.asyncio
async def test_insert_persists_platform_document(tenant_collection):
    repo = PlatformTenantRepository(tenant_collection)
    tenant = Tenant.create(
        legal_name="L",
        display_name="D",
        tenant_id=TENANT_A_ID,
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )
    await repo.insert(tenant)
    doc = tenant_collection.insert_one.await_args[0][0]
    assert doc["_id"] == TENANT_A_ID
    assert doc["legal_name"] == "L"


@pytest.mark.asyncio
async def test_get_by_id_returns_none_when_missing(tenant_collection):
    repo = PlatformTenantRepository(tenant_collection)
    assert await repo.get_by_id(TENANT_A_ID) is None


@pytest.mark.asyncio
async def test_exists_by_id_uses_single_key_lookup(tenant_collection):
    tenant_collection.count_documents = AsyncMock(return_value=1)
    repo = PlatformTenantRepository(tenant_collection)
    assert await repo.exists_by_id(TENANT_A_ID) is True
    tenant_collection.count_documents.assert_awaited_once()
    assert tenant_collection.count_documents.await_args[0][0] == {"_id": TENANT_A_ID}


@pytest.mark.asyncio
async def test_save_raises_when_not_found(tenant_collection):
    tenant_collection.update_one = AsyncMock(return_value=MagicMock(matched_count=0))
    repo = PlatformTenantRepository(tenant_collection)
    tenant = Tenant.create(
        legal_name="L",
        display_name="D",
        tenant_id=TENANT_A_ID,
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )
    with pytest.raises(OrganizationEntityNotFoundError):
        await repo.save(tenant)


def test_platform_repository_has_no_global_list_method():
    assert not hasattr(PlatformTenantRepository, "list_all")
    assert not hasattr(PlatformTenantRepository, "list")


def test_platform_repository_is_separate_from_operational_scoped():
    from gym_erp_api.infrastructure.mongo.scoped_repository import TenantScopedRepository

    assert PlatformTenantRepository is not TenantScopedRepository
