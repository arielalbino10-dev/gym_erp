"""Índices compuestos y parciales en colección efímera."""

import pytest
from pymongo.errors import DuplicateKeyError

pytestmark = [
    pytest.mark.integration,
    pytest.mark.tenant_isolation,
    pytest.mark.asyncio(loop_scope="session"),
]


async def test_partial_unique_index_active_member_code_per_branch(repo_titan):
    base = {
        "email_normalized": "partial.a@example.test",
        "display_name": "Partial A",
        "status": "active",
        "branch_id": "990e8400-e29b-41d4-a716-446655440030",
        "member_code": "T-PARTIAL-1",
    }
    await repo_titan.insert_one(dict(base))
    base["email_normalized"] = "partial.b@example.test"
    with pytest.raises(DuplicateKeyError):
        await repo_titan.insert_one(base)


async def test_partial_unique_allows_same_code_when_not_active(repo_titan):
    branch = "990e8400-e29b-41d4-a716-446655440030"
    code = "T-PARTIAL-INACTIVE"
    await repo_titan.insert_one(
        {
            "email_normalized": "inactive.a@example.test",
            "display_name": "Inactive A",
            "status": "active",
            "branch_id": branch,
            "member_code": code,
        }
    )
    await repo_titan.insert_one(
        {
            "email_normalized": "inactive.b@example.test",
            "display_name": "Inactive B",
            "status": "inactive",
            "branch_id": branch,
            "member_code": code,
        }
    )
