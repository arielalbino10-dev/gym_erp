"""Anti-escalada para futuros grants de roles gym (sin API pública en H2-C.4)."""

from __future__ import annotations

from gym_erp_api.modules.access.application.authorization.role_permission_matrix import (
    effective_permissions_for_roles,
)
from gym_erp_api.modules.access.application.errors import PermissionDeniedError
from gym_erp_api.modules.access.domain.enums import GymRole
from gym_erp_api.modules.access.domain.gym_permission import GymPermission


def roles_grantable_by_actor(actor_roles: frozenset[GymRole]) -> frozenset[GymRole]:
    """Roles que el actor puede asignar a otros miembros (nunca más privilegio que el propio)."""
    if GymRole.GYM_OWNER in actor_roles:
        return frozenset(GymRole)
    if GymRole.GYM_ADMIN in actor_roles:
        return frozenset({GymRole.GYM_ADMIN, GymRole.BRANCH_ADMIN})
    return frozenset()


def validate_role_grant(
    *,
    actor_roles: frozenset[GymRole],
    proposed_roles: frozenset[GymRole],
    target_membership_id: str,
    actor_membership_id: str,
) -> None:
    """Impide escalada branch_admin→owner, gym_admin→owner y auto-privilegio no autorizado."""
    if not proposed_roles:
        raise PermissionDeniedError("Debe especificarse al menos un rol gym.")
    grantable = roles_grantable_by_actor(actor_roles)
    illegal = proposed_roles - grantable
    if illegal:
        raise PermissionDeniedError("No puede asignar roles con mayor privilegio que el suyo.")
    if target_membership_id == actor_membership_id:
        if proposed_roles != actor_roles:
            raise PermissionDeniedError("No puede modificar sus propios roles sin autorización.")
    actor_perms = effective_permissions_for_roles(actor_roles)
    if GymPermission.TENANT_ROLES_MANAGE not in actor_perms:
        raise PermissionDeniedError("No tiene permiso para gestionar roles.")


def validate_permission_grant_via_roles(
    *,
    actor_roles: frozenset[GymRole],
    proposed_roles: frozenset[GymRole],
) -> None:
    """El actor no puede conferir permisos (vía roles) que él mismo no posee."""
    actor_perms = effective_permissions_for_roles(actor_roles)
    target_perms = effective_permissions_for_roles(proposed_roles)
    if not target_perms.issubset(actor_perms):
        raise PermissionDeniedError("No puede conceder permisos que no posee.")
