"""Round-trip de persistencia organization contra MongoDB de prueba (H1-D.2.2)."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from gym_erp_api.modules.organization.domain.branch import Branch
from gym_erp_api.modules.organization.domain.enums import TenantStatus
from gym_erp_api.modules.organization.domain.tenant import Tenant
from gym_erp_api.modules.organization.domain.value_objects import BranchAddress
from gym_erp_api.shared_kernel.identifiers import is_valid_uuid_v4, new_uuid
from tests.support.tenant_fixtures import TENANT_A_ID, USER_A_ID

pytestmark = [
    pytest.mark.integration,
    pytest.mark.organization_persistence,
    pytest.mark.asyncio(loop_scope="session"),
]


async def test_tenant_round_trip_via_platform_repository(organization_platform_tenant_repository):
    moment = datetime(2026, 4, 1, 14, 30, tzinfo=UTC)
    tenant_id = new_uuid()
    tenant = Tenant.create(
        legal_name="Round Trip Legal SA",
        display_name="RoundTrip Gym",
        tenant_id=tenant_id,
        commercial_email="ops@roundtrip.test",
        created_by_user_id=USER_A_ID,
        now=moment,
    ).transition_status(TenantStatus.ACTIVE, now=moment)

    repo = organization_platform_tenant_repository
    await repo.insert(tenant)
    assert await repo.exists_by_id(tenant_id) is True

    restored = await repo.get_by_id(tenant_id)
    assert restored is not None
    assert restored == tenant
    assert restored.created_at.tzinfo is not None
    assert restored.updated_at.tzinfo is not None
    assert restored.created_at.astimezone(UTC) == moment
    assert is_valid_uuid_v4(restored.tenant_id)
    assert restored.commercial_email_normalized == "ops@roundtrip.test"


async def test_branch_round_trip_via_operational_repository(organization_branch_repository):
    moment = datetime(2026, 4, 2, 9, 0, tzinfo=UTC)
    branch = Branch.create(
        tenant_id=TENANT_A_ID,
        name="Persistencia Centro",
        code="persist-centro",
        address=BranchAddress.create(line1="Calle Test 1", city="CDMX"),
        created_by_user_id=USER_A_ID,
        now=moment,
    )

    repo = organization_branch_repository
    await repo.insert(branch)

    restored = await repo.get_by_id(branch.branch_id)
    assert restored is not None
    assert restored.branch_id == branch.branch_id
    assert restored.tenant_id == TENANT_A_ID
    assert restored.name == "Persistencia Centro"
    assert restored.code == "PERSIST-CENTRO"
    assert restored.created_at.tzinfo is not None
    assert restored.address is not None
    assert restored.address.city == "CDMX"

    listed = await repo.list_branches()
    assert len(listed) == 1
    assert listed[0].branch_id == branch.branch_id


async def test_branch_save_preserves_immutable_ids_and_updates_name(
    organization_branch_repository,
):
    moment = datetime(2026, 4, 3, 11, 0, tzinfo=UTC)
    branch = Branch.create(
        tenant_id=TENANT_A_ID,
        name="Nombre Original",
        now=moment,
    )
    repo = organization_branch_repository
    await repo.insert(branch)

    updated_moment = datetime(2026, 4, 3, 12, 0, tzinfo=UTC)
    to_save = replace(branch, name="Nombre Actualizado", updated_at=updated_moment)
    await repo.save(to_save)

    restored = await repo.get_by_id(branch.branch_id)
    assert restored is not None
    assert restored.name == "Nombre Actualizado"
    assert restored.branch_id == branch.branch_id
    assert restored.tenant_id == TENANT_A_ID
    assert restored.updated_at.astimezone(UTC) == updated_moment
