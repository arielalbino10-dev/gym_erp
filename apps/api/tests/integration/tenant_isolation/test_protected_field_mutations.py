"""Rechazo de alteraciones de tenant_id y branch_id en updates."""

import pytest

from gym_erp_api.shared_kernel.exceptions import TenantScopeError

pytestmark = [
    pytest.mark.integration,
    pytest.mark.tenant_isolation,
    pytest.mark.asyncio(loop_scope="session"),
]


async def test_update_rejects_tenant_id_change(repo_titan, seeded_member_docs):
    titan_id = seeded_member_docs["titan_id"]
    with pytest.raises(TenantScopeError):
        await repo_titan.update_one(
            {"_id": titan_id},
            {"$set": {"tenant_id": "00000000-0000-4000-8000-000000000099"}},
        )


async def test_update_rejects_branch_id_change(repo_titan, seeded_member_docs):
    titan_id = seeded_member_docs["titan_id"]
    with pytest.raises(TenantScopeError):
        await repo_titan.update_one(
            {"_id": titan_id},
            {"$set": {"branch_id": "aa0e8400-e29b-41d4-a716-446655440031"}},
        )
