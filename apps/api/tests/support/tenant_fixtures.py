"""Fixtures de tenant solo para tests (no código productivo)."""

from gym_erp_api.shared_kernel.tenant_context import TenantContext

TENANT_A_ID = "550e8400-e29b-41d4-a716-446655440001"
TENANT_B_ID = "660e8400-e29b-41d4-a716-446655440002"
USER_A_ID = "770e8400-e29b-41d4-a716-446655440010"
MEMBERSHIP_A_ID = "880e8400-e29b-41d4-a716-446655440020"
BRANCH_X_ID = "990e8400-e29b-41d4-a716-446655440030"
BRANCH_Y_ID = "aa0e8400-e29b-41d4-a716-446655440031"


def make_context_tenant_a(
    *,
    allowed_branch_ids: frozenset[str] | None = None,
) -> TenantContext:
    return TenantContext(
        tenant_id=TENANT_A_ID,
        user_id=USER_A_ID,
        membership_id=MEMBERSHIP_A_ID,
        allowed_branch_ids=allowed_branch_ids,
    )


def make_context_tenant_b() -> TenantContext:
    return TenantContext(
        tenant_id=TENANT_B_ID,
        user_id="bb0e8400-e29b-41d4-a716-446655440011",
        membership_id="cc0e8400-e29b-41d4-a716-446655440021",
    )
