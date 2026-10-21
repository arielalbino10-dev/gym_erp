"""GymAuthorizationService — permisos y alcance (H2-C.4)."""

from __future__ import annotations

import pytest

from gym_erp_api.modules.access.application.authorization.gym_authorization_service import (
    GymAuthorizationService,
)
from gym_erp_api.modules.access.application.authorization.trusted_gym_authorization import (
    TrustedGymAuthorizationContext,
)
from gym_erp_api.modules.access.application.errors import PermissionDeniedError
from gym_erp_api.modules.access.domain.enums import GymRole
from gym_erp_api.modules.access.domain.gym_permission import GymPermission
from tests.support.tenant_fixtures import (
    BRANCH_X_ID,
    BRANCH_Y_ID,
    MEMBERSHIP_A_ID,
    TENANT_A_ID,
    USER_A_ID,
)

_SVC = GymAuthorizationService()


def _auth(
    *,
    roles: frozenset[GymRole],
    allowed: frozenset[str] | None,
) -> TrustedGymAuthorizationContext:
    return TrustedGymAuthorizationContext(
        user_id=USER_A_ID,
        tenant_id=TENANT_A_ID,
        membership_id=MEMBERSHIP_A_ID,
        authz_epoch=1,
        gym_roles=roles,
        allowed_branch_ids=allowed,
    )


def test_owner_all_branches_without_branch_id():
    auth = _auth(roles=frozenset({GymRole.GYM_OWNER}), allowed=None)
    _SVC.require_permission(auth=auth, permission=GymPermission.BRANCHES_READ)


def test_branch_admin_explicit_allows_list_operation():
    auth = _auth(
        roles=frozenset({GymRole.BRANCH_ADMIN}),
        allowed=frozenset({BRANCH_X_ID}),
    )
    _SVC.require_permission(
        auth=auth,
        permission=GymPermission.BRANCHES_READ,
        list_operation=True,
    )


def test_branch_admin_explicit_requires_branch_id():
    auth = _auth(
        roles=frozenset({GymRole.BRANCH_ADMIN}),
        allowed=frozenset({BRANCH_X_ID}),
    )
    with pytest.raises(PermissionDeniedError):
        _SVC.require_permission(auth=auth, permission=GymPermission.BRANCHES_READ)


def test_branch_admin_in_scope_branch():
    auth = _auth(
        roles=frozenset({GymRole.BRANCH_ADMIN}),
        allowed=frozenset({BRANCH_X_ID}),
    )
    _SVC.require_permission(
        auth=auth,
        permission=GymPermission.BRANCHES_UPDATE,
        branch_id=BRANCH_X_ID,
    )


def test_branch_admin_out_of_scope_branch():
    auth = _auth(
        roles=frozenset({GymRole.BRANCH_ADMIN}),
        allowed=frozenset({BRANCH_X_ID}),
    )
    with pytest.raises(PermissionDeniedError):
        _SVC.require_permission(
            auth=auth,
            permission=GymPermission.STAFF_READ,
            branch_id=BRANCH_Y_ID,
        )


def test_branch_admin_cannot_create():
    auth = _auth(
        roles=frozenset({GymRole.BRANCH_ADMIN}),
        allowed=frozenset({BRANCH_X_ID}),
    )
    with pytest.raises(PermissionDeniedError):
        _SVC.require_permission(
            auth=auth,
            permission=GymPermission.BRANCHES_CREATE,
            branch_id=BRANCH_X_ID,
        )


def test_wrong_tenant_rejected():
    auth = _auth(roles=frozenset({GymRole.GYM_OWNER}), allowed=None)
    with pytest.raises(PermissionDeniedError):
        _SVC.require_permission(
            auth=auth,
            permission=GymPermission.BRANCHES_READ,
            requested_tenant_id="660e8400-e29b-41d4-a716-446655440002",
        )


def test_unknown_role_string_in_trusted_context():
    with pytest.raises(PermissionDeniedError):
        _SVC.trusted_context_from_resolved(_fake_resolved(roles=frozenset({"not_a_role"})))


def _fake_resolved(*, roles: frozenset[str]):
    from gym_erp_api.modules.access.application.services.tenant_context_factory import (
        ResolvedTenantContext,
    )
    from gym_erp_api.shared_kernel.tenant_context import TenantContext

    return ResolvedTenantContext(
        context=TenantContext(
            tenant_id=TENANT_A_ID,
            user_id=USER_A_ID,
            membership_id=MEMBERSHIP_A_ID,
            allowed_branch_ids=None,
        ),
        authz_epoch=1,
        gym_roles=roles,
    )
