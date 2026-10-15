import pytest

from gym_erp_api.modules.organization.application.authorization.tenant_member import (
    TenantMemberAccess,
)
from gym_erp_api.modules.organization.application.errors import (
    BranchAccessDeniedApplicationError,
    TenantAccessDeniedApplicationError,
)
from gym_erp_api.shared_kernel.exceptions import InvalidTenantContextError
from gym_erp_api.shared_kernel.tenant_context import TenantContext
from tests.support.tenant_fixtures import (
    BRANCH_X_ID,
    BRANCH_Y_ID,
    TENANT_A_ID,
    TENANT_B_ID,
    make_context_tenant_a,
)


def test_matching_tenant_passes():
    access = TenantMemberAccess.bind(make_context_tenant_a())
    access.require_matching_tenant(TENANT_A_ID)


def test_cross_tenant_access_denied():
    access = TenantMemberAccess.bind(make_context_tenant_a())
    with pytest.raises(TenantAccessDeniedApplicationError):
        access.require_matching_tenant(TENANT_B_ID)


def test_branch_in_scope_when_unrestricted():
    access = TenantMemberAccess.bind(make_context_tenant_a())
    access.require_branch_in_scope(BRANCH_Y_ID)


def test_branch_out_of_scope_denied():
    access = TenantMemberAccess.bind(
        make_context_tenant_a(allowed_branch_ids=frozenset({BRANCH_X_ID}))
    )
    access.require_branch_in_scope(BRANCH_X_ID)
    with pytest.raises(BranchAccessDeniedApplicationError):
        access.require_branch_in_scope(BRANCH_Y_ID)


def test_filter_branch_ids_respects_scope():
    access = TenantMemberAccess.bind(
        make_context_tenant_a(allowed_branch_ids=frozenset({BRANCH_X_ID}))
    )
    filtered = access.filter_branch_ids(frozenset({BRANCH_X_ID, BRANCH_Y_ID}))
    assert filtered == frozenset({BRANCH_X_ID})


def test_invalid_context_rejected_at_construction():
    with pytest.raises(InvalidTenantContextError):
        TenantContext(
            tenant_id="not-a-uuid",
            user_id="770e8400-e29b-41d4-a716-446655440010",
            membership_id="880e8400-e29b-41d4-a716-446655440020",
        )


def test_application_layer_has_no_fastapi_imports():
    from pathlib import Path

    app_root = (
        Path(__file__).resolve().parents[4] / "src/gym_erp_api/modules/organization/application"
    )
    for path in app_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        assert "fastapi" not in text
        assert "depends(" not in text
