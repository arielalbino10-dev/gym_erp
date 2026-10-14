"""T-11: restricciones por sucursal (Titan Gym, branch X)."""

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.tenant_isolation,
    pytest.mark.asyncio(loop_scope="session"),
]


async def test_t11_branch_scoped_list_excludes_other_branch(
    repo_titan_branch_x, seeded_member_docs
):
    count = await repo_titan_branch_x.count_documents({})
    assert count == 1
    doc = await repo_titan_branch_x.find_one({"_id": seeded_member_docs["titan_id"]})
    assert doc is not None


async def test_t11_branch_scoped_cannot_read_olympus_branch_doc(
    repo_titan_branch_x, seeded_member_docs
):
    olympus_id = seeded_member_docs["olympus_id"]
    assert await repo_titan_branch_x.find_one({"_id": olympus_id}) is None
