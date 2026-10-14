"""T-03, T-04, T-09: mutaciones cruzadas y update_many acotado."""

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.tenant_isolation,
    pytest.mark.asyncio(loop_scope="session"),
]


async def test_t03_cross_tenant_update_does_not_modify_other_tenant(
    repo_titan, repo_olympus, isolation_collection, seeded_member_docs
):
    olympus_id = seeded_member_docs["olympus_id"]
    result = await repo_titan.update_one(
        {"_id": olympus_id},
        {"$set": {"display_name": "Hacked"}},
    )
    assert result.matched_count == 0
    assert result.modified_count == 0
    untouched = await isolation_collection.find_one({"_id": olympus_id})
    assert untouched is not None
    assert untouched["display_name"] == "Olympus Member"


async def test_t04_cross_tenant_delete_leaves_other_tenant_intact(
    repo_titan, isolation_collection, seeded_member_docs
):
    olympus_id = seeded_member_docs["olympus_id"]
    result = await repo_titan.delete_one({"_id": olympus_id})
    assert result.deleted_count == 0
    assert await isolation_collection.find_one({"_id": olympus_id}) is not None


async def test_t09_update_many_only_affects_own_tenant(
    repo_titan, isolation_collection, seeded_member_docs
):
    titan_id = seeded_member_docs["titan_id"]
    await isolation_collection.insert_one(
        {
            "_id": "doc-titan-002",
            "tenant_id": repo_titan.context.tenant_id,
            "email_normalized": "titan.second@example.test",
            "display_name": "Titan Two",
            "status": "active",
            "branch_id": "990e8400-e29b-41d4-a716-446655440030",
            "member_code": "T-002",
        }
    )
    result = await repo_titan.update_many({"status": "active"}, {"$set": {"flag": True}})
    assert result.matched_count == 2
    olympus = await isolation_collection.find_one({"_id": seeded_member_docs["olympus_id"]})
    assert olympus is not None
    assert "flag" not in olympus
    titan = await isolation_collection.find_one({"_id": titan_id})
    assert titan is not None
    assert titan.get("flag") is True
