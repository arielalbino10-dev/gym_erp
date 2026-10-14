"""T-05, T-06, T-10: inserciones con tenant_id confiable e intentos cruzados."""

import pytest
from pymongo.errors import DuplicateKeyError

from gym_erp_api.shared_kernel.exceptions import TenantScopeError
from tests.support.tenant_fixtures import TENANT_B_ID, make_context_tenant_a

pytestmark = [
    pytest.mark.integration,
    pytest.mark.tenant_isolation,
    pytest.mark.asyncio(loop_scope="session"),
]


async def test_t05_same_email_allowed_across_tenants(repo_titan, repo_olympus):
    email = "shared.alias@example.test"
    await repo_titan.insert_one(
        {
            "email_normalized": email,
            "display_name": "Titan Shared Email",
            "status": "active",
            "member_code": "T-SHARED",
            "branch_id": "990e8400-e29b-41d4-a716-446655440030",
        }
    )
    await repo_olympus.insert_one(
        {
            "email_normalized": email,
            "display_name": "Olympus Shared Email",
            "status": "active",
            "member_code": "O-SHARED",
            "branch_id": "aa0e8400-e29b-41d4-a716-446655440031",
        }
    )


async def test_t06_duplicate_email_within_tenant_raises_duplicate_key(repo_titan):
    email = "dup.titan@example.test"
    payload = {
        "email_normalized": email,
        "display_name": "First",
        "status": "active",
        "member_code": "T-DUP-1",
        "branch_id": "990e8400-e29b-41d4-a716-446655440030",
    }
    await repo_titan.insert_one(dict(payload))
    payload["member_code"] = "T-DUP-2"
    with pytest.raises(DuplicateKeyError):
        await repo_titan.insert_one(payload)


async def test_t10_foreign_tenant_id_in_body_is_rejected(repo_titan):
    with pytest.raises(TenantScopeError):
        await repo_titan.insert_one(
            {
                "tenant_id": TENANT_B_ID,
                "email_normalized": "override.attempt@example.test",
                "display_name": "Override Attempt",
                "status": "active",
                "member_code": "T-OVERRIDE",
                "branch_id": "990e8400-e29b-41d4-a716-446655440030",
            }
        )


async def test_insert_without_tenant_id_uses_trusted_context(repo_titan, isolation_collection):
    ctx = make_context_tenant_a()
    await repo_titan.insert_one(
        {
            "email_normalized": "trusted.tenant@example.test",
            "display_name": "Trusted Tenant",
            "status": "active",
            "member_code": "T-TRUST",
            "branch_id": "990e8400-e29b-41d4-a716-446655440030",
        }
    )
    stored = await isolation_collection.find_one(
        {"email_normalized": "trusted.tenant@example.test"}
    )
    assert stored is not None
    assert stored["tenant_id"] == ctx.tenant_id


async def test_insert_rejects_conflicting_tenant_id_in_document(repo_olympus):
    with pytest.raises(TenantScopeError):
        await repo_olympus.insert_one(
            {
                "tenant_id": make_context_tenant_a().tenant_id,
                "email_normalized": "conflict@example.test",
                "display_name": "Conflict",
                "status": "active",
                "member_code": "O-CONFLICT",
                "branch_id": "aa0e8400-e29b-41d4-a716-446655440031",
            }
        )
