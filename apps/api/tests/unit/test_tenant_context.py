import pytest

from gym_erp_api.shared_kernel.exceptions import InvalidTenantContextError
from gym_erp_api.shared_kernel.tenant_context import TenantContext
from tests.support.tenant_fixtures import (
    BRANCH_X_ID,
    MEMBERSHIP_A_ID,
    TENANT_A_ID,
    TENANT_B_ID,
    USER_A_ID,
    make_context_tenant_a,
)


def test_tenant_context_is_immutable():
    ctx = make_context_tenant_a()
    with pytest.raises(AttributeError):
        ctx.tenant_id = TENANT_B_ID  # type: ignore[misc]


def test_tenant_context_rejects_invalid_uuid():
    with pytest.raises(InvalidTenantContextError):
        TenantContext(
            tenant_id="bad",
            user_id=USER_A_ID,
            membership_id=MEMBERSHIP_A_ID,
        )


def test_tenant_context_validates_branch_ids():
    with pytest.raises(InvalidTenantContextError):
        TenantContext(
            tenant_id=TENANT_A_ID,
            user_id=USER_A_ID,
            membership_id=MEMBERSHIP_A_ID,
            allowed_branch_ids=frozenset({BRANCH_X_ID, "invalid"}),
        )
