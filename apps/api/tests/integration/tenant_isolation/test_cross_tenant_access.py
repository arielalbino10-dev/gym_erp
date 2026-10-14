"""T-01, T-02: lectura y listados aislados entre Titan Gym y Olympus Gym."""

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.tenant_isolation,
    pytest.mark.asyncio(loop_scope="session"),
]


async def test_t01_cross_tenant_find_by_id_returns_none(repo_titan, seeded_member_docs):
    olympus_id = seeded_member_docs["olympus_id"]
    doc = await repo_titan.find_one({"_id": olympus_id})
    assert doc is None


async def test_t02_listing_only_returns_own_tenant(repo_titan, seeded_member_docs):
    count = await repo_titan.count_documents({})
    assert count == 1
    cursor = repo_titan.find({})
    rows = [doc async for doc in cursor]
    assert len(rows) == 1
    assert rows[0]["_id"] == seeded_member_docs["titan_id"]
    assert rows[0]["tenant_id"] == repo_titan.context.tenant_id
