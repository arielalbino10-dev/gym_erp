"""delete_many acotado al tenant."""

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.tenant_isolation,
    pytest.mark.asyncio(loop_scope="session"),
]


async def test_delete_many_does_not_remove_other_tenant(
    repo_titan, isolation_collection, seeded_member_docs
):
    result = await repo_titan.delete_many({"status": "active"})
    assert result.deleted_count == 1
    olympus_id = seeded_member_docs["olympus_id"]
    assert await isolation_collection.find_one({"_id": olympus_id}) is not None
