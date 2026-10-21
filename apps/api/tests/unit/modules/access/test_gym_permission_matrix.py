"""Matriz rol → permiso (H2-C.4)."""

from __future__ import annotations

from gym_erp_api.modules.access.application.authorization.role_permission_matrix import (
    effective_permissions_for_roles,
)
from gym_erp_api.modules.access.domain.enums import GymRole
from gym_erp_api.modules.access.domain.gym_permission import GymPermission


def test_gym_owner_has_full_mvp_catalog():
    perms = effective_permissions_for_roles(frozenset({GymRole.GYM_OWNER}))
    assert GymPermission.BRANCHES_DEACTIVATE in perms
    assert GymPermission.TENANT_ROLES_MANAGE in perms
    assert len(perms) == 6


def test_gym_admin_lacks_deactivate():
    perms = effective_permissions_for_roles(frozenset({GymRole.GYM_ADMIN}))
    assert GymPermission.BRANCHES_CREATE in perms
    assert GymPermission.BRANCHES_DEACTIVATE not in perms
    assert GymPermission.TENANT_ROLES_MANAGE in perms


def test_branch_admin_minimal_branch_ops():
    perms = effective_permissions_for_roles(frozenset({GymRole.BRANCH_ADMIN}))
    assert perms == frozenset(
        {
            GymPermission.BRANCHES_READ,
            GymPermission.BRANCHES_UPDATE,
            GymPermission.STAFF_READ,
        }
    )


def test_multiple_roles_union():
    perms = effective_permissions_for_roles(
        frozenset({GymRole.BRANCH_ADMIN, GymRole.GYM_ADMIN}),
    )
    assert GymPermission.BRANCHES_CREATE in perms
    assert GymPermission.BRANCHES_DEACTIVATE not in perms
