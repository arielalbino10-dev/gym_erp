"""Matriz estática rol → permisos (MVP H2-C.4)."""

from __future__ import annotations

from gym_erp_api.modules.access.domain.enums import GymRole
from gym_erp_api.modules.access.domain.gym_permission import GymPermission

_OWNER_PERMISSIONS: frozenset[GymPermission] = frozenset(
    {
        GymPermission.BRANCHES_READ,
        GymPermission.BRANCHES_CREATE,
        GymPermission.BRANCHES_UPDATE,
        GymPermission.BRANCHES_DEACTIVATE,
        GymPermission.STAFF_READ,
        GymPermission.TENANT_ROLES_MANAGE,
    }
)

_ADMIN_PERMISSIONS: frozenset[GymPermission] = frozenset(
    {
        GymPermission.BRANCHES_READ,
        GymPermission.BRANCHES_CREATE,
        GymPermission.BRANCHES_UPDATE,
        GymPermission.STAFF_READ,
        GymPermission.TENANT_ROLES_MANAGE,
    }
)

_BRANCH_ADMIN_PERMISSIONS: frozenset[GymPermission] = frozenset(
    {
        GymPermission.BRANCHES_READ,
        GymPermission.BRANCHES_UPDATE,
        GymPermission.STAFF_READ,
    }
)

ROLE_PERMISSION_MATRIX: dict[GymRole, frozenset[GymPermission]] = {
    GymRole.GYM_OWNER: _OWNER_PERMISSIONS,
    GymRole.GYM_ADMIN: _ADMIN_PERMISSIONS,
    GymRole.BRANCH_ADMIN: _BRANCH_ADMIN_PERMISSIONS,
}

PERMISSIONS_REQUIRING_BRANCH_TARGET_FOR_EXPLICIT_SCOPE: frozenset[GymPermission] = frozenset(
    {
        GymPermission.BRANCHES_READ,
        GymPermission.BRANCHES_UPDATE,
        GymPermission.STAFF_READ,
    }
)


def effective_permissions_for_roles(roles: frozenset[GymRole]) -> frozenset[GymPermission]:
    granted: set[GymPermission] = set()
    for role in roles:
        granted.update(ROLE_PERMISSION_MATRIX.get(role, frozenset()))
    return frozenset(granted)
