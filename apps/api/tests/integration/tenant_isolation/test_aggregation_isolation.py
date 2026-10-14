"""T-08: agregaciones con pipeline acotado al tenant."""

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.tenant_isolation,
    pytest.mark.asyncio(loop_scope="session"),
]


async def test_t08_aggregation_only_counts_own_tenant(repo_titan, seeded_member_docs):
    pipeline = [{"$group": {"_id": "$status", "total": {"$sum": 1}}}]
    cursor = await repo_titan.aggregate(pipeline)
    rows = [row async for row in cursor]
    assert len(rows) == 1
    assert rows[0]["_id"] == "active"
    assert rows[0]["total"] == 1
